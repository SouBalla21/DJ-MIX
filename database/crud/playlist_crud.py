"""
CRUD operations for the Playlist model and its association table ``PlaylistTrack``.

All functions open a short‑lived session via ``database.session.get_session``.
They raise ``ValueError`` with clear messages when an operation cannot be
performed (e.g., duplicate playlist name, adding a non‑existent track, or
reordering with an out‑of‑range index).
"""

from __future__ import annotations

from typing import List, Optional

from sqlmodel import select, delete

from ..session import get_session
from ..models import Playlist, PlaylistTrack, Track


def create_playlist(*, name: str) -> Playlist:
    """Create a new playlist.

    ``name`` must be unique; attempting to create a duplicate raises ``ValueError``.
    """
    with get_session() as session:
        # Ensure the name is not already taken.
        existing = session.exec(select(Playlist).where(Playlist.name == name)).first()
        if existing is not None:
            raise ValueError(f"Playlist with name '{name}' already exists")

        playlist = Playlist(name=name)
        session.add(playlist)
        try:
            session.commit()
            session.refresh(playlist)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to create playlist '{name}': {exc}") from exc

        return playlist


def rename_playlist(*, playlist_id: int, new_name: str) -> Playlist:
    """Rename an existing playlist.

    Raises ``ValueError`` if the playlist does not exist or the new name is already used.
    """
    with get_session() as session:
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            raise ValueError(f"Playlist with id {playlist_id} not found")

        # Check for name clash.
        clash = session.exec(
            select(Playlist).where(Playlist.name == new_name, Playlist.id != playlist_id)
        ).first()
        if clash is not None:
            raise ValueError(f"Another playlist already uses the name '{new_name}'")

        playlist.name = new_name
        try:
            session.commit()
            session.refresh(playlist)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to rename playlist {playlist_id}: {exc}") from exc

        return playlist


def delete_playlist(*, playlist_id: int) -> None:
    """Delete a playlist and all its associated ``PlaylistTrack`` rows."""
    with get_session() as session:
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            raise ValueError(f"Playlist with id {playlist_id} not found")

        # Delete associated PlaylistTrack rows.
        session.exec(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id))
        session.delete(playlist)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to delete playlist {playlist_id}: {exc}") from exc


def get_playlist(*, playlist_id: int) -> Optional[Playlist]:
    """Return a playlist with eager‑loaded tracks, or ``None`` if not found."""
    with get_session() as session:
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            return None
        # Trigger lazy loading of related objects.
        _ = playlist.tracks
        for pt in playlist.tracks:
            _ = pt.track
        return playlist


def list_playlists() -> List[Playlist]:
    """Return all playlists ordered by ``created_at`` descending."""
    with get_session() as session:
        stmt = select(Playlist).order_by(Playlist.created_at.desc())
        playlists = session.exec(stmt).all()
        for pl in playlists:
            _ = pl.tracks
            for pt in pl.tracks:
                _ = pt.track
        return playlists


def add_track_to_playlist(*, playlist_id: int, track_id: int, position: Optional[int] = None) -> PlaylistTrack:
    """Add a ``Track`` to a ``Playlist``.

    * ``position`` – zero‑based index; if omitted the track is appended to the end.
    * Raises ``ValueError`` if the playlist or track does not exist, or if the
      track is already in the playlist.
    """
    with get_session() as session:
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            raise ValueError(f"Playlist with id {playlist_id} not found")

        track = session.get(Track, track_id)
        if track is None:
            raise ValueError(f"Track with id {track_id} not found")

        # Check for duplicate entry.
        dup = session.exec(
            select(PlaylistTrack).where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id == track_id,
            )
        ).first()
        if dup is not None:
            raise ValueError(f"Track {track_id} is already in playlist {playlist_id}")

        # Determine insertion position.
        if position is None:
            # Append: find max existing position + 1.
            max_pos = session.exec(
                select(PlaylistTrack.position).where(PlaylistTrack.playlist_id == playlist_id)
            ).all()
            position = (max(max_pos) + 1) if max_pos else 0
        else:
            if position < 0:
                raise ValueError("position cannot be negative")
            # Shift existing tracks at or after this position.
            pts_to_shift = session.exec(
                select(PlaylistTrack)
                .where(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.position >= position)
                .order_by(PlaylistTrack.position.desc())
            ).all()
            for pt in pts_to_shift:
                pt.position += 1
                session.add(pt)

        pt = PlaylistTrack(playlist_id=playlist_id, track_id=track_id, position=position)
        session.add(pt)
        try:
            session.commit()
            session.refresh(pt)
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to add track {track_id} to playlist {playlist_id}: {exc}") from exc

        return pt


def remove_track_from_playlist(*, playlist_id: int, track_id: int) -> None:
    """Remove a track from a playlist.

    Raises ``ValueError`` if the association does not exist.
    """
    with get_session() as session:
        pt = session.exec(
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id)
        ).first()
        if pt is None:
            raise ValueError(f"Track {track_id} is not in playlist {playlist_id}")

        removed_position = pt.position
        session.delete(pt)
        # Collapse the gap left by the removed track.
        pts_to_shift = session.exec(
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.position > removed_position)
            .order_by(PlaylistTrack.position)
        ).all()
        for other in pts_to_shift:
            other.position -= 1
            session.add(other)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(
                f"Unable to remove track {track_id} from playlist {playlist_id}: {exc}"
            ) from exc


def reorder_playlist(*, playlist_id: int, new_order: List[int]) -> List[PlaylistTrack]:
    """Reorder tracks in a playlist.

    ``new_order`` is a list of ``track_id`` values representing the desired order.
    All ``track_id`` values must already be present in the playlist, and the list
    must contain exactly the same set of IDs (no missing or extra entries).
    Returns the updated ``PlaylistTrack`` objects ordered by their new position.
    """
    with get_session() as session:
        # Verify playlist exists.
        playlist = session.get(Playlist, playlist_id)
        if playlist is None:
            raise ValueError(f"Playlist with id {playlist_id} not found")

        # Fetch current association rows.
        current_pts = session.exec(
            select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
        ).all()
        current_ids = {pt.track_id for pt in current_pts}
        new_ids = set(new_order)

        if current_ids != new_ids:
            raise ValueError(
                "new_order must contain exactly the same track IDs as the current playlist"
            )

        # Apply new positions.
        for position, track_id in enumerate(new_order):
            pt = next(pt for pt in current_pts if pt.track_id == track_id)
            pt.position = position
            session.add(pt)

        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise ValueError(f"Unable to reorder playlist {playlist_id}: {exc}") from exc

        # Return rows ordered by new position.
        updated = session.exec(
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
        ).all()
        return updated
