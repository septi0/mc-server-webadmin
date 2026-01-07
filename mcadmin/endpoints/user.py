import logging
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import validate_request, require_roles
from mcadmin.services.users import UsersService
from mcadmin.services.sessions import SessionsService
from mcadmin.services.oidc import OIDCService
from mcadmin.schemas.users import UpdatePasswordSchema

user_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@user_routes.get("/profile")
@user_routes.post("/profile")
@require_roles(["user", "admin"])
@aiohttp_jinja2.template("profile.html")
async def profile_template(request: web.Request):
    return {}


@user_routes.get("/api/self/sessions")
@require_roles(["user", "admin"])
async def user_sessions_get(request: web.Request):
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


@user_routes.get("/api/self/identities")
@require_roles(["user", "admin"])
async def user_identities_get(request: web.Request):
    users_service: UsersService = get_di(request).users_service
    oidc_service: OIDCService = get_di(request).oidc_service

    identities = await users_service.get_user_identities(request["auth_user_id"])

    if not identities:
        return web.json_response([])

    identities_list = []

    for identity in identities:
        provider = await oidc_service.get_oidc_provider(id=identity.provider_id)
        identities_list.append({
            "id": identity.id,
            "provider_name": provider.name if provider else "Unknown",
            "added_at": str(identity.added_at),
        })

    return web.json_response(identities_list)


@user_routes.delete("/api/self/sessions/{sess_id}")
@require_roles(["user", "admin"])
async def user_session_delete(request: web.Request):
    sessions_service: SessionsService = get_di(request).sessions_service

    session_id = int(request.match_info.get("sess_id", 0))
    user_id = request["auth_user_id"]

    session = await sessions_service.get_user_session(user_id, session_id)

    if not session:
        return web.json_response({"status": "error", "message": "Session not found"}, status=404)

    try:
        await sessions_service.delete_user_session(user_id, session_id)
    except Exception as e:
        logger.exception(f"Failed to delete session for user '{user_id}' ({e})")
        return web.json_response(
            {"status": "error", "message": f"Failed to delete session ({e})"},
            status=500,
        )

    return web.json_response({"status": "success", "message": "Session deleted successfully"})


@user_routes.delete("/api/self/identities/{identity_id}")
@require_roles(["user", "admin"])
async def user_identity_delete(request: web.Request):
    users_service: UsersService = get_di(request).users_service

    identity_id = int(request.match_info.get("identity_id", 0))
    user_id = request["auth_user_id"]

    identity = await users_service.get_user_identity(id=identity_id, user_id=user_id)

    if not identity:
        return web.json_response({"status": "error", "message": "Identity not found"}, status=404)

    try:
        await users_service.delete_user_identity(identity)
    except Exception as e:
        logger.exception(f"Failed to delete identity for user '{user_id}' ({e})")
        return web.json_response(
            {"status": "error", "message": f"Failed to delete identity ({e})"},
            status=500,
        )

    return web.json_response({"status": "success", "message": "Identity deleted successfully"})


@user_routes.post("/api/self/update")
@require_roles(["user", "admin"])
@validate_request(UpdatePasswordSchema)
async def user_update(request: web.Request):
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    current_password = str(post_data.get("current_password", ""))
    new_password = str(post_data.get("new_password", ""))

    user = await users_service.check_password(request["auth_username"], current_password, validate_passwordless=True)

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
