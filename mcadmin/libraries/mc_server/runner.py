import contextlib
import logging
import json
import os
import asyncio
import aiofiles
import re
import shlex
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "McServerRunnerError",
    "McServerRunnerEvent",
    "McServerRunner",
]

logger = logging.getLogger(__name__)


class McServerRunnerError(Exception):
    pass


class McServerRunnerEvent:
    def __init__(
        self,
        type: str,
        metadata: dict | None = None,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._type: str = type
        self._metadata: dict | None = metadata
        self._reply: asyncio.Future = (loop or asyncio.get_running_loop()).create_future()

    @property
    def type(self) -> str:
        return self._type

    @property
    def metadata(self) -> dict | None:
        return self._metadata

    @property
    def reply(self) -> asyncio.Future:
        return self._reply


class McServerRunner:
    """Minecraft server runner. Interacts with the Minecraft server process"""

    def __init__(
        self,
        current_dir: str,
        server_config: dict,
        *,
        events_queue: asyncio.Queue | None = None,
    ) -> None:

        self._current_dir: str = current_dir
        self._server_config: dict = server_config
        self._events_queue: asyncio.Queue | None = events_queue

        self._tasks_queue: asyncio.Queue = asyncio.Queue()
        self._server_stats: dict = self._load_server_stats()
        self._proc = None
        self._proc_wait_task = None
        self._proc_stdout_task = None

        self._log_patterns = {
            "initialized": re.compile(r"\bDone \(\d+\.\d+s\)!", re.IGNORECASE),
            "join": re.compile(r"\bjoined the game\b", re.IGNORECASE),
            "leave": re.compile(r"\b(?:left the game|lost connection)\b", re.IGNORECASE),
            "stats": re.compile(r"(?:There are\s+(?P<n1>\d+)\s+of a max of\s+\d+\s+players online:|Players\s*\((?P<n2>\d+)\):)", re.IGNORECASE),
        }

    async def run(self) -> None:
        """Main runner loop. This should be run in a dedicated task."""
        logger.info("Starting MC server runner")

        # publish initial data
        self._publish_event("stats", self.get_server_stats())

        if self._server_stats.get("started"):
            await self._start_server(event="startup")

        try:
            await self._listen_for_events()
        except asyncio.CancelledError:
            try:
                await self._stop_server(event="shutdown")
            finally:
                raise

    async def start_server(self) -> bool:
        """Start the Minecraft server"""
        evt = McServerRunnerEvent("start")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    async def stop_server(self) -> bool:
        """Stop the Minecraft server"""
        evt = McServerRunnerEvent("stop")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    async def restart_server(self) -> bool:
        """Restart the Minecraft server"""
        evt = McServerRunnerEvent("restart")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    def get_server_status(self) -> str:
        """Get the current server status"""
        if self._server_stats.get("started") and self._server_stats.get("initialized"):
            return "running"
        elif self._server_stats.get("started") and not self._server_stats.get("initialized"):
            return "starting"

        return "stopped"

    def get_server_stats(self) -> dict:
        """Get the current server stats"""
        stats = {}

        stats["status"] = self.get_server_status()

        if stats["status"] == "stopped":
            stats["exit_code"] = self._server_stats.get("exit_code")
            return stats

        elif stats["status"] == "starting":
            return stats

        stats["started_at"] = self._server_stats.get("started_at", 0)
        stats["pid"] = self._server_stats.get("pid", 0)
        stats["players"] = self._server_stats.get("players", 0)

        return stats

    async def _listen_for_events(self) -> None:
        while True:
            event_task = asyncio.create_task(self._tasks_queue.get(), name="mc_evt_get")

            tasks = {event_task}

            if self._proc_wait_task:
                tasks.add(self._proc_wait_task)

            (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            if self._proc_wait_task and self._proc_wait_task in done:
                rc = self._proc.returncode if self._proc else 0

                self._proc = None
                self._proc_wait_task = None

                await self._cancel_stdout_reader_task()

                if not event_task.done():
                    # cancel the event task (it will be rescheduled on next loop)
                    event_task.cancel()
                    # wait for the task to finish
                    await asyncio.gather(event_task, return_exceptions=True)

                await self._set_server_stats(
                    started=False,
                    started_at=None,
                    initialized=False,
                    pid=None,
                    players=0,
                    exit_code=rc,
                )

                logger.error(f"Minecraft server exited unexpectedly (code={rc})")
                continue

            event = event_task.result()

            if not isinstance(event, McServerRunnerEvent):
                raise McServerRunnerError("Invalid event type")

            logger.debug(f"Received event: {event.type} with metadata: {event.metadata}")

            try:
                if event.type == "start":
                    if self._is_running():
                        raise McServerRunnerError("Server is already running")
                    else:
                        await self._start_server()
                        event.reply.set_result(True)
                elif event.type == "stop":
                    if not self._is_running():
                        raise McServerRunnerError("Server is not running")
                    else:
                        rc = await self._stop_server()
                        event.reply.set_result(True)
                elif event.type == "restart":
                    if self._is_running():
                        await self._stop_server()
                    await self._start_server()
                    event.reply.set_result({"status": "restarted"})
                else:
                    raise McServerRunnerError(f"Unknown event type: {event.type}")
            except Exception as e:
                logger.error(f"Error handling event {event.type}: {e}")
                event.reply.set_exception(e)

            self._tasks_queue.task_done()

    async def _start_server(self, *, event: str = "") -> None:
        if self._is_running():
            return

        xms = self._server_config.get("java_min_memory", "1024M")
        xmx = self._server_config.get("java_max_memory", "1024M")
        additional_jvm_args = self._server_config.get("server_additional_args", [])

        jvm_args = [
            f"-Xms{xms}",
            f"-Xmx{xmx}",
            *additional_jvm_args
        ]

        env = {
            "MCADMIN_RUNTIME_JVM_ARGS": shlex.join(jvm_args),
        }

        if self._server_config.get("java_bin", ""):
            env["MCADMIN_RUNTIME_JAVA_BIN"] = self._server_config["java_bin"]

        logger.info(f"Starting MC server")

        cmd = ["./mcadmin-start.sh", "nogui"]

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self._current_dir,
            env={**os.environ, **env},
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,  # allow the process to be in a new session so that we can gracefully shutdown the minecraft server
        )

        self._proc_wait_task = asyncio.create_task(self._proc.wait(), name="mc_proc_wait")
        self._proc_stdout_task = asyncio.create_task(self._proc_stdout_reader(), name="mc_proc_stdout")

        if event != "startup":
            started = True
        else:
            started = self._server_stats.get("started", False)

        await self._set_server_stats(
            started=started,
            started_at=datetime.now(timezone.utc).isoformat(),
            initialized=False,
            pid=self._proc.pid,
            players=0,
            exit_code=None,
        )

        logger.info(f"MC server started with PID {self._proc.pid}")

    async def _stop_server(self, *, event: str = "") -> int | None:
        if not self._is_running() or not self._proc:
            return None

        try:
            # prefer graceful shutdown
            logger.info("Sending stop command to MC server...")
            if self._proc.stdin:
                self._proc.stdin.write(b"stop\n")
                await self._proc.stdin.drain()

            # wait a bit for clean exit
            await asyncio.wait_for(self._proc.wait(), timeout=30)
        except asyncio.TimeoutError:
            logger.warning("Graceful stop timed out; terminating MC...")
            self._proc.terminate()
            await self._proc.wait()
        finally:
            rc = self._proc.returncode if self._proc else 0

            self._proc = None
            self._proc_wait_task = None

            await self._cancel_stdout_reader_task()

            if event != "shutdown":
                started = False
            else:
                started = self._server_stats.get("started", False)

            await self._set_server_stats(
                started=started,
                started_at=None,
                initialized=False,
                pid=None,
                players=0,
                exit_code=rc,
            )

        logger.info(f"Minecraft server stopped with exit code {rc}")

        return rc

    async def _proc_stdout_reader(self) -> None:
        while self._proc and self._proc.stdout:
            line = await self._proc.stdout.readline()

            if not line:
                break

            line = line.decode("utf-8", errors="ignore").strip()

            await self._process_server_log(line)

            self._publish_event("logs", line)

    async def _process_server_log(self, line: str) -> None:
        logger.debug(f"MC Log: {line}")

        if self._log_patterns["initialized"].search(line):
            logger.info(f"MC server ready")
            await self._set_server_stats(initialized=True)

        # increment player count if a player joins
        elif self._log_patterns["join"].search(line):
            logger.info(f"Player joined the game")
            await self._set_server_stats(players=self._server_stats.get("players", 0) + 1)

        # decrement player count if a player leaves or looses connection
        elif self._log_patterns["leave"].search(line):
            logger.info(f"Player left the game")
            await self._set_server_stats(players=max(self._server_stats.get("players", 0) - 1, 0))

        # get players count from server stats
        elif match := self._log_patterns["stats"].search(line):
            player_cnt = match.group("n1") or match.group("n2")
            logger.info(f"Player count updated to {player_cnt}")
            await self._set_server_stats(players=int(player_cnt))

        else:
            return

    async def _cancel_stdout_reader_task(self) -> None:
        if not self._proc_stdout_task or self._proc_stdout_task.done():
            return

        # cancel the stdout parser task
        self._proc_stdout_task.cancel()
        # wait for the task to finish
        await asyncio.gather(self._proc_stdout_task, return_exceptions=True)
        self._proc_stdout_task = None

    async def _set_server_stats(self, **kwargs) -> None:
        if not os.path.exists(self._current_dir):
            raise McServerRunnerError("Current directory does not exist")

        path = os.path.join(self._current_dir, "server_stats.json")
        tmp = path + ".tmp"

        self._server_stats.update(kwargs)

        async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
            await f.write(json.dumps(self._server_stats))
        os.replace(tmp, path)

        self._publish_event("stats", self.get_server_stats())

    def _publish_event(self, ev_type: str, data: Any) -> None:
        if not self._events_queue:
            return

        try:
            self._events_queue.put_nowait((ev_type, data))
        except asyncio.QueueFull:
            logger.warning(f"Events queue is full. dropping oldest event")
            with contextlib.suppress(Exception):
                # queue full. Drop the oldest event and add the new one
                self._events_queue.get_nowait()
                self._events_queue.task_done()
                self._events_queue.put_nowait(data)

    def _load_server_stats(self) -> dict:
        path = os.path.join(self._current_dir, "server_stats.json")

        if not os.path.exists(path):
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_running(self) -> bool:
        return bool(self._proc) and (self._proc.returncode is None)
