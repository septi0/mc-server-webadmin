import os
from aiohttp import web
from .server import routes as server_routes
from .auth import routes as auth_routes
from .admin import routes as admin_routes
from .user import routes as user_routes
from .logs import routes as log_routes
from .terminal import routes as terminal_routes

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
    app.add_routes(log_routes)
    app.add_routes(terminal_routes)
