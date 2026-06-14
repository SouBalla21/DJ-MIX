export interface Track {
  id: number;
  filepath: string;
  title?: string;
  artist?: string;
  album?: string;
  genre?: string;
  duration?: number;      // seconds
  bpm?: number;
  musical_key?: string;
  waveform_data?: string; // JSON string or similar representation
  beat_positions?: string; // JSON string or similar representation
  date_added: string;      // ISO 8601 timestamp
}