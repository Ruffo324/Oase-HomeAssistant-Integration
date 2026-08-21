import asyncio

from custom_components.oase_fm.switch_model import FmMasterSocket


class FakeCoordinator:
    def __init__(self):
        self.states = (False, True, False, True)
        self.commands = []

    def socket_state(self, socket):
        return self.states[socket]

    async def async_set_socket(self, socket, on):
        self.commands.append((socket, on))
        states = list(self.states)
        states[socket] = on
        self.states = tuple(states)


def test_socket_model_exposes_stable_names_and_current_state() -> None:
    coordinator = FakeCoordinator()
    entity = FmMasterSocket(coordinator, 1)

    assert entity.name == "Outlet 2"
    assert entity.unique_id == "oase_fm_socket_2"
    assert entity.is_on is True


def test_socket_model_turns_socket_on() -> None:
    coordinator = FakeCoordinator()
    entity = FmMasterSocket(coordinator, 0)

    asyncio.run(entity.async_turn_on())

    assert coordinator.commands == [(0, True)]
    assert entity.is_on is True


def test_socket_model_rejects_invalid_socket() -> None:
    import pytest

    with pytest.raises(ValueError, match="range"):
        FmMasterSocket(FakeCoordinator(), 4)
