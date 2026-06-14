"""Beat detection utility for audio files.

Provides a single public function ``detect_beats`` that loads an audio file with
``librosa`` and extracts beat timestamps using ``librosa.beat.beat_track``.  The
function returns a list of timestamps (in seconds) where beats occur.

Error handling mirrors ``analysis_pipeline.bpm_detector`` – any failure to load
or process the file raises ``ValueError`` with a clear message.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

import librosa

__all__ = ["detect_beats"]


def _load_audio(filepath: Union[str, Path]) -> tuple["np.ndarray", int]:  # type: ignore[name-defined]
    """Load an audio file with ``librosa``.

    Returns a tuple ``(audio, sample_rate)``. ``librosa.load`` raises for missing
    or unreadable files; the caller will catch and wrap those exceptions.
    """
    # ``sr=None`` preserves the original sampling rate, and ``mono=True`` converts
    # to mono which is sufficient for beat detection.
    audio, sr = librosa.load(str(filepath), sr=None, mono=True)
    return audio, sr


def detect_beats(filepath: Union[str, Path]) -> List[float]:
    """Detect beat timestamps in an audio file.

    Parameters
    ----------
    filepath:
        Path to an audio file supported by ``librosa`` (e.g., mp3, wav, flac).

    Returns
    -------
    List[float]
        A list of beat times expressed in seconds, ordered chronologically.

    Raises
    ------
    ValueError
        If the file cannot be read, is corrupted, or beat detection fails.
    """
    try:
        audio, sr = _load_audio(filepath)
    except Exception as exc:
        raise ValueError(f"Unable to load audio file '{filepath}': {exc}") from exc

    if audio.size == 0:
        raise ValueError(f"Audio file '{filepath}' contains no data")

    try:
        # ``beat_track`` returns (tempo, beat_frames). We only need the frames.
        _, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
    except Exception as exc:
        raise ValueError(f"Failed to detect beats for '{filepath}': {exc}") from exc

    if beat_frames.size == 0:
        # No beats were detected – return an empty list rather than error.
        return []

    # Convert frame indices to timestamps in seconds.
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    # Ensure we return plain Python floats (not NumPy scalars).
    return [float(t) for t in beat_times]
