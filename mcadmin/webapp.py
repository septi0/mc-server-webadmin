import aiohttp_jinja2
import jinja2
import aiohttp_session
from aiohttp import web
from mcadmin.libraries.aiohttp_sess_sqlite import SqliteTortoiseStorage
from mcadmin.models.sessions import Sessions
from mcadmin.middlewares.auth import auth_middleware
from mcadmin.endpoints.server import routes as server_routes
from mcadmin.endpoints.auth import routes as auth_routes
from mcadmin.endpoints.admin import routes as admin_routes
from mcadmin.endpoints.user import routes as user_routes
from mcadmin.endpoints.logs import routes as log_routes
from mcadmin.endpoints.terminal import routes as terminal_routes
from mcadmin.utils.web import shutdown_websockets


def setup_webapp(app: web.Application) -> None:
    setup_variables(app)
    setup_jinja(app)
    setup_sess(app)
    setup_middlewares(app)
    setup_endpoints(app)
    setup_on_startup(app)
    setup_on_shutdown(app)


def setup_middlewares(app: web.Application) -> None:
    app.middlewares.append(auth_middleware)


def setup_endpoints(app: web.Application) -> None:
    # register static routes
    app.router.add_static("/static", path="mcadmin/static", name="static")

    # register routes
    app.add_routes(server_routes)
    app.add_routes(auth_routes)
    app.add_routes(admin_routes)
    app.add_routes(user_routes)
    app.add_routes(log_routes)
    app.add_routes(terminal_routes)


def setup_jinja(app: web.Application) -> None:
    env = aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader("mcadmin/templates"),
        autoescape=True,
        filters={
            "format_datetime": lambda dt: (dt.strftime("%b %d, %Y · %H:%M %Z") if dt else ""),
        },
    )

    env.globals.update(build_version=app["di"].build_version)


def setup_sess(app: web.Application) -> None:
    aiohttp_session.setup(
        app,
        SqliteTortoiseStorage(
            Sessions,
            cookie_name="mc-webadmin-sess",
            max_age=14 * 24 * 60 * 60,
            httponly=True,
            samesite="Strict",
        ),
    )

def setup_variables(app: web.Application) -> None:
    app["websockets"] = set()

def setup_on_startup(app: web.Application) -> None:
    app.on_startup.append(lambda x: app["di"].mc_server_ev_dispatcher.start())

def setup_on_shutdown(app: web.Application) -> None:
    app.on_shutdown.append(shutdown_websockets)
    app.on_shutdown.append(lambda x: app["di"].mc_server_ev_dispatcher.stop())
