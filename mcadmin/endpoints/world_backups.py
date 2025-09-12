import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.worlds import WorldsService

world_backups_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@world_backups_routes.get("/worlds/{world_id}/backups")
@aiohttp_jinja2.template("world_backups.html")
async def world_backups_template(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    data = {}

    world = await worlds_service.get_world(id=world_id)

    if not world:
        raise web.HTTPNotFound(text="World not found")

    data["world"] = world

    return data


@world_backups_routes.get("/api/worlds/{world_id}/backups")
async def world_backups_get(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    backups = await worlds_service.list_world_backups(world)

    if not backups:
        return web.json_response([])

    backups_list = []

    for b in backups:
        backups_list.append(
            {
                "id": b.id,
                "created_at": str(b.created_at),
                "type": b.type,
                "metadata": b.metadata,
            }
        )

    return web.json_response(backups_list)


@world_backups_routes.post("/api/worlds/{world_id}/backups")
async def world_backup_create(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    try:
        backup = await worlds_service.backup_world(world, "user")
    except Exception as e:
        logger.error(f"Error creating backup for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to create backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully created"})


@world_backups_routes.delete("/api/worlds/{world_id}/backups/{backup_id}")
async def world_backup_delete(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    backup_id = int(request.match_info.get("backup_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    backup = await worlds_service.get_world_backup(world, backup_id)

    if not backup:
        return web.json_response({"status": "error", "message": "Backup not found"}, status=404)

    try:
        await worlds_service.delete_world_backup(world, backup)
    except Exception as e:
        logger.error(f"Error deleting backup {backup.id} for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully deleted"})


@world_backups_routes.post("/api/worlds/{world_id}/backups/{backup_id}/restore")
async def world_backup_restore(request: web.Request):
    worlds_service: WorldsService = get_di(request).worlds_service

    world_id = int(request.match_info.get("world_id", 0))
    backup_id = int(request.match_info.get("backup_id", 0))

    world = await worlds_service.get_world(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    backup = await worlds_service.get_world_backup(world, backup_id)

    if not backup:
        return web.json_response({"status": "error", "message": "Backup not found"}, status=404)

    try:
        await worlds_service.restore_world(world, backup)
    except Exception as e:
        logger.error(f"Error restoring backup {backup.id} for world {world.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to restore backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully restored"})
