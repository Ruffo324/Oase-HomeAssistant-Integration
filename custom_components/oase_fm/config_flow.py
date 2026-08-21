"""Config flow for local OASE FM-Master access."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_HOST, CONF_PASSWORD, DOMAIN


class OaseFmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one FM-Master through its local AP or LAN address."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="OASE FM-Master", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.1.1"): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
