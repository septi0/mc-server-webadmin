import logging
import json
import os
import asyncio
import shutil
import aiofiles
import httpx
import zipfile
import socket
from packaging import version
from typing import BinaryIO
from .downloader import McServerDownloader
from .properties_generator import McServerPropertiesGenerator
from .backup import McWorldBackup
from .datapack import McWorldDatapack


class McWorldManagerError(Exception):
    pass


__all__ = [
    "McWorldManagerError",
    "McWorldManager",
]

logger = logging.getLogger(__name__)


class McWorldManager:
    """ Minecraft world instance manager """
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

        downloader = McServerDownloader(workdir)
        properties_generator = McServerPropertiesGenerator(
            workdir,
            server_ip=self._server_config.get("server_ip", self.default_server_ip),
            server_port=self._server_config.get("server_port", self.default_server_port),
            rcon_port=self._server_config.get("rcon_port", self.default_rcon_port),
        )

        tasks = [
            asyncio.create_task(
                downloader.download_server(server_version, server_type),
                name="download_server",
            ),
            asyncio.create_task(
                properties_generator.generate(properties),
                name="generate_server_properties",
            ),
            asyncio.create_task(
                self._patch_log4j(workdir, server_version),
                name="patch_log4j",
            ),
        ]

        (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        server_params = {
            "args": [],
            "java_version": self._get_recommended_java(server_version),
        }

        for task in pending:
            logger.warning(f"Task {task.get_name()} is still pending. Cancelling it.")
            task.cancel()

        for task in done:
            if task.exception() is not None:
                raise McWorldManagerError(f"Task {task.get_name()} failed with exception: {task.exception()}")

            if task.get_name() == "patch_log4j":
                server_params["args"].extend(task.result())

        await self._write_server_params(workdir, server_params)
        await self._link_common_files(workdir)

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

    async def _link_common_files(self, workdir: str) -> None:
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

    # 1.18: Upgrade to 1.18.1, if possible. If not, use the same approach as for 1.17.x:

    # 1.17: Add the following JVM arguments to your startup command line:
    # -Dlog4j2.formatMsgNoLookups=true

    # 1.12-1.16.5: Download this file to the working directory where your server runs. Then add the following JVM arguments to your startup command line:
    # -Dlog4j.configurationFile=log4j2_112-116.xml

    # 1.7-1.11.2: Download this file to the working directory where your server runs. Then add the following JVM arguments to your  startup command line:
    # -Dlog4j.configurationFile=log4j2_17-111.xml

    # Versions below 1.7 are not affected
    async def _patch_log4j(self, workdir: str, server_version: str) -> list[str]:
        logger.info(f"Patching Log4j for server version {server_version}")

        v17_111_patch = "https://launcher.mojang.com/v1/objects/4bb89a97a66f350bc9f73b3ca8509632682aea2e/log4j2_17-111.xml"
        v112_116_patch = "https://launcher.mojang.com/v1/objects/02937d122c86ce73319ef9975b58896fc1b491d1/log4j2_112-116.xml"

        v = version.parse(server_version)
        args = []

        if v < version.parse("1.7"):
            pass
        elif v < version.parse("1.12"):
            await self._download_file(v17_111_patch, os.path.join(workdir, "log4j2_17-111.xml"))
            args = ["-Dlog4j.configurationFile=log4j2_17-111.xml"]
        elif v < version.parse("1.17"):
            await self._download_file(v112_116_patch, os.path.join(workdir, "log4j2_112-116.xml"))
            args = ["-Dlog4j.configurationFile=log4j2_112-116.xml"]
        elif v < version.parse("1.18.1"):
            args = ["-Dlog4j2.formatMsgNoLookups=true"]

        return args

    async def _download_file(self, url: str, dest: str) -> None:
        logger.info(f"Downloading {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(dest, "wb") as f:
                await f.write(response.content)

    async def _write_server_params(self, workdir: str, data: dict) -> None:
        logger.info(f"Writing server params")

        info_file = os.path.join(workdir, "server_params.json")

        async with aiofiles.open(info_file, "w") as f:
            await f.write(json.dumps(data))

    def _resolve_wildcard_ip(self, ip: str) -> str:
        if ip not in ("0.0.0.0", ""):
            return ip

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()

        return ip

    def _gen_workdir(self, world: str, *, assert_exists=False) -> str:
        workdir = os.path.join(self._directory, world)

        if assert_exists and not os.path.exists(workdir):
            raise McWorldManagerError(f"World instance {world} does not exist")

        return workdir

    def _link_world_instance_to_current(self, world: str) -> None:
        logger.info(f"Linking world instance {world} to 'current'")

        current_link = self._gen_workdir("current")
        world_instance_path = self._gen_workdir(world)

        if os.path.islink(current_link) or os.path.exists(current_link):
            os.remove(current_link)

        os.symlink(world_instance_path, current_link)

    def _get_recommended_java(self, server_version: str) -> int:
        v = version.parse(server_version)

        if v >= version.parse("1.21"):
            return 21
        elif v >= version.parse("1.17"):
            return 17
        else:
            return 8
