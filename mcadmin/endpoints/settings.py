import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.instances import InstancesService
from mcadmin.utils.validate import require_roles

settings_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@settings_routes.get("/settings")
@require_roles(["user", "admin"])
@aiohttp_jinja2.template("settings.html")
async def settings_template(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service
    data = {}

    data["level_types"] = instances_service.get_level_types()
    data["server_types"] = list(instances_service.get_server_types().keys())

    return data
