"""Track model definition.

Represents an audio file with metadata required for the DJ platform.  The
``waveform_data`` and ``beat_positions`` fields store JSON‑serialisable data –
they are kept as ``TEXT`` columns to avoid coupling the model to a particular
serialization format.
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Track(SQLModel, table=True):
    # Relationships
    playlists: List["PlaylistTrack"] = Relationship(back_populates="track")
    favorite: Optional["FavoriteTrack"] = Relationship(back_populates="track")
    """Audio track metadata.

    * ``id`` – Primary key, auto‑generated.
    * ``filepath`` – Absolute path to the source file; unique index.
    * ``title``, ``artist``, ``album``, ``genre`` – Basic tags.
    * ``duration`` – Length in seconds.
    * ``bpm`` – Beats per minute (floating point for fractional values).
    * ``musical_key`` – Optional musical key (e.g. "C#m").
    * ``waveform_data`` – JSON string with waveform peaks/RMS for UI.
    * ``beat_positions`` – JSON string with beat timestamps.
    * ``date_added`` – Timestamp of when the track was first imported.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str = Field(index=True, unique=True)
    title: Optional[str] = Field(default=None, index=True)
    artist: Optional[str] = Field(default=None, index=True)
    album: Optional[str] = Field(default=None)
    genre: Optional[str] = Field(default=None)
    duration: Optional[float] = Field(default=None, description="seconds")
    bpm: Optional[float] = Field(default=None)
    musical_key: Optional[str] = Field(default=None)
    waveform_data: Optional[str] = Field(default=None, description="JSON string")
    beat_positions: Optional[str] = Field(default=None, description="JSON string")
    date_added: datetime = Field(default_factory=datetime.utcnow)
