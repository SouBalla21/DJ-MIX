// Minimal track library view. It fetches the list of tracks from the API,
// shows a loading / error state, and lets the user click a track to load it
// into Deck A via the audio store.
//
// No WebSocket, business logic, or styling beyond basic layout is included.

import React, { useEffect, useState } from "react";
import { getTracks } from "../services/api";
import { useAudioStore } from "../store/audioStore";
import type { Track } from "../types/track";

export default function Library() {
  // Local UI state
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Store action to load a track into Deck A
  const loadTrackA = useAudioStore((state) => state.loadTrackA);

  // Fetch the library once on mount
  useEffect(() => {
    let cancelled = false;

    const fetch = async () => {
      try {
        const data = await getTracks();
        if (!cancelled) {
          setTracks(data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetch();

    // Cleanup in case the component unmounts while fetching
    return () => {
      cancelled = true;
    };
  }, []);

  // Render states
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (tracks.length === 0) return <div>Library is empty</div>;

  // Helper to safely display metadata
  const safe = (value: unknown): string =>
  value ? String(value) : "Unknown";

  return (
    <div style={{ border: "1px solid #ccc", padding: "1rem", margin: "0.5rem" }}>
      <h3>Library</h3>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {tracks.map((track, idx) => (
          <li
            key={track.id ?? idx}
            onClick={() => loadTrackA(track)}
            style={{
              cursor: "pointer",
              padding: "0.25rem 0",
              borderBottom: "1px solid #eee",
            }}
          >
            {safe(track.title)} — {safe(track.artist)}
          </li>
        ))}
      </ul>
    </div>
  );
}