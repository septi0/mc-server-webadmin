import aiofiles
import httpx
import os
import logging
from .error import McServerDownloaderError

__all__ = ["VanillaServerDownloader"]

logger = logging.getLogger(__name__)

class VanillaServerDownloader:
    def __init__(self, directory: str, *, java_bin: str) -> None:
        self._directory: str = directory
        self._java_bin: str = java_bin

        self._versions_index_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

    async def download(self, server_version: str) -> None:
        url = await self._get_download_url(server_version)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(os.path.join(self._directory, "server.jar"), "wb") as f:
                await f.write(response.content)

    async def _get_download_url(self, server_version: str) -> str:
        logger.info(f"Fetching versions index from {self._versions_index_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(self._versions_index_url)
            response.raise_for_status()
            versions_index = response.json()

        # search for desired version
        version_info = next((v for v in versions_index["versions"] if v["id"] == server_version), None)

        if not version_info:
            raise McServerDownloaderError(f"Server version {server_version} not found")

        version_manifest_url = version_info["url"]

        logger.info(f"Fetching version manifest from {version_manifest_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(version_manifest_url)
            response.raise_for_status()
            manifest = response.json()

        return manifest["downloads"]["server"]["url"]
