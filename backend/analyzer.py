"""TF-Lite bird analysis: watches StreamData/ and runs inference on new WAV files."""

import signal
import subprocess
import sys
import time
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import librosa
import numpy as np
import yaml

try:
    from ai_edge_litert.interpreter import Interpreter
    _INTERP_BACKEND = "ai_edge_litert"
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
        _INTERP_BACKEND = "tflite_runtime"
    except ImportError:
        from tensorflow.lite.python.interpreter import Interpreter
        _INTERP_BACKEND = "tensorflow.lite"

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import database
import spectrogram as spec_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [analyzer] %(levelname)s %(message)s",
)
logging.getLogger("analyzer").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Globals loaded at startup
config = None
interpreter = None
input_details = None
output_details = None
labels = []
data_dir = None


def load_config():
    global config, data_dir
    config_path = Path(__file__).parent / "config.yml"
    logger.debug("Loading config from %s", config_path)
    with open(config_path) as f:
        config = yaml.safe_load(f)
    data_dir = Path(__file__).parent / config["data_dir"]
    logger.info("Config loaded. data_dir=%s, confidence_threshold=%s",
                data_dir, config["confidence_threshold"])


def load_model():
    global interpreter, input_details, output_details
    model_path = Path(__file__).parent / config["model"]["path"]
    logger.info("TFLite backend: %s", _INTERP_BACKEND)
    logger.info("Loading model from %s", model_path)

    if not model_path.exists():
        logger.error("Model file NOT FOUND: %s", model_path)
        sys.exit(1)

    logger.debug("Model file size: %.1f MB", model_path.stat().st_size / 1e6)

    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    logger.info("Model loaded. Input shape=%s dtype=%s | Output shape=%s dtype=%s",
                input_details[0]["shape"], input_details[0]["dtype"],
                output_details[0]["shape"], output_details[0]["dtype"])


def load_labels():
    global labels
    labels_path = Path(__file__).parent / config["model"]["labels"]
    logger.debug("Loading labels from %s", labels_path)

    if not labels_path.exists():
        logger.error("Labels file NOT FOUND: %s", labels_path)
        sys.exit(1)

    with open(labels_path) as f:
        labels = [line.strip() for line in f if line.strip()]
    logger.info("Loaded %d labels. First: %r  Last: %r", len(labels), labels[0], labels[-1])


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Apply sigmoid to convert raw logits to probabilities (0–1)."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))


@dataclass
class PendingDetection:
    """A detection buffered until the species reaches the confirmation threshold."""
    audio_chunk: np.ndarray
    sr: int
    detection_time: datetime
    common_name: str
    scientific_name: str
    confidence: float
    mono_ts: float  # time.monotonic() when recorded


class DetectionTracker:
    """Rolling time-window species counter to filter false positives.

    A species must be detected min_count times within window_seconds before
    any of its detections are saved. Once confirmed, subsequent detections
    for that species are saved immediately until the window expires.
    """

    def __init__(self, min_count: int, window_seconds: float):
        self.min_count = min_count
        self.window_seconds = window_seconds
        self._pending: dict[str, list[PendingDetection]] = defaultdict(list)
        self._confirmed: dict[str, float] = {}  # species -> mono_ts of confirmation

    def track(self, audio_chunk: np.ndarray, sr: int, detection_time: datetime,
              common_name: str, scientific_name: str,
              confidence: float) -> list[PendingDetection]:
        """Buffer a detection and return any that should be saved now."""
        det = PendingDetection(
            audio_chunk=audio_chunk, sr=sr, detection_time=detection_time,
            common_name=common_name, scientific_name=scientific_name,
            confidence=confidence, mono_ts=time.monotonic(),
        )

        # Pass-through when filtering is disabled
        if self.min_count <= 1:
            return [det]

        self._prune()

        # Already confirmed — save immediately
        if scientific_name in self._confirmed:
            logger.debug("  Species %s already confirmed — saving immediately", scientific_name)
            return [det]

        # Buffer and check threshold
        self._pending[scientific_name].append(det)
        count = len(self._pending[scientific_name])
        logger.debug("  Buffered detection #%d for %s (need %d)",
                     count, scientific_name, self.min_count)

        if count >= self.min_count:
            # Confirm species and flush all pending detections
            self._confirmed[scientific_name] = time.monotonic()
            flushed = self._pending.pop(scientific_name)
            logger.info("  Species %s confirmed (%d detections in window) — "
                        "flushing %d pending", scientific_name, count, len(flushed))
            return flushed

        return []

    def _prune(self):
        """Remove stale pending detections and expired confirmations."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune pending
        stale_keys = []
        for species, dets in self._pending.items():
            before = len(dets)
            self._pending[species] = [d for d in dets if d.mono_ts > cutoff]
            pruned = before - len(self._pending[species])
            if pruned:
                logger.debug("  Pruned %d stale pending detection(s) for %s", pruned, species)
            if not self._pending[species]:
                stale_keys.append(species)
        for key in stale_keys:
            del self._pending[key]

        # Expire confirmations
        expired = [sp for sp, ts in self._confirmed.items() if ts <= cutoff]
        for sp in expired:
            logger.debug("  Confirmation expired for %s", sp)
            del self._confirmed[sp]


detection_tracker: DetectionTracker | None = None


def analyze_chunk(audio_chunk: np.ndarray, chunk_idx: int) -> list[tuple[str, str, float]]:
    """Run inference on a 3s audio chunk.

    Returns list of (common_name, scientific_name, confidence) tuples
    where confidence is a sigmoid probability (0–1).
    """
    expected_shape = input_details[0]["shape"]
    expected_samples = expected_shape[-1] if len(expected_shape) > 1 else expected_shape[0]

    logger.debug("  Chunk %d: raw audio samples=%d, min=%.4f, max=%.4f, rms=%.4f",
                 chunk_idx, len(audio_chunk),
                 float(audio_chunk.min()), float(audio_chunk.max()),
                 float(np.sqrt(np.mean(audio_chunk ** 2))))

    # Pad or trim to expected length
    if len(audio_chunk) < expected_samples:
        logger.debug("  Chunk %d: padding %d → %d samples",
                     chunk_idx, len(audio_chunk), expected_samples)
        audio_chunk = np.pad(audio_chunk, (0, expected_samples - len(audio_chunk)))
    elif len(audio_chunk) > expected_samples:
        logger.debug("  Chunk %d: trimming %d → %d samples",
                     chunk_idx, len(audio_chunk), expected_samples)
        audio_chunk = audio_chunk[:expected_samples]

    input_data = audio_chunk.astype(np.float32).reshape(expected_shape)

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]["index"])
    raw_logits = output_data.flatten()

    logger.debug("  Chunk %d: raw logits  min=%.4f, max=%.4f, mean=%.4f",
                 chunk_idx, float(raw_logits.min()), float(raw_logits.max()),
                 float(raw_logits.mean()))

    predictions = _sigmoid(raw_logits)

    logger.debug("  Chunk %d: sigmoid probs min=%.4f, max=%.4f, mean=%.4f",
                 chunk_idx, float(predictions.min()), float(predictions.max()),
                 float(predictions.mean()))

    # Log top-5 predictions regardless of threshold
    top5_idx = np.argsort(predictions)[-5:][::-1]
    logger.debug("  Chunk %d: top-5 predictions (threshold=%.2f):",
                 chunk_idx, config["confidence_threshold"])
    for rank, idx in enumerate(top5_idx):
        label = labels[idx] if idx < len(labels) else f"<unknown idx {idx}>"
        logger.debug("    #%d  conf=%.4f  label=%r", rank + 1, float(predictions[idx]), label)

    threshold = config["confidence_threshold"]
    results = []
    for idx, conf in enumerate(predictions):
        if conf >= threshold and idx < len(labels):
            label = labels[idx]
            if "_" in label:
                scientific_name, common_name = label.split("_", 1)
            else:
                scientific_name = label
                common_name = label
            results.append((common_name, scientific_name, float(conf)))

    if results:
        logger.info("  Chunk %d: %d detection(s) above threshold %.2f",
                    chunk_idx, len(results), threshold)
        for common_name, scientific_name, conf in results:
            logger.info("    DETECTION: %s (%s)  conf=%.4f", common_name, scientific_name, conf)
    else:
        logger.debug("  Chunk %d: no detections above threshold %.2f",
                     chunk_idx, threshold)

    return results


def _wait_for_file_ready(path: Path, timeout: float = 15.0) -> bool:
    """Wait until the file size stops growing (i.e. arecord has finished writing)."""
    deadline = time.monotonic() + timeout
    prev_size = -1
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            logger.warning("File disappeared while waiting: %s", path.name)
            return False
        if size == prev_size and size > 0:
            return True
        prev_size = size
        time.sleep(0.5)
    logger.warning("Timed out waiting for %s to finish writing (size=%d)", path.name, prev_size)
    return True  # proceed anyway


def process_wav(wav_path: Path):
    """Process a single WAV file: split into chunks, analyze, save detections."""
    logger.info(">>> Processing %s", wav_path.name)

    try:
        file_size = wav_path.stat().st_size
        logger.debug("  File size: %d bytes (%.1f KB)", file_size, file_size / 1024)
    except FileNotFoundError:
        logger.error("File not found (may have been deleted): %s", wav_path)
        return

    try:
        audio, sr = librosa.load(str(wav_path), sr=config["audio"]["sample_rate"],
                                 mono=True, res_type="kaiser_fast")
    except Exception as e:
        logger.error("Failed to load %s: %s", wav_path.name, e)
        return

    duration_s = len(audio) / sr
    logger.info("  Audio loaded: duration=%.2fs, sr=%dHz, samples=%d, min=%.4f, max=%.4f, rms=%.4f",
                duration_s, sr, len(audio),
                float(audio.min()), float(audio.max()),
                float(np.sqrt(np.mean(audio ** 2))))

    if float(np.sqrt(np.mean(audio ** 2))) < 1e-6:
        logger.warning("  Audio appears to be silent (near-zero RMS) — skipping inference")

    chunk_duration = config["audio"]["chunk_duration"]
    chunk_samples = sr * chunk_duration
    min_samples = int(sr * 1.5)

    # Parse timestamp from filename: YYYY-MM-DD-HH-MM-SS.wav
    stem = wav_path.stem
    try:
        file_dt = datetime.strptime(stem, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        logger.warning("  Could not parse timestamp from filename %r, using now()", stem)
        file_dt = datetime.now()

    num_chunks = len(audio) // chunk_samples
    remainder = len(audio) % chunk_samples
    logger.debug("  chunk_samples=%d, num_full_chunks=%d, remainder=%d samples",
                 chunk_samples, num_chunks, remainder)

    chunks = []
    for i in range(num_chunks):
        start = i * chunk_samples
        chunks.append((i, audio[start:start + chunk_samples]))

    if remainder >= min_samples:
        logger.debug("  Last partial chunk (%d samples) >= min (%d) — padding and including",
                     remainder, min_samples)
        last_chunk = np.pad(audio[num_chunks * chunk_samples:],
                            (0, chunk_samples - remainder))
        chunks.append((num_chunks, last_chunk))
    elif remainder > 0:
        logger.debug("  Last partial chunk (%d samples) < min (%d) — discarding",
                     remainder, min_samples)

    logger.info("  Running inference on %d chunk(s)", len(chunks))

    total_detections = 0
    for chunk_idx, chunk_audio in chunks:
        chunk_offset = chunk_idx * chunk_duration
        chunk_time = file_dt.replace(
            second=min(59, file_dt.second + chunk_offset)
        )

        results = analyze_chunk(chunk_audio, chunk_idx)
        total_detections += len(results)

        for common_name, scientific_name, confidence in results:
            to_save = detection_tracker.track(
                chunk_audio, sr, chunk_time,
                common_name, scientific_name, confidence,
            )
            for det in to_save:
                save_detection(
                    det.audio_chunk, det.sr, det.detection_time,
                    det.common_name, det.scientific_name, det.confidence,
                )

    logger.info("  Total detections in %s: %d", wav_path.name, total_detections)

    # Delete the original WAV after processing
    try:
        wav_path.unlink()
        logger.debug("  Deleted %s", wav_path.name)
    except OSError as e:
        logger.warning("  Could not delete %s: %s", wav_path.name, e)


def save_detection(audio_chunk: np.ndarray, sr: int, detection_time: datetime,
                   common_name: str, scientific_name: str, confidence: float):
    """Save a detection: spectrogram PNG, MP3 clip, and database record."""
    date_str = detection_time.strftime("%Y-%m-%d")
    time_str = detection_time.strftime("%H-%M-%S")
    safe_species = common_name.replace(" ", "_")

    det_dir = data_dir / "detections" / date_str / safe_species
    det_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{time_str}_{confidence:.2f}"
    png_path = det_dir / f"{base_name}.png"
    mp3_path = det_dir / f"{base_name}.mp3"

    logger.debug("  Saving detection to %s", det_dir)

    # Generate spectrogram
    try:
        spec_module.generate_spectrogram(audio_chunk, sr, str(png_path),
                                         common_name, confidence)
        logger.debug("  Spectrogram saved: %s", png_path.name)
    except Exception as e:
        logger.error("  Spectrogram generation failed: %s", e)

    # Convert audio chunk to MP3 via ffmpeg (write temp WAV first)
    tmp_wav = det_dir / f"{base_name}_tmp.wav"
    try:
        import soundfile as sf
        sf.write(str(tmp_wav), audio_chunk, sr)
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp_wav), "-q:a", "6", str(mp3_path)],
            capture_output=True, timeout=30
        )
        tmp_wav.unlink(missing_ok=True)
        if result.returncode != 0:
            logger.error("  ffmpeg failed (rc=%d): %s",
                         result.returncode, result.stderr.decode(errors="replace").strip())
        else:
            logger.debug("  MP3 saved: %s", mp3_path.name)
    except Exception as e:
        logger.error("  MP3 conversion failed: %s", e)
        tmp_wav.unlink(missing_ok=True)

    # Relative paths for database storage
    rel_png = str(png_path.relative_to(data_dir))
    rel_mp3 = str(mp3_path.relative_to(data_dir))

    try:
        database.insert_detection(
            str(data_dir), date_str, detection_time.strftime("%H:%M:%S"),
            common_name, scientific_name, confidence, rel_png, rel_mp3
        )
        logger.debug("  Detection written to DB")
    except Exception as e:
        logger.error("  DB insert failed: %s", e)


class WavHandler(FileSystemEventHandler):
    """Watches for new WAV files in StreamData/."""

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".wav":
            logger.debug("Ignoring non-WAV file event: %s", path.name)
            return

        logger.debug("Watchdog on_created: %s", path.name)

        # Wait for arecord to finish writing the file
        if not _wait_for_file_ready(path):
            logger.error("File never became ready: %s", path.name)
            return

        try:
            process_wav(path)
        except Exception as e:
            logger.error("Unhandled error processing %s: %s", path.name, e, exc_info=True)


def main():
    global detection_tracker
    load_config()
    load_model()
    load_labels()

    detection_tracker = DetectionTracker(
        min_count=config.get("min_detection_count", 2),
        window_seconds=config.get("detection_window_seconds", 300),
    )
    logger.info("Detection tracker: min_count=%d, window=%ds",
                detection_tracker.min_count, detection_tracker.window_seconds)

    logger.info("Initialising database at %s", data_dir)
    database.init_db(str(data_dir))

    stream_dir = data_dir / "StreamData"
    stream_dir.mkdir(parents=True, exist_ok=True)
    logger.info("StreamData dir: %s", stream_dir)

    # Process any existing WAV files first
    existing = sorted(stream_dir.glob("*.wav"))
    if existing:
        logger.info("Found %d existing WAV file(s) — processing now", len(existing))
        for wav in existing:
            try:
                process_wav(wav)
            except Exception as e:
                logger.error("Error processing %s: %s", wav.name, e, exc_info=True)
    else:
        logger.info("No existing WAV files in StreamData — waiting for recorder")

    # Start watching for new files
    observer = Observer()
    observer.schedule(WavHandler(), str(stream_dir), recursive=False)
    observer.start()
    logger.info("Watchdog started — watching %s", stream_dir)

    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        logger.info("Signal %d received — shutting down", signum)
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not shutdown:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
        logger.info("Analyzer stopped")


if __name__ == "__main__":
    main()
