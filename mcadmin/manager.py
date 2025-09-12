import os
import sys
import logging
import signal
import yaml
import asyncio
from aiohttp import web
from logging.handlers import TimedRotatingFileHandler
from tortoise import Tortoise
from aerich import Command as AerichCommand
from mcadmin.utils.random import random_password
from mcadmin.libraries.cleanup_queue import CleanupQueue
from mcadmin.libraries.di_container import DiContainer
from mcadmin.services.users import UsersService
from mcadmin.services.worlds import WorldsService
from mcadmin.setup_web_server import setup_web_server
from mcadmin.setup_di import setup_di
from mcadmin.exceptions import (
    McServerWebadminRuntimeError,
    ExitSignal,
    SIGHUPSignal,
)

__all__ = ["McServerWebadminManager"]
logger = logging.getLogger(__name__)


class McServerWebadminManager:
    def __init__(
        self,
        *,
        log_file: str = "",
        log_level: str = "",
        config_file: str = "",
        data_directory: str = "",
    ) -> None:
        self._init_logger(log_file, log_level)

        self._data_directory: str = data_directory if data_directory else self._gen_data_directory()
        self._cleanup: CleanupQueue = CleanupQueue()
        self._di: DiContainer = DiContainer()

        setup_di(self._di, config=self._load_config(file=config_file), data_directory=self._data_directory)

    def run(self) -> None:
        self._run_main(self._async_run)

    def _load_config(self, *, file: str = "") -> dict:
        config_files = [
            "/etc/mc-server-webadmin/config.yml",
            "/etc/opt/mc-server-webadmin/config.yml",
            os.path.expanduser("~/.config/mc-server-webadmin/config.yml"),
        ]

        if file:
            config_files = [file]

        file_to_load = None

        for config_file in config_files:
            if os.path.isfile(config_file):
                file_to_load = config_file
                break

        if not file_to_load:
            return {}

        with open(file_to_load, "r") as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise McServerWebadminRuntimeError(f"Failed to parse config file: {e}")

        return config

    def _is_venv(self) -> bool:
        return sys.prefix != getattr(sys, "base_prefix", sys.prefix)

    def _get_pid_filepath(self) -> str:
        if os.getuid() == 0:
            return "/var/run/mc-server-webadmin.pid"
        else:
            return os.path.expanduser("~/.mc-server-webadmin.pid")

    def _gen_data_directory(self) -> str:
        if self._is_venv():
            data_directory = os.path.join(sys.prefix, "var")
        elif os.getuid() == 0:
            data_directory = f"/var/lib/mc-server-webadmin/"
        else:
            data_directory = os.path.expanduser(f"~/.mc-server-webadmin/")

        return data_directory

    def _init_logger(self, log_file: str, log_level: str) -> None:
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        if not log_level in levels:
            log_level = "INFO"

        logger = logging.getLogger()
        logger.setLevel(levels[log_level])

        if log_file:
            directory = os.path.dirname(log_file)

            if not os.path.exists(directory):
                os.makedirs(directory)

            handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=4)
        else:
            handler = logging.StreamHandler()

        handler.setLevel(levels[log_level])

        handler.setFormatter(logging.Formatter(format))

        logger.addHandler(handler)

    def _exit_signal_handler(self) -> None:
        raise ExitSignal

    def _sighup_signal_handler(self) -> None:
        raise SIGHUPSignal

    def _run_main(self, main_task, *args, **kwargs) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.add_signal_handler(signal.SIGTERM, self._exit_signal_handler)
        loop.add_signal_handler(signal.SIGINT, self._exit_signal_handler)
        loop.add_signal_handler(signal.SIGQUIT, self._exit_signal_handler)
        loop.add_signal_handler(signal.SIGHUP, self._sighup_signal_handler)

        try:
            loop.run_until_complete(main_task(*args, **kwargs))
        except SIGHUPSignal as e:
            logger.info("Received SIGHUP signal")
        except ExitSignal as e:
            logger.info("Received termination signal")
        except Exception as e:
            logger.exception(e)
        finally:
            if self._cleanup.has_jobs:
                try:
                    logger.info("Running cleanup jobs")
                    loop.run_until_complete(self._cleanup.consume_all())
                except Exception as e:
                    logger.exception(f"Error during cleanup: {e}")

            try:
                self._cancel_tasks(loop)
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:

                asyncio.set_event_loop(None)
                loop.close()

    def _cancel_tasks(self, loop: asyncio.AbstractEventLoop) -> None:
        tasks = asyncio.all_tasks(loop=loop)

        if not tasks:
            return

        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        for task in tasks:
            if task.cancelled():
                continue

            if task.exception() is not None:
                loop.call_exception_handler(
                    {
                        "message": "Unhandled exception during task cancellation",
                        "exception": task.exception(),
                        "task": task,
                    }
                )

    async def _async_run(self):
        tasks = []

        pid = str(os.getpid())
        pid_filepath: str = self._get_pid_filepath()

        if os.path.isfile(pid_filepath):
            logger.error("Service is already running")
            return

        with open(pid_filepath, 'w') as f:
            f.write(pid)

        self._cleanup.push('remove_service_pid', os.remove, pid_filepath)

        # ensure data directory exists
        if not os.path.exists(self._data_directory):
            logger.info(f"Creating data directory at '{self._data_directory}'")
            os.makedirs(self._data_directory)

        logger.info("Initializing database")

        await self._init_db()
        await self._ensure_admin_user()
        await self._ensure_rcon_password()

        logger.info("Starting MC Admin tasks")

        tasks.append(asyncio.create_task(self._async_run_webserver(), name="web_server"))
        tasks.append(asyncio.create_task(self._async_run_mc_server_runner(), name="mc_server_runner"))

        (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        logger.info("Task(s) exited")

        for task in done:
            if task.exception() is not None:
                logger.exception(f"Task {task.get_name()} failed with exception: {task.exception()}")

        for task in pending:
            logger.warning(f"Task {task.get_name()} is still pending. Cancelling it.")
            task.cancel()

    async def _async_run_webserver(self):
        logger.info("Starting webserver")

        server = web.Application()

        server["di"] = self._di

        setup_web_server(server)

        runner = web.AppRunner(server, access_log=None)

        await runner.setup()

        self._cleanup.push("webserver_cleanup_runner", runner.cleanup)
        self._cleanup.push("webserver_log_shutdown", logger.info, "Webserver is shutting down")

        site = web.TCPSite(
            runner,
            str(self._di.web_server_config.get('ip')),
            self._di.web_server_config.get('port'),
        )

        await site.start()

        logger.info(f"Webserver listening on {self._di.web_server_config.get('ip')}:{self._di.web_server_config.get('port')}")

        while True:
            await asyncio.sleep(3600)

    async def _async_run_mc_server_runner(self):
        await self._di.mc_server_runner.run()

    async def _init_db(self):
        db_path = os.path.join(self._data_directory, "app.db")

        config = {
            "connections": {"default": f"sqlite://{db_path}"},
            "apps": {
                "models": {
                    "models": ["mcadmin.models", "aerich.models"],
                    "default_connection": "default",
                }
            },
        }

        migrations_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")

        await Tortoise.init(config=config)
        cmd = AerichCommand(tortoise_config=config, app="models", location=migrations_location)

        await cmd.init()
        # await cmd.init_db(safe=True)
        # await cmd.migrate()
        # await cmd.migrate(empty=True)
        await cmd.upgrade()

        self._cleanup.push("db_close", Tortoise.close_connections)

    async def _ensure_admin_user(self):
        users_service: UsersService = self._di.users_service
        username = "admin"
        admin_user = await users_service.get_user(username=username)

        if admin_user:
            return

        password = random_password(24)

        await users_service.create_user(username=username, password=password, role="admin")

        logger.info(f"Created default admin user. Username: {username}, Password: {password}")

    async def _ensure_rcon_password(self):
        worlds_service: WorldsService = self._di.worlds_service
        rcon_pass = await worlds_service.get_property("rcon.password")

        if rcon_pass:
            return

        logger.info("RCON password is not set. Generating a new one")

        password = random_password(24)

        await worlds_service.set_property("rcon.password", password)
