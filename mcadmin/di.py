import os
import asyncio
from types import SimpleNamespace
from mcadmin.utils.hash import hash_str
from mcadmin.libraries.mc_server import McServerRunner, McServerConfigurator
from mcadmin.libraries.queue_dispatcher import QueueDispatcher
from mcadmin.services.users import UsersService
from mcadmin.services.sessions import SessionsService
from mcadmin.services.server import ServerService
from mcadmin.schemas.config import ConfigSchema


def setup_di(deps: SimpleNamespace, *, config: ConfigSchema, data_directory: str = "") -> None:
    build_version = ""

    with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as f:
        build_version = hash_str(f.read().strip())

    # data
    deps.build_version = build_version

    # queues
    deps.mc_server_ev_queue = asyncio.Queue()

    # libraries
    mc_server_config = config.mc_server.model_dump()
    deps.mc_server_runner = McServerRunner(os.path.join(data_directory, "world_instances/current"), mc_server_config, events_queue=deps.mc_server_ev_queue)
    deps.mc_server_configurator = McServerConfigurator(os.path.join(data_directory, "world_instances"), mc_server_config)
    deps.mc_server_ev_dispatcher = QueueDispatcher(deps.mc_server_ev_queue)

    # services
    deps.users_service = UsersService()
    deps.sessions_service = SessionsService()
    deps.server_service = ServerService(mc_server_runner=deps.mc_server_runner, mc_server_configurator=deps.mc_server_configurator)
