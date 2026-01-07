import os
import asyncio
from mcadmin.services.auth_config import AuthConfigService
from mcadmin.services.oidc import OIDCService
from mcadmin.utils.hash import hash_str
from mcadmin.libraries.mc_server import McServerRunner, McServerInstMgr
from mcadmin.libraries.di_container import DiContainer
from mcadmin.libraries.queue_dispatcher import QueueDispatcher
from mcadmin.services.users import UsersService
from mcadmin.services.sessions import SessionsService
from mcadmin.services.server import ServerService
from mcadmin.services.instances import InstancesService
from mcadmin.schemas.config import ConfigSchema, McServerConfigSchema, WebServerConfigSchema

__all__ = ["setup_di"]


def setup_di(deps: DiContainer, *, config: dict, data_directory: str = "") -> None:
    build_version = ""
    app_version = ""

    with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as f:
        app_version = f.read().strip()
        build_version = hash_str(app_version)

    config_obj = ConfigSchema(**config)

    mc_server_config = config_obj.mc_server.model_dump()
    web_server_config = config_obj.web_server.model_dump()

    if os.getenv("APP_ENV", "") == "docker":
        del mc_server_config["java_bin"]

        mc_server_config["server_ip"] = getattr(McServerConfigSchema.model_fields.get("server_ip"), "default")
        mc_server_config["server_port"] = getattr(McServerConfigSchema.model_fields.get("server_port"), "default")
        mc_server_config["rcon_port"] = getattr(McServerConfigSchema.model_fields.get("rcon_port"), "default")

        web_server_config["ip"] = getattr(WebServerConfigSchema.model_fields.get("ip"), "default")
        web_server_config["port"] = getattr(WebServerConfigSchema.model_fields.get("port"), "default")
        web_server_config["base_url"] = getattr(WebServerConfigSchema.model_fields.get("base_url"), "default")

    mc_server_config["server_ip"] = str(mc_server_config["server_ip"])
    mc_server_config["display_ip"] = str(mc_server_config["display_ip"]) if mc_server_config["display_ip"] else None

    # ensure base url starts and ends with /
    base_url = "/" + deps.web_server_config["base_url"].strip("/") + "/"
    base_url = base_url.replace("//", "/")

    # data
    deps.mc_server_config = mc_server_config
    deps.web_server_config = web_server_config
    deps.app_version = app_version
    deps.build_version = build_version
    deps.base_url = base_url
    # queues
    deps.mc_server_ev_queue = asyncio.Queue()

    # libraries
    deps.mc_server_runner = McServerRunner(os.path.join(data_directory, "mc/current"), deps.mc_server_config, events_queue=deps.mc_server_ev_queue)
    deps.mc_server_inst_mgr = McServerInstMgr(os.path.join(data_directory, "mc"), deps.mc_server_config)
    deps.mc_server_ev_dispatcher = QueueDispatcher(deps.mc_server_ev_queue)

    # services
    deps.users_service = UsersService()
    deps.sessions_service = SessionsService()
    deps.server_service = ServerService(mc_server_runner=deps.mc_server_runner, mc_server_inst_mgr=deps.mc_server_inst_mgr)
    deps.instances_service = InstancesService(server_service=deps.server_service, mc_server_runner=deps.mc_server_runner, mc_server_inst_mgr=deps.mc_server_inst_mgr)
    deps.auth_config_service = AuthConfigService()
    deps.oidc_service = OIDCService()
