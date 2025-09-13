import asyncio
from typing import BinaryIO
from mcadmin.models.worlds import Worlds
from mcadmin.models.global_properties import GlobalProperties
from mcadmin.models.world_backups import WorldBackups
from mcadmin.models.world_datapacks import WorldDatapacks
from mcadmin.models.world_mods import WorldMods
from mcadmin.services.server import ServerService
from mcadmin.libraries.mc_server import McServerRunner, McServerWorldManager


class WorldsService:
    def __init__(self, *, server_service: ServerService, mc_server_runner: McServerRunner, mc_server_world_manager: McServerWorldManager):
        self._server_service: ServerService = server_service
        self._mc_server_runner: McServerRunner = mc_server_runner
        self._mc_server_world_manager: McServerWorldManager = mc_server_world_manager

        self._log_subscribers: list[asyncio.Queue] = []

    async def create_world(self, *, world_archive: BinaryIO | None = None, **kwargs) -> Worlds:
        world = await Worlds.create(**kwargs)

        try:
            await self._mc_server_world_manager.create_world_instance(
                str(world.id),
                server_type=world.server_type,
                server_version=world.server_version,
                world_archive=world_archive,
            )
        except Exception:
            await world.delete()
            raise

        return world

    async def activate_world(self, world: Worlds) -> None:
        world.active = True

        server_status = self._server_service.get_server_status()

        if server_status == "running":
            await self._server_service.stop_server()

        await self._mc_server_world_manager.activate_world_instance(
            str(world.id),
            server_version=world.server_version,
            server_type=world.server_type,
            properties=await self.gen_world_properties(world),
        )

        await Worlds.filter(active=True).update(active=False)
        await world.save()

        if server_status == "running":
            await self._server_service.start_server()

    async def get_world(self, **kwargs) -> Worlds | None:
        return await Worlds.get_or_none(**kwargs)

    async def update_world(self, world: Worlds, **kwargs) -> None:
        await self.backup_world(world, "auto")

        world.update_from_dict(kwargs)

        if not world.active:
            await world.save()
            return

        server_status = self._server_service.get_server_status()

        if server_status == "running":
            await self._server_service.stop_server()

        await self._mc_server_world_manager.activate_world_instance(
            str(world.id),
            server_version=world.server_version,
            server_type=world.server_type,
            properties=await self.gen_world_properties(world),
        )

        await world.save()

        if server_status == "running":
            await self._server_service.start_server()

    async def delete_world(self, world: Worlds) -> None:
        server_status = self._server_service.get_server_status()

        if world.active and server_status == "running":
            await self._server_service.stop_server()

        await self._mc_server_world_manager.delete_world_instance(str(world.id))

        # clean up related data
        await WorldBackups.filter(world_id=world.id).delete()
        await WorldDatapacks.filter(world_id=world.id).delete()
        await WorldMods.filter(world_id=world.id).delete()

        await world.delete()

    async def list_worlds(self) -> list[Worlds]:
        return await Worlds.all().order_by("-id")

    async def get_active_world(self) -> Worlds | None:
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

        server_status = self._server_service.get_server_status()

        if server_status == "running":
            await self._server_service.stop_server()

        await self._mc_server_world_manager.regen_world_properties(str(active_world.id), properties=await self.gen_world_properties(active_world))

        if server_status == "running":
            await self._server_service.start_server()

    async def set_property(self, key: str, value: str) -> None:
        await GlobalProperties.update_or_create(key=key, defaults={"value": value})

    async def gen_world_properties(self, world: Worlds) -> dict:
        global_properties = {p.key: p.value for p in await GlobalProperties.all()}
        world_properties = world.properties or {}

        return {**global_properties, **world_properties}

    async def list_world_backups(self, world: Worlds) -> list[WorldBackups]:
        return await WorldBackups.filter(world_id=world.id).order_by("-created_at")

    async def backup_world(self, world: Worlds, backup_type: str) -> WorldBackups:
        metadata = {
            "server_version": world.server_version,
        }

        backup = await WorldBackups.create(world_id=world.id, type=backup_type, metadata=metadata)

        try:
            await self._mc_server_world_manager.backup_world_instance(str(world.id), str(backup.id))
        except Exception:
            await backup.delete()
            raise

        return backup

    async def restore_world(self, world: Worlds, backup: WorldBackups) -> None:
        server_status = self._server_service.get_server_status()

        if world.active and server_status == "running":
            await self._server_service.stop_server()

        world.update_from_dict(backup.metadata)

        await self._mc_server_world_manager.restore_world_instance(str(world.id), str(backup.id))

        if not world.active:
            await world.save()
            return

        await self._mc_server_world_manager.activate_world_instance(
            str(world.id),
            server_version=world.server_version,
            server_type=world.server_type,
            properties=await self.gen_world_properties(world),
        )

        await world.save()

        if server_status == "running":
            await self._server_service.start_server()

    async def get_world_backup(self, world: Worlds, backup_id: int) -> WorldBackups | None:
        return await WorldBackups.get_or_none(world_id=world.id, id=backup_id)

    async def delete_world_backup(self, world: Worlds, backup: WorldBackups) -> None:
        await self._mc_server_world_manager.delete_world_instance_backup(str(world.id), str(backup.id))
        await backup.delete()

    async def list_world_datapacks(self, world: Worlds) -> list[WorldDatapacks]:
        return await WorldDatapacks.filter(world_id=world.id).order_by("-added_at")

    async def get_world_datapack(self, world: Worlds, datapack_id: int) -> WorldDatapacks | None:
        return await WorldDatapacks.get_or_none(world_id=world.id, id=datapack_id)

    async def add_world_datapack(self, world: Worlds, *, datapack_archive: BinaryIO, **kwargs) -> WorldDatapacks:
        datapack = await WorldDatapacks.create(world_id=world.id, **kwargs)

        try:
            await self._mc_server_world_manager.add_world_instance_datapack(str(world.id), str(datapack.id), datapack_archive=datapack_archive)
        except Exception:
            await datapack.delete()
            raise

        return datapack

    async def delete_world_datapack(self, world: Worlds, datapack: WorldDatapacks) -> None:
        await self._mc_server_world_manager.delete_world_instance_datapack(str(world.id), str(datapack.id))
        await datapack.delete()

    async def list_world_mods(self, world: Worlds) -> list[WorldMods]:
        return await WorldMods.filter(world_id=world.id).order_by("-added_at")

    async def get_world_mod(self, world: Worlds, mod_id: int) -> WorldMods | None:
        return await WorldMods.get_or_none(world_id=world.id, id=mod_id)

    async def add_world_mod(self, world: Worlds, *, mod_jar: BinaryIO, **kwargs) -> WorldMods:
        mod = await WorldMods.create(world_id=world.id, **kwargs)

        try:
            await self._mc_server_world_manager.add_world_instance_mod(str(world.id), str(mod.id), mod_jar=mod_jar)
        except Exception:
            await mod.delete()
            raise

        return mod

    async def delete_world_mod(self, world: Worlds, mod: WorldMods) -> None:
        await self._mc_server_world_manager.delete_world_instance_mod(str(world.id), str(mod.id))
        await mod.delete()

    def get_level_types(self) -> list[str]:
        return self._mc_server_world_manager.get_level_types()

    def get_min_server_version(self) -> str:
        return self._mc_server_world_manager.get_min_server_version()

    def validate_properties(self, properties: dict) -> None:
        self._mc_server_world_manager.validate_properties(properties)

    def get_server_types(self) -> dict:
        return self._mc_server_world_manager.get_server_types()

    def server_capabilities(self, server_type: str) -> list[str]:
        return self._mc_server_world_manager.server_capabilities(server_type)
