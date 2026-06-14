/**
 * Application user settings.
 *
 * Mirrors the backend `Settings` model with a few additional UI‑specific fields.
 * Optional fields correspond to nullable columns in the database.
 */
export interface Settings {
  /** Primary key (singleton row). */
  id: number;

  /** Master output gain (0.0 – 1.0). */
  master_volume: number;

  /** Cue (headphone) output gain (0.0 – 1.0). */
  cue_volume: number;

  /** Theme identifier, e.g., "light" or "dark". */
  theme: string;

  /** Curve used for the cross‑fader (e.g., "linear", "log", "exponential"). */
  crossfader_curve: string;

  /** Identifier for the selected master output device (optional). */
  master_device?: string;

  /** Identifier for the selected cue output device (optional). */
  cue_device?: string;

  /** Waveform zoom factor (optional). */
  waveform_zoom?: number;
}
