import asyncio
from types import SimpleNamespace
from aiohttp import web
from mcadmin.libraries.queue_dispatcher import EventQueue

__all__ = ["get_di", "shutdown_websockets", "drain_queue_into_websocket"]


async def shutdown_websockets(app: web.Application) -> None:
    while app["websockets"]:
        ws = app["websockets"].pop()
        await ws.close()


async def drain_queue_into_websocket(q: EventQueue, ws: web.WebSocketResponse):
    while not ws.closed:
        try:
            msg = await q.get()

            if type(msg) is str:
                await ws.send_str(msg)
            elif type(msg) is dict:
                await ws.send_json(msg)
        except asyncio.CancelledError:
            break

        q.task_done()


def get_di(request: web.Request) -> SimpleNamespace:
    return request.app["di"]


def get_filename(file_obj: web.FileField, *, strip_ext: bool = False) -> str:
    filename = getattr(file_obj, "filename", "unknown")

    if strip_ext:
        filename = filename.rsplit(".", 1)[0]
    return filename
