"""
DJ Mixer Core
Real-time mixing, EQ, crossfader, and Master/Cue routing.
This runs in the PortAudio callback - must be fast and allocation-free.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MixerState:
    """Current mixer state (controlled via WebSocket)."""
    crossfader: float = 0.5      # 0.0 = Deck A only, 1.0 = Deck B only
    master_volume: float = 1.0   # Master output gain
    cue_volume: float = 1.0      # Cue output gain
    deck_a_cue: bool = False     # Deck A cue button (pre-fader listen)
    deck_b_cue: bool = False     # Deck B cue button


class BiquadFilter:
    """
    Efficient biquad filter for 3-band EQ.
    Process in-place for zero allocation in audio callback.
    """

    def __init__(self, sample_rate: float):
        self.sample_rate = sample_rate
        # Coefficients for each band: [b0, b1, b2, a1, a2]
        self.coeffs = {
            'low': np.zeros(5, dtype=np.float32),
            'mid': np.zeros(5, dtype=np.float32),
            'high': np.zeros(5, dtype=np.float32),
        }
        # State variables (per channel)
        self.z1 = {'low': 0.0, 'mid': 0.0, 'high': 0.0}
        self.z2 = {'low': 0.0, 'mid': 0.0, 'high': 0.0}

        # Default flat response
        self.set_gains(1.0, 1.0, 1.0)

    def set_gains(self, low: float, mid: float, high: float):
        """Set EQ gains (linear, 1.0 = flat)."""
        self._calc_coeffs('low', 200.0, 0.707, low)
        self._calc_coeffs('mid', 1000.0, 0.707, mid)
        self._calc_coeffs('high', 4000.0, 0.707, high)

    def _calc_coeffs(self, band: str, freq: float, q: float, gain: float):
        """Calculate biquad coefficients for peaking EQ."""
        if abs(gain - 1.0) < 0.001:
            # Flat - passthrough
            self.coeffs[band] = np.array([1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
            return

        w0 = 2 * np.pi * freq / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        A = np.sqrt(gain)
        alpha = sin_w0 / (2 * q)

        if gain >= 1.0:
            # Boost
            b0 = 1 + alpha * A
            b1 = -2 * cos_w0
            b2 = 1 - alpha * A
            a0 = 1 + alpha / A
            a1 = -2 * cos_w0
            a2 = 1 - alpha / A
        else:
            # Cut
            b0 = 1 + alpha / A
            b1 = -2 * cos_w0
            b2 = 1 - alpha / A
            a0 = 1 + alpha * A
            a1 = -2 * cos_w0
            a2 = 1 - alpha * A

        # Normalize by a0
        self.coeffs[band] = np.array([
            b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
        ], dtype=np.float32)

    def process_stereo(self, audio: np.ndarray, band: str):
        """
        Process stereo audio through filter in-place.

        Args:
            audio: float32 array of shape (frames, 2)
            band: 'low', 'mid', or 'high'
        """
        c = self.coeffs[band]
        if c[0] == 1.0 and c[1] == 0.0:  # Flat - skip
            return

        z1 = self.z1[band]
        z2 = self.z2[band]

        # Process left channel
        x = audio[:, 0]
        y = c[0] * x + c[1] * z1 + c[2] * z2 - c[3] * z1 - c[4] * z2
        self.z1[band] = x[-1]
        self.z2[band] = y[-1]
        audio[:, 0] = y

        # Process right channel
        x = audio[:, 1]
        y = c[0] * x + c[1] * z1 + c[2] * z2 - c[3] * z1 - c[4] * z2
        self.z1[band] = x[-1]
        self.z2[band] = y[-1]
        audio[:, 1] = y


class DJMixer:
    """
    Main mixer combining two decks with EQ, crossfader, and Master/Cue routing.

    Designed for real-time PortAudio callback - no allocations, minimal branching.
    """

    def __init__(self, sample_rate: int = 48000, blocksize: int = 256):
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.state = MixerState()

        # Per-deck EQ filters
        self.deck_a_eq = BiquadFilter(sample_rate)
        self.deck_b_eq = BiquadFilter(sample_rate)

        # Pre-allocated buffers (reused every callback)
        self._deck_a_out = np.zeros((blocksize, 2), dtype=np.float32)
        self._deck_b_out = np.zeros((blocksize, 2), dtype=np.float32)
        self._master_out = np.zeros((blocksize, 2), dtype=np.float32)
        self._cue_out = np.zeros((blocksize, 2), dtype=np.float32)

        # Metering
        self.master_peak_l = 0.0
        self.master_peak_r = 0.0
        self.cue_peak_l = 0.0
        self.cue_peak_r = 0.0

    def set_crossfader(self, value: float):
        """Set crossfader position (0.0 to 1.0)."""
        self.state.crossfader = np.clip(value, 0.0, 1.0)

    def set_master_volume(self, value: float):
        self.state.master_volume = np.clip(value, 0.0, 1.0)

    def set_cue_volume(self, value: float):
        self.state.cue_volume = np.clip(value, 0.0, 1.0)

    def set_deck_cue(self, deck: str, active: bool):
        if deck == 'A':
            self.state.deck_a_cue = active
        elif deck == 'B':
            self.state.deck_b_cue = active

    def set_deck_eq(self, deck: str, low: float, mid: float, high: float):
        if deck == 'A':
            self.deck_a_eq.set_gains(low, mid, high)
        elif deck == 'B':
            self.deck_b_eq.set_gains(low, mid, high)

    def process(self, deck_a_audio: np.ndarray, deck_b_audio: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray]:
        """
        Main mixing function - call from PortAudio callback.

        Args:
            deck_a_audio: (blocksize, 2) float32 - Deck A post-fader audio
            deck_b_audio: (blocksize, 2) float32 - Deck B post-fader audio

        Returns:
            (master_out, cue_out) - both (blocksize, 2) float32
        """
        # Ensure buffers are correct size
        n = deck_a_audio.shape[0]
        if n != self.blocksize:
            # Resize buffers if blocksize changed
            self._resize_buffers(n)

        # Copy deck audio to working buffers (avoid modifying inputs)
        self._deck_a_out[:n] = deck_a_audio
        self._deck_b_out[:n] = deck_b_audio

        # Apply per-deck EQ (in-place)
        self.deck_a_eq.process_stereo(self._deck_a_out[:n], 'low')
        self.deck_a_eq.process_stereo(self._deck_a_out[:n], 'mid')
        self.deck_a_eq.process_stereo(self._deck_a_out[:n], 'high')

        self.deck_b_eq.process_stereo(self._deck_b_out[:n], 'low')
        self.deck_b_eq.process_stereo(self._deck_b_out[:n], 'mid')
        self.deck_b_eq.process_stereo(self._deck_b_out[:n], 'high')

        # Crossfader: constant-power curve
        # xfade = 0.0 -> A only, 1.0 -> B only
        xf = self.state.crossfader
        # Constant power: gain = cos(xf * pi/2) for A, sin(xf * pi/2) for B
        gain_a = np.cos(xf * np.pi / 2)
        gain_b = np.sin(xf * np.pi / 2)

        # Mix to master: A * gain_a + B * gain_b
        np.multiply(self._deck_a_out[:n], gain_a, out=self._master_out[:n])
        np.multiply(self._deck_b_out[:n], gain_b, out=self._deck_b_out[:n])
        np.add(self._master_out[:n], self._deck_b_out[:n], out=self._master_out[:n])

        # Master volume
        np.multiply(self._master_out[:n], self.state.master_volume, out=self._master_out[:n])

        # Cue routing: pre-fader listen
        # If neither cue active, default to Deck A (traditional behavior)
        if self.state.deck_a_cue and not self.state.deck_b_cue:
            np.copyto(self._cue_out[:n], deck_a_audio)
        elif self.state.deck_b_cue and not self.state.deck_a_cue:
            np.copyto(self._cue_out[:n], deck_b_audio)
        elif self.state.deck_a_cue and self.state.deck_b_cue:
            # Both cued - mix both (or could do split cue)
            np.add(deck_a_audio, deck_b_audio, out=self._cue_out[:n])
            np.multiply(self._cue_out[:n], 0.5, out=self._cue_out[:n])
        else:
            # Neither cued - monitor master (split cue style)
            np.copyto(self._cue_out[:n], self._master_out[:n])

        # Cue volume
        np.multiply(self._cue_out[:n], self.state.cue_volume, out=self._cue_out[:n])

        # Update peak meters (for UI)
        self._update_meters()

        return self._master_out[:n], self._cue_out[:n]

    def _resize_buffers(self, new_size: int):
        """Resize internal buffers (called if blocksize changes)."""
        self.blocksize = new_size
        self._deck_a_out = np.zeros((new_size, 2), dtype=np.float32)
        self._deck_b_out = np.zeros((new_size, 2), dtype=np.float32)
        self._master_out = np.zeros((new_size, 2), dtype=np.float32)
        self._cue_out = np.zeros((new_size, 2), dtype=np.float32)

    def _update_meters(self):
        """Update peak meter values."""
        # Master
        self.master_peak_l = np.max(np.abs(self._master_out[:, 0]))
        self.master_peak_r = np.max(np.abs(self._master_out[:, 1]))
        # Cue
        self.cue_peak_l = np.max(np.abs(self._cue_out[:, 0]))
        self.cue_peak_r = np.max(np.abs(self._cue_out[:, 1]))

    def get_meter_levels(self) -> dict:
        """Get current meter levels in dBFS."""
        def to_db(x):
            x = float(x)
            return float(20 * np.log10(x)) if x > 1e-10 else -60.0

        return {
            'master_l': to_db(self.master_peak_l),
            'master_r': to_db(self.master_peak_r),
            'cue_l': to_db(self.cue_peak_l),
            'cue_r': to_db(self.cue_peak_r),
        }


# Crossfader curve utilities
def constant_power_curve(position: float) -> tuple[float, float]:
    """
    Calculate constant-power crossfader gains.

    Args:
        position: 0.0 (full A) to 1.0 (full B)

    Returns:
        (gain_a, gain_b)
    """
    pos = np.clip(position, 0.0, 1.0)
    gain_a = np.cos(pos * np.pi / 2)
    gain_b = np.sin(pos * np.pi / 2)
    return float(gain_a), float(gain_b)


def linear_curve(position: float) -> tuple[float, float]:
    """Linear crossfader gains."""
    pos = np.clip(position, 0.0, 1.0)
    return 1.0 - pos, pos
