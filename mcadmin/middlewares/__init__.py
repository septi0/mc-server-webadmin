from aiohttp import web
from .real_ip import real_ip_middleware
from .auth import auth_middleware

__all__ = ["setup"]


def setup(app: web.Application) -> None:
    app.middlewares.append(real_ip_middleware)
    app.middlewares.append(auth_middleware)