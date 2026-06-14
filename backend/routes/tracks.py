"""FastAPI router for Track CRUD operations.

All endpoints delegate to the `database.crud` functions.  The router relies on the
`get_db` dependency defined in ``backend.dependencies`` to provide a SQLModel
session for each request.  Errors raised by the CRUD helpers (typically
`ValueError`) are transformed into appropriate ``HTTPException`` responses.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

# Dependency that yields a SQLModel Session.
from backend.dependencies import get_db

# CRUD helpers re‑exported from ``database.crud``.
from database.crud import (
    add_track,
    delete_track,
    get_track_by_id,
    list_tracks,
    search_tracks,
    update_track,
)

# The ORM model – used directly as the response model.
from database.models import Track

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/", response_model=list[Track])
def read_all_tracks(db: Session = Depends(get_db)) -> list[Track]:
    """Return a list of all tracks ordered by ``date_added`` descending."""
    # ``list_tracks`` creates its own session; we ignore the injected ``db`` to keep
    # the router thin and let the CRUD layer manage sessions.
    return list_tracks()


@router.get("/{track_id}", response_model=Track)
def read_track(track_id: int, db: Session = Depends(get_db)) -> Track:
    """Return a single track by ``track_id``.

    Raises ``404`` if the track does not exist.
    """
    track = get_track_by_id(track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return track


@router.get("/search", response_model=list[Track])
def search_tracks_endpoint(
    title: str | None = Query(default=None),
    artist: str | None = Query(default=None),
    album: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Track]:
    """Search tracks by optional metadata fields.

    The underlying ``search_tracks`` CRUD function performs case‑insensitive
    ``LIKE`` matches on any provided parameter.
    """
    return search_tracks(title=title, artist=artist, album=album, genre=genre)


@router.post("/", response_model=Track, status_code=status.HTTP_201_CREATED)
def create_track(track_data: dict, db: Session = Depends(get_db)) -> Track:
    """Create a new track.

    ``track_data`` should contain at least ``filepath`` and any optional fields
    accepted by ``add_track``.  Validation is delegated to the CRUD layer – any
    ``ValueError`` results in a ``400 Bad Request`` response.
    """
    try:
        # ``add_track`` expects the same named parameters as the model fields.
        return add_track(**track_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/{track_id}", response_model=Track)
def update_existing_track(
    track_id: int,
    updates: dict,
    db: Session = Depends(get_db),
) -> Track:
    """Update fields of an existing track.

    ``updates`` is a mapping of field names to new values.  Invalid fields or a
    missing track result in a ``400``/``404`` respectively.
    """
    try:
        return update_track(track_id, **updates)
    except ValueError as exc:
        # The CRUD layer raises ``ValueError`` for both not‑found and invalid
        # fields.  We inspect the message to decide the status code.
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_track(track_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a track by ID.

    Returns ``204 No Content`` on success; ``404`` if the track does not exist.
    """
    try:
        delete_track(track_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

# Export the router for inclusion in ``backend.main``.
__all__ = ["router"]
