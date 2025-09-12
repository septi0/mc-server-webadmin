import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di, get_filename
from mcadmin.services.worlds import WorldsService
from mcadmin.utils.validate import validate_request_schema
from mcadmin.schemas.worlds import AddWorldDatapackSchema

world_datapacks_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@world_datapacks_routes.get("/worlds/{world_id}/datapacks")
@aiohttp_jinja2.template("world_datapacks.html")
async def world_datapacks_template(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    data = {}

    world = await worlds_service.get_world(id=world_id)

    if not world:
        raise web.HTTPNotFound(text="World not found")

    if not "datapacks" in worlds_service.server_capabilities(world.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this world type"}, status=403)

    data["world"] = world

    return data


@world_datapacks_routes.get("/api/worlds/{world_id}/datapacks")
async def world_datapacks_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if not "datapacks" in worlds_service.server_capabilities(world.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this world type"}, status=403)

    datapacks = await worlds_service.list_world_datapacks(world)

    if not datapacks:
        return web.json_response([])

    datapacks_list = []

    for b in datapacks:
        datapacks_list.append(
            {
                "id": b.id,
                "name": b.name,
                "added_at": str(b.added_at),
            }
        )

    return web.json_response(datapacks_list)


@world_datapacks_routes.post("/api/worlds/{world_id}/datapacks")
@validate_request_schema(AddWorldDatapackSchema)
async def world_datapack_add(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    post_data = await request.post()

    world_id = int(request.match_info.get("world_id", 0))
    datapack_archive = post_data.get("datapack_archive", None)

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)
    
    if not "datapacks" in worlds_service.server_capabilities(world.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this world type"}, status=403)

    if not datapack_archive or not isinstance(datapack_archive, web.FileField):
        return web.json_response({"status": "error", "message": "No datapack archive provided"}, status=403)

    try:
        await worlds_service.add_world_datapack(
            world,
            datapack_archive=datapack_archive.file,
            name=get_filename(datapack_archive, strip_ext=True),
        )
    except Exception as e:
        logger.error(f"Error adding datapack for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to add datapack"}, status=500)

    return web.json_response({"status": "success", "message": "Datapack successfully added"})


@world_datapacks_routes.delete("/api/worlds/{world_id}/datapacks/{datapack_id}")
async def world_datapack_delete(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    datapack_id = int(request.match_info.get("datapack_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    datapack = await worlds_service.get_world_datapack(world, datapack_id)

    if not datapack:
        return web.json_response({"status": "error", "message": "Datapack not found"}, status=404)

    try:
        await worlds_service.delete_world_datapack(world, datapack)
    except Exception as e:
        logger.error(f"Error deleting datapack {datapack.id} for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete datapack"}, status=500)

    return web.json_response({"status": "success", "message": "Datapack successfully deleted"})
