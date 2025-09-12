import logging
import asyncio
import aiohttp_jinja2
from aiohttp import web
from mcadmin.utils.web import get_di
from mcadmin.services.server import ServerService

terminal_routes = web.RouteTableDef()
logger = logging.getLogger(__name__)


@terminal_routes.get("/terminal")
@aiohttp_jinja2.template("terminal.html")
async def terminal_template(request):
    return {}


@terminal_routes.get("/ws/terminal")
async def terminal_ws(request: web.Request) -> web.WebSocketResponse:
    server_service: ServerService = get_di(request).server_service
    ws = web.WebSocketResponse(heartbeat=30, compress=True)

    await ws.prepare(request)

    request.app["websockets"].add(ws)

    try:
        async with server_service.rcon_connect() as command:
            async for msg in ws:
                if msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket connection closed with exception {ws.exception()}")
                    break
                elif msg.type == web.WSMsgType.TEXT:
                    data = msg.data.strip()

                    try:
                        response = await command(data)
                    except Exception as e:
                        logger.error(f"Error occurred while processing command '{data}': {e}")
                        await ws.send_str("RCON server unreachable")
                    else:
                        logger.debug(f"Terminal command received: {data} and responded with: {response}")
                        await ws.send_str(response)
    except Exception as e:
        logger.exception(f"Error in WebSocket logs stream: {e}")
    finally:
        request.app["websockets"].remove(ws) if ws in request.app["websockets"] else None
        await ws.close() if not ws.closed else None

    return ws
