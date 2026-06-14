// frontend/src/components/Waveform.tsx
//
// Minimal waveform visualizer for a deck. It reads the currently loaded
// track from the audio store and, if the track contains a `waveform_data`
// array, renders a simple SVG polyline. When no track is loaded (or the
// track lacks waveform data) a placeholder message is shown.
//
// No WebSocket, API calls, or business logic are performed – this component
// is purely presentational.

import React from "react";
import { useAudioStore } from "../store/audioStore";
import type { Track } from "../types/track";

export interface WaveformProps {
  /** Deck identifier – "A" or "B" */
  deckId: "A" | "B";
}

/** Helper to select the correct deck slice from the store. */
function selectDeck(state: ReturnType<typeof useAudioStore.getState>, deckId: "A" | "B") {
  return deckId === "A" ? state.deckA : state.deckB;
}

/** Render a basic SVG waveform for the track on the given deck. */
const Waveform: React.FC<WaveformProps> = ({ deckId }) => {
  // Pull only the loadedTrack field – everything else is unnecessary here.
  const loadedTrack = useAudioStore((state) =>
  deckId === "A"
    ? state.deckA.loadedTrack
    : state.deckB.loadedTrack
);

  // If there is no track or no waveform data, show a placeholder.
  if (!loadedTrack?.waveform_data || loadedTrack.waveform_data.length === 0) {
    return <div>No waveform available</div>;
  }

  return (
  <div
    style={{
      border: "1px solid #ddd",
      padding: "1rem",
      margin: "0.5rem",
    }}
  >
    {loadedTrack
      ? `Waveform for ${loadedTrack.title ?? "Unknown Track"}`
      : "No waveform available"}
  </div>
);
 
};

export default Waveform;