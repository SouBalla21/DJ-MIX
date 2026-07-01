// frontend/src/hooks/useAudioWebSocket.ts
//
// Custom React hook that manages the lifecycle of the global audio WebSocket
// singleton (audioWS). It connects when the component mounts, disconnects on
// unmount, and exposes simple connection state and any error that occurs.
//
// The hook does not perform any UI rendering or business logic – it just
// wires the WebSocket events to React state.

import { useEffect, useState, useCallback } from "react";
import { audioWS } from "../services/websocket";
import { useAudioStore } from "../store/audioStore";

/**
 * Hook exposing the WebSocket connection status.
 *
 * Returned tuple:
 *   - connected: boolean – true when the socket is open.
 *   - error: string | null – last error message, if any.
 *   - register callbacks (optional) – callers can subscribe to events.
 */
export function useAudioWebSocket() {
  const [connected, setConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Stable callbacks that forward to the component state.
  const handleOpen = useCallback(() => {
    setConnected(true);
    useAudioStore.getState().setConnected(true);
    setError(null);
    useAudioStore.getState().setError(null);
    void useAudioStore.getState().refreshDevices().catch((err) => {
      useAudioStore
        .getState()
        .setError(err instanceof Error ? err.message : String(err));
    });
  }, []);

  const handleClose = useCallback(() => {
    setConnected(false);
    useAudioStore.getState().setConnected(false);
  }, []);

  const handleError = useCallback((e: any) => {
    // The error may be an Error object or a string.
    const msg = e?.message ?? String(e);
    setError(msg);
    useAudioStore.getState().setError(msg);
    setConnected(false);
    useAudioStore.getState().setConnected(false);
  }, []);

  useEffect(() => {
    // Register event listeners.
    if (typeof audioWS.onOpen === "function") audioWS.onOpen(handleOpen);
    if (typeof audioWS.onClose === "function") audioWS.onClose(handleClose);
    if (typeof audioWS.onError === "function") audioWS.onError(handleError);
    if (typeof audioWS.onMessage === "function") {
      audioWS.onMessage(useAudioStore.getState().handleEngineMessage);
    }

    // Initiate connection.
    void audioWS
      .connect()
      .then(() => {
        if (audioWS.isConnected()) handleOpen();
      })
      .catch(handleError);

    return undefined;
    // Dependencies are stable because callbacks are memoized.
  }, [handleOpen, handleClose, handleError]);

  useEffect(() => {
    if (!connected) return undefined;

    const pollEngineState = async () => {
      try {
        const [position, meters] = await Promise.all([
          audioWS.sendCommand("get_position"),
          audioWS.sendCommand("get_meters"),
        ]);

        const store = useAudioStore.getState();
        store.handleEngineMessage({ type: "position", payload: position });
        store.handleEngineMessage({ type: "meters", payload: meters });
        store.setError(null);
      } catch (err) {
        useAudioStore
          .getState()
          .setError(err instanceof Error ? err.message : String(err));
      }
    };

    void pollEngineState();
    const intervalId = window.setInterval(() => {
      void pollEngineState();
    }, 250);

    return () => window.clearInterval(intervalId);
  }, [connected]);

  // Expose the state and also a way to manually register additional handlers.
  const register = {
    onOpen: (cb: () => void) => {
      if (typeof audioWS.onOpen === "function") audioWS.onOpen(cb);
    },
    onClose: (cb: () => void) => {
      if (typeof audioWS.onClose === "function") audioWS.onClose(cb);
    },
    onError: (cb: (err: any) => void) => {
      if (typeof audioWS.onError === "function") audioWS.onError(cb);
    },
  } as const;

  return { connected, error, register };
}
