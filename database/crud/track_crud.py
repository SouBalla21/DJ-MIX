"""
CRUD operations for the Track model.

All functions open a short-lived session via ``database.session.get_session``.
They return model instances (or lists thereof) and raise ``ValueError`` with a
clear message when a requested record cannot be found or when an operation
fails (e.g., duplicate filepath).

The search function performs case-insensitive "contains" matches on the four
indexed string fields.
"""

from __future__ import annotations

from typing import List, Optional

from sqlmodel import select

from ..session import get_session
from ..models import Track


def add_track(
    *,
    filepath: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    duration: Optional[float] = None,
    bpm: Optional[float] = None,
    musical_key: Optional[str] = None,
    waveform_data: Optional[str] = None,
    beat_positions: Optional[str] = None,
) -> Track:
    """
    Insert a new Track record.

    ``filepath`` must be unique; attempting to insert a duplicate
    raises ``ValueError``.
    """
    with get_session() as session:
        track = Track(
            filepath=filepath,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            duration=duration,
            bpm=bpm,
            musical_key=musical_key,
            waveform_data=waveform_data,
            beat_positions=beat_positions,
        )

        session.add(track)

        try:
            session.commit()
            session.refresh(track)
        except Exception as exc:
            session.rollback()
            raise ValueError(
                f"Unable to add track: {exc}"
            ) from exc

        return track


def get_track_by_id(track_id: int) -> Optional[Track]:
    """Return a Track by primary key or None if not found."""
    with get_session() as session:
        return session.get(Track, track_id)


def get_track_by_filepath(filepath: str) -> Optional[Track]:
    """Return a Track matching the filepath or None."""
    with get_session() as session:
        stmt = select(Track).where(Track.filepath == filepath)
        return session.exec(stmt).first()


def search_tracks(
    *,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    genre: Optional[str] = None,
) -> List[Track]:
    """
    Search tracks using any combination of title, artist, album, and genre.

    Matching is case-insensitive and uses LIKE with wildcards.
    """
    with get_session() as session:
        stmt = select(Track)

        if title:
            stmt = stmt.where(Track.title.ilike(f"%{title}%"))

        if artist:
            stmt = stmt.where(Track.artist.ilike(f"%{artist}%"))

        if album:
            stmt = stmt.where(Track.album.ilike(f"%{album}%"))

        if genre:
            stmt = stmt.where(Track.genre.ilike(f"%{genre}%"))

        return session.exec(stmt).all()


def update_track(track_id: int, **updates: object) -> Track:
    """
    Update fields of an existing Track.

    ``updates`` may contain any column name defined on the model.
    Invalid field names raise ``ValueError``.
    """
    with get_session() as session:
        track = session.get(Track, track_id)

        if track is None:
            raise ValueError(
                f"Track with id {track_id} not found"
            )

        for key, value in updates.items():
            if key not in Track.model_fields:
                raise ValueError(
                    f"'{key}' is not a valid Track field"
                )

            setattr(track, key, value)

        try:
            session.commit()
            session.refresh(track)
        except Exception as exc:
            session.rollback()
            raise ValueError(
                f"Unable to update track {track_id}: {exc}"
            ) from exc

        return track


def delete_track(track_id: int) -> None:
    """
    Delete a Track by its primary key.

    Raises ``ValueError`` if the track does not exist.
    """
    with get_session() as session:
        track = session.get(Track, track_id)

        if track is None:
            raise ValueError(
                f"Track with id {track_id} not found"
            )

        session.delete(track)

        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(
                f"Unable to delete track {track_id}: {exc}"
            ) from exc


def list_tracks() -> List[Track]:
    """
    Return all tracks ordered by date_added descending.
    """
    with get_session() as session:
        stmt = select(Track).order_by(Track.date_added.desc())
        return session.exec(stmt).all()