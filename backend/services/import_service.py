"""
Service for importing music files into the library.

Responsibilities:
- Recursively scan folders.
- Detect supported audio formats.
- Skip duplicate tracks.
- Extract metadata.
- Add tracks to the database.
- Return import statistics.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from audio_engine.decoder import get_decoder
from database.crud import add_track, get_track_by_filepath

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".ogg",
}


def _extract_metadata(filepath: Path) -> Dict[str, Any]:
    """
    Extract metadata from an audio file.

    Missing fields are replaced with None.
    """
    metadata = get_decoder().get_metadata(filepath)

    return {
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "album": metadata.get("album"),
        "genre": metadata.get("genre"),
        "duration": metadata.get("duration"),
        "bpm": metadata.get("bpm"),
        "musical_key": metadata.get("key"),
    }


def import_file(filepath: Path) -> Dict[str, int]:
    """
    Import a single audio file.

    Returns:
        {
            "added": 1,
            "skipped": 0,
            "errors": 0
        }
    """

    if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {
            "added": 0,
            "skipped": 0,
            "errors": 0,
        }

    # Skip duplicates
    if get_track_by_filepath(str(filepath)):
        return {
            "added": 0,
            "skipped": 1,
            "errors": 0,
        }

    try:
        metadata = _extract_metadata(filepath)

        add_track(
            filepath=str(filepath),
            **metadata,
        )

        return {
            "added": 1,
            "skipped": 0,
            "errors": 0,
        }

    except Exception:
        return {
            "added": 0,
            "skipped": 0,
            "errors": 1,
        }


def import_directory(directory_path: str) -> Dict[str, int]:
    """
    Recursively import all supported audio files inside a directory.

    Returns:
        {
            "added": int,
            "skipped": int,
            "errors": int
        }
    """

    root = Path(directory_path).expanduser().resolve()

    if not root.is_dir():
        raise ValueError(
            f"'{directory_path}' is not a valid directory."
        )

    stats = {
        "added": 0,
        "skipped": 0,
        "errors": 0,
    }

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            filepath = Path(dirpath) / filename

            if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            file_stats = import_file(filepath)

            for key in stats:
                stats[key] += file_stats[key]

    return stats


def rescan_library() -> Dict[str, int]:
    """
    Re-scan the configured music library.

    Uses the MUSIC_LIBRARY_ROOT environment variable.
    """

    library_root = os.getenv("MUSIC_LIBRARY_ROOT")

    if library_root is None:
        raise ValueError(
            "Environment variable 'MUSIC_LIBRARY_ROOT' is not set."
        )

    return import_directory(library_root)
