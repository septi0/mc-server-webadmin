import logging
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.worlds import WorldsService

global_properties_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@global_properties_routes.get("/api/global-properties")
async def global_properties_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    global_properties = await worlds_service.get_properties()

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
async def global_properties_update(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    post_data = await request.post()

    properties = {key: value for key, value in post_data.items()}
    whitelist = properties.get("enforce-whitelist", None)

    if whitelist:
        properties["white-list"] = whitelist

    try:
        worlds_service.validate_properties(properties)

        await worlds_service.set_properties(properties)
    except Exception as e:
        logger.exception(f"Failed to update global properties ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update global properties ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "Global properties updated successfully"})
