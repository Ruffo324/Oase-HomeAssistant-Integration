import asyncio

from homeassistant.components.light import ATTR_BRIGHTNESS

from custom_components.oase_fm.light import OaseFmDimmer


class Client:
    def __init__(self) -> None:
        self.level = 0

    async def read_dimmer_level(self) -> int:
        return self.level

    async def set_dimmer_level(self, level: int) -> None:
        self.level = level


class Coordinator:
    async def async_refresh(self):
        return ()


def test_dimmer_turn_on_with_brightness() -> None:
    client = Client()
    entity = OaseFmDimmer(client, Coordinator())
    entity.async_write_ha_state = lambda: None
    asyncio.run(entity.async_turn_on(**{ATTR_BRIGHTNESS: 64}))
    assert entity.is_on is True
    assert entity.brightness == 64


def test_dimmer_turn_off() -> None:
    client = Client()
    entity = OaseFmDimmer(client, Coordinator())
    entity.async_write_ha_state = lambda: None
    asyncio.run(entity.async_turn_on(**{ATTR_BRIGHTNESS: 64}))
    asyncio.run(entity.async_turn_off())
    assert entity.is_on is False
    assert entity.brightness == 0


def test_dimmer_default_turn_on_is_full_brightness() -> None:
    client = Client()
    entity = OaseFmDimmer(client, Coordinator())
    entity.async_write_ha_state = lambda: None
    asyncio.run(entity.async_turn_on())
    assert entity.brightness == 255
