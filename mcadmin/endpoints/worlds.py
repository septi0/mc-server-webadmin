import logging
import json
from aiohttp import web
from packaging import version
from mcadmin.utils.web import get_di, validate_request_schema
from mcadmin.services.worlds import WorldsService
from mcadmin.schemas.worlds import CreateWorldSchema, UpdateWorldSchema

worlds_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@worlds_routes.get("/api/worlds")
async def worlds_get(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    worlds = await worlds_service.list_world_instances()

    if not worlds:
        return web.json_response([])

    worlds_list = []

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
            }
        )

    return web.json_response(worlds_list)


@worlds_routes.get("/api/worlds/active")
async def active_world_get(request):
    worlds_service: WorldsService = get_di(request).worlds_service

    active_world = await worlds_service.get_active_world_instance()

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
async def world_create(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    post_data = await request.post()
    name = post_data.get("name", "")
    server_version = post_data.get("server_version", "")
    world_archive = post_data.get("file", "")
    properties = {}

    min_version = worlds_service.get_min_server_version()

    if version.parse(server_version) < version.parse(min_version):
        return web.json_response({"status": "error", "message": f"Server version must be {min_version} or greater"}, status=403)

    if not world_archive:
        properties = json.loads(post_data.get("properties", "{}"))

    try:
        worlds_service.validate_properties(properties)

        world = await worlds_service.create_world_instance(
            name=name,
            server_version=server_version,
            properties=properties,
            world_archive=world_archive.file if world_archive else None,
        )
    except Exception as e:
        logger.exception(f"Failed to create world '{name}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to create world ({e})"}, status=500)

    logger.info(f"World '{world.id}' created successfully")
    return web.json_response({"status": "success", "message": "World created successfully"})


@worlds_routes.post("/api/worlds/{world_id}")
@validate_request_schema(UpdateWorldSchema)
async def world_update(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    post_data = await request.post()
    world_id = request.match_info.get("world_id", "")
    server_version = post_data.get("server_version", "")

    world = await worlds_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    # ensure desired server version is greater than current one
    if version.parse(server_version) <= version.parse(world.server_version):
        return web.json_response({"status": "error", "message": "Server version must be greater than current version"}, status=403)

    try:
        await worlds_service.update_world_instance(world, server_version=server_version)
    except Exception as e:
        return web.json_response({"status": "error", "message": f"Failed to update world ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "World updated successfully"})


@worlds_routes.delete("/api/worlds/{world_id}")
async def world_delete(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    world_id = request.match_info.get("world_id", "")

    if not world_id:
        return web.json_response({"status": "error", "message": "World ID is required"}, status=403)

    world = await worlds_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    try:
        await worlds_service.delete_world_instance(world)
    except Exception as e:
        logger.exception(f"Failed to delete world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete world ({e})"}, status=500)

    logger.info(f"World '{world_id}' deleted successfully")
    return web.json_response({"status": "success", "message": "World deleted successfully"})


@worlds_routes.post("/api/worlds/{world_id}/activate")
async def world_activate(request):
    worlds_service: WorldsService = get_di(request).worlds_service
    world_id = request.match_info.get("world_id", "")

    if not world_id:
        return web.json_response({"status": "error", "message": "World ID is required"}, status=403)

    world = await worlds_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if world.active:
        return web.json_response({"status": "error", "message": "World is already active"}, status=403)

    try:
        await worlds_service.activate_world_instance(world)
    except Exception as e:
        logger.exception(f"Failed to activate world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to activate world ({e})"}, status=500)

    logger.info(f"World '{world_id}' activated successfully")
    return web.json_response({"status": "success", "message": "World activated successfully"})
