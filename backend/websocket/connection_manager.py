"""Connection manager for FastAPI WebSocket handling.

This utility maintains a set of active WebSocket connections, provides helpers to
connect/disconnect clients, send a message to a single client, and broadcast a
message to all connected clients.  It gracefully handles clients that disconnect
unexpectedly – any send error results in the connection being removed to avoid
memory leaks.
"""

from __future__ import annotations

from typing import List

from fastapi import WebSocket


class ConnectionManager:
    """Track active WebSocket connections and provide messaging utilities.

    Typical usage in a FastAPI endpoint:

    ```python
    manager = ConnectionManager()

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                data = await ws.receive_text()
                await manager.broadcast(f"Client said: {data}")
        except WebSocketDisconnect:
            await manager.disconnect(ws)
    ```
    """

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []

    # ---------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------
    @property
    def active_connections(self) -> List[WebSocket]:
        """Return a shallow copy of the list of active connections.

        A copy is returned to prevent callers from inadvertently mutating the
        internal list.
        """
        return list(self._connections)

    # ---------------------------------------------------------------------
    # Connection lifecycle
    # ---------------------------------------------------------------------
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection and store it.

        The call awaits ``websocket.accept()`` before adding the connection to the
        internal list.
        """
        await websocket.accept()
        self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from the active list.

        If the websocket is not present, the method does nothing – this covers
        cases where a disconnect is triggered by a send failure.
        """
        if websocket in self._connections:
            self._connections.remove(websocket)
        # Ensure the socket is closed; ignore errors if it is already closed.
        try:
            await websocket.close()
        except Exception:
            # Silently ignore close errors – the socket is already gone.
            pass

    # ---------------------------------------------------------------------
    # Messaging helpers
    # ---------------------------------------------------------------------
    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a text message to a single client.

        If sending fails (e.g., the client has disconnected), the connection is
        removed to keep the manager's state consistent.
        """
        try:
            await websocket.send_text(message)
        except Exception:
            # Assume the connection is broken – clean it up.
            await self.disconnect(websocket)

    async def broadcast(self, message: str) -> None:
        """Broadcast a text message to all active connections.

        Sends the message to each connection individually; if a send raises an
        exception, that connection is removed but broadcasting continues for the
        remaining clients.
        """
        # Iterate over a copy to allow safe mutation during the loop.
        for connection in list(self._connections):
            try:
                await connection.send_text(message)
            except Exception:
                # Remove the broken connection and continue.
                await self.disconnect(connection)
