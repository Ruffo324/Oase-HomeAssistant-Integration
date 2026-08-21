import asyncio

from homeassistant.core import HomeAssistant

from custom_components.oase_fm.switch import OaseFmSwitch


class FakeCoordinator:
    def __init__(self) -> None:
        self.states = (False, False, False, False)
        self.refreshes = 0

    def socket_state(self, socket: int) -> bool:
        return self.states[socket]

    async def async_set_socket(self, socket: int, on: bool) -> None:
        states = list(self.states)
        states[socket] = on
        self.states = tuple(states)

    async def async_refresh(self) -> tuple[bool, bool, bool, bool]:
        self.refreshes += 1
        return self.states


def test_ha_switch_exposes_fourth_outlet_identity() -> None:
    entity = OaseFmSwitch(FakeCoordinator(), 3)

    assert entity.name == "Outlet 4"
    assert entity.unique_id == "oase_fm_socket_4"
    assert entity.is_on is False


def test_ha_switch_turn_on_and_refresh() -> None:
    coordinator = FakeCoordinator()
    entity = OaseFmSwitch(coordinator, 1)
    entity.async_write_ha_state = lambda: None

    asyncio.run(entity.async_turn_on())
    asyncio.run(entity.async_update())

    assert entity.is_on is True
    assert coordinator.refreshes == 1
