import logging
import aiohttp_jinja2
from aiohttp import web

dashboard_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@dashboard_routes.get("/")
async def root(request: web.Request):
    return web.HTTPFound("/dashboard")


@dashboard_routes.get("/dashboard")
@aiohttp_jinja2.template("dashboard.html")
async def dashboard_template(request: web.Request):
    return {}
