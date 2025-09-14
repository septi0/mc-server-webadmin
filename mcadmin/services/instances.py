import asyncio
from typing import BinaryIO
from tortoise.transactions import in_transaction
from mcadmin.models.instances import Instances
from mcadmin.models.global_properties import GlobalProperties
from mcadmin.models.instance_backups import InstanceBackups
from mcadmin.models.instance_datapacks import InstanceDatapacks
from mcadmin.models.instance_mods import InstanceMods
from mcadmin.services.server import ServerService
from mcadmin.libraries.mc_server import McServerRunner, McServerInstMgr


class InstancesService:

    def __init__(
        self,
        *,
        server_service: ServerService,
        mc_server_runner: McServerRunner,
        mc_server_inst_mgr: McServerInstMgr,
    ) -> None:
        self._server_service: ServerService = server_service
        self._mc_server_runner: McServerRunner = mc_server_runner
        self._mc_server_inst_mgr: McServerInstMgr = mc_server_inst_mgr

        self._log_subscribers: list[asyncio.Queue] = []

    async def create_instance(self, *, world_archive: BinaryIO | None = None, **kwargs) -> Instances:
        await self._mc_server_inst_mgr.download_version(kwargs["server_type"], kwargs["server_version"])

        async with in_transaction():
            instance = await Instances.create(**kwargs)

            instance_name = str(instance.id)

            await self._mc_server_inst_mgr.create_instance(
                instance_name,
                world_archive=world_archive,
                server_type=instance.server_type,
                server_version=instance.server_version,
            )

        return instance

    async def activate_instance(self, instance: Instances) -> None:
        await self._mc_server_inst_mgr.download_version(instance.server_type, instance.server_version)

        await self._provision_and_activate(instance)

    async def get_instance(self, **kwargs) -> Instances | None:
        return await Instances.get_or_none(**kwargs)

    async def update_instance(self, instance: Instances, **kwargs) -> None:
        await self._mc_server_inst_mgr.download_version(instance.server_type, instance.server_version)
        await self.create_backup(instance, "auto")

        async with in_transaction():
            instance.update_from_dict(kwargs)
            await instance.save()

            instance_name = str(instance.id)

            await self._mc_server_inst_mgr.update_instance(
                instance_name,
                server_type=instance.server_type,
                server_version=instance.server_version,
            )

        if not instance.active:
            return

        await self._provision_and_activate(instance)

    async def delete_instance(self, instance: Instances) -> None:
        server_status = self._server_service.get_server_status()

        if instance.active and server_status == "running":
            await self._server_service.stop_server()

        async with in_transaction():
            instance_name = str(instance.id)

            await InstanceBackups.filter(instance_id=instance.id).delete()
            await InstanceDatapacks.filter(instance_id=instance.id).delete()
            await InstanceMods.filter(instance_id=instance.id).delete()
            await instance.delete()

            await self._mc_server_inst_mgr.delete_instance(instance_name)

    async def list_instances(self) -> list[Instances]:
        return await Instances.all().order_by("-id")

    async def get_active_instance(self) -> Instances | None:
        return await Instances.get_or_none(active=True)

    async def get_properties(self) -> list[GlobalProperties]:
        return await GlobalProperties.all()

    async def get_property(self, key: str) -> GlobalProperties | None:
        return await GlobalProperties.get_or_none(key=key)

    async def set_properties(self, properties: dict) -> None:
        server_status = self._server_service.get_server_status()
        active_instance = await Instances.get_or_none(active=True)

        if server_status == "running":
            await self._server_service.stop_server()

        async with in_transaction():
            for key, value in properties.items():
                await GlobalProperties.update_or_create(key=key, defaults={"value": value})

            if active_instance:
                instance = str(active_instance.id)
                properties = await self.get_joined_properties(active_instance)

                await self._mc_server_inst_mgr.gen_properties(instance, properties=properties)

        if server_status == "running":
            await self._server_service.start_server()

    async def set_property(self, key: str, value: str) -> None:
        await GlobalProperties.update_or_create(key=key, defaults={"value": value})

    async def get_joined_properties(self, instance: Instances) -> dict:
        global_properties = {p.key: p.value for p in await GlobalProperties.all()}
        instance_properties = instance.properties or {}

        return {**global_properties, **instance_properties}

    async def list_backups(self, instance: Instances) -> list[InstanceBackups]:
        return await InstanceBackups.filter(instance_id=instance.id).order_by("-created_at")

    async def create_backup(self, instance: Instances, backup_type: str) -> InstanceBackups:
        metadata = await self._gen_backup_metadata(instance)

        async with in_transaction():
            backup = await InstanceBackups.create(instance_id=instance.id, type=backup_type, metadata=metadata)

            instance_name = str(instance.id)
            backup_name = str(backup.id)

            await self._mc_server_inst_mgr.create_backup(instance_name, backup_name)

        return backup

    async def restore_backup(self, instance: Instances, backup: InstanceBackups) -> None:
        if instance.id != backup.instance_id:
            raise ValueError("Backup does not belong to the specified instance")

        server_status = self._server_service.get_server_status()

        if instance.active and server_status == "running":
            await self._server_service.stop_server()

        async with in_transaction():
            await self._restore_from_metadata(instance, backup)

            instance_name = str(instance.id)
            backup_name = str(backup.id)

            await self._mc_server_inst_mgr.restore_backup(instance_name, backup_name)

        if not instance.active:
            await instance.save()
            return

        await self._provision_and_activate(instance)

        if server_status == "running":
            await self._server_service.start_server()

    async def get_backup(self, instance: Instances, backup_id: int) -> InstanceBackups | None:
        return await InstanceBackups.get_or_none(instance_id=instance.id, id=backup_id)

    async def delete_backup(self, instance: Instances, backup: InstanceBackups) -> None:
        if instance.id != backup.instance_id:
            raise ValueError("Backup does not belong to the specified instance")

        async with in_transaction():
            await backup.delete()

            instance_name = str(instance.id)
            backup_name = str(backup.id)

            await self._mc_server_inst_mgr.delete_backup(instance_name, backup_name)

    async def list_datapacks(self, instance: Instances) -> list[InstanceDatapacks]:
        return await InstanceDatapacks.filter(instance_id=instance.id).order_by("-added_at")

    async def get_datapack(self, instance: Instances, datapack_id: int) -> InstanceDatapacks | None:
        return await InstanceDatapacks.get_or_none(instance_id=instance.id, id=datapack_id)

    async def add_datapack(self, instance: Instances, *, datapack_archive: BinaryIO, **kwargs) -> InstanceDatapacks:
        async with in_transaction():
            datapack = await InstanceDatapacks.create(instance_id=instance.id, **kwargs)

            instance_name = str(instance.id)
            datapack_name = str(datapack.id)

            await self._mc_server_inst_mgr.add_datapack(instance_name, datapack_name, datapack_archive=datapack_archive)

        return datapack

    async def delete_datapack(self, instance: Instances, datapack: InstanceDatapacks) -> None:
        if instance.id != datapack.instance_id:
            raise ValueError("Datapack does not belong to the specified instance")

        async with in_transaction():
            await datapack.delete()

            instance_name = str(instance.id)
            datapack_name = str(datapack.id)

            await self._mc_server_inst_mgr.delete_datapack(instance_name, datapack_name)

    async def list_mods(self, instance: Instances) -> list[InstanceMods]:
        return await InstanceMods.filter(instance_id=instance.id).order_by("-added_at")

    async def get_mod(self, instance: Instances, mod_id: int) -> InstanceMods | None:
        return await InstanceMods.get_or_none(instance_id=instance.id, id=mod_id)

    async def add_mod(self, instance: Instances, *, mod_jar: BinaryIO, **kwargs) -> InstanceMods:
        async with in_transaction():
            mod = await InstanceMods.create(instance_id=instance.id, **kwargs)

            instance_name = str(instance.id)
            mod_name = str(mod.id)

            await self._mc_server_inst_mgr.add_mod(instance_name, mod_name, mod_jar=mod_jar)

        return mod

    async def delete_mod(self, instance: Instances, mod: InstanceMods) -> None:
        if instance.id != mod.instance_id:
            raise ValueError("Mod does not belong to the specified instance")

        async with in_transaction():
            await mod.delete()

            instance_name = str(instance.id)
            mod_name = str(mod.id)

            await self._mc_server_inst_mgr.delete_mod(instance_name, mod_name)

    def get_level_types(self) -> list[str]:
        return self._mc_server_inst_mgr.get_level_types()

    def get_min_server_version(self) -> str:
        return self._mc_server_inst_mgr.get_min_server_version()

    def validate_properties(self, properties: dict) -> None:
        self._mc_server_inst_mgr.validate_properties(properties)

    def get_server_types(self) -> dict:
        return self._mc_server_inst_mgr.get_server_types()

    def get_server_capabilities(self, server_type: str) -> list[str]:
        return self._mc_server_inst_mgr.get_server_capabilities(server_type)

    async def _provision_and_activate(self, instance: Instances) -> None:
        # flag all instances as inactive
        await Instances.filter(active=True).update(active=False)

        server_status = self._server_service.get_server_status()

        if server_status == "running":
            await self._server_service.stop_server()

        async with in_transaction():
            instance.active = True
            await instance.save()

            instance_name = str(instance.id)
            properties = await self.get_joined_properties(instance)

            await self._mc_server_inst_mgr.gen_properties(instance_name, properties=properties)
            await self._mc_server_inst_mgr.activate_instance(instance_name)

        if server_status == "running":
            await self._server_service.start_server()

    async def _gen_backup_metadata(self, instance: Instances) -> dict:
        metadata = {}
        datapacks_fields = ["name", "added_at"]
        mods_fields = ["name", "added_at"]

        metadata["instance"] = {"server_version": instance.server_version, "server_type": instance.server_type}
        metadata["datapacks"] = [{field: str(getattr(dp, field)) for field in datapacks_fields} for dp in await InstanceDatapacks.filter(instance_id=instance.id)]
        metadata["mods"] = [{field: str(getattr(mod, field)) for field in mods_fields} for mod in await InstanceMods.filter(instance_id=instance.id)]

        return metadata

    async def _restore_from_metadata(self, instance: Instances, backup: InstanceBackups) -> None:
        metadata = backup.metadata

        if not metadata:
            return

        if metadata.get("instance") is not None:
            instance.update_from_dict(metadata["instance"])
            await instance.save()

        if metadata.get("datapacks") is not None:
            # delete existing datapacks
            await InstanceDatapacks.filter(instance_id=instance.id).delete()

            # add datapacks from metadata
            for dp in metadata["datapacks"]:
                await InstanceDatapacks.create(instance_id=instance.id, **dp)

        if metadata.get("mods") is not None:
            # delete existing mods
            await InstanceMods.filter(instance_id=instance.id).delete()

            # add mods from metadata
            for mod in metadata["mods"]:
                await InstanceMods.create(instance_id=instance.id, **mod)