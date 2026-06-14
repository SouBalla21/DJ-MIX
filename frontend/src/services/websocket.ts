/**
 * Centralized WebSocket client for communicating with the audio engine.
 *
 * Implements a request/response pattern using unique request IDs.
 * Completely independent of React and state management.
 */

export interface WSRequest {
  type: string;
  payload?: Record<string, unknown>;
  request_id?: string;
}

export interface WSResponse {
  type: string;
  payload?: unknown;
  request_id?: string;
}

class AudioWebSocketClient {
  private static readonly URL = "ws://localhost:8000/ws/audio";
  private static readonly DEFAULT_TIMEOUT = 5000;

  private ws: WebSocket | null = null;
  private connected = false;

  private requestCounter = 0;

  private pendingRequests = new Map<
    string,
    {
      resolve: (value: unknown) => void;
      reject: (reason?: unknown) => void;
      timeoutId: number;
    }
  >();

  private openListeners: Array<() => void> = [];
  private closeListeners: Array<() => void> = [];
  private errorListeners: Array<(event: Event) => void> = [];

  /**
   * Connect to the WebSocket server.
   */
  public connect(): Promise<void> {
    if (this.isConnected()) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(AudioWebSocketClient.URL);

      const handleOpen = () => {
        this.connected = true;

        this.ws?.addEventListener("message", this.handleMessage);
        this.ws?.addEventListener("close", this.handleClose);
        this.ws?.addEventListener("error", this.handleError);

        this.openListeners.forEach((cb) => cb());

        resolve();
      };

      const handleError = (event: Event) => {
        this.cleanupSocket();

        this.errorListeners.forEach((cb) => cb(event));

        reject(new Error("Failed to connect to audio WebSocket"));
      };

      this.ws.addEventListener("open", handleOpen, { once: true });
      this.ws.addEventListener("error", handleError, { once: true });
    });
  }

  /**
   * Disconnect from the server.
   */
  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
    }

    this.cleanupSocket();
  }

  /**
   * Whether the socket is currently connected.
   */
  public isConnected(): boolean {
    return (
      this.connected &&
      this.ws !== null &&
      this.ws.readyState === WebSocket.OPEN
    );
  }

  /**
   * Register callbacks.
   */
  public onOpen(callback: () => void): void {
    this.openListeners.push(callback);
  }

  public onClose(callback: () => void): void {
    this.closeListeners.push(callback);
  }

  public onError(callback: (event: Event) => void): void {
    this.errorListeners.push(callback);
  }

  /**
   * Send a command and await its response.
   */
  public async sendCommand(
    type: string,
    payload?: Record<string, unknown>
  ): Promise<unknown> {
    if (!this.isConnected() || !this.ws) {
      throw new Error("WebSocket is not connected");
    }

    const requestId = `req_${this.requestCounter++}`;

    const message: WSRequest = {
      type,
      payload,
      request_id: requestId,
    };

    return new Promise((resolve, reject) => {
      const timeoutId = window.setTimeout(() => {
        this.pendingRequests.delete(requestId);

        reject(
          new Error(
            `WebSocket request timed out after ${AudioWebSocketClient.DEFAULT_TIMEOUT} ms`
          )
        );
      }, AudioWebSocketClient.DEFAULT_TIMEOUT);

      this.pendingRequests.set(requestId, {
        resolve,
        reject,
        timeoutId,
      });

      try {
        this.ws!.send(JSON.stringify(message));
      } catch (err) {
        clearTimeout(timeoutId);
        this.pendingRequests.delete(requestId);
        reject(err);
      }
    });
  }

  /**
   * Handle incoming messages.
   */
  private handleMessage = (event: MessageEvent): void => {
    let response: WSResponse;

    try {
      response = JSON.parse(event.data);
    } catch {
      // Ignore malformed JSON.
      return;
    }

    const requestId = response.request_id;

    if (!requestId) {
      return;
    }

    const pending = this.pendingRequests.get(requestId);

    if (!pending) {
      return;
    }

    clearTimeout(pending.timeoutId);

    this.pendingRequests.delete(requestId);

    if (response.type === "response") {
      pending.resolve(response.payload);
    } else if (response.type === "error") {
      const message =
        typeof response.payload === "object" &&
        response.payload !== null &&
        "message" in response.payload
          ? String((response.payload as { message: unknown }).message)
          : "Unknown server error";

      pending.reject(new Error(message));
    } else {
      pending.resolve(response.payload);
    }
  };

  /**
   * Handle socket closure.
   */
  private handleClose = (): void => {
    this.connected = false;

    this.closeListeners.forEach((cb) => cb());

    this.pendingRequests.forEach(({ reject, timeoutId }) => {
      clearTimeout(timeoutId);

      reject(new Error("WebSocket connection closed"));
    });

    this.pendingRequests.clear();
  };

  /**
   * Handle socket errors.
   */
  private handleError = (event: Event): void => {
    this.errorListeners.forEach((cb) => cb(event));
  };

  /**
   * Clean up socket resources.
   */
  private cleanupSocket(): void {
    if (this.ws) {
      this.ws.removeEventListener("message", this.handleMessage);
      this.ws.removeEventListener("close", this.handleClose);
      this.ws.removeEventListener("error", this.handleError);

      this.ws = null;
    }

    this.connected = false;

    this.pendingRequests.forEach(({ reject, timeoutId }) => {
      clearTimeout(timeoutId);

      reject(new Error("WebSocket client disposed"));
    });

    this.pendingRequests.clear();
  }
}

/**
 * Singleton instance used throughout the app.
 */
export const audioWS = new AudioWebSocketClient();