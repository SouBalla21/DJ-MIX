export interface Playlist {
  id: number;
  name: string;
  description?: string;
  date_created: string; // ISO 8601 timestamp
}

export interface PlaylistTrack {
  playlist_id: number;
  track_id: number;
  position: number; // zero‑based order in the playlist
}