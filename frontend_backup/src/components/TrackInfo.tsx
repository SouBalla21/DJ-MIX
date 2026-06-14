import React from "react";
import { useAudioStore } from "../store/audioStore";
import { Track } from "../types/track";

export interface TrackInfoProps {
  /** Deck identifier – "A" or "B" */
  deckId: "A" | "B";
}

/** Helper to fetch the correct deck slice from the store. */
function selectDeck(
  state: ReturnType<typeof useAudioStore.getState>,
  deckId: "A" | "B"
) {
  return deckId === "A" ? state.deckA : state.deckB;
}

/** Render track metadata for the given deck. */
const TrackInfo: React.FC<TrackInfoProps> = ({ deckId }) => {
  const { loadedTrack } = useAudioStore((state) => {
    const deck = selectDeck(state, deckId);
    return { loadedTrack: deck.loadedTrack as Track | null };
  });

  if (!loadedTrack) {
    return <div>No track loaded</div>;
  }

  // Helper to safely read a string field.
  const val = (field: unknown) =>
    field === undefined || field === null || field === ""
      ? "Unknown"
      : String(field);

  // Duration handling – assume seconds or a pre‑formatted string.
  const formatDuration = (dur: unknown) => {
    if (typeof dur === "number") {
      const mins = Math.floor(dur / 60);
      const secs = Math.round(dur % 60)
        .toString()
        .padStart(2, "0");
      return `${mins}:${secs}`;
    }
    return val(dur);
  };

  return (
    <div style={{ border: "1px solid #ccc", padding: "1rem", margin: "0.5rem" }}>
      <h3>Deck {deckId} Track Info</h3>
      <p>
        <strong>Title:</strong> {val(loadedTrack.title)}
      </p>
      <p>
        <strong>Artist:</strong> {val(loadedTrack.artist)}
      </p>
      <p>
        <strong>Album:</strong> {val(loadedTrack.album)}
      </p>
      <p>
        <strong>Genre:</strong> {val(loadedTrack.genre)}
      </p>
      <p>
        <strong>BPM:</strong> {val(loadedTrack.bpm)}
      </p>
      <p>
        <strong>Key:</strong> {val(loadedTrack.key)}
      </p>
      <p>
        <strong>Duration:</strong> {formatDuration(loadedTrack.duration)}
      </p>
    </div>
  );
};

export default TrackInfo;