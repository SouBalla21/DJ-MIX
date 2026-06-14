// Playlist management UI. It fetches the list of playlists from the API,
// lets the user create a new playlist, and delete existing ones.
// No WebSocket or business‑logic code is included – just straightforward
// data fetching and rendering.

import React, { useEffect, useState, ChangeEvent, FormEvent } from "react";
import {
  getPlaylists,
  createPlaylist,
  deletePlaylist,
} from "../services/api";

interface Playlist {
  /** Unique identifier for the playlist (type depends on backend) */
  id: string | number;
  /** Human‑readable name */
  name: string;
  /** Optional description */
  description?: string;
}

/** PlaylistPanel component – displays, creates and deletes playlists. */
export default function PlaylistPanel() {
  // Component UI state
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState<string>("");

  /** Load playlists from the backend. */
  const fetchPlaylists = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPlaylists();
      // Assume API returns an array of playlist objects compatible with the Playlist.
      setPlaylists(data as Playlist[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getPlaylists();
        if (!cancelled) setPlaylists(data as Playlist[]);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  /** Handle creation of a new playlist. */
  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    try {
      await createPlaylist(newName.trim());
      setNewName("");
      // Refresh list after successful creation
      await fetchPlaylists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  /** Handle deletion of a playlist. */
  const handleDelete = async (id: string | number) => {
    try {
      await deletePlaylist(id);
      // Refresh list after deletion
      await fetchPlaylists();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  // Rendering
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div
  style={{
    border: "1px solid #ccc",
    padding: "1rem",
    margin: "0.5rem",
  }}
>
      <h3>Playlists</h3>

      {/* New playlist form */}
      <form
  onSubmit={handleCreate}
  style={{ marginBottom: "1rem" }}
>
        <input
          type="text"
          placeholder="New playlist name"
          value={newName}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setNewName(e.target.value)
          }
          style={{ marginRight: "0.5rem" }}
        />
        <button type="submit">Create</button>
      </form>

      {/* List of playlists */}
      {playlists.length === 0 ? (
        <div>No playlists</div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {playlists.map((pl) => (
            <li
              key={pl.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.25rem 0",
                borderBottom: "1px solid #eee",
              }}
            >
              <div>
                <strong>{pl.name}</strong>
                {pl.description && (
                  <div
  style={{
    fontSize: "0.9em",
    color: "#555",
  }}
>
                    {pl.description}
                  </div>
                )}
              </div>
              <button onClick={() => handleDelete(pl.id)}>Delete</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}