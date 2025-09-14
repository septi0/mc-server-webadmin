import os
from aiohttp import web
from .dashboard import dashboard_routes
from .server import server_routes
from .auth import auth_routes
from .admin import admin_routes
from .user import user_routes
from .logs import logs_routes
from .terminal import terminal_routes
from .settings import settings_routes
from .global_properties import global_properties_routes
from .instances import instances_routes
from .instance_backups import instance_backups_routes
from .instance_datapacks import instance_datapacks_routes
from .instance_mods import instance_mods_routes

__all__ = ["setup"]

def setup(app: web.Application) -> None:
    static_path = os.path.join(os.path.dirname(__file__), '..', "static")

    # register static routes
    app.router.add_static("/static", path=static_path, name="static")

    # register routes
    app.add_routes(dashboard_routes)
    app.add_routes(server_routes)
    app.add_routes(auth_routes)
    app.add_routes(admin_routes)
    app.add_routes(user_routes)
    app.add_routes(logs_routes)
    app.add_routes(terminal_routes)
    app.add_routes(settings_routes)
    app.add_routes(global_properties_routes)
    app.add_routes(instances_routes)
    app.add_routes(instance_backups_routes)
    app.add_routes(instance_datapacks_routes)
    app.add_routes(instance_mods_routes)
