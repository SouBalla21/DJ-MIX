import React from "react";
import { useAudioStore } from "../store/audioStore";
import type { Track } from "../types/track";

export interface DeckProps {
  deckId: "A" | "B";
}

function selectDeck(
  state: ReturnType<typeof useAudioStore.getState>,
  deckId: "A" | "B"
) {
  return deckId === "A" ? state.deckA : state.deckB;
}

const Deck: React.FC<DeckProps> = ({ deckId }) => {
  const deck = useAudioStore((state) =>
  deckId === "A"
    ? state.deckA
    : state.deckB
);

const loadedTrack = deck.loadedTrack;
const playing = deck.playing;
const volume = deck.volume;
const rate = deck.rate;

  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: "1rem",
        margin: "0.5rem",
      }}
    >
      <h2>Deck {deckId}</h2>

      {loadedTrack ? (
        <div>
          <p>
            <strong>Title:</strong>{" "}
            {loadedTrack.title ?? "Unknown Title"}
          </p>

          <p>
            <strong>Artist:</strong>{" "}
            {loadedTrack.artist ?? "Unknown Artist"}
          </p>

          <p>
            <strong>Status:</strong>{" "}
            {playing ? "Playing" : "Paused"}
          </p>

          <p>
            <strong>Volume:</strong>{" "}
            {(volume * 100).toFixed(0)}%
          </p>

          <p>
            <strong>Rate:</strong>{" "}
            {rate.toFixed(2)}×
          </p>
        </div>
      ) : (
        <p>No track loaded.</p>
      )}
    </div>
  );
};

export default Deck;