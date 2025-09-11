import os
from aiohttp import web
from .server import server_routes
from .auth import auth_routes
from .admin import admin_routes
from .user import user_routes
from .logs import logs_routes
from .terminal import terminal_routes

__all__ = ["setup"]

def setup(app: web.Application) -> None:
    static_path = os.path.join(os.path.dirname(__file__), '..', "static")
    
    # register static routes
    app.router.add_static("/static", path=static_path, name="static")

    # register routes
    app.add_routes(server_routes)
    app.add_routes(auth_routes)
    app.add_routes(admin_routes)
    app.add_routes(user_routes)
    app.add_routes(logs_routes)
    app.add_routes(terminal_routes)
