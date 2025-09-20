import logging
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di, get_filename
from mcadmin.services.instances import InstancesService
from mcadmin.utils.validate import validate_request
from mcadmin.schemas.instances import AddInstanceDatapackSchema

instance_datapacks_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@instance_datapacks_routes.get("/instances/{instance_id}/datapacks")
@aiohttp_jinja2.template("instance_datapacks.html")
async def instance_datapacks_template(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    data = {}

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        raise web.HTTPNotFound(text="Instance not found")

    if not "datapacks" in instances_service.get_server_capabilities(instance.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this instance type"}, status=403)

    data["instance"] = instance

    return data


@instance_datapacks_routes.get("/api/instances/{instance_id}/datapacks")
async def instance_datapacks_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if not "datapacks" in instances_service.get_server_capabilities(instance.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this instance type"}, status=403)

    datapacks = await instances_service.list_datapacks(instance)

    if not datapacks:
        return web.json_response([])

    datapacks_list = []

    for b in datapacks:
        datapacks_list.append(
            {
                "id": b.id,
                "name": b.name,
                "enabled": b.enabled,
                "added_at": str(b.added_at),
                "modified_at": str(b.modified_at),
            }
        )

    return web.json_response(datapacks_list)


@instance_datapacks_routes.post("/api/instances/{instance_id}/datapacks")
@validate_request(AddInstanceDatapackSchema)
async def instance_datapack_add(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    instance_id = int(request.match_info.get("instance_id", 0))
    datapack_archive = post_data.get("datapack_archive", None)

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if not "datapacks" in instances_service.get_server_capabilities(instance.server_type):
        return web.json_response({"status": "error", "message": "Datapacks are not supported for this instance type"}, status=403)

    if not datapack_archive or not isinstance(datapack_archive, web.FileField):
        return web.json_response({"status": "error", "message": "No datapack archive provided"}, status=403)

    try:
        await instances_service.add_datapack(
            instance,
            datapack_archive=datapack_archive.file,
            name=get_filename(datapack_archive, strip_ext=True),
        )
    except Exception as e:
        logger.error(f"Error adding datapack for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to add datapack"}, status=500)

    return web.json_response({"status": "success", "message": "Datapack successfully added"})


@instance_datapacks_routes.post("/api/instances/{instance_id}/datapacks/{datapack_id}")
async def instance_datapack_edit(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    instance_id = int(request.match_info.get("instance_id", 0))
    datapack_id = int(request.match_info.get("datapack_id", 0))
    enabled = post_data.get("enabled", None)

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    datapack = await instances_service.get_datapack(instance, datapack_id)

    if not datapack:
        return web.json_response({"status": "error", "message": "Datapack not found"}, status=404)

    if enabled is None:
        return web.json_response({"status": "error", "message": "No enabled value provided"}, status=403)

    try:
        await instances_service.update_datapack(instance, datapack, enabled=bool(int(str(enabled))))
    except Exception as e:
        logger.error(f"Error updating datapack {datapack.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to update datapack"}, status=500)

    return web.json_response({"status": "success", "message": "Datapack successfully updated"})


@instance_datapacks_routes.delete("/api/instances/{instance_id}/datapacks/{datapack_id}")
async def instance_datapack_delete(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))
    datapack_id = int(request.match_info.get("datapack_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    datapack = await instances_service.get_datapack(instance, datapack_id)

    if not datapack:
        return web.json_response({"status": "error", "message": "Datapack not found"}, status=404)

    try:
        await instances_service.delete_datapack(instance, datapack)
    except Exception as e:
        logger.error(f"Error deleting datapack {datapack.id} for instance {instance.id}: {e}")
        return web.json_response({"status": "error", "message": "Failed to delete datapack"}, status=500)

    return web.json_response({"status": "success", "message": "Datapack successfully deleted"})
