import logging
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from mcadmin.utils.url import sanitize_url_path
from mcadmin.utils.web import get_di
from mcadmin.services.users import UsersService

auth_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)

@auth_routes.get("/login")
@auth_routes.post("/login")
@aiohttp_jinja2.template("login.html")
async def login_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    if request.get("auth_username"):
        # already logged in
        raise web.HTTPFound("/dashboard")

    if request.method == "GET":
        return {}

    session = await get_session(request)
    post_data = await request.post()
    get_data = request.query

    username = post_data.get("username", "")
    password = post_data.get("password", "")
    next_url = sanitize_url_path(get_data.get("redirect", "/dashboard"))

    user = await users_service.check_password(username, password)

    if user:
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        logger.info(f"New login for user '{username}' (ip: {request['real_ip']})")
        raise web.HTTPFound(next_url if next_url else "/dashboard")

    logger.warning(f"Failed login attempt for user '{username}' (ip: {request['real_ip']})")
    return {
        "message": ("danger", "Invalid credentials"),
        "last_username": username,
    }


@auth_routes.get("/logout")
async def logout_endpoint(request):
    session = await get_session(request)

    if not request.get("auth_username"):
        raise web.HTTPFound("/login")

    session.invalidate()

    logger.info(f"User '{request['auth_username']}' logged out")

    raise web.HTTPFound("/login")
