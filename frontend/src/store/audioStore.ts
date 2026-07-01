import { create } from "zustand";
import type { Track } from "../types/track";
import { audioWS, type WSResponse } from "../services/websocket";

export interface AudioDevice {
  index: number;
  name: string;
  hostapi: string;
  max_output_channels: number;
  default_samplerate: number;
  is_default_output: boolean;
}

interface DeckState {
  loadedTrack: Track | null;
  playing: boolean;
  position: number;
  duration: number;
  volume: number;
  rate: number;
  cue: boolean;
  eq: {
    low: number;
    mid: number;
    high: number;
  };
}

interface MixerState {
  crossfader: number;
  masterVolume: number;
  cueVolume: number;
}

interface MeterState {
  masterL: number;
  masterR: number;
  cueL: number;
  cueR: number;
}

interface AudioState {
  deckA: DeckState;
  deckB: DeckState;
  mixer: MixerState;
  meters: MeterState;
  devices: AudioDevice[];
  masterDevice: AudioDevice | null;
  cueDevice: AudioDevice | null;
  connected: boolean;
  error: string | null;
}

interface AudioActions {
  setConnected: (connected: boolean) => void;
  setError: (error: string | null) => void;
  handleEngineMessage: (message: WSResponse) => void;
  refreshDevices: () => Promise<void>;
  setDevices: (master: number | null, cue: number | null) => Promise<void>;
  loadTrackA: (track: Track) => Promise<void>;
  loadTrackB: (track: Track) => Promise<void>;
  playA: () => Promise<void>;
  playB: () => Promise<void>;
  pauseA: () => Promise<void>;
  pauseB: () => Promise<void>;
  seekA: (position: number) => Promise<void>;
  seekB: (position: number) => Promise<void>;
  setVolumeA: (volume: number) => Promise<void>;
  setVolumeB: (volume: number) => Promise<void>;
  setRateA: (rate: number) => Promise<void>;
  setRateB: (rate: number) => Promise<void>;
  setCueA: (active: boolean) => Promise<void>;
  setCueB: (active: boolean) => Promise<void>;
  setEqA: (band: keyof DeckState["eq"], value: number) => Promise<void>;
  setEqB: (band: keyof DeckState["eq"], value: number) => Promise<void>;
  setCrossfader: (value: number) => Promise<void>;
  setMasterVolume: (value: number) => Promise<void>;
  setCueVolume: (value: number) => Promise<void>;
}

const emptyDeck = (): DeckState => ({
  loadedTrack: null,
  playing: false,
  position: 0,
  duration: 0,
  volume: 1,
  rate: 1,
  cue: false,
  eq: { low: 1, mid: 1, high: 1 },
});

async function send(type: string, payload?: Record<string, unknown>) {
  try {
    await audioWS.sendCommand(type, payload);
    useAudioStore.getState().setError(null);
  } catch (error) {
    useAudioStore
      .getState()
      .setError(error instanceof Error ? error.message : String(error));
    throw error;
  }
}

function linearToEqGain(value: number) {
  return Math.max(0, Math.min(2, value));
}

export const useAudioStore = create<AudioState & AudioActions>((set, get) => ({
  deckA: emptyDeck(),
  deckB: emptyDeck(),
  mixer: {
    crossfader: 0.5,
    masterVolume: 1,
    cueVolume: 1,
  },
  meters: {
    masterL: -60,
    masterR: -60,
    cueL: -60,
    cueR: -60,
  },
  devices: [],
  masterDevice: null,
  cueDevice: null,
  connected: false,
  error: null,

  setConnected: (connected) => set({ connected }),
  setError: (error) => set({ error }),

  handleEngineMessage: (message) => {
    const payload = message.payload as any;
    if (message.type === "position" && payload) {
      set((state) => ({
        deckA: {
          ...state.deckA,
          position: payload.deck_a?.position ?? state.deckA.position,
          duration: payload.deck_a?.duration ?? state.deckA.duration,
          playing: payload.deck_a?.playing ?? state.deckA.playing,
        },
        deckB: {
          ...state.deckB,
          position: payload.deck_b?.position ?? state.deckB.position,
          duration: payload.deck_b?.duration ?? state.deckB.duration,
          playing: payload.deck_b?.playing ?? state.deckB.playing,
        },
      }));
    }

    if (message.type === "meters" && payload) {
      set({
        meters: {
          masterL: payload.master_l ?? payload.master?.left ?? -60,
          masterR: payload.master_r ?? payload.master?.right ?? -60,
          cueL: payload.cue_l ?? payload.cue?.left ?? -60,
          cueR: payload.cue_r ?? payload.cue?.right ?? -60,
        },
      });
    }

    if (message.type === "state" && payload) {
      set((state) => ({
        mixer: {
          ...state.mixer,
          crossfader: payload.mixer?.crossfader ?? state.mixer.crossfader,
          masterVolume: payload.mixer?.master_volume ?? state.mixer.masterVolume,
          cueVolume: payload.mixer?.cue_volume ?? state.mixer.cueVolume,
        },
        connected: true,
      }));
    }

    if (message.type === "error" && payload?.message) {
      set({ error: String(payload.message) });
    }
  },

  refreshDevices: async () => {
    const result = (await audioWS.sendCommand("get_devices")) as {
      devices: AudioDevice[];
      master: AudioDevice | null;
      cue: AudioDevice | null;
    };
    set({
      devices: result.devices ?? [],
      masterDevice: result.master ?? null,
      cueDevice: result.cue ?? null,
      error: null,
    });
  },

  setDevices: async (master, cue) => {
    await send("set_devices", { master, cue });
    await get().refreshDevices();
  },

  loadTrackA: async (track) => {
    set((state) => ({ deckA: { ...state.deckA, loadedTrack: track, playing: false, position: 0 } }));
    await send("load_track", { deck: "A", filepath: track.filepath });
  },
  loadTrackB: async (track) => {
    set((state) => ({ deckB: { ...state.deckB, loadedTrack: track, playing: false, position: 0 } }));
    await send("load_track", { deck: "B", filepath: track.filepath });
  },

  playA: async () => {
    set((state) => ({ deckA: { ...state.deckA, playing: true } }));
    await send("play", { deck: "A" });
  },
  playB: async () => {
    set((state) => ({ deckB: { ...state.deckB, playing: true } }));
    await send("play", { deck: "B" });
  },
  pauseA: async () => {
    set((state) => ({ deckA: { ...state.deckA, playing: false } }));
    await send("pause", { deck: "A" });
  },
  pauseB: async () => {
    set((state) => ({ deckB: { ...state.deckB, playing: false } }));
    await send("pause", { deck: "B" });
  },
  seekA: async (position) => {
    set((state) => ({ deckA: { ...state.deckA, position } }));
    await send("seek", { deck: "A", position });
  },
  seekB: async (position) => {
    set((state) => ({ deckB: { ...state.deckB, position } }));
    await send("seek", { deck: "B", position });
  },

  setVolumeA: async (volume) => {
    set((state) => ({ deckA: { ...state.deckA, volume } }));
    await send("set_volume", { deck: "A", volume });
  },
  setVolumeB: async (volume) => {
    set((state) => ({ deckB: { ...state.deckB, volume } }));
    await send("set_volume", { deck: "B", volume });
  },
  setRateA: async (rate) => {
    set((state) => ({ deckA: { ...state.deckA, rate } }));
    await send("set_rate", { deck: "A", rate });
  },
  setRateB: async (rate) => {
    set((state) => ({ deckB: { ...state.deckB, rate } }));
    await send("set_rate", { deck: "B", rate });
  },
  setCueA: async (active) => {
    set((state) => ({ deckA: { ...state.deckA, cue: active } }));
    await send("set_deck_cue", { deck: "A", active });
  },
  setCueB: async (active) => {
    set((state) => ({ deckB: { ...state.deckB, cue: active } }));
    await send("set_deck_cue", { deck: "B", active });
  },
  setEqA: async (band, value) => {
    const next = { ...get().deckA.eq, [band]: linearToEqGain(value) };
    set((state) => ({ deckA: { ...state.deckA, eq: next } }));
    await send("set_eq", { deck: "A", ...next });
  },
  setEqB: async (band, value) => {
    const next = { ...get().deckB.eq, [band]: linearToEqGain(value) };
    set((state) => ({ deckB: { ...state.deckB, eq: next } }));
    await send("set_eq", { deck: "B", ...next });
  },

  setCrossfader: async (crossfader) => {
    set((state) => ({ mixer: { ...state.mixer, crossfader } }));
    await send("set_crossfader", { value: crossfader });
  },
  setMasterVolume: async (masterVolume) => {
    set((state) => ({ mixer: { ...state.mixer, masterVolume } }));
    await send("set_master_volume", { value: masterVolume });
  },
  setCueVolume: async (cueVolume) => {
    set((state) => ({ mixer: { ...state.mixer, cueVolume } }));
    await send("set_cue_volume", { value: cueVolume });
  },
}));
