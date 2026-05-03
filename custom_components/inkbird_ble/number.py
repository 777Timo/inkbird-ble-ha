"""Inkbird BLE Number-Entities: Grill-Zieltemperatur + Sonden-Alarm-Temperaturen."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, InkbirdCoordinator, InkbirdData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = [InkbirdTargetTemp(coordinator, entry)]
    entities += [
        InkbirdProbeAlarm(coordinator, entry, probe, name)
        for probe, name in (
            ("probe1_alarm", "Sonde 1 Alarm-Temperatur"),
            ("probe2_alarm", "Sonde 2 Alarm-Temperatur"),
            ("probe3_alarm", "Sonde 3 Alarm-Temperatur"),
        )
    ]
    async_add_entities(entities)


class InkbirdTargetTemp(NumberEntity):
    _attr_has_entity_name = True
    _attr_name = "Grill-Zieltemperatur"
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 20.0
    _attr_native_max_value = 300.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX
    _attr_available = True

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
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._coordinator.target_temp

    async def async_set_native_value(self, value: float) -> None:
        await self._coordinator.async_set_target_temp(value)
        self.async_write_ha_state()


class InkbirdProbeAlarm(NumberEntity):
    """Alarm-Zieltemperatur für eine einzelne Sonde (schreibbar via FFF3)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer-alert"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 20.0
    _attr_native_max_value = 300.0
    _attr_native_step = 1.0
    _attr_mode = NumberMode.BOX
    _attr_available = True

    def __init__(
        self,
        coordinator: InkbirdCoordinator,
        entry: ConfigEntry,
        probe: str,
        name: str,
    ) -> None:
        self._coordinator = coordinator
        self._probe = probe  # z.B. "probe1_alarm"
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{probe}"
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
    def native_value(self) -> float | None:
        return getattr(self._coordinator.data, self._probe)

    async def async_set_native_value(self, value: float) -> None:
        await self._coordinator.async_set_probe_alarm(self._probe, value)
        self.async_write_ha_state()
