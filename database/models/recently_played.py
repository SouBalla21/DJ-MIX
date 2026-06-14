"""Model for recently played tracks.

Each entry records when a track was played.  The ``played_at`` timestamp can be
used to query the most recent N tracks.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class RecentlyPlayed(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    track_id: int = Field(foreign_key="track.id", index=True)
    played_at: datetime = Field(default_factory=datetime.utcnow, index=True)
