"""
FastAPI WebSocket endpoint that forwards client commands to the audio engine.

The endpoint:

- Accepts JSON messages from the client.
- Dispatches each message to the appropriate handler registered in the
  audio_engine.ws_server.AudioEngineWSServer instance.
- Sends a JSON response (or an error) back to the client.
- Uses the reusable ConnectionManager.
- Maintains a persistent connection until the client disconnects.

All playback logic lives inside the audio engine; this module is only a
JSON ↔ Python adapter with error handling.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .connection_manager import ConnectionManager
from audio_engine.ws_server import WSMessage, get_ws_server

router = APIRouter()

_manager = ConnectionManager()


def _error_message(
    message: str,
    request_id: str | None = None,
) -> str:
    """
    Create an error response compatible with the audio-engine protocol.
    """
    return WSMessage(
        type="error",
        payload={"message": message},
        request_id=request_id,
    ).to_json()


def _response_message(
    payload: Any,
    request_id: str | None = None,
) -> str:
    """
    Create a success response compatible with the audio-engine protocol.
    """
    return WSMessage(
        type="response",
        payload=payload,
        request_id=request_id,
    ).to_json()


@router.websocket("/ws/audio")
async def audio_websocket_endpoint(
    websocket: WebSocket,
) -> None:
    """
    Persistent WebSocket endpoint used by the frontend.

    Expected message format:

    {
        "type": "<command>",
        "payload": {...},
        "request_id": "optional-id"
    }

    Commands are forwarded to handlers registered by the audio engine.
    """

    await _manager.connect(websocket)

    # Singleton AudioEngineWSServer instance
    ws_server = get_ws_server()

    try:
        while True:
            raw_msg = await websocket.receive_text()

            # ---------------------------------------------------------
            # Parse incoming message
            # ---------------------------------------------------------
            try:
                msg = WSMessage.from_json(raw_msg)
            except Exception:
                await websocket.send_text(
                    _error_message("Invalid JSON")
                )
                continue

            cmd = msg.type
            payload = msg.payload or {}
            request_id = msg.request_id

            # ---------------------------------------------------------
            # Find handler
            # ---------------------------------------------------------
            handler = ws_server.handlers.get(cmd)

            if handler is None:
                await websocket.send_text(
                    _error_message(
                        f"Unknown command: {cmd}",
                        request_id,
                    )
                )
                continue

            # ---------------------------------------------------------
            # Execute command
            # ---------------------------------------------------------
            try:
                result = await handler(payload)

                await websocket.send_text(
                    _response_message(
                        result,
                        request_id,
                    )
                )

            except Exception as exc:
                await websocket.send_text(
                    _error_message(
                        str(exc),
                        request_id,
                    )
                )

    except WebSocketDisconnect:
        # Normal client disconnect
        pass

    finally:
        # Remove websocket from manager
        _manager.disconnect(websocket)