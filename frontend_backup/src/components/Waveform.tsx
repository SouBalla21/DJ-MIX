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
import { Track } from "../types/track";

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
  const { loadedTrack } = useAudioStore((state) => {
    const deck = selectDeck(state, deckId);
    return { loadedTrack: deck.loadedTrack as Track | null };
  });

  // If there is no track or no waveform data, show a placeholder.
  if (!loadedTrack?.waveform_data || loadedTrack.waveform_data.length === 0) {
    return <div>No waveform available</div>;
  }

  // Normalise waveform data (assume values are in the range [-1, 1]).
  const data: number[] = loadedTrack.waveform_data;
  const width = 200; // pixels – arbitrary simple size
  const height = 50; // pixels

  const points = data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      // Flip Y because SVG origin is top‑left.
      const y = height / 2 - (value * height) / 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} style={{ border: "1px solid #ddd" }}>
      <polyline points={points} fill="none" stroke="black" strokeWidth={1} />
    </svg>
  );
};

export default Waveform;
