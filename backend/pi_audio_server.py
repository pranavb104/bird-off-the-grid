"""Pi audio server: records audio via arecord and serves WAV files over HTTP.

Run this on the Raspberry Pi:
    source ~/birdnet-venv/bin/activate
    cd /home/pi/backend
    python pi_audio_server.py

Endpoints:
    GET  /wavs           — list available WAV files
    GET  /wavs/{name}    — download a WAV file
    DELETE /wavs/{name}  — delete after processing
    GET  /status         — recorder health check
"""

import logging
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [pi-server] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.yml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

audio_cfg = config["audio"]
DEVICE = audio_cfg["device"]
SAMPLE_RATE = audio_cfg["sample_rate"]
DURATION = audio_cfg["record_duration"]

DATA_DIR = Path(__file__).parent / config["data_dir"]
STREAM_DIR = DATA_DIR / "StreamData"
STREAM_DIR.mkdir(parents=True, exist_ok=True)

SERVER_PORT = 7008  # separate from the main API on 7007

# ---------------------------------------------------------------------------
# Recorder thread
# ---------------------------------------------------------------------------
_shutdown = threading.Event()
_recorder_thread = None
_last_recording: dict = {"file": None, "time": None, "error": None}
_current_recording: str | None = None  # filename arecord is currently writing


def recorder_loop():
    """Background thread: continuously records 15-second WAV clips."""
    logger.info("Recorder thread started (device=%s, rate=%d, duration=%ds)",
                DEVICE, SAMPLE_RATE, DURATION)
    while not _shutdown.is_set():
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filepath = STREAM_DIR / f"{timestamp}.wav"

        cmd = [
            "arecord",
            "-D", DEVICE,
            "-f", "S16_LE",
            "-c", "1",
            "-r", str(SAMPLE_RATE),
            "-d", str(DURATION),
            "-t", "wav",
            str(filepath),
        ]

        logger.info("Recording → %s", filepath.name)
        global _current_recording
        _current_recording = filepath.name
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=DURATION + 10)
            if proc.returncode != 0:
                err = proc.stderr.decode(errors="replace").strip()
                logger.error("arecord failed (rc=%d): %s", proc.returncode, err)
                _last_recording["error"] = err
                _shutdown.wait(5)
                continue

            _current_recording = None
            size = filepath.stat().st_size if filepath.exists() else 0
            logger.info("Recorded %s (%.1f KB)", filepath.name, size / 1024)
            _last_recording["file"] = filepath.name
            _last_recording["time"] = datetime.now().isoformat()
            _last_recording["error"] = None

        except subprocess.TimeoutExpired:
            logger.warning("arecord timed out")
            _last_recording["error"] = "timeout"
            _shutdown.wait(2)
        except Exception as e:
            logger.error("Recording error: %s", e)
            _last_recording["error"] = str(e)
            _shutdown.wait(5)

    logger.info("Recorder thread stopped")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="BirdNET Pi Audio Server")


@app.get("/status")
def status():
    files = sorted(STREAM_DIR.glob("*.wav"))
    return {
        "device": DEVICE,
        "sample_rate": SAMPLE_RATE,
        "record_duration": DURATION,
        "stream_dir": str(STREAM_DIR),
        "queued_files": len(files),
        "last_recording": _last_recording,
    }


@app.get("/wavs")
def list_wavs():
    """Return a list of available WAV filenames, oldest first (excludes in-progress file)."""
    files = sorted(STREAM_DIR.glob("*.wav"))
    return [f.name for f in files if f.name != _current_recording]


@app.get("/wavs/{filename}")
def get_wav(filename: str):
    """Download a WAV file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = STREAM_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    logger.debug("Serving %s (%.1f KB)", filename, path.stat().st_size / 1024)
    return FileResponse(str(path), media_type="audio/wav", filename=filename)


@app.delete("/wavs/{filename}")
def delete_wav(filename: str):
    """Delete a WAV file after the client has finished processing it."""
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = STREAM_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    path.unlink()
    logger.info("Deleted %s (confirmed by client)", filename)
    return {"deleted": filename}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    global _recorder_thread

    _recorder_thread = threading.Thread(target=recorder_loop, daemon=True)
    _recorder_thread.start()

    def handle_signal(signum, frame):
        logger.info("Shutting down...")
        _shutdown.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Starting audio server on port %d", SERVER_PORT)
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="warning")


if __name__ == "__main__":
    main()
