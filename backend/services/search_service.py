"""Service layer for searching tracks in the library.

All functions delegate to the frozen CRUD ``search_tracks`` helper which
performs case‑insensitive ``LIKE`` queries against the ``Track`` table.  The
service provides convenient, typed wrappers for the most common search use‑
cases and a ``global_search`` that merges results from all fields while
eliminating duplicates.
"""

from __future__ import annotations

from typing import List

from database.crud import search_tracks
from database.models import Track


def _search(**kwargs: str) -> List[Track]:
    """Internal helper that forwards to ``search_tracks``.

    ``kwargs`` may contain any of ``title``, ``artist``, ``album`` or ``genre``.
    Empty strings are ignored – ``search_tracks`` treats ``None`` as "no filter".
    """
    # Convert empty strings to ``None`` so the CRUD layer skips the filter.
    filtered = {k: v for k, v in kwargs.items() if v}
    if not filtered:
        # No criteria – return an empty list rather than all tracks.
        return []
    return search_tracks(**filtered)  # type: ignore[arg-type]


def search_by_title(title: str) -> List[Track]:
    """Return tracks whose title contains ``title`` (case‑insensitive)."""
    return _search(title=title)


def search_by_artist(artist: str) -> List[Track]:
    """Return tracks whose artist contains ``artist`` (case‑insensitive)."""
    return _search(artist=artist)


def search_by_album(album: str) -> List[Track]:
    """Return tracks whose album contains ``album`` (case‑insensitive)."""
    return _search(album=album)


def search_by_genre(genre: str) -> List[Track]:
    """Return tracks whose genre contains ``genre`` (case‑insensitive)."""
    return _search(genre=genre)


def global_search(query: str) -> List[Track]:
    """Search across title, artist, album, and genre."""

    if not query:
        return []

    results = (
        search_tracks(title=query)
        + search_tracks(artist=query)
        + search_tracks(album=query)
        + search_tracks(genre=query)
    )

    unique: List[Track] = []
    seen_ids = set()

    for track in results:
        if track.id not in seen_ids:
            seen_ids.add(track.id)
            unique.append(track)

    return unique

__all__ = [
    "search_by_title",
    "search_by_artist",
    "search_by_album",
    "search_by_genre",
    "global_search",
]
