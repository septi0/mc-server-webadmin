import logging
import asyncio
from aiohttp import web
from mcadmin.utils.web import get_di, drain_queue_into_websocket
from mcadmin.services.server import ServerService
from mcadmin.libraries.queue_dispatcher import QueueDispatcher
from mcadmin.utils.validate import require_roles

server_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@server_routes.get("/api/server/status")
@require_roles(["user", "admin"])
async def status_get(request: web.Request):
    server_service: ServerService = get_di(request).server_service

    try:
        reply = server_service.get_server_status()
    except Exception as e:
        logger.exception(f"Failed to get server status: {e}")
        return web.json_response({"error": str(e)}, status=500)

    return web.json_response(reply)


@server_routes.get("/api/server/info")
@require_roles(["user", "admin"])
async def info_get(request: web.Request):
    server_service: ServerService = get_di(request).server_service

    info = server_service.get_server_connect_info()
    return web.json_response(info)


@server_routes.post("/api/server/start")
@require_roles(["user", "admin"])
async def start_post(request: web.Request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.start_server()
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server started successfully")
    return web.json_response({"status": "ok", "message": "Server started successfully"})


@server_routes.post("/api/server/stop")
@require_roles(["user", "admin"])
async def stop_post(request: web.Request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.stop_server()
    except Exception as e:
        logger.exception(f"Failed to stop server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server stopped successfully")
    return web.json_response({"status": "ok", "message": "Server stopped successfully"})


@server_routes.post("/api/server/restart")
@require_roles(["user", "admin"])
async def restart_post(request: web.Request):
    server_service: ServerService = get_di(request).server_service

    try:
        await server_service.restart_server()
    except Exception as e:
        logger.exception(f"Failed to restart server: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

    logger.info("Server restarted successfully")
    return web.json_response({"status": "ok", "message": "Server restarted successfully"})


@server_routes.get("/ws/server/stats")
@require_roles(["user", "admin"])
async def stats_ws(request: web.Request) -> web.WebSocketResponse:
    ev_dispatcher: QueueDispatcher = get_di(request).mc_server_ev_dispatcher
    ws = web.WebSocketResponse(heartbeat=30, compress=True)

    await ws.prepare(request)

    request.app["websockets"].add(ws)

    q = ev_dispatcher.subscribe("stats", scrollback=1)
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
