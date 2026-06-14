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
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    setConnected(false);
  }, []);

  const handleError = useCallback((e: any) => {
    // The error may be an Error object or a string.
    const msg = e?.message ?? String(e);
    setError(msg);
    setConnected(false);
  }, []);

  useEffect(() => {
    // Register event listeners.
    if (typeof audioWS.onOpen === "function") audioWS.onOpen(handleOpen);
    if (typeof audioWS.onClose === "function") audioWS.onClose(handleClose);
    if (typeof audioWS.onError === "function") audioWS.onError(handleError);

    // Initiate connection.
    if (typeof audioWS.connect === "function") audioWS.connect();
    else if (typeof audioWS.start === "function") audioWS.start(); // fallback

    // Cleanup on unmount.
    return () => {
      if (typeof audioWS.disconnect === "function") audioWS.disconnect();
      else if (typeof audioWS.close === "function") audioWS.close(); // fallback
    };
    // Dependencies are stable because callbacks are memoized.
  }, [handleOpen, handleClose, handleError]);

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
