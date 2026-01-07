import logging
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.instances import InstancesService
from mcadmin.utils.validate import require_roles

global_properties_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@global_properties_routes.get("/api/global-properties")
@require_roles(["user", "admin"])
async def global_properties_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    global_properties = await instances_service.get_properties()

    if not global_properties:
        return web.json_response([])

    global_properties_dict = {}

    allowed_properties = [
        "allow-flight",
        "difficulty",
        "gamemode",
        "max-players",
        "motd",
        "enforce-whitelist",
    ]

    for prop in global_properties:
        if prop.key in allowed_properties:
            global_properties_dict[prop.key] = prop.value

    return web.json_response(global_properties_dict)


@global_properties_routes.post("/api/global-properties")
@require_roles(["user", "admin"])
async def global_properties_update(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    properties = {key: value for key, value in post_data.items()}
    whitelist = properties.get("enforce-whitelist", None)

    if whitelist:
        properties["white-list"] = whitelist

    try:
        instances_service.validate_properties(properties)

        await instances_service.set_properties(properties)
    except Exception as e:
        logger.exception(f"Failed to update global properties ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update global properties ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "Global properties updated successfully"})
