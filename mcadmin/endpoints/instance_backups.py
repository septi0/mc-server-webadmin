import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.instances import InstancesService
from mcadmin.utils.validate import require_roles

instance_backups_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@instance_backups_routes.get("/instances/{instance_id}/backups")
@require_roles(["user", "admin"])
@aiohttp_jinja2.template("instance_backups.html")
async def instance_backups_template(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    data = {}

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        raise web.HTTPNotFound(text="Instance not found")

    data["instance"] = instance

    return data


@instance_backups_routes.get("/api/instances/{instance_id}/backups")
@require_roles(["user", "admin"])
async def instance_backups_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    backups = await instances_service.list_backups(instance)

    if not backups:
        return web.json_response([])

    backups_list = []

    for b in backups:
        backups_list.append(
            {
                "id": b.id,
                "created_at": str(b.created_at),
                "type": b.type,
                "server_version": b.metadata.get("instance", {}).get("server_version", ""),
            }
        )

    return web.json_response(backups_list)


@instance_backups_routes.post("/api/instances/{instance_id}/backups")
@require_roles(["user", "admin"])
async def instance_backup_create(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    try:
        backup = await instances_service.create_backup(instance, "user")
    except Exception as e:
        logger.error(f"Error creating backup for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to create backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully created"})


@instance_backups_routes.delete("/api/instances/{instance_id}/backups/{backup_id}")
@require_roles(["user", "admin"])
async def instance_backup_delete(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    backup_id = int(request.match_info.get("backup_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    backup = await instances_service.get_backup(instance, backup_id)

    if not backup:
        return web.json_response({"status": "error", "message": "Backup not found"}, status=404)

    try:
        await instances_service.delete_backup(instance, backup)
    except Exception as e:
        logger.error(f"Error deleting backup {backup.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully deleted"})


@instance_backups_routes.post("/api/instances/{instance_id}/backups/{backup_id}/restore")
@require_roles(["user", "admin"])
async def instance_backup_restore(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    backup_id = int(request.match_info.get("backup_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    backup = await instances_service.get_backup(instance, backup_id)

    if not backup:
        return web.json_response({"status": "error", "message": "Backup not found"}, status=404)

    try:
        await instances_service.restore_backup(instance, backup)
    except Exception as e:
        logger.error(f"Error restoring backup {backup.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to restore backup"}, status=500)

    return web.json_response({"status": "success", "message": "Backup successfully restored"})
