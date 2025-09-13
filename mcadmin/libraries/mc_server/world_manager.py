import logging
import os
import asyncio
import shutil
import aiofiles
import zipfile
import socket
from typing import BinaryIO
from packaging import version
from .downloader import McServerDownloader
from .properties_generator import McServerPropertiesGenerator
from .backup import McWorldBackup
from .datapack import McWorldDatapack
from .mod import McWorldMod


__all__ = [
    "McWorldManagerError",
    "McWorldManager",
]

logger = logging.getLogger(__name__)


class McWorldManagerError(Exception):
    pass


class McWorldManager:
    """Minecraft world instance manager"""

    default_server_ip: str = "0.0.0.0"
    default_server_port: int = 25565
    default_rcon_port: int = 25575

    def __init__(self, directory: str, server_config: dict) -> None:
        self._directory: str = directory
        self._server_config: dict = server_config

        self._backup_dirs: list[str] = ["world"]
        self._backup_location: str = "backups"

    async def create_world_instance(self, world: str, *, world_archive: BinaryIO | None = None) -> None:
        workdir = self._gen_workdir(world)

        if os.path.exists(workdir):
            raise McWorldManagerError(f"World instance {world} already exists")

        os.makedirs(workdir)

        await self._accept_eula(workdir)

        if world_archive:
            await self._import_world(workdir, world_archive)

    async def activate_world_instance(
        self,
        world: str,
        *,
        server_version: str,
        server_type: str,
        properties: dict,
    ) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        versions_path = os.path.join(self._directory, "versions")
        java_version = self._suggested_java_version(server_version)

        if self._server_config.get("java_bin", ""):
            java_bin = self._server_config["java_bin"]
        else:
            java_bin = f"java-{java_version}" if java_version else "java"

        downloader = McServerDownloader(versions_path, java_bin=java_bin)
        properties_generator = McServerPropertiesGenerator(
            workdir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        tasks = [
            asyncio.create_task(
                downloader.download_server(server_type, server_version, no_cache=False),
                name="download_server",
            ),
            asyncio.create_task(
                properties_generator.generate(properties),
                name="generate_server_properties",
            ),
        ]

        (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            logger.warning(f"Task {task.get_name()} is still pending. Cancelling it.")
            task.cancel()

        for task in done:
            if task.exception() is not None:
                raise McWorldManagerError(f"Task {task.get_name()} failed with exception: {task.exception()}")

        jvm_args = await downloader.get_jvm_args(server_type, server_version)
        additional_links = downloader.get_link_paths(server_type, server_version)

        await self._link_common_files(workdir, additional_links=additional_links)
        await self._gen_start_script(workdir, jvm_args, java_bin=java_bin)

        self._link_world_instance_to_current(world)

        logger.info(f"World instance {world} activated successfully")

    async def regen_world_properties(self, world: str, properties: dict) -> None:
        workdir = self._gen_workdir(world)
        properties_generator = McServerPropertiesGenerator(
            workdir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        await properties_generator.generate(properties)

    async def delete_world_instance(self, world: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)

        await asyncio.to_thread(shutil.rmtree, workdir)

        logger.info(f"Directory for world instance {world} deleted")

    async def backup_world_instance(self, world: str, backup: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_backup = McWorldBackup(workdir)

        await mc_backup.backup(backup)

    async def restore_world_instance(self, world: str, backup: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_backup = McWorldBackup(workdir)

        await mc_backup.restore(backup)

        logger.info(f"World instance {world} restored from backup {backup}")

    async def delete_world_instance_backup(self, world: str, backup: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_backup = McWorldBackup(workdir)

        await mc_backup.delete_backup(backup)

    async def add_world_instance_datapack(self, world: str, datapack_name: str, *, datapack_archive: BinaryIO) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_datapack = McWorldDatapack(workdir)

        await mc_datapack.add(datapack_name, datapack_archive=datapack_archive)

    async def delete_world_instance_datapack(self, world: str, datapack_name: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_datapack = McWorldDatapack(workdir)

        await mc_datapack.delete(datapack_name)

    async def add_world_instance_mod(self, world: str, mod_name: str, *, mod_jar: BinaryIO) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_mod = McWorldMod(workdir)

        await mc_mod.add(mod_name, mod_jar=mod_jar)

    async def delete_world_instance_mod(self, world: str, mod_name: str) -> None:
        workdir = self._gen_workdir(world, assert_exists=True)
        mc_mod = McWorldMod(workdir)

        await mc_mod.delete(mod_name)

    def validate_properties(self, properties: dict) -> None:
        McServerPropertiesGenerator.validate_properties(properties)

    def get_level_types(self) -> list[str]:
        return McServerPropertiesGenerator.level_types

    def get_min_server_version(self) -> str:
        return McServerPropertiesGenerator.min_server_version

    def get_server_connect_info(self) -> dict:
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
        info = {}

        info["port"] = self._server_config.get("rcon_port", self.default_rcon_port)
        info["ip"] = self._resolve_wildcard_ip(self._server_config.get("server_ip", self.default_server_ip))

        return info

    def get_server_types(self) -> dict:
        return McServerDownloader.server_types

    def server_capabilities(self, server_type: str) -> list[str]:
        return McServerDownloader.server_types.get(server_type, {}).get("capabilities", [])

    async def _import_world(self, workdir: str, world_archive: BinaryIO) -> None:
        logger.info(f"Extracting existing world data archive")

        # unzip archive
        with zipfile.ZipFile(world_archive, "r") as zip_ref:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, zip_ref.extractall, os.path.join(workdir, "world"))

    async def _accept_eula(self, workdir: str) -> None:
        logger.info(f"Accepting EULA")

        eula_file = os.path.join(workdir, "eula.txt")

        async with aiofiles.open(eula_file, "w") as f:
            await f.write("eula=true")

    async def _link_common_files(self, workdir: str, *, additional_links: list[str]) -> None:
        logger.info(f"Linking common files for world instance {workdir}")

        common_files = ["banned-ips.json", "banned-players.json", "ops.json", "usercache.json", "whitelist.json"]

        for file in common_files:
            src = os.path.join(self._directory, file)
            dst = os.path.join(workdir, file)

            if not os.path.exists(src):
                async with aiofiles.open(src, "w") as f:
                    await f.write("[]")

            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)

            os.symlink(src, dst)
            logger.info(f"Linked {src} to {dst}")

        for src in additional_links:
            link_name = os.path.basename(src)
            dst = os.path.join(workdir, link_name)

            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)

            if os.path.exists(src):
                os.symlink(src, dst)
                logger.info(f"Linked {src} to {dst}")

    async def _gen_start_script(self, workdir: str, jvm_args: list[str], *, java_bin: str) -> None:
        logger.info(f"Generating start script for world instance {workdir}")

        start_script = os.path.join(workdir, "mcadmin-start.sh")

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

    def _gen_workdir(self, world: str, *, assert_exists=False) -> str:
        workdir = os.path.join(self._directory, "worlds", world)

        if assert_exists and not os.path.exists(workdir):
            raise McWorldManagerError(f"World instance {world} does not exist")

        return workdir

    def _link_world_instance_to_current(self, world: str) -> None:
        logger.info(f"Linking world instance {world} to 'current'")

        current_link = os.path.join(self._directory, "current")
        world_instance_path = self._gen_workdir(world)

        if os.path.islink(current_link) or os.path.exists(current_link):
            os.remove(current_link)

        os.symlink(world_instance_path, current_link)

    def _suggested_java_version(self, server_version: str) -> int:
        v = version.parse(server_version)

        if v >= version.parse("1.21"):
            return 21
        elif v >= version.parse("1.17"):
            return 17
        else:
            return 8
