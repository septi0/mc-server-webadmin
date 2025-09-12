import logging
from .error import McServerDownloaderError
from .vanilla import VanillaServerDownloader
from .forge import ForgeServerDownloader


__all__ = [
    "McServerDownloaderError",
    "McServerDownloader",
]


logger = logging.getLogger(__name__)


class McServerDownloader:
    """Low level Minecraft server jar downloader"""

    server_types: dict = {
        "vanilla": {
            "handler": VanillaServerDownloader,
            "capabilities": ["datapacks"],
        },
        "forge": {
            "handler": ForgeServerDownloader,
            "capabilities": ["datapacks", "mods"],
        },
    }
    server_types_with_mods: list[str] = ["forge"]

    def __init__(self, directory: str, *, java_bin: str = "java") -> None:
        self._directory: str = directory
        self._java_bin: str = java_bin

    async def download_server(self, server_version: str, server_type: str) -> None:
        logger.info(f"Attempting to download server version {server_version} ({server_type})")

        args = [self._directory]
        kwargs = {"java_bin": self._java_bin}

        if not server_type in self.server_types:
            raise McServerDownloaderError(f"Unsupported server type: {server_type}")

        downloader = self.server_types[server_type]["handler"](*args, **kwargs)

        await downloader.download(server_version)

        logger.info(f"Server jar downloaded successfully")
