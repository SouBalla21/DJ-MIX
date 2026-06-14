"""FastAPI router for music library management.

This router delegates heavy‑lifting to a hypothetical ``import_service`` module that
handles scanning the filesystem and importing audio files.  The service is
expected to expose two functions:

* ``import_directory(path: str) -> int`` – imports all supported audio files
  from ``path`` and returns the number of tracks added.
* ``rescan_library() -> int`` – rescans the existing library for new files,
  skipping duplicates, and returns the number of newly added tracks.

If the service module is not available at runtime, an ``ImportError`` will be
raised when the endpoint is called – this mirrors typical production behaviour
where the service is provided by a separate package.

The ``/stats`` endpoint uses the existing CRUD helpers to count the various
entities.  Direct database access is avoided in the import/rescan endpoints, as
requested, while the stats endpoint can safely use the read‑only CRUD functions.
"""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

# Dependency that yields a DB session – kept for consistency even though the
# CRUD helpers manage their own sessions.
from backend.dependencies import get_db

# Service functions – imported lazily inside the endpoint functions to avoid
# import‑time failures if the module is missing in this demo repository.
# ``import_service`` is expected to be part of the production codebase.

# CRUD helpers for statistics.
from database.crud import (
    list_tracks,
    list_playlists,
    list_favorites,
    list_recent_tracks,
)

router = APIRouter(prefix="/library", tags=["library"])


@router.post("/import", status_code=status.HTTP_200_OK)
def import_library(
    directory_path: str,
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """Import all tracks from a given directory.

    The endpoint expects a JSON payload with a single ``directory_path`` field.
    ``import_service.import_directory`` performs the actual import and returns the
    number of tracks added.
    """
    try:
        from import_service import import_directory  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import service not available",
        ) from exc

    try:
        count = import_directory(directory_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"imported": count}


@router.post("/rescan", status_code=status.HTTP_200_OK)
def rescan_library(db: Session = Depends(get_db)) -> Dict[str, int]:
    """Re‑scan the existing library for new tracks.

    ``import_service.rescan_library`` detects new files, skips duplicates, and
    returns the count of newly added tracks.
    """
    try:
        from import_service import rescan_library  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import service not available",
        ) from exc

    try:
        count = rescan_library()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"new_tracks": count}


@router.get("/stats", response_model=Dict[str, int])
def library_stats(db: Session = Depends(get_db)) -> Dict[str, int]:
    """Return simple statistics about the music library.

    * ``total_tracks`` – number of tracks in the database.
    * ``total_playlists`` – number of playlists.
    * ``total_favorites`` – number of favorited tracks.
    * ``total_recently_played`` – number of entries in the recently‑played log.
    """
    # The CRUD helpers internally create their own sessions, so the injected
    # ``db`` is not used directly – it is kept for API‑consistency.
    total_tracks = len(list_tracks())
    total_playlists = len(list_playlists())
    total_favorites = len(list_favorites())
    total_recently_played = len(list_recent_tracks())
    return {
        "total_tracks": total_tracks,
        "total_playlists": total_playlists,
        "total_favorites": total_favorites,
        "total_recently_played": total_recently_played,
    }


__all__ = ["router"]
