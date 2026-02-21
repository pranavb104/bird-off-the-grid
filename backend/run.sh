#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/birdnet-venv"
PID_FILE="$SCRIPT_DIR/.birdnet.pids"

stop_services() {
    if [ -f "$PID_FILE" ]; then
        echo "Stopping BirdNET services..."
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo "  Stopped PID $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        echo "All services stopped."
    else
        echo "No PID file found. Services may not be running."
    fi
}

start_services() {
    if [ -f "$PID_FILE" ]; then
        echo "Services appear to be running. Stop them first: $0 stop"
        exit 1
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"

    # Ensure data dirs exist
    mkdir -p "$SCRIPT_DIR/data/StreamData"
    mkdir -p "$SCRIPT_DIR/data/detections"

    echo "Starting BirdNET services..."

    # Start recorder
    python "$SCRIPT_DIR/recorder.py" &
    RECORDER_PID=$!
    echo "  Recorder started (PID $RECORDER_PID)"

    # Start analyzer
    python "$SCRIPT_DIR/analyzer.py" &
    ANALYZER_PID=$!
    echo "  Analyzer started (PID $ANALYZER_PID)"

    # Start API
    python "$SCRIPT_DIR/api.py" &
    API_PID=$!
    echo "  API started (PID $API_PID)"

    # Save PIDs
    echo "$RECORDER_PID" > "$PID_FILE"
    echo "$ANALYZER_PID" >> "$PID_FILE"
    echo "$API_PID" >> "$PID_FILE"

    echo ""
    echo "All services running. API at http://localhost:7007"
    echo "Stop with: $0 stop"
}

case "${1:-start}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac
