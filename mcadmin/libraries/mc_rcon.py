import asyncio
import struct
import logging
from typing import Optional

__all__ = ["MCRcon", "MCRconError", "MCRconAuthError"]

logger = logging.getLogger(__name__)

SERVERDATA_RESPONSE_VALUE = 0
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2


class MCRconError(Exception):
    pass


class MCRconAuthError(MCRconError):
    pass


class MCRcon:
    def __init__(self, host: str, password: str = "", *, port: int = 25575, connect_timeout: int = 5, io_timeout: int = 5) -> None:
        self.host = host
        self.password = password
        self.port = port
        self.connect_timeout = connect_timeout
        self.io_timeout = io_timeout
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._req_id: int = 0
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._reader and self._writer:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout=self.connect_timeout)
        except Exception as e:
            raise MCRconError(f"RCON server not reachable ({e})") from None

        logger.info(f"Connected to RCON server at {self.host}:{self.port}")

        cmd_id = self._next_id()
        ok = False

        await self._write_packet(cmd_id, SERVERDATA_AUTH, self.password.encode("utf-8"))

        for _ in range(3):
            rid, ptype, payload = await self._read_packet()

            if rid == -1:
                break
            if ptype in (SERVERDATA_AUTH_RESPONSE, SERVERDATA_EXECCOMMAND) and rid == cmd_id:
                ok = True
                break

        if not ok:
            await self.disconnect()
            raise MCRconAuthError("RCON authentication failed")

        logger.info("Authenticated successfully")

    async def command(self, cmd: str, *, retry: int = 3) -> str:
        # logger.info(f"Sending RCON command: {cmd}")
        # logger.debug(f"Sending RCON command: {cmd}")

        async with self._lock:
            last_error = None

            for _ in range(retry):
                try:
                    return await self._send_command(cmd)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, asyncio.IncompleteReadError) as e:
                    last_error = e
                    logger.warning(f"RCON connection lost: {e}")
                    await self.disconnect()

                logger.info(f"Reconnecting to RCON server (attempt {_ + 1})...")

            raise MCRconError(f"RCON server not reachable ({last_error})")

    async def disconnect(self) -> None:
        if self._writer is None:
            return

        self._writer.close()
        try:
            await self._writer.wait_closed()
        finally:
            self._reader = None
            self._writer = None
            self._req_id = 0

        logger.info("Disconnected from RCON server")

    async def _send_command(self, cmd: str) -> str:
        await self._ensure_connected()

        cmd_id = self._next_id()
        await self._write_packet(cmd_id, SERVERDATA_EXECCOMMAND, cmd.encode("utf-8"))

        await asyncio.sleep(0.1)

        control_id = self._next_id()
        await self._write_packet(control_id, SERVERDATA_EXECCOMMAND, "".encode("utf-8"))

        chunks: list[bytes] = []

        while True:
            rid, ptype, payload = await self._read_packet()
            if rid == control_id and ptype == SERVERDATA_RESPONSE_VALUE:
                break
            if rid == cmd_id and ptype == SERVERDATA_RESPONSE_VALUE:
                if payload:
                    chunks.append(payload)
                continue

        return b"".join(chunks).decode("utf-8", errors="replace")

    async def _ensure_connected(self) -> None:
        if self._reader and self._writer:
            return

        await self.connect()

    def _next_id(self) -> int:
        self._req_id += 1
        if self._req_id > 0x7FFFFFF0:
            self._req_id = 1
        return self._req_id

    async def _write_packet(self, req_id: int, ptype: int, payload: bytes) -> None:
        assert self._writer is not None

        body = struct.pack("<ii", req_id, ptype) + payload + b"\x00\x00"
        frame = struct.pack("<i", len(body)) + body
        self._writer.write(frame)
        await asyncio.wait_for(self._writer.drain(), timeout=self.io_timeout)

    async def _read_exactly(self, n: int) -> bytes:
        assert self._reader is not None

        return await asyncio.wait_for(self._reader.readexactly(n), timeout=self.io_timeout)

    async def _read_packet(self) -> tuple[int, int, bytes]:
        raw_len = await self._read_exactly(4)
        (length,) = struct.unpack("<i", raw_len)
        data = await self._read_exactly(length)
        req_id, ptype = struct.unpack("<ii", data[:8])
        payload = data[8:]
        if not payload.endswith(b"\x00\x00"):
            payload = payload.rstrip(b"\x00")
        else:
            payload = payload[:-2]

        return req_id, ptype, payload
