import aiofiles
import httpx
import os
import logging
import asyncio
from .error import McServerDownloaderError

__all__ = ["ForgeServerDownloader"]

logger = logging.getLogger(__name__)

class ForgeServerDownloader:
    def __init__(self, directory: str, *, java_bin: str) -> None:
        self._directory: str = directory
        self._java_bin: str = java_bin

        self._versions_index_url = "https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json"
        self._version_download_url = "https://files.minecraftforge.net/maven/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"

    async def download(self, server_version: str) -> None:
        (url, forge_version) = await self._get_download_url(server_version)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(os.path.join(self._directory, "forge-installer.jar"), "wb") as f:
                await f.write(response.content)

        await self._run_installer()
        await self._cleanup()
        await self._rename(forge_version)

    async def _get_download_url(self, server_version: str) -> tuple[str, str]:
        logger.info(f"Fetching Forge versions index from {self._versions_index_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(self._versions_index_url)
            response.raise_for_status()
            versions = response.json()

        if not server_version in versions:
            raise McServerDownloaderError(f"Forge version {server_version} not found")

        version_name = versions[server_version][-1]
        return (self._version_download_url.format(version=version_name), version_name)

    async def _run_installer(self) -> None:
        logger.info(f"Running Forge installer")

        process = await asyncio.create_subprocess_exec(
            self._java_bin,
            "-jar",
            "forge-installer.jar",
            "--installServer",
            cwd=self._directory,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise McServerDownloaderError(f"Forge installer failed: {stderr.decode().strip()}")

        logger.info(f"Forge installer completed successfully")

    async def _cleanup(self) -> None:
        remove = ["forge-installer.jar"]

        for f in remove:
            path = os.path.join(self._directory, f)

            if os.path.exists(path):
                logger.info(f"Removing temporary file {f}")
                await asyncio.to_thread(os.remove, path)

    async def _rename(self, forge_version: str) -> None:
        base_name = f"forge-{forge_version}"
        rename = ["shim.jar", "universal.jar"]

        for f in rename:

            src = os.path.join(self._directory, f"{base_name}-{f}")
            dst = os.path.join(self._directory, "server.jar")

            if os.path.exists(src):
                logger.info(f"Renaming {f} to server.jar")
                await asyncio.to_thread(os.rename, src, dst)
                break
