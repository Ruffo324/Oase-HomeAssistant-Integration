"""O-Net v2 local UDP discovery plus authenticated TLS callback transport."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import socket
import ssl
import struct

from .const import (
    CHECK_PASSWORD,
    CHECK_PASSWORD_REPLY,
    REQUEST_TCP_CALLBACK,
    REQUEST_TCP_CALLBACK_REPLY,
    TCP_CALLBACK_PORT,
    UDP_PORT,
)

_MARKER = b"\\#OA"
_HEADER_SIZE = 16


def parse_packet(raw: bytes) -> tuple[int, int, bytes]:
    if len(raw) < _HEADER_SIZE or raw[:4] != _MARKER:
        raise ValueError("invalid O-Net v2 packet marker")
    data_length, version, transaction, packet_type = struct.unpack_from("<IBBH", raw, 4)
    if version != 2 or len(raw) != _HEADER_SIZE + data_length:
        raise ValueError("invalid O-Net v2 packet")
    return transaction, packet_type, raw[_HEADER_SIZE:]


class ONetV2:
    """Packet payload factories for current EasyControl FM-Master firmware."""

    @staticmethod
    def packet(transaction: int, packet_type: int, payload: bytes = b"") -> bytes:
        return _MARKER + struct.pack("<IBBH", len(payload), 2, transaction, packet_type) + b"\0" * 4 + payload

    @staticmethod
    def request_tcp_callback(port: int) -> bytes:
        if not 1 <= port <= 65535:
            raise ValueError("TCP callback port must be in range 1 through 65535")
        return bytes((0,)) + port.to_bytes(2, "little")

    @staticmethod
    def socket_query() -> bytes:
        return bytes((4,)) + struct.pack("<I", 0)

    @staticmethod
    def password_payload(password: str) -> bytes:
        encoded = password.encode("ascii")
        if len(encoded) > 64:
            raise ValueError("device password exceeds 64 ASCII bytes")
        return encoded.ljust(64, b"\0")


class FmMasterSession:
    """One authenticated callback connection initiated by the FM-Master."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._transaction = 1

    async def request(self, packet_type: int, payload: bytes) -> tuple[int, bytes]:
        transaction = self._transaction
        self._transaction = (self._transaction % 255) + 1
        self._writer.write(ONetV2.packet(transaction, packet_type, payload))
        await self._writer.drain()
        header = await self._reader.readexactly(_HEADER_SIZE)
        data_length, version, reply_transaction, reply_type = struct.unpack_from("<IBBH", header, 4)
        if version != 2 or reply_transaction != transaction:
            raise ValueError("FM-Master reply does not match request")
        return reply_type, await self._reader.readexactly(data_length)

    async def authenticate(self, password: str) -> None:
        reply_type, payload = await self.request(CHECK_PASSWORD, ONetV2.password_payload(password))
        if reply_type != CHECK_PASSWORD_REPLY or payload != b"\x01":
            raise PermissionError("FM-Master rejected device password")

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


async def open_authenticated_session(
    host: str,
    password: str,
    certificate_directory: str,
    *,
    callback_port: int = TCP_CALLBACK_PORT,
    timeout: float = 12,
) -> FmMasterSession:
    """Request a local callback, accept TLS 1.2, then authenticate it."""
    from pathlib import Path
    from .tls import create_server_context

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((host, UDP_PORT))
        local_ip = probe.getsockname()[0]

    loop = asyncio.get_running_loop()
    accepted: asyncio.Future[tuple[asyncio.StreamReader, asyncio.StreamWriter]] = loop.create_future()

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if accepted.done():
            writer.close()
            await writer.wait_closed()
            return
        accepted.set_result((reader, writer))

    server = await asyncio.start_server(
        handle_client,
        host=local_ip,
        port=callback_port,
        ssl=create_server_context(Path(certificate_directory)),
    )
    try:
        _, acknowledgement = await asyncio.to_thread(
            request_callback_datagram, host, local_ip, callback_port
        )
        if not acknowledgement or acknowledgement[0] != 1:
            raise ConnectionError("FM-Master did not accept the TCP callback")
        reader, writer = await asyncio.wait_for(accepted, timeout)
        session = FmMasterSession(reader, writer)
        try:
            await session.authenticate(password)
        except Exception:
            await session.close()
            raise
        return session
    finally:
        server.close()
        await server.wait_closed()


def request_callback_datagram(host: str, local_ip: str, port: int = TCP_CALLBACK_PORT) -> tuple[int, bytes]:
    """Synchronous low-level callback request; used only by hardware diagnostics."""
    datagram = ONetV2.packet(1, REQUEST_TCP_CALLBACK, ONetV2.request_tcp_callback(port))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind((local_ip, UDP_PORT))
        udp.settimeout(5)
        udp.sendto(datagram, (host, UDP_PORT))
        raw, _ = udp.recvfrom(2048)
    _, packet_type, payload = parse_packet(raw)
    if packet_type != REQUEST_TCP_CALLBACK_REPLY:
        raise ValueError("FM-Master rejected TCP callback request")
    return packet_type, payload
