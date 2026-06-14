"""BPM detection utility for audio files.

This module provides a single public function ``detect_bpm`` that loads an
audio file with ``librosa`` and estimates its tempo (beats per minute) using
``librosa.beat.beat_track``.  The implementation is deliberately lightweight
and independent of the rest of the project – it does not import any database or
backend code.

Error handling:
* If the file cannot be read (missing, unsupported format, or corrupted), a
  ``ValueError`` is raised with a descriptive message.
* Unexpected exceptions from ``librosa`` are caught and re‑raised as ``ValueError``
  to keep the API surface simple for callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import librosa

__all__ = ["detect_bpm"]


def _load_audio(filepath: Union[str, Path]) -> tuple[np.ndarray, int]:
    """Load audio using ``librosa.load``.

    Returns the audio time series (as a NumPy array) and the sample rate.
    ``librosa`` automatically converts to mono; for BPM detection mono is fine.
    """
    # ``librosa.load`` raises ``FileNotFoundError`` or ``Exception`` for
    # unsupported/corrupted files – we let those propagate to be handled by the
    # public ``detect_bpm`` wrapper.
    audio, sr = librosa.load(str(filepath), sr=None, mono=True)
    return audio, sr


def detect_bpm(filepath: Union[str, Path]) -> float:
    """Estimate the BPM (tempo) of an audio file.

    Parameters
    ----------
    filepath:
        Path to an audio file readable by ``librosa`` (e.g., mp3, wav, flac).  The
        function accepts both ``str`` and ``Path`` objects.

    Returns
    -------
    float
        Estimated beats per minute.  The value is rounded to one decimal place
        for consistency, but the raw float is returned.

    Raises
    ------
    ValueError
        If the file cannot be read, is corrupted, or ``librosa`` fails to compute
        a tempo.
    """
    try:
        audio, sr = _load_audio(filepath)
    except Exception as exc:
        raise ValueError(f"Unable to load audio file '{filepath}': {exc}") from exc

    if audio.size == 0:
        raise ValueError(f"Audio file '{filepath}' contains no data")

    try:
        # ``beat_track`` returns (tempo, beat_frames).  ``tempo`` is a float.
        tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    except Exception as exc:
        raise ValueError(f"Failed to detect BPM for '{filepath}': {exc}") from exc

    # ``tempo`` may be ``nan`` if detection fails – treat as error.
    if tempo is None or not isinstance(tempo, (int, float)):
        raise ValueError(f"BPM detection returned invalid result for '{filepath}'")

    return float(tempo)
