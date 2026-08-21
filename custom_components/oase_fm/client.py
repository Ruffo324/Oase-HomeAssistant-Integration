"""Current EasyControl TCP command shapes for a local FM-Master."""

from __future__ import annotations

import struct
from collections.abc import Awaitable, Callable
from typing import Protocol


class Session(Protocol):
    async def request(self, packet_type: int, payload: bytes) -> tuple[int, bytes]: ...


class FmMasterClient:
    """Authenticated local FM-Master socket controller."""

    def __init__(
        self,
        host: str,
        password: str,
        *,
        session_factory: Callable[[], Session],
    ) -> None:
        self.host = host
        self.password = password
        self._session_factory = session_factory

    @staticmethod
    def socket_scene(*, socket: int, on: bool) -> bytes:
        if not 0 <= socket <= 3:
            raise ValueError("socket must be in range 0 through 3")
        return bytes((4,)) + struct.pack("<II", 0, 0) + bytes((100, 2, socket, 255 if on else 0))

    @staticmethod
    def parse_socket_states(payload: bytes) -> tuple[bool, bool, bool, bool]:
        if len(payload) < 16 or payload[9] != 101 or payload[10] < 4:
            raise ValueError("response does not contain an FM-Master socket scene")
        return tuple(value >= 128 for value in payload[11:15])  # type: ignore[return-value]

    async def read_sockets(self) -> tuple[bool, bool, bool, bool]:
        _, payload = await self._session_factory().request(0xC500, bytes((4,)) + struct.pack("<I", 0))
        return self.parse_socket_states(payload)

    async def set_socket(self, socket: int, on: bool) -> None:
        packet_type, payload = await self._session_factory().request(0xC400, self.socket_scene(socket=socket, on=on))
        if packet_type != 0xC4FF or payload != b"\x01":
            raise ValueError("FM-Master rejected socket command")


class LiveFmMasterClient:
    """FM-Master client that opens one short authenticated TLS callback per operation."""

    def __init__(self, open_session: Callable[[], Awaitable[Session]]) -> None:
        self._open_session = open_session

    async def read_sockets(self) -> tuple[bool, bool, bool, bool]:
        session = await self._open_session()
        try:
            _, payload = await session.request(0xC500, bytes((4,)) + struct.pack("<I", 0))
            return FmMasterClient.parse_socket_states(payload)
        finally:
            await session.close()

    async def set_socket(self, socket: int, on: bool) -> None:
        session = await self._open_session()
        try:
            packet_type, payload = await session.request(0xC400, FmMasterClient.socket_scene(socket=socket, on=on))
            if packet_type != 0xC4FF or payload != b"\x01":
                raise ValueError("FM-Master rejected socket command")
        finally:
            await session.close()
