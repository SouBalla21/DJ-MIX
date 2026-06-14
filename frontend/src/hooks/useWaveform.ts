// frontend/src/hooks/useWaveform.ts
//
// Hook to extract waveform data from a Track object.
// Returns the waveform array and a flag indicating whether data is present.
// Uses useMemo to avoid recomputing unless the track reference changes.

import { useMemo } from "react";
import { Track } from "../types/track";

export interface UseWaveformResult {
  /** Normalised waveform data (array of numbers). */
  waveform: number[];
  /** True when the track contains waveform_data. */
  hasWaveform: boolean;
}

/**
 * Extract waveform information from a track.
 * @param track The track object or null.
 * @returns waveform array and presence flag.
 */
export function useWaveform(track: Track | null): UseWaveformResult {
  return useMemo(() => {
    if (!track) {
      return { waveform: [], hasWaveform: false };
    }
    const data = (track as any).waveform_data as unknown;
    if (Array.isArray(data) && data.length > 0) {
      // Assume the data is an array of numbers.
      return { waveform: data as number[], hasWaveform: true };
    }
    return { waveform: [], hasWaveform: false };
  }, [track]);
}
