import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import require_roles, get_di, validate_request_schema
from mcadmin.services.users import UsersService
from mcadmin.schemas.users import CreateUserSchema, UpdateUserSchema

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@routes.get("/users")
@require_roles(["admin"])
@aiohttp_jinja2.template("users.html")
async def users_get_endpoint(request):
    data = {"roles": ["admin", "user"]}

    return data


@routes.get("/api/admin/users")
@require_roles(["admin"])
async def admin_users_get_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    users = await users_service.list_users()
    user_id = request["auth_user_id"]

    if not users:
        return web.json_response([])

    users_list = []

    for s in users:
        users_list.append(
            {
                "id": s.id,
                "username": s.username,
                "role": s.role,
                "created_at": str(s.created_at),
                "current": (s.id == user_id),
            }
        )

    return web.json_response(users_list)


@routes.post("/api/admin/user-create")
@require_roles(["admin"])
@validate_request_schema(CreateUserSchema)
async def admin_user_create_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    username = post_data.get("username", "")
    password = post_data.get("password", "")
    role = post_data.get("role", "user")

    try:
        await users_service.create_user(username=username, password=password, role=role)
    except Exception as e:
        logger.exception(f"Failed to create user '{username}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to create user ({e})"}, status=500)

    logger.info(f"User '{username}' created successfully")
    return web.json_response({"status": "success", "message": "User created successfully"})


@routes.post("/api/admin/user-update")
@require_roles(["admin"])
@validate_request_schema(UpdateUserSchema)
async def admin_user_update_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    user_id = post_data.get("id", "")
    password = post_data.get("password", "")
    role = post_data.get("role", "")

    user = await users_service.get_user(id=user_id)

    if not user:
        return web.json_response({"status": "error", "message": "User not found"}, status=404)

    try:
        update = {"role": role}

        if password:
            update["password"] = password

        await users_service.update_user(user, **update)
    except Exception as e:
        logger.exception(f"Failed to update user '{user_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update user ({e})"}, status=500)

    logger.info(f"User '{user_id}' updated successfully")
    return web.json_response({"status": "success", "message": "User updated successfully"})


@routes.post("/api/admin/user-delete")
@require_roles(["admin"])
async def admin_user_delete_endpoint(request):
    users_service: UsersService = get_di(request).users_service

    post_data = await request.post()

    user_id = post_data.get("id", "")

    if not user_id:
        return web.json_response({"status": "error", "message": "User ID is required"}, status=403)

    user = await users_service.get_user(id=user_id)

    if not user:
        return web.json_response({"status": "error", "message": "User not found"}, status=404)

    try:
        await users_service.delete_user(user)
    except Exception as e:
        logger.exception(f"Failed to delete user '{user_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete user ({e})"}, status=500)

    logger.info(f"User '{user_id}' deleted successfully")
    return web.json_response({"status": "success", "message": "User deleted successfully"})
