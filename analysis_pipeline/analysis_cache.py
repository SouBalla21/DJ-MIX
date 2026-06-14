"""
Cache layer for audio-analysis results.

This module ties together the individual analysis utilities
(BPM, beat positions, waveform, and key detection) and stores
their combined output as JSON files on disk.

Public API
----------
- analyze_track(filepath)
- save_analysis(filepath, analysis)
- load_analysis(filepath)
- get_cached_analysis(filepath)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .bpm_detector import detect_bpm
from .beat_tracker import detect_beats
from .waveform_generator import generate_waveform
from .key_detector import detect_key

# ---------------------------------------------------------------------------
# Cache directory
# ---------------------------------------------------------------------------

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

__all__ = [
    "analyze_track",
    "save_analysis",
    "load_analysis",
    "get_cached_analysis",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_path(filepath: str | Path) -> str:
    """
    Generate a deterministic SHA-256 hash from an absolute file path.
    """
    absolute_path = Path(filepath).expanduser().resolve()

    return hashlib.sha256(
        str(absolute_path).encode("utf-8")
    ).hexdigest()


def _cache_path(filepath: str | Path) -> Path:
    """
    Return the cache file path corresponding to an audio file.
    """
    return _CACHE_DIR / f"{_hash_path(filepath)}.json"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_track(filepath: str | Path) -> dict[str, Any]:
    """
    Run the complete analysis pipeline.

    Returns
    -------
    dict
        {
            "bpm": float,
            "beat_positions": list[float],
            "waveform": list[float],
            "key": str
        }
    """

    bpm = detect_bpm(filepath)
    beat_positions = detect_beats(filepath)
    waveform = generate_waveform(filepath)
    key = detect_key(filepath)

    return {
        "bpm": bpm,
        "beat_positions": beat_positions,
        "waveform": waveform,
        "key": key,
    }


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------

def save_analysis(
    filepath: str | Path,
    analysis: dict[str, Any],
) -> None:
    """
    Save analysis results to a JSON cache file.
    """
    cache_file = _cache_path(filepath)

    try:
        cache_file.write_text(
            json.dumps(
                analysis,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except Exception as exc:
        raise OSError(
            f"Failed to write cache file '{cache_file}': {exc}"
        ) from exc


def load_analysis(
    filepath: str | Path,
) -> dict[str, Any] | None:
    """
    Load cached analysis.

    Returns None if:

    - cache file does not exist
    - cache file is corrupted
    - required keys are missing
    """
    cache_file = _cache_path(filepath)

    if not cache_file.exists():
        return None

    try:
        data = json.loads(
            cache_file.read_text(
                encoding="utf-8"
            )
        )

        required_keys = {
            "bpm",
            "beat_positions",
            "waveform",
            "key",
        }

        if not required_keys.issubset(data):
            return None

        return data

    except Exception:
        # Corrupted cache → behave like cache miss
        return None


# ---------------------------------------------------------------------------
# Main cache entry point
# ---------------------------------------------------------------------------

def get_cached_analysis(
    filepath: str | Path,
) -> dict[str, Any]:
    """
    Return cached analysis if available.

    Otherwise:

    1. Run the analysis pipeline.
    2. Save results to disk.
    3. Return the analysis.
    """

    cached = load_analysis(filepath)

    if cached is not None:
        return cached

    analysis = analyze_track(filepath)

    try:
        save_analysis(filepath, analysis)

    except OSError:
        # Cache failures are non-critical.
        pass

    return analysis