# Inkbird ISC-027BW BLE — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Vibe coded** — Diese Integration wurde vollständig mit Hilfe von [Claude Code](https://claude.ai/code) (Anthropic) entwickelt, inklusive BLE-Protokoll-Analyse per iPhone-Sniffer.

Custom Integration für den **Inkbird ISC-027BW** Bluetooth-Grillthermometer mit Lüftersteuerung.

---

## Features

- 🌡️ **4 Temperatursonden** — Echtzeit-Messwerte via BLE Notify (FFF2)
- 💨 **Lüfter-Ist-Drehzahl** — aktueller Gebläsewert in %
- 🎯 **Grill-Zieltemperatur** — Lesen und Setzen via FFF3
- 🔄 **Persistente BLE-Verbindung** mit automatischem Reconnect
- 📡 **Kein Cloud-Zwang** — rein lokal über Bluetooth

---

## Unterstützte Geräte

| Gerät | Getestet |
|-------|----------|
| Inkbird ISC-027BW | ✅ |

---

## Installation

### Manuell

1. Ordner `custom_components/inkbird_ble` in dein HA-Konfigurationsverzeichnis kopieren
2. Home Assistant neu starten
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Inkbird BLE**
4. Bluetooth-Adresse des Geräts eingeben (z. B. `49:24:12:07:08:A6`)

### Voraussetzungen

- Home Assistant mit aktiviertem Bluetooth-Add-on oder lokalem Bluetooth-Adapter
- Inkbird ISC-027BW in Reichweite

---

## Entitäten

| Entität | Typ | Beschreibung |
|---------|-----|--------------|
| Innentemperatur / Sonde 0 | Sensor | Interne Sonde (°C) |
| Sonde 1–3 | Sensor | Externe Sonden (°C) |
| Lüfter Ist-Drehzahl | Sensor | Aktueller Gebläsewert (%) |
| Grill-Zieltemperatur | Number | Zieltemperatur setzen (20–300°C) |

---

## BLE-Protokoll

Das Protokoll wurde per iPhone-BLE-Sniffer (`idevicebtlogger`) reverse-engineered:

| Charakteristik | UUID | Funktion |
|----------------|------|----------|
| FFF2 | `0000fff2-...` | Temperaturen + Lüfterdrehzahl (Notify, 20 Bytes) |
| FFF3 | `0000fff3-...` | Grill-Zieltemperatur (Read/Write, 20 Bytes) |

**Temperaturkodierung:** Fahrenheit × 10 als `uint16` little-endian  
**CRC:** CRC16-Modbus über Bytes 0–17, gespeichert an Bytes 18–19

---

## Lizenz

MIT — siehe [LICENSE](LICENSE)
