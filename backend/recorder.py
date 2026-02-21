"""Audio capture: records continuous 15s WAV files via arecord."""

import signal
import subprocess
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [recorder] %(message)s")
logger = logging.getLogger(__name__)

shutdown = False


def handle_signal(signum, frame):
    global shutdown
    logger.info("Shutdown signal received")
    shutdown = True


def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    config_path = Path(__file__).parent / "config.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    audio_cfg = config["audio"]
    device = audio_cfg["device"]
    sample_rate = audio_cfg["sample_rate"]
    duration = audio_cfg["record_duration"]

    data_dir = Path(__file__).parent / config["data_dir"]
    stream_dir = data_dir / "StreamData"
    stream_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Recording %ds clips at %dHz from device '%s'", duration, sample_rate, device)
    logger.info("Saving to %s", stream_dir)

    while not shutdown:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        filepath = stream_dir / f"{timestamp}.wav"

        cmd = [
            "arecord",
            "-D", device,
            "-f", "S16_LE",
            "-c", "1",
            "-r", str(sample_rate),
            "-d", str(duration),
            "-t", "wav",
            str(filepath),
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=duration + 10)
            if proc.returncode != 0:
                stderr = proc.stderr.decode(errors="replace").strip()
                logger.error("arecord failed: %s", stderr)
                time.sleep(5)
        except subprocess.TimeoutExpired:
            logger.warning("arecord timed out, retrying")
        except Exception as e:
            logger.error("Recording error: %s", e)
            time.sleep(5)

    logger.info("Recorder stopped")


if __name__ == "__main__":
    main()
