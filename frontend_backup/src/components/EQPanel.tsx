// frontend/src/components/EQPanel.tsx
//
// Simple EQ panel for a DJ deck. The component maintains its own local
// state for low, mid, and high gain settings. No backend or WebSocket
// communication occurs – it is purely a UI element.
//
// Props:
//   deckId – "A" or "B" – used only for display purposes.
//
// Each slider ranges from -1 to 1 with a step of 0.01.
// The current numeric value is shown next to the slider.

import React, { useState, ChangeEvent } from "react";

export interface EQPanelProps {
  /** Identifier of the deck – "A" or "B" */
  deckId: "A" | "B";
}

const EQPanel: React.FC<EQPanelProps> = ({ deckId }) => {
  // Local state for the three EQ bands.
  const [low, setLow] = useState<number>(0);
  const [mid, setMid] = useState<number>(0);
  const [high, setHigh] = useState<number>(0);

  // Generic change handler creator to avoid repetition.
  const makeHandler = (setter: React.Dispatch<React.SetStateAction<number>>) =>
    (e: ChangeEvent<HTMLInputElement>) => {
      setter(parseFloat(e.target.value));
    };

  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: "1rem",
        margin: "0.5rem",
        maxWidth: "300px",
      }}
    >
      <h3>Deck {deckId} EQ</h3>
      {/* Low band */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
        <label style={{ width: "40px" }}>Low</label>
        <input
          type="range"
          min={-1}
          max={1}
          step={0.01}
          value={low}
          onChange={makeHandler(setLow)}
          style={{ flexGrow: 1, margin: "0 0.5rem" }}
        />
        <span>{low.toFixed(2)}</span>
      </div>

      {/* Mid band */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: "0.5rem" }}>
        <label style={{ width: "40px" }}>Mid</label>
        <input
          type="range"
          min={-1}
          max={1}
          step={0.01}
          value={mid}
          onChange={makeHandler(setMid)}
          style={{ flexGrow: 1, margin: "0 0.5rem" }}
        />
        <span>{mid.toFixed(2)}</span>
      </div>

      {/* High band */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <label style={{ width: "40px" }}>High</label>
        <input
          type="range"
          min={-1}
          max={1}
          step={0.01}
          value={high}
          onChange={makeHandler(setHigh)}
          style={{ flexGrow: 1, margin: "0 0.5rem" }}
        />
        <span>{high.toFixed(2)}</span>
      </div>
    </div>
  );
};

export default EQPanel;
