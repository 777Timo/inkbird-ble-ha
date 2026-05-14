# Inkbird ISC-027BW BLE — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/github/v/release/777Timo/inkbird-ble-ha)](https://github.com/777Timo/inkbird-ble-ha/releases)

> **Vibe coded** — Developed entirely with [Claude Code](https://claude.ai/code) (Anthropic).

[🇩🇪 Deutsche Version](README.de.md)

Custom integration for the **Inkbird ISC-027BW** Bluetooth grill thermometer with fan controller.

---

## Features

- 🌡️ **4 temperature probes** — real-time readings via BLE Notify (FFF2)
- 💨 **Fan actual speed** — current blower value in %
- 🎯 **Grill target temperature** — read and set via FFF3
- 🔌 **Fan on/off** — direct blower control via FFF1
- 🔄 **Persistent BLE connection** with automatic reconnect
- 📊 **Lovelace dashboard** — pre-configured with gauge cards and history graphs
- 📡 **No cloud required** — fully local via Bluetooth

---

## Supported Devices

| Device | Tested |
|--------|--------|
| Inkbird ISC-027BW | ✅ |

---

## Installation

### Via HACS (recommended)

1. Open HACS → **⋮ → Custom Repositories**
2. Enter URL `777Timo/inkbird-ble-ha`, category **Integration** → **Add**
3. Search for the integration and click **Download**
4. Restart Home Assistant
5. **Settings → Devices & Services → Add Integration → Inkbird BLE**
6. Enter the Bluetooth address of your device (e.g. `49:24:12:07:08:A6`)

### Manual

1. Download [`inkbird_ble.zip`](https://github.com/777Timo/inkbird-ble-ha/releases/latest) and unpack it
2. Copy the `custom_components/inkbird_ble` folder to your HA config directory
3. Restart Home Assistant
4. **Settings → Devices & Services → Add Integration → Inkbird BLE**
5. Enter the Bluetooth address of your device

### Dashboard (optional)

1. Copy `dashboard/inkbird.yaml` to `/config/dashboards/inkbird.yaml`
2. Add to `configuration.yaml`:
   ```yaml
   lovelace:
     mode: storage
     dashboards:
       inkbird-grill:
         mode: yaml
         filename: dashboards/inkbird.yaml
         title: Inkbird Grill
         icon: mdi:grill
         show_in_sidebar: true
   ```
3. Restart Home Assistant → dashboard appears in the sidebar

### Requirements

- Home Assistant with the Bluetooth add-on or a local Bluetooth adapter
- Inkbird ISC-027BW within range

---

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Inside Temperature / Probe 0 | Sensor | Grill probe (°C/°F) |
| Probe 1–3 | Sensor | External probes (°C/°F) |
| Fan Speed | Sensor | Current blower value (%) |
| Target Temperature (Device) | Sensor | Target temperature read from device (°C/°F) |
| Grill Target Temperature | Number | Set target temperature (20–300°C) |
| Probe 1–3 Alarm Temperature | Number | Set alarm temperature per probe (20–300°C) |
| Fan | Switch | Blower on/off |

---

## BLE Protocol

Protocol was fully reverse-engineered:

| Characteristic | UUID | Function |
|----------------|------|----------|
| FFF1 | `0000fff1-...` | Fan control (Read/Write, 20 bytes) |
| FFF2 | `0000fff2-...` | Temperatures + fan speed (Notify, 20 bytes) |
| FFF3 | `0000fff3-...` | Grill target temp + probe alarms (Read/Write, 20 bytes) |

**Temperature encoding:** Fahrenheit × 10 as `uint16` little-endian  
**CRC:** CRC16-Modbus over bytes 0–17, stored at bytes 18–19

### FFF2 — Temperatures & Fan (primary data source)

| Bytes | Content |
|-------|---------|
| [0–1] | Probe 0 (inside), F×10 |
| [2–3] | Probe 1, F×10 |
| [4–5] | Probe 2, F×10 |
| [6–7] | Probe 3, F×10 |
| [8]   | Fan actual speed % |

### FFF1 — Fan Control

| Byte | Content |
|------|---------|
| [0]  | Fan: `1` = on, `0` = off |
| [6]  | Fan speed setpoint (%) |

> **Note:** FFF1 reads fail inconsistently on some Home Assistant / BlueZ combinations (`_services_resolved` flag not set). Writes work reliably. The speed setpoint is therefore not implemented as a writable entity.

---

## Changelog

### v1.2.0 (2026-05-14)
- **New:** Multilingual support — English and German translations for all entity names and config flow
- **Fix:** `NumberDeviceClass.TEMPERATURE` set for target temp and probe alarm entities — HA now displays values in the user's configured unit (°C/°F)
- **Fix:** Missing entry for Probe 3 in `de.json` added
- Contribution by [@drjjr2](https://github.com/drjjr2)

### v1.1.1 (2026-05-06)
- **Fix:** Replaced `hass.async_create_task()` with `entry.async_create_background_task()` — HA was waiting for the endless BLE loop during bootstrap, delaying startup by ~8–10 minutes

### v1.1.0
- Probe alarm entities (Probe 1–3, writable via FFF3)
- GATT cache fix for more reliable reads
- All entities always available (show 0/None when disconnected)

### v1.0.0
- Initial release
- Temperature sensors, fan switch, target temperature

---

## License

MIT — see [LICENSE](LICENSE)
