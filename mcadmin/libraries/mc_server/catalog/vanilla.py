import aiofiles
import httpx
import os
import logging
from .error import McServerCatalogError
from .abstract import McServerSpecializedCatalog

__all__ = ["VanillaServerCatalog"]

logger = logging.getLogger(__name__)


class VanillaServerCatalog(McServerSpecializedCatalog):
    capabilities: list[str] = ["datapacks"]
    link_paths: list[str] = []

    def __init__(self, version_dir: str, server_version: str, *, java_bin: str = "java") -> None:
        self._version_dir: str = version_dir
        self._server_version: str = server_version
        self._java_bin: str = java_bin

        self._versions_index_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

    async def download(self) -> None:
        url = await self._get_download_url()
        filename = f"server-{self._server_version}.jar"
        jar_path = os.path.join(self._version_dir, filename)

        if not os.path.exists(self._version_dir):
            os.makedirs(self._version_dir)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(jar_path, "wb") as f:
                await f.write(response.content)

    async def get_jvm_args(self) -> list[str]:
        filename = f"server-{self._server_version}.jar"
        jar_path = os.path.join(self._version_dir, filename)

        return [f"-jar {jar_path}"]

    async def _get_download_url(self) -> str:
        logger.info(f"Fetching versions index from {self._versions_index_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(self._versions_index_url)
            response.raise_for_status()
            versions_index = response.json()

        # search for desired version
        version_info = next((v for v in versions_index["versions"] if v["id"] == self._server_version), None)

        if not version_info:
            raise McServerCatalogError(f"Server version {self._server_version} not found")

        version_manifest_url = version_info["url"]

        logger.info(f"Fetching version manifest from {version_manifest_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(version_manifest_url)
            response.raise_for_status()
            manifest = response.json()

        return manifest["downloads"]["server"]["url"]
