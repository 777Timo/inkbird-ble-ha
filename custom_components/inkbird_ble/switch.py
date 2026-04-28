"""Inkbird BLE Lüfter-Switch: Gebläse ein/aus."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, InkbirdCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InkbirdFanSwitch(coordinator, entry)])


class InkbirdFanSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Lüfter"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator: InkbirdCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_fan_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Inkbird ISC-027BW",
            manufacturer="Inkbird",
            model="ISC-027BW",
        )

    async def async_added_to_hass(self) -> None:
        self._unregister = self._coordinator.register_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._unregister()

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return bool(self._coordinator.data.fan_on)

    @property
    def available(self) -> bool:
        return self._coordinator.data.connected and self._coordinator.data.fan_on is not None

    async def async_turn_on(self, **kwargs) -> None:
        await self._coordinator.async_set_fan_on(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_set_fan_on(False)
