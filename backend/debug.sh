#!/usr/bin/env bash
set -euo pipefail

# debug.sh — runs recorder, analyzer, and API locally (no Docker, no frontend)
# Useful for debugging the frontend on a separate device pointed at this Pi's API.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/birdnet-venv"
PID_FILE="$SCRIPT_DIR/.birdnet-debug.pids"
LOG_DIR="$SCRIPT_DIR/logs"

stop_services() {
    if [ -f "$PID_FILE" ]; then
        echo "Stopping debug services..."
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                echo "  Stopped PID $pid"
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
        echo "All debug services stopped."
    else
        echo "No PID file found. Services may not be running."
    fi
}

start_services() {
    if [ -f "$PID_FILE" ]; then
        echo "Debug services appear to be running. Stop them first: $0 stop"
        exit 1
    fi

    source "$VENV_DIR/bin/activate"

    mkdir -p "$SCRIPT_DIR/data/StreamData"
    mkdir -p "$SCRIPT_DIR/data/detections"
    mkdir -p "$LOG_DIR"

    echo "Starting BirdNET backend in debug mode..."
    echo "  Logs → $LOG_DIR/"
    echo ""

    python "$SCRIPT_DIR/recorder.py" > "$LOG_DIR/recorder.log" 2>&1 &
    RECORDER_PID=$!
    echo "  Recorder  started (PID $RECORDER_PID) → logs/recorder.log"

    python "$SCRIPT_DIR/analyzer.py" > "$LOG_DIR/analyzer.log" 2>&1 &
    ANALYZER_PID=$!
    echo "  Analyzer  started (PID $ANALYZER_PID) → logs/analyzer.log"

    python "$SCRIPT_DIR/api.py" > "$LOG_DIR/api.log" 2>&1 &
    API_PID=$!
    echo "  API       started (PID $API_PID)       → logs/api.log"

    printf '%s\n' "$RECORDER_PID" "$ANALYZER_PID" "$API_PID" > "$PID_FILE"

    echo ""
    echo "API listening at http://$(hostname -I | awk '{print $1}'):7007"
    echo "Point your frontend dev server at that address."
    echo ""
    echo "Tail all logs:  tail -f $LOG_DIR/*.log"
    echo "Stop services:  $0 stop"
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
