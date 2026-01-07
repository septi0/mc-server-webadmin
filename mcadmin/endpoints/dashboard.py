import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.validate import require_roles

dashboard_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@dashboard_routes.get("/")
@require_roles(["user", "admin"])
async def dashboard_redirect(request: web.Request):
    return web.HTTPFound("/dashboard")


@dashboard_routes.get("/dashboard")
@require_roles(["user", "admin"])
@aiohttp_jinja2.template("dashboard.html")
async def dashboard_template(request: web.Request):
    return {}
