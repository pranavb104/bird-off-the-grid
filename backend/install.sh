#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/birdnet-venv"
MODEL_DIR="$SCRIPT_DIR/model"

echo "=== BirdNET Backend Installer ==="

# --- System packages ---
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    ffmpeg libsndfile1 libasound2-dev \
    alsa-utils

# Ensure the running user is in the audio group for ALSA access
sudo usermod -aG audio "$USER"

# --- Python venv ---
echo "Creating Python virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# --- Verify BirdNET model ---
echo "Checking BirdNET model files..."
if [ ! -f "$MODEL_DIR/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite" ] || \
   [ ! -f "$MODEL_DIR/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt" ]; then
    echo "ERROR: Model files not found in $MODEL_DIR"
    echo "Expected:"
    echo "  $MODEL_DIR/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite"
    echo "  $MODEL_DIR/BirdNET_GLOBAL_6K_V2.4_Model_FP16_Labels.txt"
    exit 1
else
    echo "Model and labels found."
fi

# --- Create data directories ---
mkdir -p "$SCRIPT_DIR/data/StreamData"
mkdir -p "$SCRIPT_DIR/data/detections"

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit $SCRIPT_DIR/config.yml with your latitude/longitude"
echo "  2. Verify mic with: arecord -l"
echo "  3. Debug mode (no Docker): $SCRIPT_DIR/debug.sh start"
echo "  4. Production (Docker):    docker compose up -d  (from repo root)"
echo "  5. Check API: curl http://localhost:7007/api/health"
echo "  NOTE: Log out and back in for audio group membership to take effect."
