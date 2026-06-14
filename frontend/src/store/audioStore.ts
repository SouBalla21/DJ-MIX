// frontend/src/store/audioStore.ts

import { create } from "zustand";
import type { Track } from "../types/track";
import { audioWS } from "../services/websocket";

interface DeckState {
  loadedTrack: Track | null;
  playing: boolean;
  position: number;
  volume: number;
  rate: number;
}

interface MixerState {
  crossfader: number;
  masterVolume: number;
  cueVolume: number;
}

interface AudioState {
  deckA: DeckState;
  deckB: DeckState;
  mixer: MixerState;
}

interface AudioActions {
  // Deck A
  loadTrackA: (track: Track) => void;
  playA: () => void;
  pauseA: () => void;
  setVolumeA: (volume: number) => void;
  setRateA: (rate: number) => void;

  // Deck B
  loadTrackB: (track: Track) => void;
  playB: () => void;
  pauseB: () => void;
  setVolumeB: (volume: number) => void;
  setRateB: (rate: number) => void;

  // Mixer
  setCrossfader: (value: number) => void;
  setMasterVolume: (value: number) => void;
  setCueVolume: (value: number) => void;
}

export const useAudioStore = create<AudioState & AudioActions>((set) => ({
  // Initial Deck A
  deckA: {
    loadedTrack: null,
    playing: false,
    position: 0,
    volume: 1,
    rate: 1,
  },

  // Initial Deck B
  deckB: {
    loadedTrack: null,
    playing: false,
    position: 0,
    volume: 1,
    rate: 1,
  },

  // Initial Mixer
  mixer: {
    crossfader: 0,
    masterVolume: 1,
    cueVolume: 1,
  },

  // Deck A Actions
  loadTrackA: (track) => {
    set((state) => ({
      deckA: {
        ...state.deckA,
        loadedTrack: track,
        playing: false,
        position: 0,
      },
    }));

//    void audioWS.sendCommand(
//      "load_track",
//      {
//        deck: "A",
//        filepath: track.filepath,
//      }
//    );
  },

  playA: () => {
    set((state) => ({
      deckA: {
        ...state.deckA,
        playing: true,
      },
    }));

//       void audioWS.sendCommand(
//      "play",
//      {
//        deck: "A",
//      }
//    );
  },

  pauseA: () => {
    set((state) => ({
      deckA: {
        ...state.deckA,
        playing: false,
      },
    }));

//       void audioWS.sendCommand(
//      "pause",
//      {
//        deck: "A",
//      }
//    );
  },

  setVolumeA: (volume) => {
    set((state) => ({
      deckA: {
        ...state.deckA,
        volume,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_volume",
    //     {
    //       deck: "A",
    //       volume,
    //     }
    //   );
  },

  setRateA: (rate) => {
    set((state) => ({
      deckA: {
        ...state.deckA,
        rate,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_rate",
    //     {
    //       deck: "A",
    //       rate,
    //     }
    //   );
  },

  // Deck B Actions
  loadTrackB: (track) => {
    set((state) => ({
      deckB: {
        ...state.deckB,
        loadedTrack: track,
        playing: false,
        position: 0,
      },
    }));

    //   void audioWS.sendCommand(
    //     "load_track",
    //     {
    //       deck: "B",
    //       filepath: track.filepath,
    //     }
    //   );
  },

  playB: () => {
    set((state) => ({
      deckB: {
        ...state.deckB,
        playing: true,
      },
    }));

    //   void audioWS.sendCommand(
    //     "play",
    //     {
    //       deck: "B",
    //     }
    //   );
  },

  pauseB: () => {
    set((state) => ({
      deckB: {
        ...state.deckB,
        playing: false,
      },
    }));

    //   void audioWS.sendCommand(
    //     "pause",
    //     {
    //       deck: "B",
    //     }
    //   );
  },

  setVolumeB: (volume) => {
    set((state) => ({
      deckB: {
        ...state.deckB,
        volume,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_volume",
    //     {
    //       deck: "B",
    //       volume,
    //     }
    //   );
  },

  setRateB: (rate) => {
    set((state) => ({
      deckB: {
        ...state.deckB,
        rate,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_rate",
    //     {
    //       deck: "B",
    //       rate,
    //     }
    //   );
  },

  // Mixer Actions
  setCrossfader: (crossfader) => {
    set((state) => ({
      mixer: {
        ...state.mixer,
        crossfader,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_crossfader",
    //     {
    //       value: crossfader,
    //     }
    //   );
  },

  setMasterVolume: (masterVolume) => {
    set((state) => ({
      mixer: {
        ...state.mixer,
        masterVolume,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_master_volume",
    //     {
    //       value: masterVolume,
    //     }
    //   );
  },

  setCueVolume: (cueVolume) => {
    set((state) => ({
      mixer: {
        ...state.mixer,
        cueVolume,
      },
    }));

    //   void audioWS.sendCommand(
    //     "set_cue_volume",
    //     {
    //       value: cueVolume,
    //     }
    //   );
  },
}));