"""Config flow für Inkbird ISC-027BW BLE."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from . import DOMAIN

DEFAULT_ADDRESS = "49:24:12:07:08:A6"


class InkbirdConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Auto-Discovery via BT-Scanner."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovered_address = discovery_info.address
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        # Vorausgefüllte Adresse: aus Discovery oder Default
        default_addr = self._discovered_address or DEFAULT_ADDRESS

        # Bereits konfigurierten Eintrag nicht doppelt anlegen
        for entry in self._async_current_entries():
            if entry.data.get(CONF_ADDRESS, "").upper() == default_addr.upper():
                return self.async_abort(reason="already_configured")

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Inkbird S27 ({address})",
                data={CONF_ADDRESS: address},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS, default=default_addr): str,
            }),
            errors=errors,
            description_placeholders={"address": default_addr},
        )
