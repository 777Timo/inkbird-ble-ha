"""Inkbird BLE Zieltemperatur — steuert Grill-Lüfter."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    async_add_entities([InkbirdTargetTemp(coordinator, entry)])


class InkbirdTargetTemp(NumberEntity):
    """Grill-Zieltemperatur setzen (FFF3 Byte[0-1], Fahrenheit×10)."""

    _attr_has_entity_name = True
    _attr_name = "Grill-Zieltemperatur"
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 20.0
    _attr_native_max_value = 300.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: InkbirdCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_target_temp"
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
        self._attr_available = self._coordinator.data.connected
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._coordinator.target_temp

    @property
    def available(self) -> bool:
        return self._coordinator.data.connected

    async def async_set_native_value(self, value: float) -> None:
        await self._coordinator.async_set_target_temp(value)
        self.async_write_ha_state()
