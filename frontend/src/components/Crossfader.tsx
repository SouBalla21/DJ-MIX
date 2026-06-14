// frontend/src/components/Crossfader.tsx
//
// Simple cross‑fader control for the DJ app.
// Reads the current crossfader value from the audio store and provides a
// horizontal range input for the user to adjust it. The value is sent back
// to the store via the `setCrossfader` action.
//
// No WebSocket, API, or business logic is performed here – it is a pure UI
// component.

import React, { ChangeEvent } from "react";
import { useAudioStore } from "../store/audioStore";

/** Crossfader component – renders a slider that controls the global mixer */
const Crossfader: React.FC = () => {
  // Pull current value and the setter from the store.
  const crossfader = useAudioStore(
  (state) => state.mixer.crossfader
);

const setCrossfader = useAudioStore(
  (state) => state.setCrossfader
);

  // Handler for slider changes – value comes as a string, convert to number.
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setCrossfader(value);
  };

  return (
    <div style={{ width: "100%", maxWidth: "300px", margin: "1rem auto" }}>
      <label htmlFor="crossfader-slider" style={{ display: "block", textAlign: "center" }}>
        Crossfader: {crossfader.toFixed(2)}
      </label>
      <input
        id="crossfader-slider"
        type="range"
        min={-1}
        max={1}
        step={0.01}
        value={crossfader}
        onChange={handleChange}
        style={{ width: "100%" }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.9rem" }}>
        <span>Deck A ←</span>
        <span>Center</span>
        <span>→ Deck B</span>
      </div>
    </div>
  );
};

export default Crossfader;
