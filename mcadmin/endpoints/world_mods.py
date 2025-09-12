import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di, get_filename
from mcadmin.services.worlds import WorldsService
from mcadmin.utils.validate import validate_request_schema
from mcadmin.schemas.worlds import AddWorldModSchema

world_mods_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@world_mods_routes.get("/worlds/{world_id}/mods")
@aiohttp_jinja2.template("world_mods.html")
async def world_mods_template(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    data = {}

    world = await worlds_service.get_world(id=world_id)

    if not world:
        raise web.HTTPNotFound(text="World not found")

    if not "mods" in worlds_service.server_capabilities(world.server_type):
        raise web.HTTPForbidden(text="Mods are not supported for this world type")

    data["world"] = world

    return data


@world_mods_routes.get("/api/worlds/{world_id}/mods")
async def world_mods_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if not "mods" in worlds_service.server_capabilities(world.server_type):
        return web.json_response({"status": "error", "message": "Mods are not supported for this world type"}, status=403)

    mods = await worlds_service.list_world_mods(world)

    if not mods:
        return web.json_response([])

    mods_list = []

    for b in mods:
        mods_list.append(
            {
                "id": b.id,
                "name": b.name,
                "added_at": str(b.added_at),
            }
        )

    return web.json_response(mods_list)


@world_mods_routes.post("/api/worlds/{world_id}/mods")
@validate_request_schema(AddWorldModSchema)
async def world_mod_add(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    post_data = await request.post()

    world_id = int(request.match_info.get("world_id", 0))
    mod_jar = post_data.get("mod_jar", None)

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if not "mods" in worlds_service.server_capabilities(world.server_type):
        return web.json_response({"status": "error", "message": "Mods are not supported for this world type"}, status=403)

    if not mod_jar or not isinstance(mod_jar, web.FileField):
        return web.json_response({"status": "error", "message": "No mod jar provided"}, status=403)

    try:
        await worlds_service.add_world_mod(
            world,
            mod_jar=mod_jar.file,
            name=get_filename(mod_jar, strip_ext=True),
        )
    except Exception as e:
        logger.error(f"Error adding mod for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to add mod"}, status=500)

    return web.json_response({"status": "success", "message": "Mod successfully added"})


@world_mods_routes.delete("/api/worlds/{world_id}/mods/{mod_id}")
async def world_mod_delete(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    mod_id = int(request.match_info.get("mod_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    mod = await worlds_service.get_world_mod(world, mod_id)

    if not mod:
        return web.json_response({"status": "error", "message": "Mod not found"}, status=404)

    try:
        await worlds_service.delete_world_mod(world, mod)
    except Exception as e:
        logger.error(f"Error deleting mod {mod.id} for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete mod"}, status=500)

    return web.json_response({"status": "success", "message": "Mod successfully deleted"})
