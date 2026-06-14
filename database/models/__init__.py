"""SQLModel definitions for the DJ platform.

All models are deliberately simple and use appropriate indexes for fast look‑ups.
"""

from .track import Track
from .favorites import FavoriteTrack
from .playlist import Playlist, PlaylistTrack
from .recently_played import RecentlyPlayed
from .settings import Settings

__all__ = [
    "Track",
    "Playlist",
    "PlaylistTrack",
    "RecentlyPlayed",
    "FavoriteTrack",
    "Settings",
]

# Alias for backward compatibility (init_db expects ``Favorite``)
Favorite = FavoriteTrack
