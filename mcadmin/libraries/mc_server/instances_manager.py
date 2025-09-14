import json
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
    "McServerInstMgrError",
    "McServerInstMgr",
]

logger = logging.getLogger(__name__)


class McServerInstMgrError(Exception):
    pass


class McServerInstMgr:
    """Minecraft instances manager"""

    default_server_ip: str = "0.0.0.0"
    default_server_port: int = 25565
    default_rcon_port: int = 25575

    def __init__(self, work_dir: str, server_config: dict) -> None:
        self._work_dir: str = work_dir
        self._server_config: dict = server_config

        self._link_paths: list[str] = ["banned-ips.json", "banned-players.json", "ops.json", "usercache.json", "whitelist.json"]

    async def create_instance(self, instance: str, *, server_type: str, server_version: str, world_archive: BinaryIO | None = None) -> None:
        """Create a new instance with the given parameters"""
        instance_dir = self.get_instance_dir(instance)

        if os.path.exists(instance_dir):
            raise McServerInstMgrError(f"Instance {instance} already exists")

        os.makedirs(instance_dir)

        if world_archive:
            await self._import_world(instance_dir, world_archive)

        await self._set_server_info(instance_dir, server_type=server_type, server_version=server_version)
        await self._accept_eula(instance_dir)

        logger.info(f"Instance {instance} created successfully")

    async def update_instance(self, instance: str, *, server_type: str, server_version: str) -> None:
        """Update the server version for an existing instance"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)

        await self._set_server_info(instance_dir, server_type=server_type, server_version=server_version)

        logger.info(f"Instance {instance} updated successfully")

    async def activate_instance(self, instance: str) -> None:
        """Activate the given instance, setting up server files and linking it to 'current'"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)
        info = await self._get_server_info(instance_dir)

        java_bin = self._get_java_bin(info.get("server_version", ""))
        catalog = self._catalog_factory(info.get("server_type", ""), info.get("server_version", ""))

        jvm_args = await catalog.get_jvm_args()
        additional_links = catalog.get_link_paths()

        await self._link_common_files(instance_dir, additional_links=additional_links)
        await self._gen_start_script(instance_dir, jvm_args, java_bin=java_bin)
        self._link_instance_to_current(instance)

        logger.info(f"Instance {instance} activated successfully")

    async def delete_instance(self, instance: str) -> None:
        """Delete the given instance and all its data"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)

        await asyncio.to_thread(shutil.rmtree, instance_dir)

        logger.info(f"Directory for instance {instance} deleted")

    async def create_backup(self, instance: str, backup: str) -> None:
        """Create a backup for the given instance"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)
        backups_dir = self._get_backup_dir(instance)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.backup(backup)

    async def restore_backup(self, instance: str, backup: str) -> None:
        """Restore a backup for the given instance"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)
        backups_dir = self._get_backup_dir(instance)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.restore(backup)

        logger.info(f"Instance {instance} restored from backup {backup}")

    async def delete_backup(self, instance: str, backup: str) -> None:
        """Delete a backup for the given instance"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)
        backups_dir = self._get_backup_dir(instance)
        mc_backup = McServerBackup(instance_dir, backups_dir)

        await mc_backup.delete_backup(backup)

    async def add_datapack(self, instance: str, datapack_name: str, *, datapack_archive: BinaryIO) -> None:
        """Add a datapack to the given instance"""
        datapacks_dir = self._get_datapacks_dir(instance)
        mc_datapack = McServerDatapack(datapacks_dir)

        await mc_datapack.add(datapack_name, datapack_archive=datapack_archive)

    async def delete_datapack(self, instance: str, datapack_name: str) -> None:
        """Delete a datapack from the given instance"""
        datapacks_dir = self._get_datapacks_dir(instance)
        mc_datapack = McServerDatapack(datapacks_dir)

        await mc_datapack.delete(datapack_name)

    async def add_mod(self, instance: str, mod_name: str, *, mod_jar: BinaryIO) -> None:
        """Add a mod to the given instance"""
        mods_dir = self._get_mods_dir(instance)
        mc_mod = McServerMod(mods_dir)

        await mc_mod.add(mod_name, mod_jar=mod_jar)

    async def delete_mod(self, instance: str, mod_name: str) -> None:
        """Delete a mod from the given instance"""
        mods_dir = self._get_mods_dir(instance)
        mc_mod = McServerMod(mods_dir)

        await mc_mod.delete(mod_name)

    async def download_version(self, server_type: str, server_version: str) -> None:
        catalog = self._catalog_factory(server_type, server_version)

        await catalog.download()

    async def gen_properties(self, instance: str, *, properties: dict) -> None:
        """Regenerate the server.properties file for the given instance"""
        instance_dir = self.get_instance_dir(instance, assert_exists=True)
        properties_generator = McServerPropertiesGenerator(
            instance_dir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        await properties_generator.generate(properties)

    def validate_properties(self, properties: dict) -> None:
        """Validate the given properties to ensure they conform to expected types and values for the server.properties file"""
        McServerPropertiesGenerator.validate_properties(properties)

    def get_level_types(self) -> list[str]:
        """Get the list of supported level types"""
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

    def get_server_capabilities(self, server_type: str) -> list[str]:
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
        logger.info(f"Linking common files for instance {instance_dir}")

        links = [os.path.join(self._work_dir, f) for f in self._link_paths] + additional_links

        for src in links:
            link_name = os.path.basename(src)
            dst = os.path.join(instance_dir, link_name)

            if not os.path.exists(src) and link_name.endswith(".json"):
                async with aiofiles.open(src, "w") as f:
                    await f.write("[]")

            if os.path.islink(dst):
                os.unlink(dst)

            os.symlink(src, dst)
            logger.info(f"Linked {src} to {dst}")

    async def _gen_start_script(self, instance_dir: str, jvm_args: list[str], *, java_bin: str) -> None:
        logger.info(f"Generating start script for instance {instance_dir}")

        start_script = os.path.join(instance_dir, "mcadmin-start.sh")

        async with aiofiles.open(start_script, "w") as f:
            await f.write("#!/usr/bin/env sh\n")
            await f.write(f"MCADMIN_RUNTIME_JAVA_BIN=${{MCADMIN_RUNTIME_JAVA_BIN:-{java_bin}}}\n")
            await f.write(f'$MCADMIN_RUNTIME_JAVA_BIN $MCADMIN_RUNTIME_JVM_ARGS {" ".join(jvm_args)} "$@"\n')

        os.chmod(start_script, 0o755)

    async def _set_server_info(self, instance_dir: str, **kwargs) -> None:
        server_info_file = os.path.join(instance_dir, "server_info.json")

        async with aiofiles.open(server_info_file, "w") as f:
            await f.write(json.dumps(kwargs))

    async def _get_server_info(self, instance_dir: str) -> dict:
        server_info_file = os.path.join(instance_dir, "server_info.json")

        if not os.path.exists(server_info_file):
            raise McServerInstMgrError(f"Server info file does not exist in instance directory {instance_dir}")

        async with aiofiles.open(server_info_file, "r") as f:
            content = await f.read()
            return json.loads(content)

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

    def get_instance_dir(self, instance: str, *, assert_exists=False) -> str:
        instance_dir = os.path.join(self._work_dir, "instances", instance)

        if assert_exists and not os.path.exists(instance_dir):
            raise McServerInstMgrError(f"Instance {instance} does not exist")

        return instance_dir

    def _get_backup_dir(self, instance: str) -> str:
        return os.path.join(self.get_instance_dir(instance, assert_exists=True), "backups")

    def _get_datapacks_dir(self, instance: str) -> str:
        return os.path.join(self.get_instance_dir(instance, assert_exists=True), "world", "datapacks")

    def _get_mods_dir(self, instance: str) -> str:
        return os.path.join(self.get_instance_dir(instance, assert_exists=True), "mods")

    def _link_instance_to_current(self, instance: str) -> None:
        logger.info(f"Linking instance {instance} to 'current'")

        current_link = os.path.join(self._work_dir, "current")
        instance_dir = self.get_instance_dir(instance, assert_exists=True)

        if os.path.islink(current_link):
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

    def _catalog_factory(self, server_type: str, server_version: str) -> McServerCatalog:
        versions_dir = os.path.join(self._work_dir, "versions")
        java_bin = self._get_java_bin(server_version)

        return McServerCatalog(versions_dir, server_type, server_version, java_bin=java_bin)
