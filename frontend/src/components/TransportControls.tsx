// frontend/src/components/TransportControls.tsx
//
// Simple transport control panel for a DJ deck. It shows Play / Pause
// buttons and the current playback state. All interactions are routed
// through the Zustand audio store – no direct WebSocket or API calls.

import React from "react";
import { useAudioStore } from "../store/audioStore";

export interface TransportControlsProps {
  /** Deck identifier – "A" or "B" */
  deckId: "A" | "B";
}

/** Helper to pick the correct deck slice from the store. */
function selectDeck(state: ReturnType<typeof useAudioStore.getState>, deckId: "A" | "B") {
  return deckId === "A" ? state.deckA : state.deckB;
}

/** Transport controls – play/pause buttons and a status label. */
const TransportControls: React.FC<TransportControlsProps> = ({ deckId }) => {
  // Current playback state for the deck.
  const playing = useAudioStore((state) =>
  deckId === "A"
    ? state.deckA.playing
    : state.deckB.playing
);

  // Action dispatchers – choose the correct store action based on deck.
  const play = useAudioStore((state) => (deckId === "A" ? state.playA : state.playB));
  const pause = useAudioStore((state) => (deckId === "A" ? state.pauseA : state.pauseB));

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <button onClick={play} disabled={playing}>
        Play
      </button>
      <button onClick={pause} disabled={!playing}>
        Pause
      </button>
      <span>{playing ? "Playing" : "Paused"}</span>
    </div>
  );
};

export default TransportControls;
