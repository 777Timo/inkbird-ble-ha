# Inkbird ISC-027BW BLE — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Vibe coded** — Diese Integration wurde vollständig mit Hilfe von [Claude Code](https://claude.ai/code) (Anthropic) entwickelt.

Custom Integration für den **Inkbird ISC-027BW** Bluetooth-Grillthermometer mit Lüftersteuerung.

---

## Features

- 🌡️ **4 Temperatursonden** — Echtzeit-Messwerte via BLE Notify (FFF2)
- 💨 **Lüfter-Ist-Drehzahl** — aktueller Gebläsewert in %
- 🎯 **Grill-Zieltemperatur** — Lesen und Setzen via FFF3
- 🔌 **Lüfter An/Aus** — Schalter zur direkten Gebläsesteuerung via FFF1
- 🔄 **Persistente BLE-Verbindung** mit automatischem Reconnect
- 📊 **Lovelace-Dashboard** — fertig konfiguriert mit Gauge-Karten und Verlaufsgraphen
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

### Dashboard (optional)

1. Datei `dashboard/inkbird.yaml` nach `/config/dashboards/inkbird.yaml` kopieren
2. In `configuration.yaml` eintragen:
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
3. Home Assistant neu starten → Dashboard erscheint in der Seitenleiste

### Voraussetzungen

- Home Assistant mit aktiviertem Bluetooth-Add-on oder lokalem Bluetooth-Adapter
- Inkbird ISC-027BW in Reichweite

---

## Entitäten

| Entität | Typ | Beschreibung |
|---------|-----|--------------|
| Innentemperatur / Sonde 0 | Sensor | Grill Sonde (°C) |
| Sonde 1–3 | Sensor | Externe Sonden (°C) |
| Lüfter Ist-Drehzahl | Sensor | Aktueller Gebläsewert (%) |
| Zieltemperatur Gerät | Sensor | Vom Gerät gelesene Zieltemperatur (°C) |
| Grill-Zieltemperatur | Number | Zieltemperatur setzen (20–300°C) |
| Lüfter | Switch | Gebläse ein/aus |

---

## BLE-Protokoll

Das Protokoll wurde reverse-engineered:

| Charakteristik | UUID | Funktion |
|----------------|------|----------|
| FFF1 | `0000fff1-...` | Lüftersteuerung (Read/Write, 20 Bytes) |
| FFF2 | `0000fff2-...` | Temperaturen + Lüfterdrehzahl (Notify, 20 Bytes) |
| FFF3 | `0000fff3-...` | Grill-Zieltemperatur (Read/Write, 20 Bytes) |

**Temperaturkodierung:** Fahrenheit × 10 als `uint16` little-endian  
**CRC:** CRC16-Modbus über Bytes 0–17, gespeichert an Bytes 18–19

### FFF2 — Temperaturen & Lüfter (primäre Datenquelle)

| Bytes | Inhalt |
|-------|--------|
| [0–1] | Sonde 0 (Innen), F×10 |
| [2–3] | Sonde 1, F×10 |
| [4–5] | Sonde 2, F×10 |
| [6–7] | Sonde 3, F×10 |
| [8]   | Lüfter Ist-Drehzahl % |

### FFF1 — Lüftersteuerung

| Byte | Inhalt |
|------|--------|
| [0]  | Lüfter: `1` = an, `0` = aus |
| [6]  | Lüfterdrehzahl-Sollwert (%) |

> **Hinweis:** FFF1-Reads schlagen auf einigen Home Assistant / BlueZ-Kombinationen inkonsistent fehl (`_services_resolved`-Flag nicht gesetzt). Writes funktionieren zuverlässig. Die Solldrehzahl-Eingabe ist daher nicht als Entität implementiert.

---

## Lizenz

MIT — siehe [LICENSE](LICENSE)
