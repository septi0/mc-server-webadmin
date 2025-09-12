import logging
import os
import asyncio
import shutil


class McWorldBackupError(Exception):
    pass


__all__ = [
    "McWorldBackupError",
    "McWorldBackup",
]

logger = logging.getLogger(__name__)


class McWorldBackup:
    """ Low level Minecraft world backup manager """
    backup_dirs: list[str] = ["world"]
    backup_location: str = "backups"

    def __init__(self, directory: str) -> None:
        self._directory: str = directory

    async def backup(self, backup: str) -> None:
        backup_dir = os.path.join(self._directory, self.backup_location, backup)

        if not os.path.exists(backup_dir):
            logger.info(f"Creating backup directory {backup_dir}")
            os.makedirs(backup_dir)

        for d in self.backup_dirs:
            src_dir = os.path.join(self._directory, d)
            dst_dir = os.path.join(backup_dir, d)

            if os.path.exists(src_dir):
                await asyncio.to_thread(shutil.copytree, src_dir, dst_dir)
            else:
                # create empty directory
                os.makedirs(dst_dir)

        logger.info(f"Successfully backed up data to {backup}")

    async def restore(self, backup: str) -> None:
        backup_dir = os.path.join(self._directory, self.backup_location, backup)

        if not os.path.exists(backup_dir):
            raise McWorldBackupError(f"Backup {backup} does not exist")

        for d in os.listdir(backup_dir):
            src_dir = os.path.join(backup_dir, d)
            dst_dir = os.path.join(self._directory, d)

            if os.path.exists(dst_dir):
                await asyncio.to_thread(shutil.rmtree, dst_dir)

            await asyncio.to_thread(shutil.copytree, src_dir, dst_dir)

    async def delete_backup(self, backup: str) -> None:
        backup_dir = os.path.join(self._directory, self.backup_location, backup)

        if not os.path.exists(backup_dir):
            raise McWorldBackupError(f"Backup {backup} does not exist")

        await asyncio.to_thread(shutil.rmtree, backup_dir)

        logger.info(f"Successfully deleted backup {backup}")