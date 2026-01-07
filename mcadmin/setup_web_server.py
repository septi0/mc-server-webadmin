import os
import aiohttp_jinja2
import jinja2
import aiohttp_session
from aiohttp import web
from mcadmin.libraries.aiohttp_sess_sqlite import SqliteTortoiseStorage
from mcadmin.models.sessions import Sessions
from mcadmin.middlewares import setup as _setup_middlewares
from mcadmin.endpoints import setup as _setup_endpoints
from mcadmin.utils.web import shutdown_websockets

__all__ = ["setup_web_server"]


def setup_web_server(app: web.Application) -> None:
    _setup_variables(app)
    _setup_jinja(app)
    _setup_sess(app)
    _setup_middlewares(app)
    _setup_endpoints(app)
    _setup_on_startup(app)
    _setup_on_shutdown(app)


def _setup_jinja(app: web.Application) -> None:
    templates_path = os.path.join(os.path.dirname(__file__), "templates")

    env = aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(templates_path),
        autoescape=True,
        filters={
            "format_datetime": lambda dt: (dt.strftime("%b %d, %Y · %H:%M %Z") if dt else ""),
        },
    )

    env.globals.update(
        app_version=app["di"].app_version,
        build_version=app["di"].build_version,
        base_url=app["di"].base_url
    )


def _setup_sess(app: web.Application) -> None:
    aiohttp_session.setup(
        app,
        SqliteTortoiseStorage(
            Sessions,
            cookie_name="mc-webadmin-sess",
            max_age=14 * 24 * 60 * 60,
            httponly=True,
            samesite="Lax",
        ),
    )


def _setup_variables(app: web.Application) -> None:
    app["websockets"] = set()


def _setup_on_startup(app: web.Application) -> None:
    app.on_startup.append(lambda x: app["di"].mc_server_ev_dispatcher.start())


def _setup_on_shutdown(app: web.Application) -> None:
    app.on_shutdown.append(shutdown_websockets)
    app.on_shutdown.append(lambda x: app["di"].mc_server_ev_dispatcher.stop())
