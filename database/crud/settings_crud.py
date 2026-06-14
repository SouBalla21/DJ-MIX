"""
CRUD helpers for the ``Settings`` model.

All functions open a short‑lived session via ``database.session.get_session``.
They raise ``ValueError`` with clear messages when an operation cannot be
performed (e.g., trying to update a non‑existent setting field).
"""

from __future__ import annotations

from typing import Any, Dict

from sqlmodel import select

from ..session import get_session
from ..models import Settings


def _ensure_singleton(session) -> Settings:
    """Return the unique ``Settings`` row, creating it if necessary.

    The ``Settings`` table is expected to contain at most one row – the app uses it
    as a singleton configuration store.  If the table is empty we create a new row
    with the model's default values (SQLModel applies ``Field(default=…)`` when the
    instance is instantiated).
    """
    settings = session.get(Settings, 1)
    if settings is None:
        settings = Settings()
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


def get_settings() -> Settings:
    """Return the current user settings.

    If the settings table is empty a new row with defaults is created on‑the‑fly.
    """
    with get_session() as session:
        return _ensure_singleton(session)


def update_settings(**updates: Any) -> Settings:
    """Update one or more settings fields.

    ``updates`` keys must correspond to column names defined on the ``Settings``
    model.  Invalid keys raise ``ValueError``.  The function returns the refreshed
    ``Settings`` instance after committing.
    """
    if not updates:
        raise ValueError("No updates provided to update_settings()")

    with get_session() as session:
        settings = _ensure_singleton(session)

        for key, value in updates.items():
            if key not in Settings.model_fields:
                raise ValueError(f"'{key}' is not a valid Settings field")
            setattr(settings, key, value)

        try:
            session.commit()
            session.refresh(settings)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to update settings: {exc}") from exc

        return settings


def reset_settings() -> Settings:
    """Reset all settings to their model defaults.

    The existing row (if any) is replaced with a freshly‑instantiated ``Settings``
    object that uses the default values declared on each ``Field``.  The function
    returns the new settings instance.
    """
    with get_session() as session:
        # Delete any existing row(s) – there should be at most one.
        session.exec(select(Settings))  # ensures table exists
        session.execute("DELETE FROM settings")  # raw SQL for simplicity
        session.commit()
        # Create a new defaults row.
        new_settings = Settings()
        session.add(new_settings)
        try:
            session.commit()
            session.refresh(new_settings)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to reset settings: {exc}") from exc
        return new_settings
