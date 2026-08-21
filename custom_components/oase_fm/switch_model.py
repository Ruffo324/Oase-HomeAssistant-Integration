"""Pure switch model, adapted by the Home Assistant platform entity."""

from __future__ import annotations

from typing import Protocol


class SocketCoordinator(Protocol):
    def socket_state(self, socket: int) -> bool: ...

    async def async_set_socket(self, socket: int, on: bool) -> object: ...


class FmMasterSocket:
    """One of the FM-Master's four local outlets."""

    def __init__(self, coordinator: SocketCoordinator, socket: int) -> None:
        if not 0 <= socket <= 3:
            raise ValueError("socket must be in range 0 through 3")
        self.coordinator = coordinator
        self.socket = socket

    @property
    def name(self) -> str:
        return f"Outlet {self.socket + 1}"

    @property
    def unique_id(self) -> str:
        return f"oase_fm_socket_{self.socket + 1}"

    @property
    def is_on(self) -> bool:
        return self.coordinator.socket_state(self.socket)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_socket(self.socket, True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_socket(self.socket, False)
