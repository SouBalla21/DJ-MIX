"""
Audio Analysis
BPM detection, beat tracking, and waveform peak generation.
Runs in backend (not real-time audio thread).
"""

import numpy as np
import librosa
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


def detect_bpm(audio: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
    """
    Detect tempo (BPM) and beat positions.

    Args:
        audio: float32 array (frames, 2) or (frames,)
        sr: Sample rate

    Returns:
        (bpm, beat_times_seconds)
    """
    # Convert to mono for analysis
    if audio.ndim == 2:
        y = np.mean(audio, axis=1)
    else:
        y = audio

    # Ensure float32
    y = y.astype(np.float32)

    # Detect tempo and beats
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    logger.info(f"Detected BPM: {tempo:.1f}, {len(beat_times)} beats")
    return float(tempo), beat_times


def detect_beats_plp(audio: np.ndarray, sr: int) -> np.ndarray:
    """
    Detect beats using Perceptual Linear Prediction (PLP) onset strength.
    More accurate for electronic music.

    Returns:
        Beat times in seconds
    """
    if audio.ndim == 2:
        y = np.mean(audio, axis=1)
    else:
        y = audio

    y = y.astype(np.float32)

    # Onset strength using PLP
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, feature=librosa.feature.plp)

    # Find peaks in onset envelope
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beats, sr=sr)

    return beat_times


def generate_waveform_peaks(audio: np.ndarray, sr: int,
                            peaks_per_second: int = 20) -> np.ndarray:
    """
    Generate downsampled waveform peaks for visualization.

    Args:
        audio: float32 array (frames, 2) or (frames,)
        sr: Sample rate
        peaks_per_second: Number of peak points per second (e.g., 20 = 50ms resolution)

    Returns:
        Array of shape (num_peaks, 2) with [min, max] for each peak point
    """
    # Convert to mono
    if audio.ndim == 2:
        y = np.mean(audio, axis=1)
    else:
        y = audio

    y = np.abs(y.astype(np.float32))

    # Calculate frames per peak
    frames_per_peak = sr // peaks_per_second
    if frames_per_peak < 1:
        frames_per_peak = 1

    num_peaks = (len(y) + frames_per_peak - 1) // frames_per_peak
    peaks = np.zeros((num_peaks, 2), dtype=np.float32)

    for i in range(num_peaks):
        start = i * frames_per_peak
        end = min(start + frames_per_peak, len(y))
        chunk = y[start:end]
        if len(chunk) > 0:
            peaks[i, 0] = np.min(chunk)  # Negative peak (inverted for display)
            peaks[i, 1] = np.max(chunk)  # Positive peak

    return peaks


def generate_waveform_rms(audio: np.ndarray, sr: int,
                          points_per_second: int = 50) -> np.ndarray:
    """
    Generate RMS-based waveform (smoother, better for overview).

    Returns:
        Array of RMS values per point
    """
    if audio.ndim == 2:
        y = np.mean(audio, axis=1)
    else:
        y = audio

    y = y.astype(np.float32)

    hop_length = sr // points_per_second
    if hop_length < 1:
        hop_length = 1

    # Compute RMS using librosa
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    return rms.astype(np.float32)


def compute_spectral_centroid(audio: np.ndarray, sr: int) -> float:
    """Compute spectral centroid (brightness measure)."""
    if audio.ndim == 2:
        y = np.mean(audio, axis=1)
    else:
        y = audio

    cent = librosa.feature.spectral_centroid(y=y.astype(np.float32), sr=sr)
    return float(np.mean(cent))


def analyze_track(audio: np.ndarray, sr: int) -> dict:
    """
    Full track analysis: BPM, beats, waveform, spectral features.

    Returns:
        Dictionary with all analysis results
    """
    logger.info("Starting full track analysis...")

    # BPM and beats
    bpm, beat_times = detect_bpm(audio, sr)

    # Waveform peaks (for detailed zoom view)
    waveform_peaks = generate_waveform_peaks(audio, sr, peaks_per_second=20)

    # RMS waveform (for overview)
    waveform_rms = generate_waveform_rms(audio, sr, points_per_second=50)

    # Spectral centroid
    brightness = compute_spectral_centroid(audio, sr)

    # Duration
    duration = audio.shape[0] / sr if audio.ndim > 0 else 0

    return {
        'bpm': bpm,
        'beat_times': beat_times.tolist(),
        'waveform_peaks': waveform_peaks.tolist(),
        'waveform_rms': waveform_rms.tolist(),
        'brightness': brightness,
        'duration': duration,
        'sample_rate': sr,
    }


def beats_to_grid(beat_times: np.ndarray, duration: float,
                  subdivisions: int = 4) -> List[dict]:
    """
    Convert beat times to a beat grid with subdivisions.

    Returns list of {time, type} where type is 'downbeat', 'beat', 'subdivision'
    """
    if len(beat_times) < 2:
        return []

    grid = []
    for i, bt in enumerate(beat_times):
        grid.append({'time': float(bt), 'type': 'downbeat' if i % 4 == 0 else 'beat', 'index': i})

        # Add subdivisions between beats
        if i < len(beat_times) - 1:
            next_bt = beat_times[i + 1]
            interval = next_bt - bt
            for sub in range(1, subdivisions):
                sub_time = bt + (interval * sub / subdivisions)
                grid.append({'time': float(sub_time), 'type': 'subdivision', 'index': i * subdivisions + sub})

    grid.sort(key=lambda x: x['time'])
    return grid


# Caching for repeated analysis
_analysis_cache = {}


def get_cached_analysis(filepath: str, audio: np.ndarray, sr: int) -> dict:
    """Get analysis from cache or compute and cache."""
    import hashlib

    # Create cache key from filepath + audio hash
    audio_hash = hashlib.md5(audio.tobytes()[:10000]).hexdigest()[:16]
    key = f"{filepath}:{audio_hash}"

    if key in _analysis_cache:
        logger.debug(f"Cache hit for {filepath}")
        return _analysis_cache[key]

    result = analyze_track(audio, sr)
    _analysis_cache[key] = result
    return result


def clear_analysis_cache():
    """Clear analysis cache."""
    global _analysis_cache
    _analysis_cache.clear()