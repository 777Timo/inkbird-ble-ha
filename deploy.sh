#!/bin/zsh
# deploy.sh — Inkbird BLE Integration auf HA deployen + neu starten
set -e

HA_IP="192.168.0.35"
HA_PASS="hardcore"
HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI0YTYyMDI4ZjIyZmQ0YTQzYWUyNmJkMDQwM2Q3NGM3ZSIsImlhdCI6MTc3Mjk2ODk3NSwiZXhwIjoyMDg4MzI4OTc1fQ.fFx5v3LVMQUVyWlCeQ1zyyQLy3MTNMNH78i2bfnNdKo"
DEST="/config/custom_components/inkbird_ble"
SRC="$(dirname "$0")/custom_components/inkbird_ble"

echo "→ Kopiere Dateien..."
sshpass -p "$HA_PASS" scp "$SRC"/*.py "$SRC"/manifest.json root@$HA_IP:$DEST/

echo "→ Lösche __pycache__..."
sshpass -p "$HA_PASS" ssh -o StrictHostKeyChecking=no root@$HA_IP \
  "rm -rf $DEST/__pycache__"

echo "→ Starte HA neu (non-blocking)..."
curl -s -o /dev/null \
  -X POST "http://$HA_IP:8123/api/services/homeassistant/restart" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  --max-time 5 || true

echo "✓ Deploy fertig — HA startet neu (~30s)"
