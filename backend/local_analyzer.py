"""Local analyzer: pulls WAV files from the Pi audio server and runs inference locally.

Run this on your Mac (from backend/):
    source venv/bin/activate        # or however you activate locally
    cd backend/
    python local_analyzer.py

Set PI_HOST to the Pi's IP if different from the default.
"""

import logging
import sys
import tempfile
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Pi connection settings — change PI_HOST if needed
# ---------------------------------------------------------------------------
PI_HOST = "192.168.1.160"
PI_PORT = 7008
BASE_URL = f"http://{PI_HOST}:{PI_PORT}"
POLL_INTERVAL = 2  # seconds between polls

# ---------------------------------------------------------------------------
# Logging — DEBUG so we see all analyzer output
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [local-analyzer] %(levelname)s %(message)s",
)
# Keep third-party loggers quiet; only our code and analyzer log at DEBUG
for _name in ("analyzer", "database", "__main__"):
    logging.getLogger(_name).setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Bootstrap analyzer module (must run from backend/)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

import analyzer  # noqa: E402  (local backend/analyzer.py)


def check_pi_connection():
    """Verify we can reach the Pi audio server and print its status."""
    try:
        resp = requests.get(f"{BASE_URL}/status", timeout=5)
        resp.raise_for_status()
        status = resp.json()
        logger.info("Pi audio server reachable at %s", BASE_URL)
        logger.info("  Device:       %s", status.get("device"))
        logger.info("  Sample rate:  %s Hz", status.get("sample_rate"))
        logger.info("  Record dur:   %s s", status.get("record_duration"))
        logger.info("  Stream dir:   %s", status.get("stream_dir"))
        logger.info("  Queued files: %s", status.get("queued_files"))
        last = status.get("last_recording", {})
        if last.get("error"):
            logger.warning("  Last recording ERROR: %s", last["error"])
        elif last.get("file"):
            logger.info("  Last recording: %s at %s", last["file"], last["time"])
        return True
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach Pi at %s — is pi_audio_server.py running?", BASE_URL)
        return False
    except Exception as e:
        logger.error("Status check failed: %s", e)
        return False


def fetch_wav_list() -> list[str]:
    try:
        resp = requests.get(f"{BASE_URL}/wavs", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Failed to fetch WAV list: %s", e)
        return []


def download_wav(filename: str, dest: Path) -> bool:
    try:
        resp = requests.get(f"{BASE_URL}/wavs/{filename}", timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        size = dest.stat().st_size
        logger.info("Downloaded %s → %s (%.1f KB)", filename, dest, size / 1024)
        return True
    except Exception as e:
        logger.error("Failed to download %s: %s", filename, e)
        return False


def delete_wav_on_pi(filename: str):
    try:
        resp = requests.delete(f"{BASE_URL}/wavs/{filename}", timeout=5)
        resp.raise_for_status()
        logger.debug("Deleted %s on Pi", filename)
    except Exception as e:
        logger.warning("Could not delete %s on Pi: %s", filename, e)


def main():
    logger.info("=== BirdNET Local Analyzer ===")
    logger.info("Pi audio server: %s", BASE_URL)
    logger.info("Poll interval: %ds", POLL_INTERVAL)
    logger.info("")

    # Check Pi is reachable
    if not check_pi_connection():
        sys.exit(1)

    # Bootstrap the analyzer (loads config, model, labels, DB)
    logger.info("")
    logger.info("Loading model and config...")
    analyzer.load_config()
    analyzer.load_model()
    analyzer.load_labels()

    import database
    database.init_db(str(analyzer.data_dir))

    logger.info("Ready — waiting for WAV files from Pi")
    logger.info("")

    seen = set()  # filenames already processed this session

    try:
        while True:
            wav_list = fetch_wav_list()

            new_files = [f for f in wav_list if f not in seen]
            if not new_files:
                logger.debug("No new files (Pi has %d total queued)", len(wav_list))
                time.sleep(POLL_INTERVAL)
                continue

            logger.info("%d new file(s) available on Pi: %s", len(new_files), new_files)

            for filename in new_files:
                seen.add(filename)

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = Path(tmp.name)

                if not download_wav(filename, tmp_path):
                    tmp_path.unlink(missing_ok=True)
                    continue

                # Run inference locally using the full analyzer pipeline
                try:
                    analyzer.process_wav(tmp_path)
                except Exception as e:
                    logger.error("process_wav failed for %s: %s", filename, e, exc_info=True)
                finally:
                    tmp_path.unlink(missing_ok=True)

                # Tell Pi to delete it
                delete_wav_on_pi(filename)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Stopped by user")


if __name__ == "__main__":
    main()
