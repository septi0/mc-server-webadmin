import logging
import aiohttp_jinja2
import json
import asyncio
from aiohttp import web
from packaging import version
from mcadmin.utils.web import get_di, validate_request_schema, drain_queue_into_websocket
from mcadmin.services.server import ServerService
from mcadmin.schemas.worlds import CreateWorldSchema, UpdateWorldSchema
from mcadmin.libraries.queue_dispatcher import QueueDispatcher

server_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@server_routes.get("/")
async def root_endpoint(request):
    return web.HTTPFound("/dashboard")


@server_routes.get("/dashboard")
@aiohttp_jinja2.template("dashboard.html")
async def dashboard_get_endpoint(request):
    return {}


@server_routes.get("/settings")
@aiohttp_jinja2.template("settings.html")
async def settings_get_endpoint(request):
    server_service: ServerService = get_di(request).server_service

    data = {
        "level_types": server_service.get_level_types(),
    }

    return data


@server_routes.get("/api/server/status")
async def status_get_handler(request):
    server_service: ServerService = get_di(request).server_service

    try:
        reply = server_service.get_server_status()
    except Exception as e:
        logger.exception(f"Failed to get server status: {e}")
        return web.json_response({"error": str(e)}, status=500)

    return web.json_response(reply)


@server_routes.get("/api/server/info")
async def info_get_handler(request):
    server_service: ServerService = get_di(request).server_service

    info = server_service.get_server_connect_info()
    return web.json_response(info)


@server_routes.post("/api/server/start")
async def start_post_handler(request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.start_server()
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server started successfully")
    return web.json_response({"status": "ok", "message": "Server started successfully"})


@server_routes.post("/api/server/stop")
async def stop_post_handler(request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.stop_server()
    except Exception as e:
        logger.exception(f"Failed to stop server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server stopped successfully")
    return web.json_response({"status": "ok", "message": "Server stopped successfully"})


@server_routes.post("/api/server/restart")
async def restart_post_handler(request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.restart_server()
    except Exception as e:
        logger.exception(f"Failed to restart server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server restarted successfully")
    return web.json_response({"status": "ok", "message": "Server restarted successfully"})


@server_routes.get("/api/server/worlds")
async def worlds_get_handler(request):
    server_service: ServerService = get_di(request).server_service
    worlds = await server_service.list_world_instances()

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


@server_routes.get("/api/server/active-world")
async def active_world_get_handler(request):
    server_service: ServerService = get_di(request).server_service

    active_world = await server_service.get_active_world_instance()

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


@server_routes.post("/api/server/world-create")
@validate_request_schema(CreateWorldSchema)
async def world_create_handler(request):
    server_service: ServerService = get_di(request).server_service
    post_data = await request.post()
    name = post_data.get("name", "")
    server_version = post_data.get("server_version", "")
    world_archive = post_data.get("file", "")
    properties = {}

    min_version = server_service.get_min_server_version()

    if version.parse(server_version) < version.parse(min_version):
        return web.json_response({"status": "error", "message": f"Server version must be {min_version} or greater"}, status=403)

    if not world_archive:
        properties = json.loads(post_data.get("properties", "{}"))

    try:
        server_service.validate_properties(properties)

        world = await server_service.create_world_instance(
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


@server_routes.post("/api/server/world-activate")
async def world_activate_handler(request):
    server_service: ServerService = get_di(request).server_service
    post_data = await request.post()
    world_id = post_data.get("id", "")

    if not world_id:
        return web.json_response({"status": "error", "message": "World ID is required"}, status=403)

    world = await server_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    if world.active:
        return web.json_response({"status": "error", "message": "World is already active"}, status=403)

    try:
        await server_service.activate_world_instance(world)
    except Exception as e:
        logger.exception(f"Failed to activate world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to activate world ({e})"}, status=500)

    logger.info(f"World '{world_id}' activated successfully")
    return web.json_response({"status": "success", "message": "World activated successfully"})


@server_routes.post("/api/server/world-update")
@validate_request_schema(UpdateWorldSchema)
async def world_update_handler(request):
    server_service: ServerService = get_di(request).server_service
    post_data = await request.post()
    world_id = post_data.get("id", "")
    server_version = post_data.get("server_version", "")

    world = await server_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    # ensure desired server version is greater than current one
    if version.parse(server_version) <= version.parse(world.server_version):
        return web.json_response({"status": "error", "message": "Server version must be greater than current version"}, status=403)

    try:
        await server_service.update_world_instance(world, server_version=server_version)
    except Exception as e:
        return web.json_response({"status": "error", "message": f"Failed to update world ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "World updated successfully"})


@server_routes.post("/api/server/world-delete")
async def world_delete_handler(request):
    server_service: ServerService = get_di(request).server_service
    post_data = await request.post()
    world_id = post_data.get("id", "")

    if not world_id:
        return web.json_response({"status": "error", "message": "World ID is required"}, status=403)

    world = await server_service.get_world_instance(id=world_id)

    if not world:
        return web.json_response({"status": "error", "message": "World not found"}, status=404)

    try:
        await server_service.delete_world_instance(world)
    except Exception as e:
        logger.exception(f"Failed to delete world '{world_id}' ({e})")
        return web.json_response({"status": "error", "message": f"Failed to delete world ({e})"}, status=500)

    logger.info(f"World '{world_id}' deleted successfully")
    return web.json_response({"status": "success", "message": "World deleted successfully"})


@server_routes.get("/api/server/global-properties")
async def global_properties_handler(request):
    server_service: ServerService = get_di(request).server_service
    global_properties = await server_service.get_properties()

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


@server_routes.post("/api/server/global-properties")
async def global_properties_update_handler(request):
    server_service: ServerService = get_di(request).server_service
    post_data = await request.post()

    properties = {key: value for key, value in post_data.items()}
    whitelist = properties.get("enforce-whitelist", None)

    if whitelist:
        properties["white-list"] = whitelist

    try:
        server_service.validate_properties(properties)

        await server_service.set_properties(properties)
    except Exception as e:
        logger.exception(f"Failed to update global properties ({e})")
        return web.json_response({"status": "error", "message": f"Failed to update global properties ({e})"}, status=500)

    return web.json_response({"status": "success", "message": "Global properties updated successfully"})

@server_routes.get("/ws/stats")
async def websocket_server_stats(request: web.Request) -> web.WebSocketResponse:
    ev_dispatcher: QueueDispatcher = get_di(request).mc_server_ev_dispatcher
    ws = web.WebSocketResponse(heartbeat=30, compress=True)

    await ws.prepare(request)

    request.app["websockets"].add(ws)

    q = ev_dispatcher.subscribe('stats', scrollback=1)
    listener_task = asyncio.create_task(drain_queue_into_websocket(q, ws))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket connection closed with exception {ws.exception()}")
                break
    except Exception as e:
        logger.exception(f"Error in WebSocket logs stream: {e}")
    finally:
        request.app["websockets"].remove(ws) if ws in request.app["websockets"] else None
        await ws.close() if not ws.closed else None

        listener_task.cancel()
        await asyncio.gather(listener_task, return_exceptions=True)
        ev_dispatcher.unsubscribe(q)

    return ws
