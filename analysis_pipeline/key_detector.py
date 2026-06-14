"""
Musical key detection utility for audio files.

The public function ``detect_key`` loads an audio file with librosa,
extracts chroma features, and applies a simple Krumhansl-Schmuckler
key-template matching algorithm to estimate the most likely tonic and
mode (major/minor).

The implementation is lightweight, independent of any database or
backend code, and raises ValueError for unreadable or corrupted inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import librosa
import numpy as np

__all__ = ["detect_key"]


# ---------------------------------------------------------------------------
# Krumhansl-Schmuckler key profiles
# ---------------------------------------------------------------------------

_MAJOR_PROFILE = np.array(
    [
        6.35,
        2.23,
        3.48,
        2.33,
        4.38,
        4.09,
        2.52,
        5.19,
        2.39,
        3.66,
        2.29,
        2.88,
    ]
)

_MINOR_PROFILE = np.array(
    [
        6.33,
        2.68,
        3.52,
        5.38,
        2.60,
        3.53,
        2.54,
        4.75,
        3.98,
        2.69,
        3.34,
        3.17,
    ]
)

# Normalize profiles for cosine similarity
_MAJOR_PROFILE = _MAJOR_PROFILE / np.linalg.norm(_MAJOR_PROFILE)
_MINOR_PROFILE = _MINOR_PROFILE / np.linalg.norm(_MINOR_PROFILE)

_NOTE_NAMES = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]


def _load_mono_audio(
    filepath: Union[str, Path],
) -> tuple[np.ndarray, int]:
    """
    Load an audio file as mono.

    Returns
    -------
    tuple[np.ndarray, int]
        (audio, sample_rate)
    """
    try:
        audio, sr = librosa.load(
            str(filepath),
            sr=None,
            mono=True,
        )
    except Exception as exc:
        raise ValueError(
            f"Unable to load audio file '{filepath}': {exc}"
        ) from exc

    if audio.size == 0:
        raise ValueError(
            f"Audio file '{filepath}' contains no data"
        )

    return audio, sr


def _compute_average_chroma(
    audio: np.ndarray,
    sr: int,
) -> np.ndarray:
    """
    Compute the average chroma vector over the whole track.

    Returns
    -------
    np.ndarray
        Length-12 normalized chroma vector.
    """
    chroma = librosa.feature.chroma_cqt(
        y=audio,
        sr=sr,
        hop_length=512,
    )

    mean_chroma = np.mean(chroma, axis=1)

    norm = np.linalg.norm(mean_chroma)

    if norm == 0:
        return np.zeros_like(mean_chroma)

    return mean_chroma / norm


def _correlate_with_profiles(
    chroma: np.ndarray,
) -> tuple[int, str]:
    """
    Compare the chroma vector with all 24 major/minor templates.

    Returns
    -------
    tuple[int, str]
        (pitch_class_index, mode)
    """
    best_score = -np.inf
    best_pitch = 0
    best_mode = "Major"

    for i in range(12):
        major_template = np.roll(_MAJOR_PROFILE, i)
        minor_template = np.roll(_MINOR_PROFILE, i)

        major_score = np.dot(chroma, major_template)
        minor_score = np.dot(chroma, minor_template)

        if major_score > best_score:
            best_score = major_score
            best_pitch = i
            best_mode = "Major"

        if minor_score > best_score:
            best_score = minor_score
            best_pitch = i
            best_mode = "Minor"

    return best_pitch, best_mode


def detect_key(
    filepath: Union[str, Path],
) -> str:
    """
    Detect the musical key of an audio file.

    Parameters
    ----------
    filepath : str | Path
        Path to an audio file readable by librosa.

    Returns
    -------
    str
        A key name such as:

        - "C Major"
        - "G Major"
        - "A Minor"
        - "F# Minor"

        Returns "Unknown" if no tonal center can be determined.

    Raises
    ------
    ValueError
        If the file is unreadable or corrupted.
    """
    audio, sr = _load_mono_audio(filepath)

    chroma = _compute_average_chroma(audio, sr)

    if np.allclose(chroma, 0):
        return "Unknown"

    pitch_index, mode = _correlate_with_profiles(chroma)

    return f"{_NOTE_NAMES[pitch_index]} {mode}"