import aiofiles
import httpx
import os
import logging
import asyncio
from glob import glob
from .error import McServerCatalogError
from .abstract import McServerSpecializedCatalog

__all__ = ["ForgeServerCatalog"]

logger = logging.getLogger(__name__)


class ForgeServerCatalog(McServerSpecializedCatalog):
    capabilities: list[str] = ["datapacks", "mods"]
    link_paths: list[str] = ["libraries"]

    def __init__(self, version_dir: str, server_version: str, *, java_bin: str = "java") -> None:
        self._version_dir: str = version_dir
        self._server_version: str = server_version
        self._java_bin: str = java_bin

        self._versions_index_url = "https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json"
        self._version_download_url = "https://files.minecraftforge.net/maven/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
        self._installer_path = "/tmp/forge-installer.jar"

    async def download(self) -> None:
        url = await self._get_installer_download_url()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(self._installer_path, "wb") as f:
                await f.write(response.content)

        await self._run_installer()

    async def get_jvm_args(self) -> list[str]:
        # search for a forge-<version>*.jar file
        jar_path = None
        for f in os.listdir(self._version_dir):
            if f.startswith(f"forge-{self._server_version}") and f.endswith(".jar"):
                jar_path = os.path.join(self._version_dir, f)
                break

        if jar_path:
            return [f"-jar {jar_path}"]

        # fallback to unix_args.txt if exists
        glob_path = os.path.join(self._version_dir, "libraries", "net", "minecraftforge", "forge", f"{self._server_version}-*", "unix_args.txt")
        match = await asyncio.to_thread(glob, glob_path)

        if match:
            return [f"@{match[0]}"]

        raise McServerCatalogError("Could not find the Forge server jar after installation")

    async def _get_installer_download_url(self) -> str:
        logger.info(f"Fetching Forge versions index from {self._versions_index_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(self._versions_index_url)
            response.raise_for_status()
            versions = response.json()

        if not self._server_version in versions:
            raise McServerCatalogError(f"Forge version {self._server_version} not found")

        version_name = versions[self._server_version][-1]
        return self._version_download_url.format(version=version_name)

    async def _run_installer(self) -> None:
        logger.info(f"Running Forge installer")
        
        if not os.path.exists(self._version_dir):
            os.makedirs(self._version_dir)

        process = await asyncio.create_subprocess_exec(
            self._java_bin,
            "-jar",
            self._installer_path,
            "--installServer",
            self._version_dir,
            cwd=self._version_dir,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise McServerCatalogError(f"Forge installer failed: {stderr.decode().strip()}")

        logger.info(f"Forge installer completed successfully")

        await asyncio.to_thread(os.remove, self._installer_path)
