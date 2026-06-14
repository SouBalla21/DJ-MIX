"""FastAPI router for Playlist CRUD operations.

This module provides endpoints to manage playlists and their track associations.
All database interactions are delegated to the frozen ``database.crud``
functions; the router only handles request/response handling and error
translation.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

# Dependency that yields a DB session.
from backend.dependencies import get_db

# Exported CRUD helpers.
from database.crud import (
    create_playlist,
    delete_playlist,
    get_playlist,
    list_playlists,
    rename_playlist,
    add_track_to_playlist,
    remove_track_from_playlist,
    reorder_playlist,
)

# ORM models – used directly as response models.
from database.models import Playlist, PlaylistTrack

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("/", response_model=List[Playlist])
def read_all_playlists(db: Session = Depends(get_db)) -> List[Playlist]:
    """Return a list of all playlists ordered by creation time descending."""
    return list_playlists()


@router.get("/{playlist_id}", response_model=Playlist)
def read_playlist(playlist_id: int, db: Session = Depends(get_db)) -> Playlist:
    """Return a single playlist by its ID.

    Raises ``404`` if the playlist does not exist.
    """
    playlist = get_playlist(playlist_id=playlist_id)
    if playlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    return playlist


@router.post("/", response_model=Playlist, status_code=status.HTTP_201_CREATED)
def create_new_playlist(
    payload: dict,
    db: Session = Depends(get_db),
) -> Playlist:
    """Create a new playlist.

    ``payload`` should contain ``name`` (required) and optionally ``description``.
    The underlying model does not have a description field, so any extra data is
    ignored.
    """
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'name' is required")
    try:
        return create_playlist(name=name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/{playlist_id}", response_model=Playlist)
def rename_existing_playlist(
    playlist_id: int,
    payload: dict,
    db: Session = Depends(get_db),
) -> Playlist:
    """Rename an existing playlist.

    ``payload`` must contain ``new_name``.
    """
    new_name = payload.get("new_name")
    if not new_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'new_name' is required")
    try:
        return rename_playlist(playlist_id=playlist_id, new_name=new_name)
    except ValueError as exc:
        # ``rename_playlist`` raises ValueError for not‑found or name clash.
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_playlist(playlist_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a playlist and its track associations.

    Returns ``204 No Content`` on success; ``404`` if the playlist does not exist.
    """
    try:
        delete_playlist(playlist_id=playlist_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/{playlist_id}/tracks/{track_id}",
    response_model=PlaylistTrack,
    status_code=status.HTTP_201_CREATED,
)
def add_track(
    playlist_id: int,
    track_id: int,
    position: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PlaylistTrack:
    """Add a track to a playlist at an optional position.

    Returns the created ``PlaylistTrack`` association.
    """
    try:
        return add_track_to_playlist(
            playlist_id=playlist_id, track_id=track_id, position=position
        )
    except ValueError as exc:
        # ``add_track_to_playlist`` raises for missing playlist/track or duplicate.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete(
    "/{playlist_id}/tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_track(
    playlist_id: int,
    track_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Remove a track from a playlist.

    Returns ``204 No Content`` on success; ``404`` if the association does not exist.
    """
    try:
        remove_track_from_playlist(playlist_id=playlist_id, track_id=track_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put(
    "/{playlist_id}/reorder",
    response_model=List[PlaylistTrack],
)
def reorder_tracks(
    playlist_id: int,
    new_order: List[int],
    db: Session = Depends(get_db),
) -> List[PlaylistTrack]:
    """Reorder tracks within a playlist.

    ``new_order`` is a list of ``track_id`` values representing the desired order.
    The function returns the updated ``PlaylistTrack`` objects.
    """
    try:
        return reorder_playlist(playlist_id=playlist_id, new_order=new_order)
    except ValueError as exc:
        # Could be not‑found playlist or mismatched IDs.
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


__all__ = ["router"]
