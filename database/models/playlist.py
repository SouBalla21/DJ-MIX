"""Playlist and association models.

A ``Playlist`` is a named collection of tracks.  The many‑to‑many relationship is
expressed via the ``PlaylistTrack`` association table, which stores the order of
tracks within a playlist.
"""

from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class PlaylistTrack(SQLModel, table=True):
    """Association table linking ``Playlist`` and ``Track`` with explicit order.

    ``position`` starts at ``0`` for the first track in the playlist.
    """

    playlist_id: Optional[int] = Field(default=None, foreign_key="playlist.id", primary_key=True)
    track_id: Optional[int] = Field(default=None, foreign_key="track.id", primary_key=True)
    position: int = Field(default=0, description="Zero‑based order in the playlist")

    # Back‑references (optional, used by SQLModel for relationship loading)
    playlist: Optional["Playlist"] = Relationship(back_populates="tracks")
    track: Optional["Track"] = Relationship(back_populates="playlists")


class Playlist(SQLModel, table=True):
    """User‑defined playlist.

    ``name`` is unique per user (the current app has a single user, so it is globally
    unique).  ``created_at`` and ``updated_at`` timestamps aid UI sorting.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: Optional[float] = Field(default_factory=lambda: __import__('time').time())
    updated_at: Optional[float] = Field(default_factory=lambda: __import__('time').time())

    # Relationship to association objects – enables ``playlist.tracks``
    tracks: List[PlaylistTrack] = Relationship(back_populates="playlist")
