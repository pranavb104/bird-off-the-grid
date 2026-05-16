"""TF-Lite bird analysis: watches StreamData/ and runs inference on new WAV files."""

import signal
import sys
import time
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml
from scipy.io import wavfile

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
excluded_species: set[str] = set()


def load_config():
    global config, data_dir, excluded_species
    config_path = Path(__file__).parent / "config.yml"
    logger.debug("Loading config from %s", config_path)
    with open(config_path) as f:
        config = yaml.safe_load(f)
    data_dir = Path(__file__).parent / config["data_dir"]

    raw = config.get("exclusions") or []
    excluded_species = {str(name).strip().lower() for name in raw if str(name).strip()}
    if excluded_species:
        logger.info("Loaded %d species exclusion(s)", len(excluded_species))

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


def _sigmoid(x: np.ndarray, sensitivity: float = 1.0) -> np.ndarray:
    """Sensitivity-scaled sigmoid (BirdNET-Analyzer flat_sigmoid).

    sensitivity=1.0 is the standard sigmoid. >1 sharpens (fewer detections),
    <1 softens (more detections). Logits are clipped to keep exp() bounded.
    """
    return 1.0 / (1.0 + np.exp(-sensitivity * np.clip(x, -15.0, 15.0)))


max_per_species: int = 0
_species_counts: dict[str, int] = {}
_capped_species: set[str] = set()


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

    predictions = _sigmoid(raw_logits, config.get("sensitivity", 1.0))

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
            if (common_name.lower() in excluded_species
                    or scientific_name.lower() in excluded_species):
                logger.debug("  Chunk %d: excluded %s (%s) conf=%.4f",
                             chunk_idx, common_name, scientific_name, float(conf))
                continue
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
        sr, audio = wavfile.read(str(wav_path))
    except Exception as e:
        logger.error("Failed to load %s: %s", wav_path.name, e)
        return

    expected_sr = config["audio"]["sample_rate"]
    if sr != expected_sr:
        logger.error("Sample rate mismatch in %s: got %d Hz, expected %d Hz — skipping",
                     wav_path.name, sr, expected_sr)
        return

    if audio.ndim == 2:
        audio = audio.mean(axis=1)

    audio = audio.astype(np.float32) / 32768.0

    duration_s = len(audio) / sr
    logger.info("  Audio loaded: duration=%.2fs, sr=%dHz, samples=%d, min=%.4f, max=%.4f, rms=%.4f",
                duration_s, sr, len(audio),
                float(audio.min()), float(audio.max()),
                float(np.sqrt(np.mean(audio ** 2))))

    if float(np.sqrt(np.mean(audio ** 2))) < 1e-6:
        logger.warning("  Audio appears to be silent (near-zero RMS) — skipping inference")

    chunk_duration = config["audio"]["chunk_duration"]
    overlap = float(config["audio"].get("chunk_overlap", 0.0))
    if overlap < 0 or overlap >= chunk_duration:
        logger.warning("  Invalid chunk_overlap=%.2f (must be 0 <= overlap < %d) — using 0",
                       overlap, chunk_duration)
        overlap = 0.0

    chunk_samples = sr * chunk_duration
    step_samples = int(sr * (chunk_duration - overlap))
    min_samples = int(sr * 1.5)

    # Parse timestamp from filename: YYYY-MM-DD-HH-MM-SS.wav
    stem = wav_path.stem
    try:
        file_dt = datetime.strptime(stem, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        logger.warning("  Could not parse timestamp from filename %r, using now()", stem)
        file_dt = datetime.now()

    logger.debug("  chunk_samples=%d, step_samples=%d (overlap=%.2fs)",
                 chunk_samples, step_samples, overlap)

    chunks = []
    idx = 0
    start = 0
    while start < len(audio):
        end = start + chunk_samples
        segment = audio[start:end]
        if len(segment) >= chunk_samples:
            chunks.append((idx, segment))
        elif len(segment) >= min_samples:
            logger.debug("  Tail chunk (%d samples) >= min (%d) — padding and including",
                         len(segment), min_samples)
            chunks.append((idx, np.pad(segment, (0, chunk_samples - len(segment)))))
        else:
            if len(segment) > 0:
                logger.debug("  Tail chunk (%d samples) < min (%d) — discarding",
                             len(segment), min_samples)
            break
        idx += 1
        start += step_samples

    logger.info("  Running inference on %d chunk(s) (overlap=%.2fs)", len(chunks), overlap)

    step_seconds = chunk_duration - overlap
    total_detections = 0
    for chunk_idx, chunk_audio in chunks:
        chunk_offset = int(chunk_idx * step_seconds)
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
                if max_per_species and det.scientific_name in _capped_species:
                    logger.debug("Capped, skipping: %s", det.common_name)
                    continue
                save_detection(
                    det.audio_chunk, det.sr, det.detection_time,
                    det.common_name, det.scientific_name, det.confidence,
                )
                if max_per_species:
                    new_count = _species_counts.get(det.scientific_name, 0) + 1
                    _species_counts[det.scientific_name] = new_count
                    if new_count >= max_per_species:
                        _capped_species.add(det.scientific_name)
                        logger.info(
                            "Species '%s' reached cap (%d); further detections will be skipped",
                            det.common_name, max_per_species,
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
    """Save a detection: spectrogram PNG, WAV clip, and database record."""
    date_str = detection_time.strftime("%Y-%m-%d")
    time_str = detection_time.strftime("%H-%M-%S")
    safe_species = common_name.replace(" ", "_")

    det_dir = data_dir / "detections" / date_str / safe_species
    det_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{time_str}_{confidence:.2f}"
    png_path = det_dir / f"{base_name}.png"
    wav_path = det_dir / f"{base_name}.wav"

    logger.debug("  Saving detection to %s", det_dir)

    # Generate spectrogram
    try:
        spec_module.generate_spectrogram(audio_chunk, sr, str(png_path),
                                         common_name, confidence)
        logger.debug("  Spectrogram saved: %s", png_path.name)
    except Exception as e:
        logger.error("  Spectrogram generation failed: %s", e)

    # Write audio chunk as WAV (no lossy re-encoding)
    try:
        import soundfile as sf
        sf.write(str(wav_path), audio_chunk, sr)
        logger.debug("  WAV saved: %s", wav_path.name)
    except Exception as e:
        logger.error("  WAV write failed: %s", e)

    # Relative paths for database storage
    rel_png = str(png_path.relative_to(data_dir))
    rel_wav = str(wav_path.relative_to(data_dir))

    try:
        database.insert_detection(
            str(data_dir), date_str, detection_time.strftime("%H:%M:%S"),
            common_name, scientific_name, confidence, rel_png, rel_wav
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

    global max_per_species, _species_counts, _capped_species
    max_per_species = int(config.get("max_detections_per_species", 0) or 0)
    if max_per_species > 0:
        _species_counts = database.species_counts(str(data_dir))
        _capped_species = {s for s, c in _species_counts.items() if c >= max_per_species}
        logger.info(
            "Per-species cap: %d (already capped: %d species)",
            max_per_species, len(_capped_species),
        )
    else:
        logger.info("Per-species cap disabled")

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
