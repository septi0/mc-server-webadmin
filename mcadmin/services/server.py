import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator, Awaitable, BinaryIO, Callable
from mcadmin.models.worlds import Worlds
from mcadmin.models.global_properties import GlobalProperties
from mcadmin.libraries.mc_server import McServerRunner, McServerConfigurator, McServerPropertiesGenerator
from mcadmin.libraries.mc_rcon import MCRcon


class ServerService:
    def __init__(self, *, mc_server_runner: McServerRunner, mc_server_configurator: McServerConfigurator):
        self._mc_server_runner: McServerRunner = mc_server_runner
        self._mc_server_configurator: McServerConfigurator = mc_server_configurator

        self._log_subscribers: list[asyncio.Queue] = []

    def get_server_status(self) -> str:
        return self._mc_server_runner.get_server_status()

    def get_server_stats(self) -> dict:
        return self._mc_server_runner.get_server_stats()

    async def start_server(self) -> None:
        try:
            await self._mc_server_runner.start_server()
        except Exception as e:
            if str(e) == "server.jar not found":
                raise Exception("No active world set. Activate a world from the Settings menu") from None

            raise e

    async def stop_server(self) -> None:
        await self._mc_server_runner.stop_server()

    async def restart_server(self) -> None:
        await self._mc_server_runner.restart_server()

    async def create_world_instance(self, *, world_archive: BinaryIO | None = None, **kwargs) -> Worlds:
        world = await Worlds.create(**kwargs)

        try:
            await self._mc_server_configurator.create_world_instance(str(world.id), world_archive=world_archive)
        except Exception:
            await world.delete()
            raise

        return world

    async def activate_world_instance(self, world: Worlds) -> None:
        world.active = True

        server_status = self.get_server_status()

        if server_status == "running":
            await self.stop_server()

        await self._mc_server_configurator.activate_world_instance(
            str(world.id),
            server_version=world.server_version,
            server_type=world.server_type,
            properties=await self.gen_world_instance_properties(world),
        )

        await Worlds.filter(active=True).update(active=False)
        await world.save()

        if server_status == "running":
            await self.start_server()

    async def get_world_instance(self, **kwargs) -> Worlds | None:
        return await Worlds.get_or_none(**kwargs)

    async def update_world_instance(self, world: Worlds, **kwargs) -> None:
        world.update_from_dict(kwargs)

        if not world.active:
            await world.save()
            return

        server_status = self.get_server_status()

        if server_status == "running":
            await self.stop_server()

        await self._mc_server_configurator.activate_world_instance(
            str(world.id),
            server_version=world.server_version,
            server_type=world.server_type,
            properties=await self.gen_world_instance_properties(world),
        )

        await world.save()

        if server_status == "running":
            await self.start_server()

    async def delete_world_instance(self, world: Worlds) -> None:
        server_status = self.get_server_status()

        if world.active and server_status == "running":
            await self.stop_server()

        await self._mc_server_configurator.delete_world_instance(str(world.id))
        await world.delete()

    async def list_world_instances(self) -> list[Worlds]:
        return await Worlds.all().order_by("-id")

    async def get_active_world_instance(self) -> Worlds | None:
        return await Worlds.get_or_none(active=True)

    async def get_properties(self) -> list[GlobalProperties]:
        return await GlobalProperties.all()

    async def get_property(self, key: str) -> GlobalProperties | None:
        return await GlobalProperties.get_or_none(key=key)

    async def set_properties(self, properties: dict) -> None:
        for key, value in properties.items():
            await GlobalProperties.update_or_create(key=key, defaults={"value": value})
            
        active_world = await Worlds.get_or_none(active=True)

        if not active_world:
            return

        server_status = self.get_server_status()

        if server_status == "running":
            await self.stop_server()

        await self._mc_server_configurator.regen_world_properties(
            str(active_world.id),
            properties=await self.gen_world_instance_properties(active_world)
        )

        if server_status == "running":
            await self.start_server()

    async def set_property(self, key: str, value: str) -> None:
        await GlobalProperties.update_or_create(key=key, defaults={"value": value})

    async def gen_world_instance_properties(self, world: Worlds) -> dict:
        global_properties = {p.key: p.value for p in await GlobalProperties.all()}
        world_properties = world.properties or {}

        return {**global_properties, **world_properties}

    @asynccontextmanager
    async def rcon_connect(self) -> AsyncIterator[Callable[[str], Awaitable[str]]]:
        connect_info = self._mc_server_configurator.get_rcon_connect_info()
        prop = await GlobalProperties.get(key="rcon.password")
        connected = False

        conn = MCRcon(connect_info["ip"], prop.value)

        try:
            yield conn.command
        finally:
            await conn.disconnect()

    def get_server_connect_info(self) -> dict:
        return self._mc_server_configurator.get_server_connect_info()

    def get_level_types(self) -> list[str]:
        return McServerPropertiesGenerator.level_types

    def get_min_server_version(self) -> str:
        return McServerPropertiesGenerator.min_server_version

    def validate_properties(self, properties: dict) -> None:
        McServerPropertiesGenerator.validate_properties(properties)