import contextlib
import logging
import json
import os
import asyncio
import shutil
import aiofiles
import httpx
import zipfile
import socket
import re
from datetime import datetime, timezone
from packaging import version
from typing import BinaryIO, Any


class McServerRunnerError(Exception):
    pass


class McServerConfiguratorError(Exception):
    pass


class McServerDownloaderError(Exception):
    pass


__all__ = [
    "McServerRunnerError",
    "McServerConfiguratorError",
    "McServerDownloaderError",
    "McServerRunnerEvent",
    "McServerRunner",
    "McServerConfigurator",
    "McServerDownloader",
    "McServerPropertiesGenerator",
]

logger = logging.getLogger(__name__)


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
    def __init__(
        self,
        directory: str,
        server_config: dict,
        *,
        events_queue: asyncio.Queue | None = None,
    ) -> None:

        self._directory: str = directory
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
        evt = McServerRunnerEvent("start")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    async def stop_server(self) -> bool:
        evt = McServerRunnerEvent("stop")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    async def restart_server(self) -> bool:
        evt = McServerRunnerEvent("restart")

        await self._tasks_queue.put(evt)
        return await asyncio.wait_for(evt.reply, timeout=60)

    def get_server_status(self) -> str:
        if self._server_stats.get("started") and self._server_stats.get("initialized"):
            return "running"
        elif self._server_stats.get("started") and not self._server_stats.get("initialized"):
            return "starting"

        return "stopped"

    def get_server_stats(self) -> dict:
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

        # check if server.jar exists
        jar_path = os.path.join(self._directory, "server.jar")
        if not os.path.exists(jar_path):
            raise McServerRunnerError("server.jar not found")

        server_params = await self._get_server_params()
        cmd = self._gen_start_command(server_params=server_params)

        logger.info(f"Starting MC server with java bin '{cmd[0]}'")
        logger.debug(cmd)

        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self._directory,
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

    async def _get_server_params(self) -> dict:
        args_file = os.path.join(self._directory, "server_params.json")

        if not os.path.exists(args_file):
            return {}

        async with aiofiles.open(args_file, "r") as f:
            data_raw = await f.read()
            return json.loads(data_raw)

    async def _set_server_stats(self, **kwargs) -> None:
        if not os.path.exists(self._directory):
            raise McServerRunnerError("Workdir does not exist")

        path = os.path.join(self._directory, "server_stats.json")
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
        path = os.path.join(self._directory, "server_stats.json")

        if not os.path.exists(path):
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _is_running(self) -> bool:
        return bool(self._proc) and (self._proc.returncode is None)

    def _gen_start_command(self, *, server_params: dict = {}) -> list[str]:
        if self._server_config.get("java_bin", ""):
            java_bin = self._server_config["java_bin"]
        else:
            java_version = server_params.get("java_version", "")
            java_bin = f"java-{java_version}" if java_version else "java"

        xms = self._server_config.get("java_min_memory", "1024M")
        xmx = self._server_config.get("java_max_memory", "1024M")

        server_args = [*server_params.get("args", []), *(self._server_config.get("server_additional_args", []))]

        cmd = [
            java_bin,
            f"-Xms{xms}",
            f"-Xmx{xmx}",
            *server_args,
            "-jar",
            "server.jar",
            "nogui",
        ]

        return cmd


class McServerConfigurator:
    default_server_ip: str = "0.0.0.0"
    default_server_port: int = 25565
    default_rcon_port: int = 25575

    def __init__(self, directory: str, server_config: dict) -> None:
        self._directory: str = directory
        self._server_config: dict = server_config

    async def create_world_instance(self, world: str, *, world_archive: BinaryIO | None = None) -> None:
        workdir = self._gen_workdir(world)

        if os.path.exists(workdir):
            raise McServerConfiguratorError(f"World instance {world} already exists")

        os.makedirs(workdir)

        await self._accept_eula(workdir)
        await self._link_common_files(workdir)

        if world_archive:
            await self._import_world(workdir, world_archive)

    async def activate_world_instance(
        self,
        world: str,
        *,
        server_version: str,
        server_type: str,
        properties: dict,
    ) -> None:
        workdir = self._gen_workdir(world)

        if not os.path.exists(workdir):
            raise McServerConfiguratorError(f"World instance {world} does not exist")

        downloader = McServerDownloader(workdir)
        properties_generator = McServerPropertiesGenerator(
            workdir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        tasks = [
            asyncio.create_task(
                downloader.download_server(server_version, server_type),
                name="download_server",
            ),
            asyncio.create_task(
                properties_generator.generate(properties),
                name="generate_server_properties",
            ),
            asyncio.create_task(
                self._patch_log4j(workdir, server_version),
                name="patch_log4j",
            ),
        ]

        (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        server_params = {
            "args": [],
            "java_version": self._get_recommended_java(server_version),
        }

        for task in pending:
            logger.warning(f"Task {task.get_name()} is still pending. Cancelling it.")
            task.cancel()

        for task in done:
            if task.exception() is not None:
                raise McServerConfiguratorError(f"Task {task.get_name()} failed with exception: {task.exception()}")

            if task.get_name() == "patch_log4j":
                server_params["args"].extend(task.result())

        await self._write_server_params(workdir, server_params)

        self._link_world_instance_to_current(world)

        logger.info(f"World instance {world} activated successfully")

    async def regen_world_properties(self, world: str, properties: dict) -> None:
        workdir = self._gen_workdir(world)
        properties_generator = McServerPropertiesGenerator(
            workdir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        await properties_generator.generate(properties)

    async def delete_world_instance(self, world: str) -> None:
        workdir = self._gen_workdir(world)

        if not os.path.exists(workdir):
            raise McServerConfiguratorError(f"World instance {world} does not exist")

        shutil.rmtree(workdir)

        logger.info(f"Directory for world instance {world} deleted")

    def get_server_connect_info(self) -> dict:
        info = {}

        display_host = self._server_config.get("display_host")
        display_ip = self._server_config.get("display_ip")
        display_port = self._server_config.get("display_port")

        if display_host:
            info["host"] = display_host
            info["ip"] = socket.gethostbyname(info["host"])

        info["ip"] = self._resolve_wildcard_ip(display_ip or info.get("ip") or self._server_config.get("server_ip", self.default_server_ip))
        info["port"] = display_port or self._server_config.get("server_port", self.default_server_port)

        return info

    def get_rcon_connect_info(self) -> dict:
        info = {}

        info["port"] = self._server_config.get("rcon_port", self.default_rcon_port)
        info["ip"] = self._resolve_wildcard_ip(self._server_config.get("server_ip", self.default_server_ip))

        return info

    async def _import_world(self, workdir: str, world_archive: BinaryIO) -> None:
        logger.info(f"Extracting existing world data archive")

        # unzip archive
        with zipfile.ZipFile(world_archive, "r") as zip_ref:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, zip_ref.extractall, os.path.join(workdir, "world"))

    async def _accept_eula(self, workdir: str) -> None:
        logger.info(f"Accepting EULA")

        eula_file = os.path.join(workdir, "eula.txt")

        async with aiofiles.open(eula_file, "w") as f:
            await f.write("eula=true")

    async def _link_common_files(self, workdir: str) -> None:
        logger.info(f"Linking common files for world instance {workdir}")

        common_files = ["banned-ips.json", "banned-players.json", "ops.json", "usercache.json", "whitelist.json"]

        for file in common_files:
            src = os.path.join(self._directory, file)
            dst = os.path.join(workdir, file)

            if not os.path.exists(src):
                async with aiofiles.open(src, "w") as f:
                    await f.write("[]")

            os.symlink(src, dst)
            logger.info(f"Linked {src} to {dst}")

    # 1.18: Upgrade to 1.18.1, if possible. If not, use the same approach as for 1.17.x:

    # 1.17: Add the following JVM arguments to your startup command line:
    # -Dlog4j2.formatMsgNoLookups=true

    # 1.12-1.16.5: Download this file to the working directory where your server runs. Then add the following JVM arguments to your startup command line:
    # -Dlog4j.configurationFile=log4j2_112-116.xml

    # 1.7-1.11.2: Download this file to the working directory where your server runs. Then add the following JVM arguments to your  startup command line:
    # -Dlog4j.configurationFile=log4j2_17-111.xml

    # Versions below 1.7 are not affected
    async def _patch_log4j(self, workdir: str, server_version: str) -> list[str]:
        logger.info(f"Patching Log4j for server version {server_version}")

        v17_111_patch = "https://launcher.mojang.com/v1/objects/4bb89a97a66f350bc9f73b3ca8509632682aea2e/log4j2_17-111.xml"
        v112_116_patch = "https://launcher.mojang.com/v1/objects/02937d122c86ce73319ef9975b58896fc1b491d1/log4j2_112-116.xml"

        v = version.parse(server_version)
        args = []

        if v < version.parse("1.7"):
            pass
        elif v < version.parse("1.12"):
            await self._download_file(v17_111_patch, os.path.join(workdir, "log4j2_17-111.xml"))
            args = ["-Dlog4j.configurationFile=log4j2_17-111.xml"]
        elif v < version.parse("1.17"):
            await self._download_file(v112_116_patch, os.path.join(workdir, "log4j2_112-116.xml"))
            args = ["-Dlog4j.configurationFile=log4j2_112-116.xml"]
        elif v < version.parse("1.18.1"):
            args = ["-Dlog4j2.formatMsgNoLookups=true"]

        return args

    async def _download_file(self, url: str, dest: str) -> None:
        logger.info(f"Downloading {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(dest, "wb") as f:
                await f.write(response.content)

    async def _write_server_params(self, workdir: str, data: dict) -> None:
        logger.info(f"Writing server params")

        info_file = os.path.join(workdir, "server_params.json")

        async with aiofiles.open(info_file, "w") as f:
            await f.write(json.dumps(data))

    def _resolve_wildcard_ip(self, ip: str) -> str:
        if ip not in ("0.0.0.0", ""):
            return ip

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()

        return ip

    def _gen_workdir(self, world: str) -> str:
        return os.path.join(self._directory, world)

    def _link_world_instance_to_current(self, world: str) -> None:
        logger.info(f"Linking world instance {world} to 'current'")

        current_link = self._gen_workdir("current")
        world_instance_path = self._gen_workdir(world)

        if os.path.islink(current_link):
            os.remove(current_link)

        # symlink world instance to "current"
        os.symlink(world_instance_path, current_link)

    def _get_recommended_java(self, server_version: str) -> int:
        v = version.parse(server_version)

        if v >= version.parse("1.21"):
            return 21
        elif v >= version.parse("1.17"):
            return 17
        else:
            return 8


class McServerDownloader:
    def __init__(self, directory: str):
        self._directory: str = directory

    async def download_server(self, server_version: str, server_type: str) -> None:
        logger.info(f"Attempting to download server version {server_version} ({server_type})")

        url = None

        if server_type == "vanilla":
            server_downloader = self.VanillaServerDownloader()
            url = await server_downloader.get_download_url(server_version)
        else:
            raise McServerDownloaderError(f"Unsupported server type: {server_type}")

        await self._download_version(url)

    async def _download_version(self, url: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(os.path.join(self._directory, "server.jar"), "wb") as f:
                await f.write(response.content)

        logger.info(f"Server jar successfully downloaded")

    class VanillaServerDownloader:
        def __init__(self):
            self._versions_index_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

        async def get_download_url(self, server_version: str) -> str:
            logger.info(f"Fetching versions index from {self._versions_index_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(self._versions_index_url)
                response.raise_for_status()
                versions_index = response.json()

            # search for desired version
            version_info = next((v for v in versions_index["versions"] if v["id"] == server_version), None)

            if not version_info:
                raise McServerDownloaderError(f"Server version {server_version} not found")

            version_manifest_url = version_info["url"]

            logger.info(f"Fetching version manifest from {version_manifest_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(version_manifest_url)
                response.raise_for_status()
                manifest = response.json()

            return manifest["downloads"]["server"]["url"]


class McServerPropertiesGenerator:
    properties: dict = {
        "level-seed": {"empty": True},
        "gamemode": {"values": ["survival", "creative", "adventure", "spectator"]},
        "enable-command-block": {"type": "bool"},
        "motd": {"empty": True},
        "pvp": {"type": "bool"},
        "generate-structures": {"type": "bool"},
        "difficulty": {"values": ["peaceful", "easy", "normal", "hard"]},
        "max-players": {"type": "int"},
        "allow-flight": {"type": "bool"},
        "view-distance": {"type": "int"},
        "allow-nether": {"type": "bool"},
        "hide-online-players": {"type": "bool"},
        "simulation-distance": {"type": "int"},
        "force-gamemode": {"type": "bool"},
        "hardcore": {"type": "bool"},
        "white-list": {"type": "bool"},
        "spawn-npcs": {"type": "bool"},
        "spawn-animals": {"type": "bool"},
        "level-type": {"values": ["default", "flat", "large_biomes", "amplified"]},
        "spawn-monsters": {"type": "bool"},
        "enforce-whitelist": {"type": "bool"},
        "rcon.password": {"empty": True},
    }

    level_types: list[str] = ["default", "flat", "large_biomes", "amplified"]

    min_server_version: str = "1.7.10"

    def __init__(self, directory: str, *, server_ip: str, server_port: int, rcon_port: int) -> None:
        self._directory: str = directory
        self._enforced_properties: dict = {
            "server-port": str(server_port),
            "rcon.port": str(rcon_port),
            "server-ip": server_ip,
        }

    async def generate(self, properties: dict) -> None:
        logger.info(f"Generating server.properties")

        self.validate_properties(properties)

        properties_file = os.path.join(self._directory, "server.properties")

        if properties.get("rcon.password"):
            self._enforced_properties["enable-rcon"] = "true"

        async with aiofiles.open(properties_file, "w") as f:
            for key, value in self._enforced_properties.items():
                await f.write(f"{key}={value}\n")

            for key, value in properties.items():
                await f.write(f"{key}={value}\n")

        logger.info(f"server.properties generated successfully")

    @classmethod
    def validate_properties(cls, properties: dict) -> None:
        for key, value in properties.items():
            if key not in cls.properties:
                raise McServerConfiguratorError(f"Unknown property: {key}")

            prop_info = cls.properties[key]

            prop_empty = prop_info.get("empty", False)
            prop_values = prop_info.get("values", [])
            prop_type = prop_info.get("type", "str")

            if not prop_empty and value == "":
                raise McServerConfiguratorError(f"Property '{key}' cannot be empty")

            if prop_values and value not in prop_values:
                raise McServerConfiguratorError(f"Property '{key}' must be one of {prop_values}")

            if prop_type == "int" and not value.isdigit():
                raise McServerConfiguratorError(f"Property '{key}' must be an integer")

            if prop_type == "bool" and value not in ["true", "false"]:
                raise McServerConfiguratorError(f"Property '{key}' must be a boolean")
