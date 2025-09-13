import logging
import os
import asyncio
from typing import BinaryIO
import aiofiles


__all__ = [
    "McServerDatapackError",
    "McServerDatapack",
]

logger = logging.getLogger(__name__)


class McServerDatapackError(Exception):
    pass


class McServerDatapack:
    """Low level Minecraft world datapack manager"""

    def __init__(self, datapacks_dir: str) -> None:
        self._datapacks_dir: str = datapacks_dir

    async def add(self, datapack_name: str, *, datapack_archive: BinaryIO) -> None:
        if not os.path.exists(self._datapacks_dir):
            logger.info(f"Creating datapacks directory")
            os.makedirs(self._datapacks_dir)

        datapack_file = os.path.join(self._datapacks_dir, f"{datapack_name}.zip")

        async with aiofiles.open(datapack_file, "wb") as f:
            content = await asyncio.to_thread(datapack_archive.read)
            await f.write(content)

        logger.info(f"Datapack {datapack_name} added")

    async def delete(self, datapack_name: str) -> None:
        datapack_file = os.path.join(self._datapacks_dir, f"{datapack_name}.zip")

        if not os.path.exists(datapack_file):
            raise McServerDatapackError(f"Datapack {datapack_name} does not exist")

        await asyncio.to_thread(os.remove, datapack_file)

        logger.info(f"Datapack {datapack_name} removed")