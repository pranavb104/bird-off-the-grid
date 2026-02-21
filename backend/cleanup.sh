#!/usr/bin/env bash
# Removes all BirdNET services, the venv, and the project directory.
# Run this on the Pi before reinstalling from scratch.
set -euo pipefail

VENV_DIR="$HOME/birdnet-venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== BirdNET Cleanup ==="

# --- Stop and disable systemd services ---
for svc in birdnet-recorder birdnet-analyzer birdnet-api pulseaudio; do
    if systemctl list-unit-files "${svc}.service" &>/dev/null; then
        echo "Stopping $svc..."
        systemctl stop "$svc" 2>/dev/null || true
        systemctl disable "$svc" 2>/dev/null || true
    fi
done

# --- Remove systemd service files ---
for f in /etc/systemd/system/birdnet-recorder.service \
         /etc/systemd/system/birdnet-analyzer.service \
         /etc/systemd/system/birdnet-api.service \
         /etc/systemd/system/pulseaudio.service; do
    if [ -f "$f" ]; then
        echo "Removing $f"
        rm -f "$f"
    fi
done

systemctl daemon-reload

# --- Remove Python venv ---
if [ -d "$VENV_DIR" ]; then
    echo "Removing venv at $VENV_DIR"
    rm -rf "$VENV_DIR"
fi

# --- Remove project directory ---
echo "Removing project directory: $SCRIPT_DIR"
# Step out before deleting
cd /tmp
rm -rf "$SCRIPT_DIR"

echo ""
echo "=== Cleanup complete ==="
echo "The Pi is ready for a fresh install."
echo "Copy the project files over and run: sudo bash backend/install.sh"
