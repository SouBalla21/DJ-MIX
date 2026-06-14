// Settings dialog for the DJ application.
// Fetches the current settings, lets the user edit them locally, and
// persists the changes via the API. No WebSocket or business‑logic code
// is performed here – it is a pure presentation / edit component.

import React, { useEffect, useState, ChangeEvent, FormEvent } from "react";
import { getSettings, updateSettings } from "../services/api";

/** Shape of the settings object returned by the backend. */
interface Settings {
  /** Overall output gain, 0‑1 */
  masterVolume: number;
  /** Cue volume, 0‑1 */
  cueVolume: number;
  /** UI theme name (e.g. "light" | "dark") */
  theme: string;
  /** Cross‑fader curve identifier (e.g. "linear", "log", "exp") */
  crossfaderCurve: string;
}

/** Settings dialog component. */
export default function SettingsDialog() {
  // UI state
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // --------------------------------------------------------------------
  // Fetch the settings once on mount
  // --------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    const fetch = async () => {
      try {
        const data = await getSettings();
        if (!cancelled) setSettings(data as Settings);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetch();

    return () => {
      cancelled = true;
    };
  }, []);

  // ----------------------------------------------------------
// Handlers for form fields
// ----------------------------------------------------------
const handleSliderChange =
  (field: keyof Settings) =>
  (e: ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);

    setSettings((prev) =>
      prev
        ? {
            ...prev,
            [field]: value,
          }
        : prev
    );
  };

const handleSelectChange =
  (field: keyof Settings) =>
  (e: ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;

    setSettings((prev) =>
      prev
        ? {
            ...prev,
            [field]: value,
          }
        : prev
    );
  };

  // --------------------------------------------------------------------
  // Save handler
  // --------------------------------------------------------------------
  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!settings) return;

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await updateSettings(settings);
      setSaveSuccess(true);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  // --------------------------------------------------------------------
  // Render
  // --------------------------------------------------------------------
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error loading settings: {error}</div>;
  if (!settings) return <div>No settings available.</div>;

  // Helper options – you can extend these as needed.
  const themeOptions = ["light", "dark"];
  const curveOptions = ["linear", "log", "exp"];

  return (
    <form
      onSubmit={handleSave}
      style={{
        border: "1px solid #ccc",
        padding: "1rem",
        maxWidth: "400px",
        margin: "0.5rem",
      }}
    >
      <h3>Settings</h3>

      {/* Master Volume */}
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Master Volume
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={settings.masterVolume}
            onChange={handleSliderChange("masterVolume")}
            style={{ width: "100%" }}
          />
          <span>{settings.masterVolume.toFixed(2)}</span>
        </label>
      </div>

      {/* Cue Volume */}
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Cue Volume
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={settings.cueVolume}
            onChange={handleSliderChange("cueVolume")}
            style={{ width: "100%" }}
          />
          <span>{settings.cueVolume.toFixed(2)}</span>
        </label>
      </div>

      {/* Theme */}
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Theme
          <select
            value={settings.theme}
            onChange={handleSelectChange("theme")}
            style={{ marginLeft: "0.5rem" }}
          >
            {themeOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Crossfader Curve */}
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Crossfader Curve
          <select
            value={settings.crossfaderCurve}
            onChange={handleSelectChange("crossfaderCurve")}
            style={{ marginLeft: "0.5rem" }}
          >
            {curveOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Save button & feedback */}
      <button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </button>
      {saveError && (
        <div style={{ color: "red", marginTop: "0.5rem" }}>
          Error saving: {saveError}
        </div>
      )}
      {saveSuccess && (
        <div style={{ color: "green", marginTop: "0.5rem" }}>
          Settings saved.
        </div>
      )}
    </form>
  );
}