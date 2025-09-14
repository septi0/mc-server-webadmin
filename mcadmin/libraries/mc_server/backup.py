import logging
import os
import asyncio
import shutil
import json
import aiofiles


__all__ = [
    "McServerBackupError",
    "McServerBackup",
]

logger = logging.getLogger(__name__)


class McServerBackupError(Exception):
    pass


class McServerBackup:
    """Low level Minecraft server backup manager"""

    backup_targets: list[tuple[str, str]] = [
        ("world", "dir"),
        ("mods", "dir"),
        ("server_info.json", "file"),
    ]

    def __init__(self, instance_dir: str, backups_dir: str) -> None:
        self._instance_dir: str = instance_dir
        self._backups_dir: str = backups_dir

    async def backup(self, backup: str) -> None:
        """Create a backup with the given name"""
        backup_dir = os.path.join(self._backups_dir, backup)

        if not os.path.exists(backup_dir):
            logger.info(f"Creating backup directory {backup_dir}")
            os.makedirs(backup_dir)

        for d, t in self.backup_targets:
            src_path = os.path.join(self._instance_dir, d)
            dst_path = os.path.join(backup_dir, d)

            if not os.path.exists(src_path):
                if t == "dir":
                    os.makedirs(dst_path)
                else:
                    async with aiofiles.open(dst_path, "w") as f:
                        await f.write("")

                continue

            if t == "dir":
                await asyncio.to_thread(shutil.copytree, src_path, dst_path)
            else:
                await asyncio.to_thread(shutil.copy2, src_path, dst_path)

        logger.info(f"Successfully backed up data to {backup}")

    async def restore(self, backup: str) -> None:
        """Restore a backup with the given name"""
        backup_dir = os.path.join(self._backups_dir, backup)

        if not os.path.exists(backup_dir):
            raise McServerBackupError(f"Backup {backup} does not exist")

        for d in os.listdir(backup_dir):
            src_dir = os.path.join(backup_dir, d)
            dst_dir = os.path.join(self._instance_dir, d)

            if os.path.exists(dst_dir):
                if os.path.isdir(dst_dir):
                    await asyncio.to_thread(shutil.rmtree, dst_dir)
                else:
                    await asyncio.to_thread(os.remove, dst_dir)

            if os.path.isdir(src_dir):
                await asyncio.to_thread(shutil.copytree, src_dir, dst_dir)
            else:
                await asyncio.to_thread(shutil.copy2, src_dir, dst_dir)

    async def delete_backup(self, backup: str) -> None:
        """Delete a backup with the given name"""
        backup_dir = os.path.join(self._backups_dir, backup)

        if not os.path.exists(backup_dir):
            raise McServerBackupError(f"Backup {backup} does not exist")

        await asyncio.to_thread(shutil.rmtree, backup_dir)

        logger.info(f"Successfully deleted backup {backup}")
