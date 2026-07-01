"""
Ring Buffer & Deck Transport
Lock-free circular buffers for each deck with pitch-independent playback.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
import threading
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeckState:
    """Current playback state of a deck."""
    playing: bool = False
    position: float = 0.0      # Position in samples (at engine sample rate)
    duration: float = 0.0      # Total duration in samples
    rate: float = 1.0          # Playback rate (0.5 to 2.0 for ±50% pitch)
    volume: float = 1.0        # Deck volume (0.0 to 1.0)
    cue_active: bool = False   # Cue button pressed (pre-fader listen)
    eq_low: float = 1.0        # Low EQ gain (0.0 to 2.0, 1.0 = flat)
    eq_mid: float = 1.0        # Mid EQ gain
    eq_high: float = 1.0       # High EQ gain


class RingBuffer:
    """
    Lock-free ring buffer for audio samples.

    Uses NumPy array with atomic read/write indices.
    Supports variable-rate reading via linear interpolation.
    """

    def __init__(self, capacity: int, channels: int = 2, dtype=np.float32):
        """
        Initialize ring buffer.

        Args:
            capacity: Number of frames (samples per channel)
            channels: Number of audio channels (2 for stereo)
            dtype: Sample data type (float32 recommended)
        """
        self.capacity = capacity
        self.channels = channels
        self.dtype = dtype
        self._buffer = np.zeros((capacity, channels), dtype=dtype)
        self._write_pos = 0
        self._frames_written = 0
        self._lock = threading.Lock()  # Only for write operations

    def write(self, data: np.ndarray) -> int:
        """
        Write frames to buffer. Returns number of frames written.

        Handles wrap-around automatically. Thread-safe for single writer.
        """
        if data.ndim == 1:
            data = data[:, np.newaxis]
        if data.shape[1] != self.channels:
            raise ValueError(f"Expected {self.channels} channels, got {data.shape[1]}")

        frames = data.shape[0]
        if frames > self.capacity:
            # Buffer too small - truncate (shouldn't happen with proper sizing)
            data = data[-self.capacity:]
            frames = self.capacity

        with self._lock:
            end_pos = self._write_pos + frames
            if end_pos <= self.capacity:
                # No wrap
                self._buffer[self._write_pos:end_pos] = data
            else:
                # Wrap around
                first_part = self.capacity - self._write_pos
                self._buffer[self._write_pos:] = data[:first_part]
                self._buffer[:end_pos - self.capacity] = data[first_part:]

            self._write_pos = end_pos % self.capacity
            self._frames_written = min(self._frames_written + frames, self.capacity)

        return frames

    def read_at_rate(self, read_pos: float, num_frames: int, rate: float = 1.0) -> np.ndarray:
        """
        Read frames at variable playback rate using linear interpolation.

        Args:
            read_pos: Read position in frames (can be fractional)
            num_frames: Number of output frames to generate
            rate: Playback rate (1.0 = normal, 0.5 = half speed, 2.0 = double)

        Returns:
            Array of shape (num_frames, channels)
        """
        if self._frames_written == 0:
            return np.zeros((num_frames, self.channels), dtype=self.dtype)

        output = np.zeros((num_frames, self.channels), dtype=self.dtype)

        # Generate read positions for each output frame
        read_positions = read_pos + np.arange(num_frames) * rate

        for ch in range(self.channels):
            # Linear interpolation
            pos_floor = np.floor(read_positions).astype(np.int64)
            pos_frac = read_positions - pos_floor

            # Wrap positions
            pos_floor = pos_floor % self.capacity
            pos_ceil = (pos_floor + 1) % self.capacity

            # Get samples
            sample_floor = self._buffer[pos_floor, ch]
            sample_ceil = self._buffer[pos_ceil, ch]

            # Interpolate
            output[:, ch] = sample_floor + pos_frac * (sample_ceil - sample_floor)

        return output

    def get_available_frames(self) -> int:
        """Get number of valid frames in buffer."""
        return self._frames_written

    def clear(self):
        """Clear buffer."""
        with self._lock:
            self._buffer.fill(0)
            self._write_pos = 0
            self._frames_written = 0


class DeckTransport:
    """
    High-level deck transport controlling playback of a single track.

    Manages: play/pause, seek, pitch, volume, EQ, cue.
    """


    def _init_eq_filters(self) -> dict:
        """Initialize 3-band EQ filter coefficients (biquad)."""
        # Simplified: just store gains, actual filtering in mixer
        # For production: implement proper biquad filters here
        return {
            'low': {'gain': 1.0, 'freq': 200.0, 'q': 0.707},
            'mid': {'gain': 1.0, 'freq': 1000.0, 'q': 0.707},
            'high': {'gain': 1.0, 'freq': 4000.0, 'q': 0.707},
        }

    def load_track(self, audio_data: np.ndarray, sample_rate: int):
        """
        Load decoded audio data into the deck buffer.

        Args:
            audio_data: Float32 array of shape (frames, channels) or (frames,)
            sample_rate: Source sample rate (will be resampled if different)
        """
        if audio_data.ndim == 1:
            audio_data = audio_data[:, np.newaxis]

        # Resample if needed (simple linear for now; use scipy.signal.resample for quality)
        if sample_rate != self.sample_rate:
            from scipy import signal
            ratio = self.sample_rate / sample_rate
            num_frames = int(audio_data.shape[0] * ratio)
            audio_data = signal.resample(audio_data, num_frames, axis=0)

        # Ensure stereo
        if audio_data.shape[1] == 1:
            audio_data = np.repeat(audio_data, 2, axis=1)
        elif audio_data.shape[1] > 2:
            audio_data = audio_data[:, :2]

        if audio_data.shape[0] > self.buffer.capacity:
            self.buffer = RingBuffer(audio_data.shape[0], channels=2)
        else:
            self.buffer.clear()
        self.buffer.write(audio_data)

        self._track_duration_samples = audio_data.shape[0]
        self.state.duration = float(self._track_duration_samples)
        self.state.position = 0.0
        self.state.playing = False

        logger.info(f"Deck {self.deck_id}: Loaded {self.state.duration/self.sample_rate:.1f}s track")

    def play(self):
        """Start playback."""
        self.state.playing = True
        logger.debug(f"Deck {self.deck_id}: Play")

    def pause(self):
        """Pause playback."""
        self.state.playing = False
        logger.debug(f"Deck {self.deck_id}: Pause")

    def stop(self):
        """Stop and reset to beginning."""
        self.state.playing = False
        self.state.position = 0.0
        logger.debug(f"Deck {self.deck_id}: Stop")

    def seek(self, position_seconds: float):
        """Seek to position in seconds."""
        target_samples = position_seconds * self.sample_rate
        target_samples = np.clip(target_samples, 0, self.state.duration - 1)
        self.state.position = float(target_samples)
        logger.debug(f"Deck {self.deck_id}: Seek to {position_seconds:.2f}s")

    def seek_relative(self, delta_seconds: float):
        """Seek relative to current position."""
        self.seek(self.state.position / self.sample_rate + delta_seconds)

    def set_rate(self, rate: float):
        """Set playback rate (pitch). Clamped to 0.5-2.0."""
        self.state.rate = np.clip(rate, 0.5, 2.0)

    def set_volume(self, volume: float):
        """Set deck volume (0.0 to 1.0)."""
        self.state.volume = np.clip(volume, 0.0, 1.0)

    def set_eq(self, low: float = None, mid: float = None, high: float = None):
        """Set EQ gains (0.0 to 2.0, 1.0 = flat)."""
        if low is not None:
            self.state.eq_low = np.clip(low, 0.0, 2.0)
            self._eq_state['low']['gain'] = self.state.eq_low
        if mid is not None:
            self.state.eq_mid = np.clip(mid, 0.0, 2.0)
            self._eq_state['mid']['gain'] = self.state.eq_mid
        if high is not None:
            self.state.eq_high = np.clip(high, 0.0, 2.0)
            self._eq_state['high']['gain'] = self.state.eq_high

    def set_cue(self, active: bool):
        """Activate/deactivate cue (pre-fader listen)."""
        self.state.cue_active = active

    def get_position_seconds(self) -> float:
        """Get current playback position in seconds."""
        return self.state.position / self.sample_rate

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)."""
        if self.state.duration <= 0:
            return 0.0
        return float(self.state.position / self.state.duration)

    def is_finished(self) -> bool:
        """Check if playback reached end of track."""
        return self.state.position >= self.state.duration - self.sample_rate

    def __init__(self, deck_id: str, sample_rate: int = 48000, buffer_seconds: float = 30.0, blocksize: int = 256):
        """
        Initialize deck transport.

        Args:
            deck_id: Identifier ('A' or 'B')
            sample_rate: Engine sample rate
            buffer_seconds: Ring buffer duration in seconds
            blocksize: Size of each audio callback block (frames)
        """
        self.deck_id = deck_id
        self.sample_rate = sample_rate
        self.state = DeckState()
        self.blocksize = blocksize

        # Ring buffer: large enough to hold decoded track
        buffer_frames = int(buffer_seconds * sample_rate)
        self.buffer = RingBuffer(buffer_frames, channels=2)

        # Track metadata
        self._track_path: Optional[str] = None
        self._track_duration_samples: int = 0

        # Pre‑allocated output buffer for real‑time callback (reused each call)
        self._output_buffer = np.zeros((blocksize, 2), dtype=np.float32)

        # EQ filter state (biquad filters for 3‑band EQ)
        self._eq_state = self._init_eq_filters()

    def process_audio(self, num_frames: int) -> np.ndarray:
        """Fill the pre‑allocated buffer and return it.

        This method reuses ``self._output_buffer`` to avoid per‑callback allocations.
        If ``num_frames`` differs from the pre‑allocated size, the buffer is resized
        (rare, occurs only if the device blocksize changes).
        """
        if not self.state.playing or self._track_duration_samples == 0:
            # Silence – ensure buffer size matches request
            if self._output_buffer.shape[0] != num_frames:
                self._output_buffer = np.zeros((num_frames, 2), dtype=np.float32)
            else:
                self._output_buffer.fill(0.0)
            return self._output_buffer

        # Ensure buffer size matches request
        if self._output_buffer.shape[0] != num_frames:
            self._output_buffer = np.zeros((num_frames, 2), dtype=np.float32)

        # Read from ring buffer (creates a temporary array, then copy once)
        temp = self.buffer.read_at_rate(self.state.position, num_frames, self.state.rate)
        np.copyto(self._output_buffer, temp)

        # Advance position
        self.state.position += num_frames * self.state.rate

        # End‑of‑track handling
        if self.state.position >= self.state.duration:
            self.state.position = self.state.duration
            self.state.playing = False
            # Zero out any remaining frames after track ends
            remaining = int(num_frames - (self.state.position - self.state.duration) / self.state.rate)
            if remaining < num_frames:
                self._output_buffer[remaining:].fill(0.0)

        # Apply volume (in‑place)
        self._output_buffer *= self.state.volume
        return self._output_buffer


# Convenience: stereo peak meter calculation
def calculate_peak_meters(audio: np.ndarray) -> tuple[float, float]:
    """
    Calculate peak levels for left/right channels.

    Returns:
        (left_peak, right_peak) in dBFS (-inf to 0)
    """
    if audio.size == 0:
        return (-np.inf, -np.inf)

    left_peak = np.max(np.abs(audio[:, 0])) if audio.shape[1] > 0 else 0
    right_peak = np.max(np.abs(audio[:, 1])) if audio.shape[1] > 1 else 0

    def to_db(x):
        return 20 * np.log10(x) if x > 0 else -np.inf

    return (to_db(left_peak), to_db(right_peak))
