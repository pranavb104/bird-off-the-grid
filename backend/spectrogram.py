"""Spectrogram generation for detected bird audio clips."""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_spectrogram(audio_data: np.ndarray, sample_rate: int, output_path: str,
                         species: str, confidence: float):
    """Generate a spectrogram PNG from audio data.

    Args:
        audio_data: Audio samples as numpy array.
        sample_rate: Sample rate of the audio.
        output_path: File path for the output PNG.
        species: Species common name to overlay.
        confidence: Detection confidence to overlay.
    """
    fig, ax = plt.subplots(1, 1, figsize=(6, 3), dpi=100)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    ax.specgram(audio_data, NFFT=1024, Fs=sample_rate, noverlap=512,
                cmap="viridis", scale="dB")

    ax.set_xlabel("Time (s)", color="white", fontsize=8)
    ax.set_ylabel("Frequency (Hz)", color="white", fontsize=8)
    ax.tick_params(colors="white", labelsize=7)

    ax.set_title(f"{species} — {confidence:.0%}", color="white", fontsize=10,
                 fontweight="bold", pad=8)

    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

    fig.tight_layout(pad=1.0)
    fig.savefig(output_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
