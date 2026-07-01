'''
Audio Engine Entrypoint

Wires together device management, decoding, deck transports, mixer, and WebSocket command server.
Implements real‑time safe PortAudio callback, engine state, and command handlers.
'''  # noqa: E261

import asyncio
import logging
import threading
from pathlib import Path
from dataclasses import asdict

import numpy as np

from .device_manager import get_device_manager
from .decoder import get_decoder, is_supported_format
from .buffer import DeckTransport
from .mixer import DJMixer
from .ws_server import get_ws_server, AudioEngineWSServer
from .analysis import get_cached_analysis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global real‑time lock – protects shared state accessed from the audio
# callback and from WebSocket command handlers. The callback holds this lock
# only for the few microseconds required to generate one block.
# ---------------------------------------------------------------------------
_rt_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Engine components – created lazily by `initialize_engine()`.
# ---------------------------------------------------------------------------
_device_manager = None          # type: get_device_manager
_decoder = None                # type: get_decoder
_deck_a: DeckTransport = None
_deck_b: DeckTransport = None
_mixer: DJMixer = None
_ws_server: AudioEngineWSServer = None

# ---------------------------------------------------------------------------
# Helper – generate a single block of mixed audio.
# Returns (master_out, cue_out) as float32 (frames, 2).
# ---------------------------------------------------------------------------
def _process_block(frames: int):
    # Deck processing
    deck_a_audio = _deck_a.process_audio(frames)
    deck_b_audio = _deck_b.process_audio(frames)

    # Mixer combines decks, applies cross‑fader, EQ and routes to master/cue
    master_out, cue_out = _mixer.process(deck_a_audio, deck_b_audio)
    return master_out, cue_out

# ---------------------------------------------------------------------------
# PortAudio callbacks – one for each output stream (master & cue).
# The callback runs in the real‑time audio thread; it must not block.
# ---------------------------------------------------------------------------
def _make_callback(is_master: bool):
    def callback(outdata, frames, time, status):  # pragma: no cover – exercised at runtime
        if status:
            logger.warning(f"PortAudio status: {status}")
        # Minimal lock – only protects read‑only state used by the decks/mixer.
        with _rt_lock:
            master, cue = _process_block(frames)
            outdata[:] = master if is_master else cue
    return callback

# ---------------------------------------------------------------------------
# WebSocket command handlers – all async, but they acquire the same lock to
# guarantee thread‑safety with the real‑time callback.
# ---------------------------------------------------------------------------
async def _load_track(payload: dict):
    deck_id = payload.get('deck')  # Expected 'A' or 'B'
    filepath = payload.get('filepath')
    if deck_id not in ('A', 'B') or not filepath:
        raise ValueError('load_track requires "deck" (A/B) and "filepath"')

    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Track not found: {filepath}")
    if not is_supported_format(path):
        raise ValueError(f"Unsupported audio format: {path.suffix}")

    # Decode
    audio_data, sr = await asyncio.to_thread(_decoder.decode_file, path)

    # Load into selected deck
    deck = _deck_a if deck_id == 'A' else _deck_b
    with _rt_lock:
        deck.load_track(audio_data, sr)

    # Analyse (bpm, duration) – cached for speed
    duration = float(deck.state.duration / deck.sample_rate)
    asyncio.create_task(_push_track_analysis(deck_id, path, audio_data, sr, duration))
    await _ws_server.push_track_loaded(deck_id, str(path), duration, 0.0)
    return {'status': 'ok'}


async def _push_track_analysis(deck_id: str, path: Path, audio_data: np.ndarray, sr: int, duration: float):
    try:
        analysis = await asyncio.to_thread(get_cached_analysis, str(path), audio_data, sr)
        bpm = float(analysis.get('bpm', 0.0) or 0.0)
    except Exception as exc:
        logger.warning("Track analysis failed for %s: %s", path, exc)
        bpm = 0.0

    await _ws_server.push_track_loaded(deck_id, str(path), duration, bpm)

async def _play(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    with _rt_lock:
        deck.play()
    return {'status': 'ok'}

async def _pause(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    with _rt_lock:
        deck.pause()
    return {'status': 'ok'}

async def _stop(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    with _rt_lock:
        deck.stop()
    return {'status': 'ok'}

async def _seek(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    position = float(payload.get('position', 0.0))
    with _rt_lock:
        deck.seek(position)
    return {'status': 'ok'}

async def _set_volume(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    volume = float(payload.get('volume', 1.0))
    with _rt_lock:
        deck.set_volume(volume)
    return {'status': 'ok'}

async def _set_rate(payload: dict):
    deck = _deck_a if payload.get('deck') == 'A' else _deck_b
    rate = float(payload.get('rate', 1.0))
    with _rt_lock:
        deck.set_rate(rate)
    return {'status': 'ok'}

async def _set_eq(payload: dict):
    deck_id = payload.get('deck')
    deck = _deck_a if deck_id == 'A' else _deck_b
    low = payload.get('low')
    mid = payload.get('mid')
    high = payload.get('high')
    with _rt_lock:
        deck.set_eq(low, mid, high)
        _mixer.set_deck_eq(deck_id, deck.state.eq_low, deck.state.eq_mid, deck.state.eq_high)
    return {'status': 'ok'}

async def _set_crossfader(payload: dict):
    value = float(payload.get('value', 0.5))
    with _rt_lock:
        _mixer.set_crossfader(value)
    return {'status': 'ok'}

async def _set_master_volume(payload: dict):
    value = float(payload.get('value', 1.0))
    with _rt_lock:
        _mixer.set_master_volume(value)
    return {'status': 'ok'}

async def _set_cue_volume(payload: dict):
    value = float(payload.get('value', 1.0))
    with _rt_lock:
        _mixer.set_cue_volume(value)
    return {'status': 'ok'}

async def _set_deck_cue(payload: dict):
    deck_id = payload.get('deck')
    active = bool(payload.get('active', False))
    with _rt_lock:
        _mixer.set_deck_cue(deck_id, active)
    return {'status': 'ok'}

async def _set_devices(payload: dict):
    master_idx = payload.get('master')
    cue_idx = payload.get('cue')
    if master_idx is not None:
        _device_manager.set_master_device(int(master_idx))
    if cue_idx is not None:
        _device_manager.set_cue_device(int(cue_idx))
    # Restart streams with new device config
    with _rt_lock:
        _device_manager.close_streams()
        _device_manager.open_streams(_make_callback(True), _make_callback(False))
        _device_manager.start_streams()
    return {'status': 'ok'}

async def _get_devices(_: dict):
    return {
        'devices': [asdict(device) for device in _device_manager.list_output_devices()],
        'master': asdict(_device_manager.master_device) if _device_manager.master_device else None,
        'cue': asdict(_device_manager.cue_device) if _device_manager.cue_device else None,
    }

async def _get_position(_: dict):
    return {
        'deck_a': {
            'position': float(_deck_a.get_position_seconds()),
            'duration': float(_deck_a.state.duration / _deck_a.sample_rate),
            'playing': bool(_deck_a.state.playing),
        },
        'deck_b': {
            'position': float(_deck_b.get_position_seconds()),
            'duration': float(_deck_b.state.duration / _deck_b.sample_rate),
            'playing': bool(_deck_b.state.playing),
        },
    }

async def _get_meters(_: dict):
    return _mixer.get_meter_levels()

async def _get_state(_: dict):
    return {
        'mixer': asdict(_mixer.state),
        'deck_a': asdict(_deck_a.state),
        'deck_b': asdict(_deck_b.state),
        'devices': {
            'master': _device_manager.master_device.name if _device_manager.master_device else None,
            'cue': _device_manager.cue_device.name if _device_manager.cue_device else None,
        },
    }

# ---------------------------------------------------------------------------
# Engine initialisation – creates components, registers handlers and starts
# the PortAudio streams and WebSocket server.
# ---------------------------------------------------------------------------
async def initialize_engine():
    global _device_manager, _decoder, _deck_a, _deck_b, _mixer, _ws_server

    logger.info('Initializing audio engine')

    # Device manager – picks default devices and opens streams
    _device_manager = get_device_manager()
    _device_manager.auto_select_devices()

    # Decoder (global singleton)
    _decoder = get_decoder()

    # Deck transports – use same sample rate as device manager output
    sample_rate = _device_manager.get_output_config()['master']['samplerate']
    _deck_a = DeckTransport('A', sample_rate)
    _deck_b = DeckTransport('B', sample_rate)

    # Mixer
    blocksize = _device_manager.get_output_config()['master']['blocksize']
    _mixer = DJMixer(sample_rate, blocksize)

    # WebSocket server
    _ws_server = await get_ws_server()

    # Register command handlers
    handlers = {
        'load_track': _load_track,
        'play': _play,
        'pause': _pause,
        'stop': _stop,
        'seek': _seek,
        'set_volume': _set_volume,
        'set_rate': _set_rate,
        'set_eq': _set_eq,
        'set_crossfader': _set_crossfader,
        'set_master_volume': _set_master_volume,
        'set_cue_volume': _set_cue_volume,
        'set_deck_cue': _set_deck_cue,
        'set_devices': _set_devices,
        'get_devices': _get_devices,
        'get_position': _get_position,
        'get_meters': _get_meters,
        'get_state': _get_state,
    }
    for cmd, fn in handlers.items():
        _ws_server.register_handler(cmd, fn)

    # Open streams with callbacks (master & cue)
    master_cb = _make_callback(True)
    cue_cb = _make_callback(False)
    _device_manager.open_streams(master_cb, cue_cb)

    # Start streams
    _device_manager.start_streams()

    # Start WebSocket server
    await _ws_server.start()
    logger.info('Audio engine started')

# ---------------------------------------------------------------------------
# Graceful shutdown helper.
# ---------------------------------------------------------------------------
async def shutdown_engine():
    logger.info('Shutting down audio engine')
    if _ws_server:
        await _ws_server.stop()
    if _device_manager:
        _device_manager.stop_streams()
        _device_manager.close_streams()

# ---------------------------------------------------------------------------
# Entry‑point for `python -m audio_engine.main`.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        asyncio.run(initialize_engine())
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
    finally:
        # Ensure resources are cleaned up even if the event loop exits early.
        try:
            asyncio.run(shutdown_engine())
        except Exception as e:
            logger.error(f'Error during shutdown: {e}')
