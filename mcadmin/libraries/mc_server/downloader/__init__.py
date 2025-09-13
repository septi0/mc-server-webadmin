import os
import logging
from .error import McServerDownloaderError
from .patcher import McServerPatcher
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

        self._link_paths: list[str] = ["libraries"]
        self._jvm_args_filename: str = "mcadmin_jvm_args.txt"

    async def download_server(self, server_type: str, server_version: str, no_cache: bool = False) -> None:
        logger.info(f"Attempting to download server version {server_version} ({server_type})")

        workdir = self._gen_workdir(server_type, server_version)

        if os.path.exists(workdir):
            if not no_cache:
                logger.info(f"Server version {server_version} ({server_type}) already exists, skipping download")
                return
        else:
            os.makedirs(workdir)

        downloader = self._get_downloader_instance(server_type, workdir, server_version, java_bin=self._java_bin)
        patcher = McServerPatcher(workdir, server_version)

        await downloader.download()
        await patcher.patch()

        logger.info(f"Server downloaded successfully")

        return

    def get_link_paths(self, server_type: str, server_version: str) -> list[str]:
        workdir = self._gen_workdir(server_type, server_version)
        return [os.path.join(workdir, p) for p in self._link_paths]

    async def get_jvm_args(self, server_type: str, server_version: str) -> list[str]:
        workdir = self._gen_workdir(server_type, server_version)
        downloader = self._get_downloader_instance(server_type, workdir, server_version, java_bin=self._java_bin)
        patcher = McServerPatcher(workdir, server_version)

        jvm_args = []

        jvm_args.extend(await patcher.get_jvm_args())
        
        # downloader jvm args must be last, as they may contain -jar argument
        jvm_args.extend(await downloader.get_jvm_args())

        return jvm_args

    def _get_downloader_instance(self, server_type: str, *args, **kwargs) -> VanillaServerDownloader | ForgeServerDownloader:
        if not server_type in self.server_types:
            raise McServerDownloaderError(f"Unsupported server type: {server_type}")

        return self.server_types[server_type]["handler"](*args, **kwargs)

    def _gen_workdir(self, server_type: str, server_version: str) -> str:
        return os.path.join(self._directory, f"{server_type}-{server_version}")
