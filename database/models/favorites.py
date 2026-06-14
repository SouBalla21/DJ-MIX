"""FavoriteTrack model.

Stores a track marked as a favorite by the user, with the date it was added.
Uniqueness on ``track_id`` prevents duplicate favorites.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship

from .track import Track


class FavoriteTrack(SQLModel, table=True):
    """Association model for a user's favorite tracks.

    ``track_id`` is the primary key and also a foreign key to ``Track.id``.
    ``date_added`` records when the track was favorited.
    """

    track_id: Optional[int] = Field(
        default=None,
        primary_key=True,
        foreign_key="track.id",
        unique=True,
        index=True,
    )
    date_added: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationship back to the Track model for convenient eager loading.
    track: Optional[Track] = Relationship(back_populates="favorite")
