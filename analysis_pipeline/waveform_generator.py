"""Waveform generation utility for audio files.

Loads audio with librosa, converts to mono, downsamples to a manageable number
of points, normalizes amplitudes to [-1, 1], and returns a simple list of
floats suitable for frontend display. Errors (missing, corrupted, or unreadable
files) raise `ValueError`.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

import librosa
import numpy as np

__all__ = ["generate_waveform"]


def _load_audio(filepath: Union[str, Path]) -> tuple[np.ndarray, int]:
    """Load audio with librosa, preserving original sample rate and channels."""
    # mono=False retains channel dimension; sr=None keeps original rate.
    audio, sr = librosa.load(str(filepath), sr=None, mono=False)
    return audio, sr


def _to_mono(audio: np.ndarray) -> np.ndarray:
    """Convert stereo (or multi‑channel) audio to mono."""
    if audio.ndim == 1:
        return audio
    # librosa provides a robust conversion that handles any number of channels.
    return librosa.to_mono(audio)


def _downsample(signal: np.ndarray, target_points: int = 500) -> np.ndarray:
    """
    Reduce the signal to ``target_points`` evenly‑spaced samples.

    If the signal is already short enough, it is returned unchanged.
    Linear interpolation via ``np.interp`` is fast and memory‑light.
    """
    if signal.size <= target_points:
        return signal

    original_idx = np.arange(signal.size)
    target_idx = np.linspace(0, signal.size - 1, target_points)
    return np.interp(target_idx, original_idx, signal)


def _normalize(signal: np.ndarray) -> np.ndarray:
    """Scale amplitudes to the range [-1, 1] (silent signals stay unchanged)."""
    max_amp = np.max(np.abs(signal))
    if max_amp == 0:
        return signal
    return signal / max_amp


def generate_waveform(filepath: Union[str, Path]) -> List[float]:
    """
    Generate a down‑sampled, normalized waveform for the given audio file.

    Parameters
    ----------
    filepath : Union[str, Path]
        Path to an audio file readable by librosa (e.g., mp3, wav, flac, m4a).

    Returns
    -------
    List[float]
        Normalized waveform values in the range [-1, 1], down‑sampled to a
        reasonable number of points for UI rendering.

    Raises
    ------
    ValueError
        If the file cannot be read, is corrupted, or contains no audio data.
    """
    try:
        audio, _ = _load_audio(filepath)
    except Exception as exc:
        raise ValueError(f"Unable to load audio file '{filepath}': {exc}") from exc

    if audio.size == 0:
        raise ValueError(f"Audio file '{filepath}' contains no data")

    mono = _to_mono(audio)
    downsampled = _downsample(mono, target_points=500)
    normalized = _normalize(downsampled)

    # Convert NumPy scalars to plain Python floats for easy JSON serialization.
    return [float(v) for v in normalized.tolist()]