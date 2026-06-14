"""FastAPI router for recently played history.

Endpoints delegate to the frozen ``database.crud`` helpers for:

* Listing recently played tracks (most recent first).
* Adding a track to the history.
* Clearing the entire history.

All routes use the ``get_db`` dependency for consistency, although the CRUD
functions manage their own sessions. ``ValueError`` exceptions from the CRUD
layer are converted into ``HTTPException`` with appropriate status codes.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

# Dependency that yields a DB session.
from backend.dependencies import get_db

# CRUD helpers for recently played history.
from database.crud import (
    add_recent_track,
    clear_history,
    list_recent_tracks,
)

# ORM model – used directly as the response payload.
from database.models import RecentlyPlayed

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/", response_model=List[RecentlyPlayed])
def get_history(limit: int = 100, db: Session = Depends(get_db)) -> List[RecentlyPlayed]:
    """Return the most recent played tracks.

    ``limit`` caps the number of items returned (default 100). The underlying
    CRUD function orders by ``played_at`` descending.
    """
    return list_recent_tracks(limit=limit)


@router.post("/{track_id}", response_model=RecentlyPlayed, status_code=status.HTTP_201_CREATED)
def add_to_history(track_id: int, db: Session = Depends(get_db)) -> RecentlyPlayed:
    """Record that ``track_id`` has been played now.

    Raises ``400 Bad Request`` if the track does not exist.
    """
    try:
        return add_recent_track(track_id=track_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_history(db: Session = Depends(get_db)) -> None:
    """Delete all entries from the recently played history.

    Returns ``204 No Content`` on success; any failure yields a ``500`` error.
    """
    try:
        clear_history()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


__all__ = ["router"]
