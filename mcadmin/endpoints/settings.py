import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.worlds import WorldsService

settings_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)

@settings_routes.get("/settings")
@aiohttp_jinja2.template("settings.html")
async def settings_template(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    data = {}

    data["level_types"] = worlds_service.get_level_types()

    return data