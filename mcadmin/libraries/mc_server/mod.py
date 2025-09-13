import logging
import os
import asyncio
from typing import BinaryIO
import aiofiles


__all__ = [
    "McServerModError",
    "McServerMod",
]

logger = logging.getLogger(__name__)


class McServerModError(Exception):
    pass


class McServerMod:
    """Low level Minecraft world mod manager"""

    def __init__(self, mods_dir: str) -> None:
        self._mods_dir: str = mods_dir

    async def add(self, mod_name: str, *, mod_jar: BinaryIO) -> None:
        if not os.path.exists(self._mods_dir):
            logger.info(f"Creating mods directory")
            os.makedirs(self._mods_dir)

        mod_file = os.path.join(self._mods_dir, f"{mod_name}.jar")

        async with aiofiles.open(mod_file, "wb") as f:
            content = await asyncio.to_thread(mod_jar.read)
            await f.write(content)

        logger.info(f"Mod {mod_name} added")

    async def delete(self, mod_name: str) -> None:
        mod_file = os.path.join(self._mods_dir, f"{mod_name}.jar")

        if not os.path.exists(mod_file):
            raise McServerModError(f"Mod {mod_name} does not exist")

        await asyncio.to_thread(os.remove, mod_file)

        logger.info(f"Mod {mod_name} removed")