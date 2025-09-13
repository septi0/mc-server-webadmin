import os
import logging
import httpx
import aiofiles
from packaging import version

__all__ = ["McServerPatcher"]

logger = logging.getLogger(__name__)

class McServerPatcher:
    def __init__(self, version_dir: str, server_version: str) -> None:
        self._version_dir: str = version_dir
        self._server_version: str = server_version

    async def patch(self) -> None:
        await self._patch_log4j()

    async def get_jvm_args(self) -> list[str]:
        args = []

        args.extend(await self._get_log4j_jvm_args())

        return args

    # 1.18: Upgrade to 1.18.1, if possible. If not, use the same approach as for 1.17.x:

    # 1.17: Add the following JVM arguments to your startup command line:
    # -Dlog4j2.formatMsgNoLookups=true

    # 1.12-1.16.5: Download this file to the working directory where your server runs. Then add the following JVM arguments to your startup command line:
    # -Dlog4j.configurationFile=log4j2_112-116.xml

    # 1.7-1.11.2: Download this file to the working directory where your server runs. Then add the following JVM arguments to your  startup command line:
    # -Dlog4j.configurationFile=log4j2_17-111.xml

    # Versions below 1.7 are not affected
    async def _patch_log4j(self) -> None:
        logger.info(f"Patching Log4j for server version {self._server_version}")

        v17_111_patch = "https://launcher.mojang.com/v1/objects/4bb89a97a66f350bc9f73b3ca8509632682aea2e/log4j2_17-111.xml"
        v112_116_patch = "https://launcher.mojang.com/v1/objects/02937d122c86ce73319ef9975b58896fc1b491d1/log4j2_112-116.xml"

        v = version.parse(self._server_version)

        if v < version.parse("1.7"):
            pass
        elif v < version.parse("1.12"):
            file = os.path.join(self._version_dir, "log4j2_17-111.xml")
            await self._download_file(v17_111_patch, file)
        elif v < version.parse("1.17"):
            file = os.path.join(self._version_dir, "log4j2_112-116.xml")
            await self._download_file(v112_116_patch, file)

    async def _get_log4j_jvm_args(self) -> list[str]:
        args = []
        v = version.parse(self._server_version)

        if v < version.parse("1.7"):
            pass
        elif v < version.parse("1.12"):
            file = os.path.join(self._version_dir, "log4j2_17-111.xml")
            args = [f"-Dlog4j.configurationFile={file}"]
        elif v < version.parse("1.17"):
            file = os.path.join(self._version_dir, "log4j2_112-116.xml")
            args = [f"-Dlog4j.configurationFile={file}"]
        elif v < version.parse("1.18.1"):
            args = ["-Dlog4j2.formatMsgNoLookups=true"]

        return args

    async def _download_file(self, url: str, dest: str) -> None:
        logger.info(f"Downloading {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            async with aiofiles.open(dest, "wb") as f:
                await f.write(response.content)
