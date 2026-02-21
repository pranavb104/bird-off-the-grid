#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.birdnet.pids"

echo "=== Stopping BirdNET Services ==="

# Stop systemd services (if running on a systemd system)
if command -v systemctl &>/dev/null; then
    echo "Stopping systemd services..."
    sudo systemctl stop birdnet-api birdnet-analyzer birdnet-recorder 2>/dev/null && \
        echo "  Stopped birdnet-api, birdnet-analyzer, birdnet-recorder" || \
        echo "  No systemd services were running"

    sudo systemctl stop pulseaudio 2>/dev/null && \
        echo "  Stopped pulseaudio" || \
        echo "  PulseAudio service was not running"
fi

# Stop any manually started processes (from run.sh)
if [ -f "$PID_FILE" ]; then
    echo "Stopping manually started processes..."
    while read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "  Stopped PID $pid"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

echo ""
echo "All BirdNET services stopped."
