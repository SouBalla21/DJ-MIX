"""Shared FastAPI dependencies for the DJ backend.

Only ``get_db`` is provided – a lightweight dependency that yields a SQLModel
Session for request handlers.  The session is created via the ``get_session``
context manager from the frozen ``database.session`` module, guaranteeing that it
is properly closed (or rolled back) after each request.

The file is deliberately minimal and contains no business logic; all data
operations live in the ``database.crud`` package, which is treated as immutable
production code.
"""

from __future__ import annotations

from typing import Generator

from sqlmodel import Session
from fastapi import Depends

# Import the session factory from the frozen ``database`` package.
from database.session import get_session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage example in a route:
    ```python
    @router.get("/items")
    def read_items(db: Session = Depends(get_db)):
        ...
    ```

    The ``with`` block ensures the session is automatically closed (or rolled
    back on error) when the request finishes.
    """
    with get_session() as session:
        yield session


__all__ = ["get_db"]
