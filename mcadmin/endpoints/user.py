import logging
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from mcadmin.utils.web import get_di, validate_request_schema
from mcadmin.services.users import UsersService
from mcadmin.services.sessions import SessionsService
from mcadmin.schemas.users import UpdatePasswordSchema

user_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@user_routes.get("/profile")
@user_routes.post("/profile")
@aiohttp_jinja2.template("profile.html")
async def profile_get_endpoint(request):
    return {}


@user_routes.get("/api/profile/sessions")
async def profile_sessions_get_endpoint(request):
    sessions_service: SessionsService = get_di(request).sessions_service

    session = await get_session(request)
    user_sessions = await sessions_service.get_user_sessions(request["auth_user_id"])

    if not user_sessions:
        return web.json_response([])

    user_sessions_list = []

    for s in user_sessions:
        user_sessions_list.append(
            {
                "id": s.id,
                "device": s.device,
                "ip": s.ip,
                "created_at": str(s.created_at),
                "updated_at": str(s.updated_at),
                "current": (s.token == session.identity),
            }
        )

    return web.json_response(user_sessions_list)


@user_routes.post("/api/profile/session-delete")
async def profile_sessions_delete_endpoint(request):
    sessions_service: SessionsService = get_di(request).sessions_service

    post_data = await request.post()

    session_id = post_data.get("session_id")
    user_id = request["auth_user_id"]

    if not session_id:
        return web.json_response({"status": "error", "message": "Invalid session ID"}, status=403)

    try:
        await sessions_service.delete_user_session(user_id, session_id)
    except Exception as e:
        logger.exception(f"Failed to delete session for user '{user_id}' ({e})")
        return web.json_response(
            {"status": "error", "message": f"Failed to delete session ({e})"},
            status=500,
        )

    return web.json_response({"status": "success", "message": "Session deleted successfully"})


@user_routes.post("/api/profile/password-update")
@validate_request_schema(UpdatePasswordSchema)
async def profile_password_update_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    current_password = post_data.get("current_password", "")
    new_password = post_data.get("new_password", "")

    user = await users_service.check_password(request["auth_username"], current_password)

    if not user:
        return web.json_response({"status": "error", "message": "Current password is incorrect"}, status=403)

    try:
        await users_service.update_user(user, password=new_password)
    except Exception as e:
        logger.exception(f"Failed to update password for user '{user.username}' ({e})")
        return web.json_response(
            {"status": "error", "message": f"Failed to update password ({e})"},
            status=500,
        )

    logger.info(f"User '{user.username}' updated their password")
    return web.json_response({"status": "success", "message": "Password updated successfully"})
