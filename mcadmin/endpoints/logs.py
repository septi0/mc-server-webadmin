import logging
import asyncio
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di, drain_queue_into_websocket
from mcadmin.libraries.queue_dispatcher import QueueDispatcher

routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@routes.get("/logs")
@aiohttp_jinja2.template("logs.html")
async def logs_get_endpoint(request):
    return {}


@routes.get("/ws/logs")
async def websocket_logs(request: web.Request) -> web.WebSocketResponse:
    ev_dispatcher: QueueDispatcher = get_di(request).mc_server_ev_dispatcher
    ws = web.WebSocketResponse(heartbeat=30, compress=True)

    await ws.prepare(request)

    request.app["websockets"].add(ws)

    q = ev_dispatcher.subscribe('logs', scrollback=20)
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
