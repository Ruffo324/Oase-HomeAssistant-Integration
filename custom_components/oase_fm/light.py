"""Dimmable fourth FM-Master outlet."""

from __future__ import annotations

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN
from .coordinator import FmMasterCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OaseFmDimmer(data[DATA_CLIENT], data[DATA_COORDINATOR])])


class OaseFmDimmer(LightEntity):
    """FM-Master outlet 4 dimmer control."""

    _attr_has_entity_name = True
    _attr_name = "Outlet 4 dimmer"
    _attr_unique_id = "oase_fm_dimmer_4"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, client, coordinator: FmMasterCoordinator) -> None:
        self._client = client
        self._coordinator = coordinator
        self._level = 0

    @property
    def is_on(self) -> bool:
        return self._level > 0

    @property
    def brightness(self) -> int:
        return self._level

    async def async_update(self) -> None:
        self._level = await self._client.read_dimmer_level()
        await self._coordinator.async_refresh()

    async def async_turn_on(self, **kwargs: object) -> None:
        level = int(kwargs.get(ATTR_BRIGHTNESS, self._level or 255))
        await self._client.set_dimmer_level(level)
        self._level = await self._client.read_dimmer_level()
        await self._coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._client.set_dimmer_level(0)
        self._level = await self._client.read_dimmer_level()
        await self._coordinator.async_refresh()
        self.async_write_ha_state()
