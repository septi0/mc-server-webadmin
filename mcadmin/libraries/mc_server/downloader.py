import logging
import os
import aiofiles
import httpx


class McServerDownloaderError(Exception):
    pass


__all__ = [
    "McServerDownloaderError",
    "McServerDownloader",
]

logger = logging.getLogger(__name__)


class McServerDownloader:
    """ Low level Minecraft server jar downloader """
    def __init__(self, directory: str):
        self._directory: str = directory

    async def download_server(self, server_version: str, server_type: str) -> None:
        logger.info(f"Attempting to download server version {server_version} ({server_type})")

        url = None

        if server_type == "vanilla":
            server_downloader = self.VanillaServerDownloader()
            url = await server_downloader.get_download_url(server_version)
        else:
            raise McServerDownloaderError(f"Unsupported server type: {server_type}")

        await self._download_version(url)

    async def _download_version(self, url: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(os.path.join(self._directory, "server.jar"), "wb") as f:
                await f.write(response.content)

        logger.info(f"Server jar successfully downloaded")

    class VanillaServerDownloader:
        def __init__(self):
            self._versions_index_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

        async def get_download_url(self, server_version: str) -> str:
            logger.info(f"Fetching versions index from {self._versions_index_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(self._versions_index_url)
                response.raise_for_status()
                versions_index = response.json()

            # search for desired version
            version_info = next((v for v in versions_index["versions"] if v["id"] == server_version), None)

            if not version_info:
                raise McServerDownloaderError(f"Server version {server_version} not found")

            version_manifest_url = version_info["url"]

            logger.info(f"Fetching version manifest from {version_manifest_url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(version_manifest_url)
                response.raise_for_status()
                manifest = response.json()

            return manifest["downloads"]["server"]["url"]