import urllib.parse
import aiohttp_jinja2
from datetime import datetime, timezone
from aiohttp import web
from aiohttp_session import get_session


@web.middleware
async def auth_middleware(request, handler):
    # public paths
    if request.path.startswith("/static/"):
        return await handler(request)

    session = await get_session(request)

    user_id = session.get("user_id", 0)
    username = session.get("username", "")
    role = session.get("role", "")

    allowed_paths = ["/login"]
    required_roles = getattr(handler, "required_roles", None)

    if request.path not in allowed_paths and (not username or (required_roles and role not in required_roles)):
        # APIs return 401
        if request.path.startswith("/api/"):
            return web.json_response({"error": "denied"}, status=401)

        # pages redirect to login
        next_qs = urllib.parse.quote(str(request.rel_url))
        raise web.HTTPFound(f"/login?redirect={next_qs}")

    if user_id:
        session["last_activity"] = datetime.now(timezone.utc).timestamp()

    # make username available to endpoints
    request["auth_user_id"] = user_id
    request["auth_username"] = username
    request["auth_role"] = role

    env = aiohttp_jinja2.get_env(request.app)
    env.globals.update(auth_user_id=user_id, auth_username=username, auth_role=role)

    return await handler(request)
