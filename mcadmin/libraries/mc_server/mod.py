import logging
import os
import asyncio
from typing import BinaryIO
import aiofiles


__all__ = [
    "McWorldModError",
    "McWorldMod",
]

logger = logging.getLogger(__name__)


class McWorldModError(Exception):
    pass


class McWorldMod:
    """Low level Minecraft world mod manager"""

    mods_location: str = "mods"

    def __init__(self, directory: str) -> None:
        self._directory: str = directory

    async def add(self, mod_name: str, *, mod_jar: BinaryIO) -> None:
        mods_dir = os.path.join(self._directory, self.mods_location)

        if not os.path.exists(mods_dir):
            logger.info(f"Creating mods directory")
            os.makedirs(mods_dir)

        mod_path = os.path.join(mods_dir, f"{mod_name}.jar")

        async with aiofiles.open(mod_path, "wb") as f:
            content = await asyncio.to_thread(mod_jar.read)
            await f.write(content)

        logger.info(f"Mod {mod_name} added")

    async def delete(self, mod_name: str) -> None:
        mods_dir = os.path.join(self._directory, self.mods_location)
        mod_path = os.path.join(mods_dir, f"{mod_name}.jar")

        if not os.path.exists(mod_path):
            raise McWorldModError(f"Mod {mod_name} does not exist")

        await asyncio.to_thread(os.remove, mod_path)

        logger.info(f"Mod {mod_name} removed")
