"""
WebSocket Command Server
Asyncio-based WebSocket server for controlling the audio engine from the backend.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


@dataclass
class WSMessage:
    """WebSocket message structure."""
    type: str
    payload: dict = None
    request_id: str = None

    def to_json(self) -> str:
        data = {'type': self.type}
        if self.payload is not None:
            data['payload'] = self.payload
        if self.request_id is not None:
            data['request_id'] = self.request_id
        return json.dumps(data)

    @classmethod
    def from_json(cls, text: str) -> 'WSMessage':
        data = json.loads(text)
        return cls(
            type=data.get('type', ''),
            payload=data.get('payload'),
            request_id=data.get('request_id')
        )


class AudioEngineWSServer:
    """WebSocket server for audio engine commands and state streaming.

    Additional method ``push_analysis`` allows broadcasting asynchronous analysis results.
    """
    """Extended with analysis result broadcast."""
    """
    WebSocket server for audio engine commands and state streaming.

    Commands (from backend):
    - load_track: Load track into deck
    - play/pause/stop: Transport control
    - seek: Seek to position
    - set_volume: Deck volume
    - set_rate: Playback rate (pitch)
    - set_eq: EQ gains
    - set_crossfader: Crossfader position
    - set_master_volume: Master output volume
    - set_cue_volume: Cue output volume
    - set_deck_cue: Cue button (pre-fader listen)
    - set_devices: Change Master/Cue output devices

    State pushes (to backend):
    - state: Full state snapshot
    - position: Playback position update
    - meters: Level meter values
    - track_loaded: Track load confirmation
    - error: Error message
    """

    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.server: Optional[websockets.WebSocketServer] = None
        self.clients: Set[WebSocketServerProtocol] = set()

        # Command handlers (set by audio engine)
        self.handlers: Dict[str, Callable] = {}

        # State for periodic updates
        self._state_push_task: Optional[asyncio.Task] = None
        self._push_interval = 1/30  # 30 Hz

    def register_handler(self, command: str, handler: Callable):
        """Register a command handler."""
        self.handlers[command] = handler

    async def start(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
        except OSError as exc:
            logger.warning(
                "Standalone audio WebSocket ws://%s:%s unavailable; continuing with FastAPI WebSocket: %s",
                self.host,
                self.port,
                exc,
            )
            return

        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

        # Start state push task
        self._state_push_task = asyncio.create_task(self._push_state_loop())

    async def stop(self):
        """Stop the WebSocket server."""
        if self._state_push_task:
            self._state_push_task.cancel()
            try:
                await self._state_push_task
            except asyncio.CancelledError:
                pass

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Close all client connections
        for client in self.clients:
            await client.close()
        self.clients.clear()

        logger.info("WebSocket server stopped")

    async def _handle_connection(self, websocket: WebSocketServerProtocol):
        """Handle new client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            # Send initial state
            await self._send_state(websocket)

            # Process messages
            async for message in websocket:
                await self._handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def _handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming message from client."""
        try:
            msg = WSMessage.from_json(message)
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON")
            return

        logger.debug(f"Received: {msg.type}")

        # Handle request
        if msg.type in self.handlers:
            try:
                result = await self.handlers[msg.type](msg.payload or {})
                if msg.request_id:
                    await websocket.send(WSMessage(
                        type='response',
                        payload=result,
                        request_id=msg.request_id
                    ).to_json())
            except Exception as e:
                logger.error(f"Handler error for {msg.type}: {e}")
                if msg.request_id:
                    await websocket.send(WSMessage(
                        type='error',
                        payload={'message': str(e)},
                        request_id=msg.request_id
                    ).to_json())
        else:
            logger.warning(f"Unknown command: {msg.type}")
            if msg.request_id:
                await websocket.send(WSMessage(
                    type='error',
                    payload={'message': f'Unknown command: {msg.type}'},
                    request_id=msg.request_id
                ).to_json())

    async def _send_state(self, websocket: WebSocketServerProtocol):
        """Send full state to a specific client."""
        if 'get_state' in self.handlers:
            state = await self.handlers['get_state']({})
            await websocket.send(WSMessage(type='state', payload=state).to_json())

    async def _send_error(self, websocket: WebSocketServerProtocol, message: str):
        """Send error to client."""
        await websocket.send(WSMessage(type='error', payload={'message': message}).to_json())

    async def broadcast(self, message: WSMessage):
        """Broadcast message to all connected clients."""
        if not self.clients:
            return

        text = message.to_json()
        disconnected = set()

        for client in self.clients:
            try:
                await client.send(text)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.add(client)

        # Clean up disconnected
        self.clients -= disconnected

    async def push_position(self, deck_a_pos: float, deck_b_pos: float,
                            deck_a_dur: float, deck_b_dur: float,
                            deck_a_playing: bool, deck_b_playing: bool):
        """Push position update to all clients."""
        await self.broadcast(WSMessage(type='position', payload={
            'deck_a': {'position': deck_a_pos, 'duration': deck_a_dur, 'playing': deck_a_playing},
            'deck_b': {'position': deck_b_pos, 'duration': deck_b_dur, 'playing': deck_b_playing},
        }))

    async def push_meters(self, master_l: float, master_r: float,
                          cue_l: float, cue_r: float):
        """Push meter levels to all clients."""
        await self.broadcast(WSMessage(type='meters', payload={
            'master': {'left': master_l, 'right': master_r},
            'cue': {'left': cue_l, 'right': cue_r},
        }))

    async def push_track_loaded(self, deck: str, filepath: str, duration: float, bpm: float):
        """Notify track loaded."""
        await self.broadcast(WSMessage(type='track_loaded', payload={
            'deck': deck,
            'filepath': filepath,
            'duration': duration,
            'bpm': bpm,
        }))

    async def _push_state_loop(self):
        """Periodic state push loop (position + meters)."""
        while True:
            try:
                await asyncio.sleep(self._push_interval)

                if 'get_position' in self.handlers and self.clients:
                    pos_data = await self.handlers['get_position']({})
                    await self.broadcast(WSMessage(type='position', payload=pos_data))

                if 'get_meters' in self.handlers and self.clients:
                    meter_data = await self.handlers['get_meters']({})
                    await self.broadcast(WSMessage(type='meters', payload=meter_data))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"State push error: {e}")


# Global server instance
_ws_server: Optional[AudioEngineWSServer] = None


async def get_ws_server(host: str = 'localhost', port: int = 8765) -> AudioEngineWSServer:
    """Get or create global WebSocket server."""
    global _ws_server
    if _ws_server is None:
        _ws_server = AudioEngineWSServer(host, port)
    return _ws_server
