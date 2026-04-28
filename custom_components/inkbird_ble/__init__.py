"""Inkbird ISC-027BW BLE Integration."""
from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from dataclasses import dataclass

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_ble_device_from_address,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DOMAIN = "inkbird_ble"
PLATFORMS = ["sensor", "number", "switch"]

FFF1 = "0000fff1-0000-1000-8000-00805f9b34fb"
FFF2 = "0000fff2-0000-1000-8000-00805f9b34fb"
FFF3 = "0000fff3-0000-1000-8000-00805f9b34fb"

CONF_ADDRESS = "address"

# Fahrenheit×10 Schwellenwert: 0x1770 = 6000 = 600.0°F ≈ 315°C
_F10_MAX_VALID = 0x1770


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _f10_to_c(f10: int) -> float | None:
    if 0 < f10 < _F10_MAX_VALID:
        return round((f10 / 10 - 32) * 5 / 9, 1)
    return None


def _c_to_f10(celsius: float) -> int:
    return max(680, min(5720, round((celsius * 9 / 5 + 32) * 10)))


def decode_fff2(data: bytes) -> dict:
    """FFF2: 4 Sonden in Bytes 0-7 (Fahrenheit×10, little-endian), Lüfter-Ist-% in Byte 8."""
    result: dict[str, float | int | None] = {}
    for i in range(4):
        v = struct.unpack_from("<H", data, i * 2)[0]
        result[f"probe{i}"] = _f10_to_c(v)
    result["fan_speed"] = data[8] if len(data) > 8 else None
    return result


def build_fff1(
    current_fff1: bytes,
    fan_on: bool | None = None,
    speed: int | None = None,
) -> bytes:
    """FFF1 Write: Byte[0]=fan, Byte[6]=speed (0-100), CRC16-Modbus neu berechnen."""
    payload = bytearray(current_fff1)
    if fan_on is not None:
        payload[0] = 1 if fan_on else 0
    if speed is not None:
        payload[6] = max(0, min(100, speed))
    struct.pack_into("<H", payload, 18, crc16_modbus(bytes(payload[:18])))
    return bytes(payload)


def build_fff3(current_fff3: bytes, target_c: float) -> bytes:
    """FFF3 Write: bytes[0-1] = Grill-Zieltemp in Fahrenheit×10, CRC16-Modbus an bytes[18-19]."""
    payload = bytearray(current_fff3)
    struct.pack_into("<H", payload, 0, _c_to_f10(target_c))
    struct.pack_into("<H", payload, 18, crc16_modbus(bytes(payload[:18])))
    return bytes(payload)


@dataclass
class InkbirdData:
    probe0: float | None = None
    probe1: float | None = None
    probe2: float | None = None
    probe3: float | None = None
    fan_speed: int | None = None
    grill_target_actual: float | None = None
    fan_on: bool | None = None
    connected: bool = False


class InkbirdCoordinator:
    """Persistente BLE-Verbindung zum Inkbird ISC-027BW."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self.hass = hass
        self.address = address
        self.data = InkbirdData()
        self._target_temp: float = 100.0
        self._listeners: list[Callable] = []
        self._task: asyncio.Task | None = None
        self._fff1_current: bytes = bytes(20)
        self._fff3_current: bytes = bytes(20)
        self._pending_fan_on: bool | None = None
        self._pending_target: float | None = None

    @property
    def target_temp(self) -> float:
        return self._target_temp

    def register_listener(self, callback: Callable) -> Callable:
        self._listeners.append(callback)
        def unregister():
            self._listeners.remove(callback)
        return unregister

    def _notify(self) -> None:
        for cb in self._listeners:
            self.hass.loop.call_soon(cb)

    async def async_start(self) -> None:
        self._task = self.hass.async_create_task(self._ble_loop())

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def async_set_fan_on(self, on: bool) -> None:
        self._pending_fan_on = on
        self.data.fan_on = on
        self._notify()

    async def async_set_target_temp(self, temp_c: float) -> None:
        self._pending_target = temp_c
        self._target_temp = temp_c
        _LOGGER.debug("Inkbird: Zieltemp → %.1f°C", temp_c)

    async def _ble_loop(self) -> None:
        while True:
            try:
                await self._connect_and_run()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _LOGGER.warning("Inkbird BLE Fehler: %s — Retry in 15s", exc)
                self.data.connected = False
                self._notify()
                await asyncio.sleep(15)

    async def _wait_for_advertisement(self, timeout: float = 60.0):
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def _bt_callback(service_info, change) -> None:
            if service_info.address.upper() != self.address.upper():
                return
            ha_device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            chosen = ha_device if ha_device is not None else service_info.device
            if not future.done():
                future.set_result(chosen)

        cancel = async_register_callback(
            self.hass,
            _bt_callback,
            None,
            BluetoothScanningMode.ACTIVE,
        )
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            cancel()

    async def _connect_and_run(self) -> None:
        ble_device = async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            _LOGGER.info("Inkbird (%s) nicht im Scanner — warte auf Advertisement...", self.address)
            ble_device = await self._wait_for_advertisement(timeout=60.0)

        if ble_device is None:
            _LOGGER.info("Inkbird (%s) — kein Advertisement in 60s, retry in 15s", self.address)
            await asyncio.sleep(15)
            return

        _LOGGER.info("Verbinde mit Inkbird %s", self.address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.address,
            max_attempts=3,
        )
        async with client:
            for svc in client.services:
                chars = [c.uuid for c in svc.characteristics]
                _LOGGER.warning("BLE Service %s: %s", svc.uuid, chars)
            self.data.connected = True

            def fff2_handler(sender, data: bytearray) -> None:
                _LOGGER.debug("FFF2 notify: %s", bytes(data).hex(" "))
                decoded = decode_fff2(bytes(data))
                self.data.probe0 = decoded.get("probe0")
                self.data.probe1 = decoded.get("probe1")
                self.data.probe2 = decoded.get("probe2")
                self.data.probe3 = decoded.get("probe3")
                self.data.fan_speed = decoded.get("fan_speed")
                self._notify()

            try:
                await asyncio.wait_for(
                    client.start_notify(FFF2, fff2_handler), timeout=10.0
                )
                _LOGGER.warning("FFF2 Notify registriert")
            except Exception as exc:
                _LOGGER.warning("FFF2 start_notify Fehler: %s", exc)

            await asyncio.sleep(2.0)

            # FFF3 lesen — bytes[0-1] = Grill-Zieltemp in Fahrenheit×10
            try:
                fff3_init = bytes(await asyncio.wait_for(
                    client.read_gatt_char(FFF3), timeout=10.0
                ))
                self._fff3_current = fff3_init
                tgt_f10 = struct.unpack_from("<H", fff3_init, 0)[0]
                tgt_c = _f10_to_c(tgt_f10)
                _LOGGER.warning("FFF3 Zieltemp: %d F×10 → %s°C", tgt_f10, tgt_c)
                if tgt_c is not None and self._pending_target is None:
                    self._target_temp = tgt_c
                    self.data.grill_target_actual = tgt_c
            except Exception as exc:
                _LOGGER.warning("FFF3 read Fehler: %s", exc)

            # FFF1 lesen (Gerätestatus: fan on/off, Modus, Drehzahl)
            try:
                fff1_init = bytes(await asyncio.wait_for(
                    client.read_gatt_char(FFF1), timeout=10.0
                ))
                self._fff1_current = fff1_init
                self.data.fan_on = bool(fff1_init[0])
                _LOGGER.warning("FFF1 Lüfter: %s", "AN" if self.data.fan_on else "AUS")
            except Exception as exc:
                _LOGGER.warning("FFF1 read Fehler: %s", exc)

            _LOGGER.warning("Init abgeschlossen — starte Polling-Loop")
            self._notify()

            try:
                while client.is_connected:
                    if self._pending_fan_on is not None:
                        fan_on = self._pending_fan_on
                        self._pending_fan_on = None
                        fff1_new = build_fff1(self._fff1_current, fan_on=fan_on)
                        try:
                            await client.write_gatt_char(FFF1, fff1_new, response=True)
                            self._fff1_current = fff1_new
                            self.data.fan_on = fan_on
                            _LOGGER.warning("FFF1 geschrieben: fan=%s", fan_on)
                        except BleakError as exc:
                            _LOGGER.warning("FFF1 Write Fehler: %s", exc)

                    if self._pending_target is not None:
                        self._target_temp = self._pending_target
                        self._pending_target = None
                        fff3_new = build_fff3(self._fff3_current, self._target_temp)
                        try:
                            await client.write_gatt_char(FFF3, fff3_new, response=True)
                            self._fff3_current = fff3_new
                            _LOGGER.warning("FFF3 geschrieben: %.1f°C", self._target_temp)
                        except BleakError as exc:
                            _LOGGER.warning("FFF3 Write Fehler: %s", exc)

                    # FFF2 lesen (Fallback wenn Notify nicht kommt)
                    try:
                        fff2 = bytes(await asyncio.wait_for(
                            client.read_gatt_char(FFF2), timeout=8.0
                        ))
                        decoded = decode_fff2(fff2)
                        self.data.probe0 = decoded.get("probe0")
                        self.data.probe1 = decoded.get("probe1")
                        self.data.probe2 = decoded.get("probe2")
                        self.data.probe3 = decoded.get("probe3")
                        self.data.fan_speed = decoded.get("fan_speed")
                    except Exception:
                        pass

                    # FFF1 lesen (Lüfterstatus-Update)
                    try:
                        fff1 = bytes(await asyncio.wait_for(
                            client.read_gatt_char(FFF1), timeout=8.0
                        ))
                        self._fff1_current = fff1
                        self.data.fan_on = bool(fff1[0])
                    except Exception:
                        pass

                    # FFF3 lesen (Zieltemp-Update vom Gerät)
                    try:
                        fff3 = bytes(await asyncio.wait_for(
                            client.read_gatt_char(FFF3), timeout=8.0
                        ))
                        self._fff3_current = fff3
                        tgt_f10 = struct.unpack_from("<H", fff3, 0)[0]
                        self.data.grill_target_actual = _f10_to_c(tgt_f10)
                    except Exception:
                        pass

                    self._notify()
                    await asyncio.sleep(3.0)

            finally:
                try:
                    await client.stop_notify(FFF2)
                except Exception:
                    pass

        self.data.connected = False
        self._notify()
        _LOGGER.info("Inkbird getrennt — reconnect in 5s")
        await asyncio.sleep(5)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.data[CONF_ADDRESS]
    coordinator = InkbirdCoordinator(hass, address)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
