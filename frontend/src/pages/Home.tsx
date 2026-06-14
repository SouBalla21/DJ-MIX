import React from "react";

// Placeholder component imports – they will be provided later in the project.
import Deck from "../components/Deck";
import Waveform from "../components/Waveform";
import TransportControls from "../components/TransportControls";
import Crossfader from "../components/Crossfader";
import EQPanel from "../components/EQPanel";
import TrackInfo from "../components/TrackInfo";
import Library from "../components/Library";
import PlaylistPanel from "../components/PlaylistPanel";
import SettingsDialog from "../components/SettingsDialog";

const sectionStyle: React.CSSProperties = {
  padding: "8px",
  boxSizing: "border-box",
};

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "8px",
  marginBottom: "16px",
};

const fullWidthStyle: React.CSSProperties = {
  width: "100%",
  textAlign: "center",
  marginBottom: "16px",
};

const Home: React.FC = () => {
  return (
    <div style={{ padding: "16px", fontFamily: "sans-serif" }}>
      {/* Decks */}
      <div style={gridStyle}>
        <section style={sectionStyle}>
          <Deck deckId="A" />
        </section>
        <section style={sectionStyle}>
          <Deck deckId="B" />
        </section>
      </div>

      {/* Waveforms */}
      <div style={gridStyle}>
        <section style={sectionStyle}>
          <Waveform deckId="A" />
        </section>
        <section style={sectionStyle}>
          <Waveform deckId="B" />
        </section>
      </div>

      {/* Track Info */}
      <div style={gridStyle}>
        <section style={sectionStyle}>
          <TrackInfo deckId="A" />
        </section>
        <section style={sectionStyle}>
          <TrackInfo deckId="B" />
        </section>
      </div>

      {/* Transport Controls */}
      <div style={gridStyle}>
        <section style={sectionStyle}>
          <TransportControls deckId="A" />
        </section>
        <section style={sectionStyle}>
          <TransportControls deckId="B" />
        </section>
      </div>

      {/* Crossfader */}
      <div style={fullWidthStyle}>
        <Crossfader />
      </div>

      {/* EQ Panel (shared) */}
      <div style={fullWidthStyle}>
        <EQPanel />
      </div>

      {/* Library and Playlist */}
      <div style={gridStyle}>
        <section style={sectionStyle}>
          <Library />
        </section>
        <section style={sectionStyle}>
          <PlaylistPanel />
        </section>
      </div>

      {/* Settings Dialog trigger */}
      <div style={fullWidthStyle}>
        <SettingsDialog />
      </div>
    </div>
  );
};

export default Home;