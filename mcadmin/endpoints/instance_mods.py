import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di, get_filename
from mcadmin.services.instances import InstancesService
from mcadmin.utils.validate import validate_request
from mcadmin.schemas.instances import AddInstanceModSchema

instance_mods_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@instance_mods_routes.get("/instances/{instance_id}/mods")
@aiohttp_jinja2.template("instance_mods.html")
async def instance_mods_template(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    data = {}

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        raise web.HTTPNotFound(text="Instance not found")

    if not "mods" in instances_service.get_server_capabilities(instance.server_type):
        raise web.HTTPForbidden(text="Mods are not supported for this instance type")

    data["instance"] = instance

    return data


@instance_mods_routes.get("/api/instances/{instance_id}/mods")
async def instance_mods_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if not "mods" in instances_service.get_server_capabilities(instance.server_type):
        return web.json_response({"status": "error", "message": "Mods are not supported for this instance type"}, status=403)

    mods = await instances_service.list_mods(instance)

    if not mods:
        return web.json_response([])

    mods_list = []

    for b in mods:
        mods_list.append(
            {
                "id": b.id,
                "name": b.name,
                "enabled": b.enabled,
                "added_at": str(b.added_at),
                "modified_at": str(b.modified_at),
            }
        )

    return web.json_response(mods_list)


@instance_mods_routes.post("/api/instances/{instance_id}/mods")
@validate_request(AddInstanceModSchema)
async def instance_mod_add(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    instance_id = int(request.match_info.get("instance_id", 0))
    mod_jar = post_data.get("mod_jar", None)

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if not "mods" in instances_service.get_server_capabilities(instance.server_type):
        return web.json_response({"status": "error", "message": "Mods are not supported for this instance type"}, status=403)

    if not mod_jar or not isinstance(mod_jar, web.FileField):
        return web.json_response({"status": "error", "message": "No mod jar provided"}, status=403)

    try:
        await instances_service.add_mod(
            instance,
            mod_jar=mod_jar.file,
            name=get_filename(mod_jar, strip_ext=True),
        )
    except Exception as e:
        logger.error(f"Error adding mod for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to add mod"}, status=500)

    return web.json_response({"status": "success", "message": "Mod successfully added"})


@instance_mods_routes.post("/api/instances/{instance_id}/mods/{mod_id}")
async def instance_mod_edit(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    instance_id = int(request.match_info.get("instance_id", 0))
    mod_id = int(request.match_info.get("mod_id", 0))
    enabled = post_data.get("enabled", None)

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    mod = await instances_service.get_mod(instance, mod_id)

    if not mod:
        return web.json_response({"status": "error", "message": "Mod not found"}, status=404)

    if enabled is None:
        return web.json_response({"status": "error", "message": "No enabled value provided"}, status=403)

    try:
        await instances_service.update_mod(instance, mod, enabled=bool(int(str(enabled))))
    except Exception as e:
        logger.error(f"Error updating mod {mod.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to update mod"}, status=500)

    return web.json_response({"status": "success", "message": "Mod successfully updated"})

@instance_mods_routes.delete("/api/instances/{instance_id}/mods/{mod_id}")
async def instance_mod_delete(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    mod_id = int(request.match_info.get("mod_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    mod = await instances_service.get_mod(instance, mod_id)

    if not mod:
        return web.json_response({"status": "error", "message": "Mod not found"}, status=404)

    try:
        await instances_service.delete_mod(instance, mod)
    except Exception as e:
        logger.error(f"Error deleting mod {mod.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete mod"}, status=500)

    return web.json_response({"status": "success", "message": "Mod successfully deleted"})
