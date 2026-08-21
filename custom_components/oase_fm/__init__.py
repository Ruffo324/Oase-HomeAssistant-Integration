"""OASE FM-Master Local integration."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import LiveFmMasterClient
from .const import CONF_HOST, CONF_PASSWORD, DATA_CLIENT, DATA_COORDINATOR, DOMAIN, PLATFORMS
from .coordinator import FmMasterCoordinator
from .transport import open_authenticated_session


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a locally reachable FM-Master."""
    certificate_directory = Path(hass.config.path(".storage", DOMAIN, entry.entry_id))
    open_session = partial(
        open_authenticated_session,
        entry.data[CONF_HOST],
        entry.data[CONF_PASSWORD],
        str(certificate_directory),
    )
    client = LiveFmMasterClient(open_session)
    coordinator = FmMasterCoordinator(client)
    await coordinator.async_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload FM-Master entities."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
