"""State coordinator independent of Home Assistant's runtime."""

from __future__ import annotations

from typing import Protocol


class SocketClient(Protocol):
    async def read_sockets(self) -> tuple[bool, bool, bool, bool]: ...

    async def set_socket(self, socket: int, on: bool) -> None: ...


class FmMasterCoordinator:
    """Serializes local FM-Master reads and socket writes."""

    def __init__(self, client: SocketClient) -> None:
        self._client = client
        self._states: tuple[bool, bool, bool, bool] | None = None

    async def async_refresh(self) -> tuple[bool, bool, bool, bool]:
        self._states = await self._client.read_sockets()
        return self._states

    async def async_set_socket(self, socket: int, on: bool) -> tuple[bool, bool, bool, bool]:
        await self._client.set_socket(socket, on)
        return await self.async_refresh()

    def socket_state(self, socket: int) -> bool:
        if self._states is None:
            raise RuntimeError("FM-Master state is not available before first refresh")
        return self._states[socket]

    @property
    def states(self) -> tuple[bool, bool, bool, bool] | None:
        return self._states
