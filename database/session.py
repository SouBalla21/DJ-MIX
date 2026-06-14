"""SQLModel database session management.

Provides a simple SQLite engine, automatic table creation, and a convenient
session factory.  The engine is a singleton per process; ``init_db`` must be
called once at application startup (e.g., from the FastAPI startup event).
"""

from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session

# Default SQLite file location – placed in the project root for simplicity.
_DB_PATH = Path("sqlite.db")

_engine = None  # type: ignore[assignment]


def get_engine() -> "Engine":
    """Return the singleton SQLAlchemy engine.

    The engine is created on first call using ``sqlite:///`` URL.  The function
    is deliberately lightweight so it can be imported from anywhere without
    side‑effects.
    """
    global _engine
    if _engine is None:
        # ``echo=False`` silences SQL logging – useful for production.
        _engine = create_engine(f"sqlite:///{_DB_PATH}", echo=False, future=True)
    return _engine


def init_db() -> None:
    """Create all tables defined in ``database.models``.

    This function should be called once during application startup.  It uses the
    ``SQLModel.metadata`` collection which aggregates metadata from all imported
    model classes.
    """
    engine = get_engine()
    # Import models to ensure they are registered with SQLModel.metadata.
    from .models import Track, Playlist, PlaylistTrack, RecentlyPlayed, Favorite, Settings

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Convenient helper returning a new ``Session`` bound to the engine.

    The caller is responsible for committing/rolling back and closing the
    session (or using it as a context manager)."""
    engine = get_engine()
    return Session(engine)
