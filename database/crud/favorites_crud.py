"""
CRUD operations for the FavoriteTrack model.

All functions open a short‑lived session via ``database.session.get_session``.
They raise ``ValueError`` with clear messages when an operation cannot be
performed (e.g., adding a duplicate favorite or removing a non‑existent one).
"""

from __future__ import annotations

from typing import List

from sqlmodel import select

from ..session import get_session
from ..models import FavoriteTrack, Track


def add_favorite(*, track_id: int) -> FavoriteTrack:
    """Mark a track as a favorite.

    ``track_id`` must reference an existing ``Track``.  Attempting to add a
    duplicate favorite (the ``track_id`` is already present) raises ``ValueError``.
    """
    with get_session() as session:
        # Ensure the track exists – gives a clearer error than a foreign‑key
        # violation later.
        track = session.get(Track, track_id)
        if track is None:
            raise ValueError(f"Track with id {track_id} does not exist")

        # Check for an existing favorite entry.
        existing = session.get(FavoriteTrack, track_id)
        if existing is not None:
            raise ValueError(f"Track {track_id} is already a favorite")

        favorite = FavoriteTrack(track_id=track_id)
        session.add(favorite)
        try:
            session.commit()
            session.refresh(favorite)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to add favorite for track {track_id}: {exc}") from exc

        return favorite


def remove_favorite(*, track_id: int) -> None:
    """Remove a favorite entry.

    Raises ``ValueError`` if the ``track_id`` is not currently favorited.
    """
    with get_session() as session:
        favorite = session.get(FavoriteTrack, track_id)
        if favorite is None:
            raise ValueError(f"Track {track_id} is not in favorites")
        session.delete(favorite)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to remove favorite for track {track_id}: {exc}") from exc


def is_favorite(track_id: int) -> bool:
    """Return ``True`` if the given ``track_id`` is marked as a favorite.
    """
    with get_session() as session:
        fav = session.get(FavoriteTrack, track_id)
        return fav is not None


def list_favorites() -> List[FavoriteTrack]:
    """Return all favorite tracks ordered by ``date_added`` descending.
    The ``track`` relationship is eager‑loaded for convenient access to the
    underlying ``Track`` details.
    """
    with get_session() as session:
        stmt = select(FavoriteTrack).order_by(FavoriteTrack.date_added.desc())
        results = session.exec(stmt).all()
        # Eager‑load the related Track objects if they are not already loaded.
        for fav in results:
            # Accessing ``fav.track`` triggers lazy loading; we do it here so the
            # caller gets populated objects without needing an extra session.
            _ = fav.track
        return results
