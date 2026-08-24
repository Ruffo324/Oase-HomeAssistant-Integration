"""Switch entities for FM-Master's four local outlets."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN, SOCKET_COUNT
from .coordinator import FmMasterCoordinator
from .switch_model import FmMasterSocket


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FmMasterCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    # Outlets 1–3 are relays. Outlet 4 is exposed once as a brightness light.
    async_add_entities([OaseFmSwitch(coordinator, socket) for socket in range(SOCKET_COUNT - 1)])


class OaseFmSwitch(SwitchEntity):
    """One FM-Master local outlet."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FmMasterCoordinator, socket: int) -> None:
        self._model = FmMasterSocket(coordinator, socket)
        self._attr_name = self._model.name
        self._attr_unique_id = self._model.unique_id

    @property
    def is_on(self) -> bool:
        return self._model.is_on

    async def async_turn_on(self, **kwargs: object) -> None:
        await self._model.async_turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        await self._model.async_turn_off()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._model.coordinator.async_refresh()
