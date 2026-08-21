import asyncio

from custom_components.oase_fm.coordinator import FmMasterCoordinator


class FakeClient:
    def __init__(self) -> None:
        self.states = (False, False, False, False)
        self.set_calls = []

    async def read_sockets(self):
        return self.states

    async def set_socket(self, socket, on):
        self.set_calls.append((socket, on))
        states = list(self.states)
        states[socket] = on
        self.states = tuple(states)


def test_coordinator_refreshes_and_updates_a_single_socket() -> None:
    client = FakeClient()
    coordinator = FmMasterCoordinator(client)

    assert asyncio.run(coordinator.async_refresh()) == (False, False, False, False)
    assert asyncio.run(coordinator.async_set_socket(2, True)) == (False, False, True, False)
    assert client.set_calls == [(2, True)]


def test_coordinator_requires_first_refresh_before_state_access() -> None:
    import pytest

    with pytest.raises(RuntimeError, match="not available"):
        FmMasterCoordinator(FakeClient()).socket_state(0)
