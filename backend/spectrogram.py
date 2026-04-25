"""Monochrome Bayer-dithered spectrogram generation."""

import numpy as np
from matplotlib import mlab
from PIL import Image

# Bayer 4×4 ordered-dither matrix (matches frontend useDither.js)
_BAYER = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5],
], dtype=np.float32) / 16.0

# Theme tokens — keep in sync with frontend tailwind.css
_PAPER = np.array([240, 236, 227], dtype=np.uint8)  # --color-background #f0ece3
_INK = np.array([10, 10, 10], dtype=np.uint8)        # --color-text       #0a0a0a

_TARGET_W = 480
_TARGET_H = 240
_DB_RANGE = 60.0  # dynamic range below per-clip peak that maps to ink-dense


def generate_spectrogram(audio_data: np.ndarray, sample_rate: int, output_path: str,
                         species: str = "", confidence: float = 0.0):
    """Generate a Bayer-dithered monochrome spectrogram PNG.

    Args:
        audio_data: Audio samples as numpy array.
        sample_rate: Sample rate of the audio.
        output_path: File path for the output PNG.
        species, confidence: Accepted for caller compatibility; not rendered
            on the image (they are shown on the dashboard card).
    """
    del species, confidence

    Pxx, _freqs, _t = mlab.specgram(
        audio_data, NFFT=1024, Fs=sample_rate, noverlap=512
    )
    spec_db = 10.0 * np.log10(Pxx + 1e-12)

    # Low frequency at bottom, time on x-axis
    spec_db = np.flipud(spec_db)

    # Normalize per-clip so quieter detections still dither cleanly
    spec_db -= spec_db.max()
    intensity = np.clip((spec_db + _DB_RANGE) / _DB_RANGE, 0.0, 1.0)

    img = Image.fromarray((intensity * 255).astype(np.uint8))
    img = img.resize((_TARGET_W, _TARGET_H), Image.NEAREST)
    intensity = np.asarray(img, dtype=np.float32) / 255.0

    H, W = intensity.shape
    threshold = np.tile(_BAYER, ((H + 3) // 4, (W + 3) // 4))[:H, :W]
    ink_mask = intensity > threshold

    out = np.where(ink_mask[..., None], _INK, _PAPER).astype(np.uint8)
    Image.fromarray(out).save(output_path, optimize=True)
