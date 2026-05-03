"""Inkbird BLE Sensoren: Temperaturen + Lüfterdrehzahl."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, InkbirdCoordinator, InkbirdData


@dataclass(frozen=True, kw_only=True)
class InkbirdSensorDescription(SensorEntityDescription):
    value_fn: Callable[[InkbirdData], float | int | None]
    # Wert der gezeigt wird wenn Gerät nicht verbunden ist (None = unknown)
    offline_value: float | int | None = 0


SENSORS: tuple[InkbirdSensorDescription, ...] = (
    InkbirdSensorDescription(
        key="probe0",
        translation_key="probe0",
        name="Innentemperatur / Sonde 0",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe0,
    ),
    InkbirdSensorDescription(
        key="probe1",
        translation_key="probe1",
        name="Sonde 1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe1,
    ),
    InkbirdSensorDescription(
        key="probe2",
        translation_key="probe2",
        name="Sonde 2",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe2,
    ),
    InkbirdSensorDescription(
        key="probe3",
        translation_key="probe3",
        name="Sonde 3",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.probe3,
    ),
    InkbirdSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        name="Lüfter Ist-Drehzahl",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda d: d.fan_speed,
    ),
    InkbirdSensorDescription(
        key="grill_target_actual",
        translation_key="grill_target_actual",
        name="Zieltemperatur (Gerät)",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.grill_target_actual,
        offline_value=None,  # Zieltemp bleibt auf letztem Wert
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InkbirdSensor(coordinator, entry, description) for description in SENSORS
    )


class InkbirdSensor(SensorEntity):
    entity_description: InkbirdSensorDescription
    _attr_has_entity_name = True
    _attr_available = True  # immer verfügbar — zeigt 0 wenn getrennt

    def __init__(
        self,
        coordinator: InkbirdCoordinator,
        entry: ConfigEntry,
        description: InkbirdSensorDescription,
    ) -> None:
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
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
    def native_value(self) -> float | int | None:
        if not self._coordinator.data.connected:
            return self.entity_description.offline_value
        return self.entity_description.value_fn(self._coordinator.data)
