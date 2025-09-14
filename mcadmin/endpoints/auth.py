import logging
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from mcadmin.utils.url import sanitize_url_path
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import validate_data
from mcadmin.services.users import UsersService
from mcadmin.schemas.users import AuthSchema

auth_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)

@auth_routes.get("/login")
@auth_routes.post("/login")
@aiohttp_jinja2.template("login.html")
async def login_template(request: web.Request):
    users_service: UsersService = get_di(request).users_service
    data = {}

    if request.get("auth_username"):
        raise web.HTTPFound("/dashboard")

    if request.method == "GET":
        return data

    session = await get_session(request)
    post_data = await request.post()
    get_data = request.query

    username = str(post_data.get("username", ""))
    password = str(post_data.get("password", ""))
    next_url = sanitize_url_path(get_data.get("redirect", "/dashboard"))
    
    try:
        validate_data(AuthSchema, {"username": username, "password": password})
    except Exception as e:
        data["message"] = ("danger", str(e))
        return data

    user = await users_service.check_password(username, password)

    if user:
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        logger.info(f"New login for user '{username}' (ip: {request['real_ip']})")
        raise web.HTTPFound(next_url if next_url else "/dashboard")

    logger.warning(f"Failed login attempt for user '{username}' (ip: {request['real_ip']})")
    
    data["message"] = ("danger", "Invalid credentials")
    data["last_username"] = username
    
    return data


@auth_routes.get("/logout")
async def logout(request: web.Request):
    session = await get_session(request)

    if not request.get("auth_username"):
        raise web.HTTPFound("/login")

    session.invalidate()

    logger.info(f"User '{request['auth_username']}' logged out")

    raise web.HTTPFound("/login")
