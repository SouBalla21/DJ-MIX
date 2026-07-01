import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { useAudioWebSocket } from "../hooks/useAudioWebSocket";
import { getTracks, uploadTracks } from "../services/api";
import { useAudioStore, type AudioDevice } from "../store/audioStore";
import type { Track } from "../types/track";

const formatTime = (seconds: number) => {
  if (!Number.isFinite(seconds) || seconds <= 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const safe = (value: unknown, fallback = "Unknown") =>
  value ? String(value) : fallback;

const meterWidth = (db: number) =>
  `${Math.max(0, Math.min(100, ((db + 60) / 60) * 100))}%`;

function DeviceSelect({
  label,
  value,
  devices,
  onChange,
}: {
  label: string;
  value: AudioDevice | null;
  devices: AudioDevice[];
  onChange: (index: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select
        value={value?.index ?? ""}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        <option value="" disabled>
          No device
        </option>
        {devices.map((device) => (
          <option key={device.index} value={device.index}>
            {device.name} ({device.hostapi})
          </option>
        ))}
      </select>
    </label>
  );
}

function DeckPanel({ deckId }: { deckId: "A" | "B" }) {
  const deck = useAudioStore((state) =>
    deckId === "A" ? state.deckA : state.deckB
  );
  const playA = useAudioStore((state) => state.playA);
  const playB = useAudioStore((state) => state.playB);
  const pauseA = useAudioStore((state) => state.pauseA);
  const pauseB = useAudioStore((state) => state.pauseB);
  const seekA = useAudioStore((state) => state.seekA);
  const seekB = useAudioStore((state) => state.seekB);
  const setVolumeA = useAudioStore((state) => state.setVolumeA);
  const setVolumeB = useAudioStore((state) => state.setVolumeB);
  const setRateA = useAudioStore((state) => state.setRateA);
  const setRateB = useAudioStore((state) => state.setRateB);
  const setCueA = useAudioStore((state) => state.setCueA);
  const setCueB = useAudioStore((state) => state.setCueB);
  const setEqA = useAudioStore((state) => state.setEqA);
  const setEqB = useAudioStore((state) => state.setEqB);

  const play = deckId === "A" ? playA : playB;
  const pause = deckId === "A" ? pauseA : pauseB;
  const seek = deckId === "A" ? seekA : seekB;
  const setVolume = deckId === "A" ? setVolumeA : setVolumeB;
  const setRate = deckId === "A" ? setRateA : setRateB;
  const setCue = deckId === "A" ? setCueA : setCueB;
  const setEq = deckId === "A" ? setEqA : setEqB;

  const duration = deck.duration || deck.loadedTrack?.duration || 0;
  const progress = duration > 0 ? (deck.position / duration) * 100 : 0;

  return (
    <section className={`deck deck-${deckId.toLowerCase()}`}>
      <div className="deck-header">
        <div>
          <p className="eyebrow">Deck {deckId}</p>
          <h2>{safe(deck.loadedTrack?.title, "No track loaded")}</h2>
          <p className="artist">{safe(deck.loadedTrack?.artist, "Select from library")}</p>
        </div>
        <span className={deck.playing ? "status live" : "status"}>
          {deck.playing ? "Playing" : "Paused"}
        </span>
      </div>

      <div className="waveform">
        <div className="wave-bars" aria-hidden="true">
          {Array.from({ length: 72 }).map((_, index) => (
            <span
              key={index}
              style={{
                height: `${22 + ((index * 17 + deckId.charCodeAt(0)) % 48)}%`,
              }}
            />
          ))}
        </div>
        <div className="playhead" style={{ width: `${Math.min(100, progress)}%` }} />
      </div>

      <div className="time-row">
        <span>{formatTime(deck.position)}</span>
        <input
          type="range"
          min={0}
          max={Math.max(1, duration)}
          step={0.1}
          value={Math.min(deck.position, Math.max(1, duration))}
          onChange={(event) => void seek(Number(event.target.value))}
        />
        <span>{formatTime(duration)}</span>
      </div>

      <div className="transport">
        <button
          className="primary"
          onClick={() => void (deck.playing ? pause() : play())}
          disabled={!deck.loadedTrack}
          title={deck.playing ? "Pause" : "Play"}
        >
          {deck.playing ? "Pause" : "Play"}
        </button>
        <button
          className={deck.cue ? "cue active" : "cue"}
          onClick={() => void setCue(!deck.cue)}
          disabled={!deck.loadedTrack}
        >
          Cue
        </button>
      </div>

      <div className="controls-grid">
        <label className="field">
          <span>Volume {(deck.volume * 100).toFixed(0)}%</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={deck.volume}
            onChange={(event) => void setVolume(Number(event.target.value))}
          />
        </label>
        <label className="field">
          <span>Rate {deck.rate.toFixed(2)}x</span>
          <input
            type="range"
            min={0.5}
            max={2}
            step={0.01}
            value={deck.rate}
            onChange={(event) => void setRate(Number(event.target.value))}
          />
        </label>
      </div>

      <div className="eq-strip">
        {(["low", "mid", "high"] as const).map((band) => (
          <label className="field" key={band}>
            <span>{band.toUpperCase()} {deck.eq[band].toFixed(2)}</span>
            <input
              type="range"
              min={0}
              max={2}
              step={0.01}
              value={deck.eq[band]}
              onChange={(event) =>
                void setEq(band, Number(event.target.value))
              }
            />
          </label>
        ))}
      </div>
    </section>
  );
}

export default function Home() {
  const { connected, error: socketError } = useAudioWebSocket();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [loadingLibrary, setLoadingLibrary] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);

  const {
    mixer,
    meters,
    devices,
    masterDevice,
    cueDevice,
    error,
    loadTrackA,
    loadTrackB,
    setCrossfader,
    setMasterVolume,
    setCueVolume,
    setDevices,
    refreshDevices,
  } = useAudioStore();

  async function loadLibrary(cancelled = false) {
      try {
        const data = await getTracks();
        if (!cancelled) setTracks(data);
        if (!cancelled) setLibraryError(null);
      } catch (err) {
        if (!cancelled) {
          setLibraryError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!cancelled) setLoadingLibrary(false);
      }
    }

  useEffect(() => {
    let cancelled = false;
    void loadLibrary();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleFileImport(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setImporting(true);
    setImportMessage(null);
    setLibraryError(null);

    try {
      const result = await uploadTracks(files);
      const imported = result.imported ?? {};
      setImportMessage(
        `Added ${imported.added ?? 0}, skipped ${imported.skipped ?? 0}, errors ${imported.errors ?? 0}`
      );
      setLoadingLibrary(true);
      await loadLibrary();
    } catch (err) {
      setLibraryError(err instanceof Error ? err.message : String(err));
    } finally {
      setImporting(false);
      event.target.value = "";
    }
  }

  const connectionText = useMemo(() => {
    if (connected) return "Audio engine connected";
    if (socketError || error) return "Audio engine unavailable";
    return "Connecting to audio engine";
  }, [connected, socketError, error]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Real-Time DJ Mixing</p>
          <h1>DJ Mix</h1>
        </div>
        <div className={connected ? "engine-pill online" : "engine-pill"}>
          <span />
          {connectionText}
        </div>
      </header>

      {(error || socketError) && (
        <div className="alert">{error || socketError}</div>
      )}

      <div className="deck-grid">
        <DeckPanel deckId="A" />
        <DeckPanel deckId="B" />
      </div>

      <section className="mixer-board">
        <div className="master-section">
          <h2>Mixer</h2>
          <label className="field wide">
            <span>Crossfader</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={mixer.crossfader}
              onChange={(event) => void setCrossfader(Number(event.target.value))}
            />
            <div className="range-labels">
              <span>A</span>
              <span>Center</span>
              <span>B</span>
            </div>
          </label>
          <div className="controls-grid">
            <label className="field">
              <span>Master {(mixer.masterVolume * 100).toFixed(0)}%</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={mixer.masterVolume}
                onChange={(event) => void setMasterVolume(Number(event.target.value))}
              />
            </label>
            <label className="field">
              <span>Cue {(mixer.cueVolume * 100).toFixed(0)}%</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={mixer.cueVolume}
                onChange={(event) => void setCueVolume(Number(event.target.value))}
              />
            </label>
          </div>
        </div>

        <div className="meter-section">
          <h2>Output</h2>
          {[
            ["Master L", meters.masterL],
            ["Master R", meters.masterR],
            ["Cue L", meters.cueL],
            ["Cue R", meters.cueR],
          ].map(([label, db]) => (
            <div className="meter" key={label}>
              <span>{label}</span>
              <div><i style={{ width: meterWidth(Number(db)) }} /></div>
              <b>{Number(db).toFixed(0)} dB</b>
            </div>
          ))}
        </div>

        <div className="device-section">
          <div className="section-heading">
            <h2>Routing</h2>
            <button onClick={() => void refreshDevices()}>Refresh</button>
          </div>
          <DeviceSelect
            label="Master output"
            value={masterDevice}
            devices={devices}
            onChange={(index) => void setDevices(index, cueDevice?.index ?? null)}
          />
          <DeviceSelect
            label="Cue output"
            value={cueDevice}
            devices={devices}
            onChange={(index) => void setDevices(masterDevice?.index ?? null, index)}
          />
        </div>
      </section>

      <section className="library-panel">
        <div className="section-heading">
          <h2>Track Library</h2>
          <div className="library-actions">
            <label className="file-button">
              {importing ? "Importing..." : "Browse files"}
              <input
                type="file"
                accept="audio/*,.mp3,.wav,.flac,.m4a,.ogg,.aac,.aiff,.aif"
                multiple
                onChange={handleFileImport}
                disabled={importing}
              />
            </label>
            <span>{tracks.length} tracks</span>
          </div>
        </div>
        {loadingLibrary && <p className="muted">Loading library...</p>}
        {libraryError && <p className="alert">{libraryError}</p>}
        {importMessage && <p className="success">{importMessage}</p>}
        {!loadingLibrary && tracks.length === 0 && (
          <p className="muted">Library is empty. Use Browse files to add songs.</p>
        )}
        <div className="track-list">
          {tracks.map((track) => (
            <article className="track-row" key={track.id}>
              <div>
                <strong>{safe(track.title)}</strong>
                <span>
                  {safe(track.artist)} · {formatTime(track.duration ?? 0)}
                  {track.bpm ? ` · ${Math.round(track.bpm)} BPM` : ""}
                </span>
              </div>
              <div className="load-actions">
                <button onClick={() => void loadTrackA(track)}>Load A</button>
                <button onClick={() => void loadTrackB(track)}>Load B</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
