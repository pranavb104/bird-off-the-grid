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

# --- Create systemd services for BirdNET ---
echo "Creating systemd services..."

sudo tee /etc/systemd/system/birdnet-recorder.service > /dev/null << EOF
[Unit]
Description=BirdNET Audio Recorder
After=sound.target

[Service]
Type=simple
User=$USER
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/recorder.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/birdnet-analyzer.service > /dev/null << EOF
[Unit]
Description=BirdNET Audio Analyzer
After=birdnet-recorder.service

[Service]
Type=simple
User=$USER
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/analyzer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/birdnet-api.service > /dev/null << EOF
[Unit]
Description=BirdNET API Server
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable birdnet-recorder birdnet-analyzer birdnet-api

# --- Create data directories ---
mkdir -p "$SCRIPT_DIR/data/StreamData"
mkdir -p "$SCRIPT_DIR/data/detections"

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit $SCRIPT_DIR/config.yml with your latitude/longitude"
echo "  2. Verify mic with: arecord -l"
echo "  3. Start services: sudo systemctl start birdnet-recorder birdnet-analyzer birdnet-api"
echo "  4. Or run manually: $SCRIPT_DIR/run.sh"
echo "  5. Check API: curl http://localhost:7007/api/health"
echo "  NOTE: Log out and back in for audio group membership to take effect."
