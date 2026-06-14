"""FastAPI router for application settings.

All operations delegate to the frozen ``database.crud`` helpers. The router
provides a thin HTTP layer that:

* Retrieves the singleton Settings instance (creating defaults if absent).
* Updates permitted fields.
* Resets the settings to the model defaults.

Error handling converts ``ValueError`` from the CRUD layer into appropriate
``HTTPException`` responses.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

# Dependency that yields a DB session.
from backend.dependencies import get_db

# CRUD helpers for settings.
from database.crud import get_settings, update_settings, reset_settings

# ORM model – used directly as the response model.
from database.models import Settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=Settings)
def read_settings(db: Session = Depends(get_db)) -> Settings:
    """Return the current settings.

    ``get_settings`` creates a default row if none exists, so this endpoint always
    returns a Settings object.
    """
    return get_settings()


@router.put("/", response_model=Settings)
def modify_settings(updates: Dict[str, Any], db: Session = Depends(get_db)) -> Settings:
    """Update one or more settings fields.

    Accepted keys correspond to the columns defined on the ``Settings`` model:
    ``master_volume``, ``cue_volume``, ``theme``, ``master_device``,
    ``cue_device``, and ``waveform_zoom``.
    """
    try:
        return update_settings(**updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/reset", response_model=Settings)
def reset_to_defaults(db: Session = Depends(get_db)) -> Settings:
    """Reset all settings to their model defaults.

    Returns the freshly‑created Settings instance.
    """
    try:
        return reset_settings()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


__all__ = ["router"]
