"""
CRUD operations for the ``RecentlyPlayed`` model.

All functions open a short‑lived session via ``database.session.get_session``.
They raise ``ValueError`` with clear messages when an operation cannot be
performed (e.g., adding a record for a non‑existent track).
"""

from __future__ import annotations

from typing import List

from sqlmodel import select, delete

from ..session import get_session
from ..models import RecentlyPlayed, Track


def add_recent_track(*, track_id: int) -> RecentlyPlayed:
    """Record that a track has been played now.

    ``track_id`` must reference an existing ``Track``; otherwise a ``ValueError``
    is raised. The function creates a new ``RecentlyPlayed`` entry with the
    current UTC timestamp (handled by the model's default).
    """
    with get_session() as session:
        # Verify the track exists for a clearer error than a foreign‑key failure.
        track = session.get(Track, track_id)
        if track is None:
            raise ValueError(f"Track with id {track_id} does not exist")

        recent = RecentlyPlayed(track_id=track_id)
        session.add(recent)
        try:
            session.commit()
            session.refresh(recent)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to add recently played entry for track {track_id}: {exc}") from exc

        return recent


def list_recent_tracks(*, limit: int = 100) -> List[RecentlyPlayed]:
    """Return the most recent ``RecentlyPlayed`` entries ordered by ``played_at``.

    ``limit`` caps the number of rows returned; a sensible default of 100 keeps
    UI loads fast while still providing a useful history.
    """
    with get_session() as session:
        stmt = (
            select(RecentlyPlayed)
            .order_by(RecentlyPlayed.played_at.desc())
            .limit(limit)
        )
        results = session.exec(stmt).all()
        # Eager‑load the related Track objects for convenience.
        for rp in results:
            _ = rp.track  # triggers lazy load.
        return results


def clear_history() -> None:
    """Delete *all* entries from the ``RecentlyPlayed`` table.

    This is a destructive operation, so it is wrapped in a try/except block to
    provide a clear ``ValueError`` on failure.
    """
    with get_session() as session:
        try:
            session.exec(delete(RecentlyPlayed))
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to clear recently played history: {exc}") from exc
