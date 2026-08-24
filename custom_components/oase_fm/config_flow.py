"""Config flow for local OASE FM-Master access and AP onboarding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_HOST, CONF_PASSWORD, DOMAIN
from .onboarding import (
    async_apply_router_initial_config,
    async_discover_gateway_host,
    async_scan_wifi_ssids,
)
from .transport import open_authenticated_session

CONF_SETUP_MODE = "setup_mode"
CONF_WIFI_SSID = "wifi_ssid"
CONF_WIFI_PASSWORD = "wifi_password"
CONF_HOME_HOST = "home_host"
MODE_EXISTING = "existing"
MODE_AP_ONBOARD = "ap_onboard"


class OaseFmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure an FM-Master on LAN, or provision it from its AP."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> FlowResult:
        if user_input is not None:
            if user_input[CONF_SETUP_MODE] == MODE_AP_ONBOARD:
                return await self.async_step_ap_onboard()
            return await self.async_step_existing()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SETUP_MODE, default=MODE_EXISTING): vol.In(
                        {MODE_EXISTING: "Existing LAN gateway", MODE_AP_ONBOARD: "Gateway AP onboarding"}
                    )
                }
            ),
        )

    async def async_step_existing(self, user_input: dict[str, str] | None = None) -> FlowResult:
        if user_input is not None:
            return await self._async_create_gateway_entry(user_input[CONF_HOST], user_input[CONF_PASSWORD])
        return self.async_show_form(
            step_id="existing",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.1.1"): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
        )

    async def async_step_ap_onboard(self, user_input: dict[str, str] | None = None) -> FlowResult:
        """Authenticate to the gateway AP, then scan through its Wi-Fi radio."""
        errors: dict[str, str] = {}
        if user_input is not None:
            ap_host = user_input[CONF_HOST]
            device_password = user_input[CONF_PASSWORD]
            certificate_directory = Path(self.hass.config.path(".storage", DOMAIN, "onboarding"))

            async def open_session():
                return await open_authenticated_session(
                    ap_host, device_password, str(certificate_directory), callback_port=5999
                )

            try:
                ssids = await async_scan_wifi_ssids(open_session)
            except (ConnectionError, OSError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                self._onboarding_data = {CONF_HOST: ap_host, CONF_PASSWORD: device_password}
                return await self.async_step_ap_wifi(ssids=ssids)
        return self.async_show_form(
            step_id="ap_onboard",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="192.168.1.1"): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_ap_wifi(
        self, user_input: dict[str, str] | None = None, *, ssids: list[str] | None = None
    ) -> FlowResult:
        """Choose a Wi-Fi SSID reported by the FM-Master, then provision it."""
        if ssids is not None:
            self._scanned_ssids = ssids
        if user_input is not None:
            ap_host = self._onboarding_data[CONF_HOST]
            device_password = self._onboarding_data[CONF_PASSWORD]
            certificate_directory = Path(self.hass.config.path(".storage", DOMAIN, "onboarding"))

            async def open_session():
                return await open_authenticated_session(
                    ap_host, device_password, str(certificate_directory), callback_port=5999
                )

            try:
                await async_apply_router_initial_config(
                    open_session, device_password, user_input[CONF_WIFI_SSID], user_input[CONF_WIFI_PASSWORD]
                )
            except (ConnectionError, OSError, TimeoutError, ValueError):
                return self.async_show_form(
                    step_id="ap_wifi", data_schema=self._wifi_schema(), errors={"base": "cannot_connect"}
                )
            self._onboarding_data[CONF_WIFI_SSID] = user_input[CONF_WIFI_SSID]
            return await self.async_step_home_host()
        return self.async_show_form(step_id="ap_wifi", data_schema=self._wifi_schema())

    def _wifi_schema(self) -> vol.Schema:
        choices = {ssid: ssid for ssid in getattr(self, "_scanned_ssids", [])}
        ssid_field = vol.In(choices) if choices else str
        return vol.Schema(
            {
                vol.Required(CONF_WIFI_SSID): ssid_field,
                vol.Required(CONF_WIFI_PASSWORD): str,
            }
        )

    async def async_step_home_host(self, user_input: dict[str, str] | None = None) -> FlowResult:
        """Discover the new DHCP address across active host interfaces."""
        if user_input is not None:
            return await self._async_create_gateway_entry(
                user_input[CONF_HOME_HOST], self._onboarding_data[CONF_PASSWORD]
            )
        discovered_host = await async_discover_gateway_host()
        if discovered_host is not None:
            return await self._async_create_gateway_entry(
                discovered_host, self._onboarding_data[CONF_PASSWORD]
            )
        return self.async_show_form(
            step_id="home_host",
            description_placeholders={"hint": "Automatic LAN discovery timed out. Enter the DHCP address from your router."},
            data_schema=vol.Schema({vol.Required(CONF_HOME_HOST): str}),
        )

    async def _async_create_gateway_entry(self, host: str, password: str) -> FlowResult:
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="OASE FM-Master", data={CONF_HOST: host, CONF_PASSWORD: password})
