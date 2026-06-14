"""CRUD package for the DJ platform’s database models.

This ``__init__`` re‑exports the most‑commonly‑used functions from the individual
CRUD modules, providing a convenient single import point:

    from database.crud import (
        add_track,
        get_track_by_id,
        get_track_by_filepath,
        search_tracks,
        update_track,
        delete_track,
        list_tracks,
        # … playlist, favorites, recently played, settings helpers …
    )
"""

# Track CRUD
from .track_crud import (
    add_track,
    get_track_by_id,
    get_track_by_filepath,
    search_tracks,
    update_track,
    delete_track,
    list_tracks,
)

# Playlist CRUD
from .playlist_crud import (
    create_playlist,
    rename_playlist,
    delete_playlist,
    get_playlist,
    list_playlists,
    add_track_to_playlist,
    remove_track_from_playlist,
    reorder_playlist,
)

# Favorites CRUD
from .favorites_crud import (
    add_favorite,
    remove_favorite,
    is_favorite,
    list_favorites,
)

# Recently‑played CRUD
from .recently_played_crud import (
    add_recent_track,
    list_recent_tracks,
    clear_history,
)

# Settings CRUD
from .settings_crud import (
    get_settings,
    update_settings,
    reset_settings,
)

# Define the public API of this package
__all__ = [
    # Track
    "add_track",
    "get_track_by_id",
    "get_track_by_filepath",
    "search_tracks",
    "update_track",
    "delete_track",
    "list_tracks",
    # Playlist
    "create_playlist",
    "rename_playlist",
    "delete_playlist",
    "get_playlist",
    "list_playlists",
    "add_track_to_playlist",
    "remove_track_from_playlist",
    "reorder_playlist",
    # Favorites
    "add_favorite",
    "remove_favorite",
    "is_favorite",
    "list_favorites",
    # Recently‑played
    "add_recent_track",
    "list_recent_tracks",
    "clear_history",
    # Settings
    "get_settings",
    "update_settings",
    "reset_settings",
]