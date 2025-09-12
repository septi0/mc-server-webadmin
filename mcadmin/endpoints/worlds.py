import logging
import json
from aiohttp import web
from packaging import version
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import validate_request_schema
from mcadmin.services.worlds import WorldsService
from mcadmin.schemas.worlds import CreateWorldSchema, UpdateWorldSchema

worlds_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@worlds_routes.get("/api/worlds")
async def worlds_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    worlds = await worlds_service.list_worlds()

    if not worlds:
        return web.json_response([])

    worlds_list = []
    server_types = worlds_service.get_server_types()

    for world in worlds:
        worlds_list.append(
            {
                "id": world.id,
                "name": world.name,
                "server_version": world.server_version,
                "server_type": world.server_type,
                "active": world.active,
                "created_at": str(world.created_at),
                "updated_at": str(world.updated_at),
                "server_capabilities": server_types.get(world.server_type, {}).get("capabilities", []),
            }
        )

    return web.json_response(worlds_list)


@worlds_routes.get("/api/worlds/active")
async def active_world_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    active_world = await worlds_service.get_active_world()

    if not active_world:
        return web.json_response({})

    active_world_dict = {
        "id": active_world.id,
        "name": active_world.name,
        "server_version": active_world.server_version,
        "server_type": active_world.server_type,
        "created_at": str(active_world.created_at),
        "updated_at": str(active_world.updated_at),
    }

    return web.json_response(active_world_dict)


@worlds_routes.post("/api/worlds")
@validate_request_schema(CreateWorldSchema)
async def world_create(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    post_data = await request.post()

    name = str(post_data.get("name", ""))
    server_version = str(post_data.get("server_version", ""))
    server_type = str(post_data.get("server_type", "vanilla"))
    world_archive = post_data.get("world_archive", None)

    min_version = worlds_service.get_min_server_version()

    if version.parse(server_version) < version.parse(min_version):
        return web.json_response({"status": "error", "message": f"Server version must be {min_version} or greater"}, status=403)

    if not world_archive or not isinstance(world_archive, web.FileField):
        properties = json.loads(str(post_data.get("properties", "{}")))
        world_archive = None
    else:
        properties = {}
        world_archive = world_archive.file

    try:
        worlds_service.validate_properties(properties)

        world = await worlds_service.create_world(
            name=name,
            server_version=server_version,
            server_type=server_type,
            properties=properties,
            world_archive=world_archive,
        )
    except Exception as e:
        logger.exception(f"Failed to create world '{name}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to create world ({e})"}, status=500)

    logger.info(f"World '{world.id}' created successfully")
    return web.json_response({"status": "success", "message": "World created successfully"})


@worlds_routes.post("/api/worlds/{world_id}")
@validate_request_schema(UpdateWorldSchema)
async def world_update(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    post_data = await request.post()

    world_id = int(request.match_info.get("world_id", 0))
    server_version = str(post_data.get("server_version", ""))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if version.parse(server_version) <= version.parse(world.server_version):
        return web.json_response({"status": "error", "message": "Server version must be greater than current version"}, status=403)

    try:
        await worlds_service.update_world(world, server_version=server_version)
    except Exception as e:
        return web.json_response({"status": "error", "message": f"Failed to update world ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "World updated successfully"})


@worlds_routes.delete("/api/worlds/{world_id}")
async def world_delete(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    try:
        await worlds_service.delete_world(world)
    except Exception as e:
        logger.exception(f"Failed to delete world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete world ({e})"}, status=500)

    logger.info(f"World '{world_id}' deleted successfully")
    return web.json_response({"status": "success", "message": "World deleted successfully"})


@worlds_routes.post("/api/worlds/{world_id}/activate")
async def world_activate(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if world.active:
        return web.json_response({"status": "error", "message": "World is already active"}, status=403)

    try:
        await worlds_service.activate_world(world)
    except Exception as e:
        logger.exception(f"Failed to activate world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to activate world ({e})"}, status=500)

    logger.info(f"World '{world_id}' activated successfully")
    return web.json_response({"status": "success", "message": "World activated successfully"})
