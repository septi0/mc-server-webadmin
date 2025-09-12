import logging
import os
import asyncio
from typing import BinaryIO
import aiofiles


__all__ = [
    "McWorldDatapackError",
    "McWorldDatapack",
]

logger = logging.getLogger(__name__)


class McWorldDatapackError(Exception):
    pass


class McWorldDatapack:
    """Low level Minecraft world datapack manager"""

    datapacks_location: str = os.path.join("world", "datapacks")

    def __init__(self, directory: str) -> None:
        self._directory: str = directory

    async def add(self, datapack_name: str, *, datapack_archive: BinaryIO) -> None:
        datapacks_dir = os.path.join(self._directory, self.datapacks_location)

        if not os.path.exists(datapacks_dir):
            logger.info(f"Creating datapacks directory")
            os.makedirs(datapacks_dir)

        datapack_path = os.path.join(datapacks_dir, f"{datapack_name}.zip")

        async with aiofiles.open(datapack_path, "wb") as f:
            content = await asyncio.to_thread(datapack_archive.read)
            await f.write(content)

        logger.info(f"Datapack {datapack_name} added")

    async def delete(self, datapack_name: str) -> None:
        datapacks_dir = os.path.join(self._directory, self.datapacks_location)
        datapack_path = os.path.join(datapacks_dir, f"{datapack_name}.zip")

        if not os.path.exists(datapack_path):
            raise McWorldDatapackError(f"Datapack {datapack_name} does not exist")

        await asyncio.to_thread(os.remove, datapack_path)

        logger.info(f"Datapack {datapack_name} removed")
