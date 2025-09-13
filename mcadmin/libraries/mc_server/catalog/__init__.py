import os
import logging
from .error import McServerCatalogError
from .patcher import McServerPatcher
from .vanilla import VanillaServerCatalog
from .forge import ForgeServerCatalog


__all__ = [
    "McServerCatalogError",
    "McServerCatalog",
]


logger = logging.getLogger(__name__)


class McServerCatalog:
    """Low level Minecraft server jar repository manager"""

    server_types: dict = {
        "vanilla": {
            "handler": VanillaServerCatalog,
            "capabilities": VanillaServerCatalog.capabilities,
        },
        "forge": {
            "handler": ForgeServerCatalog,
            "capabilities": ForgeServerCatalog.capabilities,
        },
    }

    def __init__(self, versions_dir: str, server_type: str, server_version: str, *, java_bin: str = "java") -> None:
        self.server_type: str = server_type
        self.server_version: str = server_version
        self._java_bin: str = java_bin

        self._version_dir = os.path.join(versions_dir, f"{self.server_type}-{self.server_version}")

    async def download(self, no_cache: bool = False) -> None:
        """Download/setup the server environment"""
        logger.info(f"Attempting to download server version {self.server_version} ({self.server_type})")

        if os.path.exists(self._version_dir):
            if not no_cache:
                logger.info(f"Server version {self.server_version} ({self.server_type}) already exists, skipping download")
                return
        else:
            os.makedirs(self._version_dir)

        specialized_catalog = self._specialized_catalog_factory()
        patcher = McServerPatcher(self._version_dir, self.server_version)

        await specialized_catalog.download()
        await patcher.patch()

        logger.info(f"Server downloaded successfully")

        return

    def get_link_paths(self) -> list[str]:
        """Get the list of link paths needed for the server"""
        specialized_catalog = self._specialized_catalog_factory()

        return [os.path.join(self._version_dir, path) for path in specialized_catalog.link_paths]

    async def get_jvm_args(self) -> list[str]:
        """Get the list of JVM arguments needed to launch the server"""
        specialized_catalog = self._specialized_catalog_factory()
        patcher = McServerPatcher(self._version_dir, self.server_version)

        jvm_args = []

        jvm_args.extend(await patcher.get_jvm_args())

        # specialized catalog jvm args must be last, as they may contain -jar argument
        jvm_args.extend(await specialized_catalog.get_jvm_args())

        return jvm_args

    def _specialized_catalog_factory(self) -> VanillaServerCatalog | ForgeServerCatalog:
        if not self.server_type in self.server_types:
            raise McServerCatalogError(f"Unsupported server type: {self.server_type}")

        return self.server_types[self.server_type]["handler"](self._version_dir, self.server_version, java_bin=self._java_bin)
