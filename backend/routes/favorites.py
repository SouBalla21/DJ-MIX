"""FastAPI router for managing favorite tracks.

All operations delegate to the frozen ``database.crud`` helpers.  The router
provides a thin HTTP layer that translates ``ValueError`` exceptions into
appropriate ``HTTPException`` responses and uses the ``get_db`` dependency for
session handling.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

# Dependency that yields a DB session.
from backend.dependencies import get_db

# CRUD functions for favorites.
from database.crud import (
    add_favorite,
    list_favorites,
    is_favorite,
    remove_favorite,
)

# ORM model used directly as the response payload.
from database.models import FavoriteTrack

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/", response_model=List[FavoriteTrack])
def get_all_favorites(db: Session = Depends(get_db)) -> List[FavoriteTrack]:
    """Return every favorite track, ordered by ``date_added`` descending."""
    return list_favorites()


@router.get("/{track_id}", response_model=bool)
def check_favorite(track_id: int, db: Session = Depends(get_db)) -> bool:
    """Return ``True`` if the given ``track_id`` is marked as a favorite.

    A ``404`` is *not* returned – the endpoint simply reports the boolean status.
    """
    return is_favorite(track_id)


@router.post(
    "/{track_id}",
    response_model=FavoriteTrack,
    status_code=status.HTTP_201_CREATED,
)
def mark_favorite(track_id: int, db: Session = Depends(get_db)) -> FavoriteTrack:
    """Mark a track as a favorite.

    Raises ``400 Bad Request`` if the track is already a favorite or does not
    exist.
    """
    try:
        return add_favorite(track_id=track_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unmark_favorite(track_id: int, db: Session = Depends(get_db)) -> None:
    """Remove a track from the favorites list.

    Returns ``204 No Content`` on success; ``404`` if the track was not favorited.
    """
    try:
        remove_favorite(track_id=track_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


__all__ = ["router"]
