import logging
import json
from aiohttp import web
from packaging import version
from mcadmin.utils.web import get_di
from mcadmin.utils.validate import validate_request
from mcadmin.services.instances import InstancesService
from mcadmin.schemas.instances import CreateInstanceSchema, UpdateInstanceSchema

instances_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@instances_routes.get("/api/instances")
async def instances_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instances = await instances_service.list_instances()

    if not instances:
        return web.json_response([])

    instances_list = []
    server_types = instances_service.get_server_types()

    for instance in instances:
        instances_list.append(
            {
                "id": instance.id,
                "name": instance.name,
                "server_version": instance.server_version,
                "server_type": instance.server_type,
                "active": instance.active,
                "created_at": str(instance.created_at),
                "updated_at": str(instance.updated_at),
                "server_capabilities": server_types.get(instance.server_type, {}).get("capabilities", []),
            }
        )

    return web.json_response(instances_list)


@instances_routes.get("/api/instances/active")
async def active_instance_get(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    active_instance = await instances_service.get_active_instance()

    if not active_instance:
        return web.json_response({})

    active_instance_dict = {
        "id": active_instance.id,
        "name": active_instance.name,
        "server_version": active_instance.server_version,
        "server_type": active_instance.server_type,
        "created_at": str(active_instance.created_at),
        "updated_at": str(active_instance.updated_at),
    }

    return web.json_response(active_instance_dict)


@instances_routes.post("/api/instances")
@validate_request(CreateInstanceSchema)
async def instance_create(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    name = str(post_data.get("name", ""))
    server_version = str(post_data.get("server_version", ""))
    server_type = str(post_data.get("server_type", "vanilla"))
    world_archive = post_data.get("world_archive", None)

    min_version = instances_service.get_min_server_version()

    if version.parse(server_version) < version.parse(min_version):
        return web.json_response({"status": "error", "message": f"Server version must be {min_version} or greater"}, status=403)

    if not world_archive or not isinstance(world_archive, web.FileField):
        properties = json.loads(str(post_data.get("properties", "{}")))
        world_archive = None
    else:
        properties = {}
        world_archive = world_archive.file

    try:
        instances_service.validate_properties(properties)

        instance = await instances_service.create_instance(
            name=name,
            server_version=server_version,
            server_type=server_type,
            properties=properties,
            world_archive=world_archive,
        )
    except Exception as e:
        logger.exception(f"Failed to create instance '{name}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to create instance ({e})"}, status=500)

    logger.info(f"Instance '{instance.id}' created successfully")
    return web.json_response({"status": "success", "message": "Instance created successfully"})


@instances_routes.post("/api/instances/{instance_id}")
@validate_request(UpdateInstanceSchema)
async def instance_update(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    post_data = await request.post()

    instance_id = int(request.match_info.get("instance_id", 0))
    server_version = str(post_data.get("server_version", ""))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if version.parse(server_version) <= version.parse(instance.server_version):
        return web.json_response({"status": "error", "message": "Server version must be greater than current version"}, status=403)

    try:
        await instances_service.update_instance(instance, server_version=server_version)
    except Exception as e:
        return web.json_response({"status": "error", "message": f"Failed to update instance ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "Instance updated successfully"})


@instances_routes.delete("/api/instances/{instance_id}")
async def instance_delete(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    try:
        await instances_service.delete_instance(instance)
    except Exception as e:
        logger.exception(f"Failed to delete instance '{instance_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete instance ({e})"}, status=500)

    logger.info(f"Instance '{instance_id}' deleted successfully")
    return web.json_response({"status": "success", "message": "Instance deleted successfully"})


@instances_routes.post("/api/instances/{instance_id}/activate")
async def instance_activate(request: web.Request):
    instances_service: InstancesService = get_di(request).instances_service

    instance_id = int(request.match_info.get("instance_id", 0))

    instance = await instances_service.get_instance(id=instance_id)

    if not instance:
        return web.json_response({"status": "error", "message": "Instance not found"}, status=404)

    if instance.active:
        return web.json_response({"status": "error", "message": "Instance is already active"}, status=403)

    try:
        await instances_service.activate_instance(instance)
    except Exception as e:
        logger.exception(f"Failed to activate instance '{instance_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to activate instance ({e})"}, status=500)

    logger.info(f"Instance '{instance_id}' activated successfully")
    return web.json_response({"status": "success", "message": "Instance activated successfully"})
