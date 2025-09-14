import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable
from mcadmin.models.global_properties import GlobalProperties
from mcadmin.libraries.mc_server import McServerRunner, McServerInstMgr
from mcadmin.libraries.mc_rcon import MCRcon


class ServerService:
    def __init__(self, *, mc_server_runner: McServerRunner, mc_server_inst_mgr: McServerInstMgr):
        self._mc_server_runner: McServerRunner = mc_server_runner
        self._mc_server_inst_mgr: McServerInstMgr = mc_server_inst_mgr

        self._log_subscribers: list[asyncio.Queue] = []

    def get_server_status(self) -> str:
        return self._mc_server_runner.get_server_status()

    def get_server_stats(self) -> dict:
        return self._mc_server_runner.get_server_stats()

    async def start_server(self) -> None:
        await self._mc_server_runner.start_server()

    async def stop_server(self) -> None:
        await self._mc_server_runner.stop_server()

    async def restart_server(self) -> None:
        await self._mc_server_runner.restart_server()

    @asynccontextmanager
    async def rcon_connect(self) -> AsyncIterator[Callable[[str], Awaitable[str]]]:
        connect_info = self._mc_server_inst_mgr.get_rcon_connect_info()
        prop = await GlobalProperties.get(key="rcon.password")

        conn = MCRcon(connect_info["ip"], prop.value)

        try:
            yield conn.command
        finally:
            await conn.disconnect()

    def get_server_connect_info(self) -> dict:
        return self._mc_server_inst_mgr.get_server_connect_info()
