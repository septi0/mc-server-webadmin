import logging
import os
import asyncio
import shutil
import aiofiles
import zipfile
import socket
from typing import BinaryIO
from packaging import version
from .catalog import McServerCatalog
from .properties_generator import McServerPropertiesGenerator
from .backup import McServerBackup
from .datapack import McServerDatapack
from .mod import McServerMod


__all__ = [
    "McServerWorldManagerError",
    "McServerWorldManager",
]

logger = logging.getLogger(__name__)


class McServerWorldManagerError(Exception):
    pass


class McServerWorldManager:
    """Minecraft world instance manager"""

    default_server_ip: str = "0.0.0.0"
    default_server_port: int = 25565
    default_rcon_port: int = 25575

    def __init__(self, work_dir: str, server_config: dict) -> None:
        self._work_dir: str = work_dir
        self._server_config: dict = server_config

    async def create_world_instance(
        self,
        world: str,
        *,
        server_version: str,
        server_type: str,
        world_archive: BinaryIO | None = None,
    ) -> None:
        """Create a new world instance with the given parameters"""
        instance_dir = self.get_instance_dir(world)
        server_catalog = self._server_catalog_factory(server_type, server_version)

        if os.path.exists(instance_dir):
            raise McServerWorldManagerError(f"World instance {world} already exists")

        os.makedirs(instance_dir)

        await server_catalog.download()
        await self._accept_eula(instance_dir)

        if world_archive:
            await self._import_world(instance_dir, world_archive)

        logger.info(f"World instance {world} created successfully")

    async def update_world_instance(self, world: str, *, server_version: str, server_type: str) -> None:
        """Update the server version for an existing world instance"""
        server_catalog = self._server_catalog_factory(server_type, server_version)

        await server_catalog.download()

        logger.info(f"World instance {world} updated successfully")

    async def activate_world_instance(
        self,
        world: str,
        *,
        server_version: str,
        server_type: str,
    ) -> None:
        """Activate the given world instance, setting up server files and linking it to 'current'"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)
        java_bin = self._get_java_bin(server_version)
        server_catalog = self._server_catalog_factory(server_type, server_version)

        await server_catalog.download()

        jvm_args = await server_catalog.get_jvm_args()
        additional_links = server_catalog.get_link_paths()

        await self._link_common_files(instance_dir, additional_links=additional_links)
        await self._gen_start_script(instance_dir, jvm_args, java_bin=java_bin)

        self._link_world_instance_to_current(world)

        logger.info(f"World instance {world} activated successfully")

    async def generate_world_properties(self, world: str, *, properties: dict) -> None:
        """Regenerate the server.properties file for the given world instance"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)
        properties_generator = McServerPropertiesGenerator(
            instance_dir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        await properties_generator.generate(properties)

    async def delete_world_instance(self, world: str) -> None:
        """Delete the given world instance and all its data"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)

        await asyncio.to_thread(shutil.rmtree, instance_dir)

        logger.info(f"Directory for world instance {world} deleted")

    async def backup_world_instance(self, world: str, backup: str) -> None:
        """Create a backup for the given world instance"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)
        backups_dir = self._get_backup_dir(world)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.backup(backup)

    async def restore_world_instance(self, world: str, backup: str) -> None:
        """Restore a backup for the given world instance"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)
        backups_dir = self._get_backup_dir(world)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.restore(backup)

        logger.info(f"World instance {world} restored from backup {backup}")

    async def delete_world_instance_backup(self, world: str, backup: str) -> None:
        """Delete a backup for the given world instance"""
        instance_dir = self.get_instance_dir(world, assert_exists=True)
        backups_dir = self._get_backup_dir(world)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.delete_backup(backup)

    async def add_world_instance_datapack(self, world: str, datapack_name: str, *, datapack_archive: BinaryIO) -> None:
        """Add a datapack to the given world instance"""
        datapacks_dir = self._get_datapacks_dir(world)
        mc_datapack = McServerDatapack(datapacks_dir)

        await mc_datapack.add(datapack_name, datapack_archive=datapack_archive)

    async def delete_world_instance_datapack(self, world: str, datapack_name: str) -> None:
        """Delete a datapack from the given world instance"""
        datapacks_dir = self._get_datapacks_dir(world)
        mc_datapack = McServerDatapack(datapacks_dir)

        await mc_datapack.delete(datapack_name)

    async def add_world_instance_mod(self, world: str, mod_name: str, *, mod_jar: BinaryIO) -> None:
        """Add a mod to the given world instance"""
        mods_dir = self._get_mods_dir(world)
        mc_mod = McServerMod(mods_dir)

        await mc_mod.add(mod_name, mod_jar=mod_jar)

    async def delete_world_instance_mod(self, world: str, mod_name: str) -> None:
        """Delete a mod from the given world instance"""
        mods_dir = self._get_mods_dir(world)
        mc_mod = McServerMod(mods_dir)

        await mc_mod.delete(mod_name)

    def validate_properties(self, properties: dict) -> None:
        """Validate the given properties to ensure they conform to expected types and values for the server.properties file"""
        McServerPropertiesGenerator.validate_properties(properties)

    def get_level_types(self) -> list[str]:
        """Get the list of supported world level types"""
        return McServerPropertiesGenerator.level_types

    def get_min_server_version(self) -> str:
        """Get the minimum supported server version"""
        return McServerPropertiesGenerator.min_server_version

    def get_server_connect_info(self) -> dict:
        """Get the server connection info (IP and port)"""
        info = {}

        display_host = self._server_config.get("display_host")
        display_ip = self._server_config.get("display_ip")
        display_port = self._server_config.get("display_port")

        if display_host:
            info["host"] = display_host
            info["ip"] = display_ip or socket.gethostbyname(info["host"])

        info["ip"] = self._resolve_wildcard_ip(display_ip or info.get("ip") or self._server_config.get("server_ip", self.default_server_ip))
        info["port"] = display_port or self._server_config.get("server_port", self.default_server_port)

        return info

    def get_rcon_connect_info(self) -> dict:
        """Get the RCON connection info (IP and port)"""
        info = {}

        info["port"] = self._server_config.get("rcon_port", self.default_rcon_port)
        info["ip"] = self._resolve_wildcard_ip(self._server_config.get("server_ip", self.default_server_ip))

        return info

    def get_server_types(self) -> dict:
        """Get the supported server types and their capabilities"""
        return McServerCatalog.server_types

    def server_capabilities(self, server_type: str) -> list[str]:
        """Get the capabilities of the given server type"""
        return McServerCatalog.server_types.get(server_type, {}).get("capabilities", [])

    async def _import_world(self, instance_dir: str, world_archive: BinaryIO) -> None:
        logger.info(f"Extracting existing world data archive")

        # unzip archive
        with zipfile.ZipFile(world_archive, "r") as zip_ref:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, zip_ref.extractall, os.path.join(instance_dir, "world"))

    async def _accept_eula(self, instance_dir: str) -> None:
        logger.info(f"Accepting EULA")

        eula_file = os.path.join(instance_dir, "eula.txt")

        async with aiofiles.open(eula_file, "w") as f:
            await f.write("eula=true")

    async def _link_common_files(self, instance_dir: str, *, additional_links: list[str]) -> None:
        logger.info(f"Linking common files for world instance {instance_dir}")

        common_files = ["banned-ips.json", "banned-players.json", "ops.json", "usercache.json", "whitelist.json"]

        for file in common_files:
            src = os.path.join(self._work_dir, file)
            dst = os.path.join(instance_dir, file)

            if not os.path.exists(src):
                async with aiofiles.open(src, "w") as f:
                    await f.write("[]")

            if os.path.islink(dst):
                os.unlink(dst)

            os.symlink(src, dst)
            logger.info(f"Linked {src} to {dst}")

        for src in additional_links:
            link_name = os.path.basename(src)
            dst = os.path.join(instance_dir, link_name)

            if os.path.islink(dst):
                os.unlink(dst)

            if os.path.exists(src):
                os.symlink(src, dst)
                logger.info(f"Linked {src} to {dst}")

    async def _gen_start_script(self, instance_dir: str, jvm_args: list[str], *, java_bin: str) -> None:
        logger.info(f"Generating start script for world instance {instance_dir}")

        start_script = os.path.join(instance_dir, "mcadmin-start.sh")

        async with aiofiles.open(start_script, "w") as f:
            await f.write("#!/usr/bin/env sh\n")
            await f.write(f"MCADMIN_RUNTIME_JAVA_BIN=${{MCADMIN_RUNTIME_JAVA_BIN:-{java_bin}}}\n")
            await f.write(f'$MCADMIN_RUNTIME_JAVA_BIN $MCADMIN_RUNTIME_JVM_ARGS {" ".join(jvm_args)} "$@"\n')

        os.chmod(start_script, 0o755)

    def _resolve_wildcard_ip(self, ip: str) -> str:
        if ip not in ("0.0.0.0", ""):
            return ip

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.connect(("1.1.1.1", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()

        return ip

    def get_instance_dir(self, world: str, *, assert_exists=False) -> str:
        instance_dir = os.path.join(self._work_dir, "worlds", world)

        if assert_exists and not os.path.exists(instance_dir):
            raise McServerWorldManagerError(f"World instance {world} does not exist")

        return instance_dir

    def _get_backup_dir(self, world: str) -> str:
        return os.path.join(self.get_instance_dir(world, assert_exists=True), "backups")

    def _get_datapacks_dir(self, world: str) -> str:
        return os.path.join(self.get_instance_dir(world, assert_exists=True), "datapacks")

    def _get_mods_dir(self, world: str) -> str:
        return os.path.join(self.get_instance_dir(world, assert_exists=True), "mods")

    def _link_world_instance_to_current(self, world: str) -> None:
        logger.info(f"Linking world instance {world} to 'current'")

        current_link = os.path.join(self._work_dir, "current")
        instance_dir = self.get_instance_dir(world, assert_exists=True)

        if os.path.islink(current_link) or os.path.exists(current_link):
            os.remove(current_link)

        os.symlink(instance_dir, current_link)

    def _get_java_bin(self, server_version: str) -> str:
        if self._server_config.get("java_bin", ""):
            return self._server_config["java_bin"]
        else:
            v = version.parse(server_version)

            if v >= version.parse("1.21"):
                return "java-21"
            elif v >= version.parse("1.17"):
                return "java-17"
            else:
                return "java-8"

    def _server_catalog_factory(self, server_type: str, server_version: str) -> McServerCatalog:
        versions_dir = os.path.join(self._work_dir, "versions")
        java_bin = self._get_java_bin(server_version)

        return McServerCatalog(versions_dir, server_type, server_version, java_bin=java_bin)
