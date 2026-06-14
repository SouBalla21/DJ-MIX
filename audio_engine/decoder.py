"""
Audio Decoder
FFmpeg-based decoding of various audio formats to float32 PCM.
"""

import subprocess
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

# Supported formats
SUPPORTED_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.aiff', '.aif'}

# FFmpeg command for decoding to float32 PCM
FFMPEG_DECODE_CMD = [
    'ffmpeg',
    '-v', 'error',
    '-i', '{input}',
    '-f', 'f32le',        # float32 little-endian
    '-ac', '2',           # force stereo
    '-ar', '{sample_rate}',  # target sample rate
    '-',                  # output to stdout
]


class AudioDecoder:
    """
    Decodes audio files using FFmpeg.

    Produces float32 stereo PCM at target sample rate.
    """

    def __init__(self, target_sample_rate: int = 48000):
        self.target_sample_rate = target_sample_rate
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Verify FFmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and ensure it's in PATH.")

    def decode_file(self, filepath: Path, target_sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
        """
        Decode audio file to float32 stereo PCM.

        Args:
            filepath: Path to audio file
            target_sr: Override target sample rate (default: self.target_sample_rate)

        Returns:
            Tuple of (audio_data, sample_rate)
            audio_data: float32 array of shape (frames, 2)
            sample_rate: Actual output sample rate
        """
        sr = target_sr or self.target_sample_rate

        cmd = [arg.format(input=str(filepath), sample_rate=sr) for arg in FFMPEG_DECODE_CMD]

        logger.debug(f"Decoding: {filepath} at {sr}Hz")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=300  # 5 min max for very long files
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Decoding timeout: {filepath}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg decode failed: {e.stderr.decode()[:500]}")

        # Parse raw float32 PCM from stdout
        audio_bytes = result.stdout
        if len(audio_bytes) == 0:
            raise RuntimeError(f"No audio data decoded from {filepath}")

        # Convert to numpy array (float32, stereo interleaved)
        audio_data = np.frombuffer(audio_bytes, dtype=np.float32)

        # Reshape to (frames, channels)
        num_frames = len(audio_data) // 2
        audio_data = audio_data[:num_frames * 2].reshape((num_frames, 2))

        # Normalize if needed (FFmpeg f32le should be -1.0 to 1.0)
        peak = np.max(np.abs(audio_data))
        if peak > 1.0:
            audio_data = audio_data / peak * 0.99

        logger.info(f"Decoded: {filepath} -> {num_frames} frames ({num_frames/sr:.1f}s) @ {sr}Hz")
        return audio_data, sr

    def decode_to_temp_wav(self, filepath: Path, target_sr: Optional[int] = None) -> Path:
        """
        Decode to temporary WAV file (for caching/pre-loading).

        Returns path to temp WAV file.
        """
        sr = target_sr or self.target_sample_rate
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()

        cmd = [
            'ffmpeg', '-v', 'error',
            '-i', str(filepath),
            '-ar', str(sr),
            '-ac', '2',
            '-sample_fmt', 'flt',  # float32 WAV
            '-y', temp_file.name
        ]

        subprocess.run(cmd, check=True)
        return Path(temp_file.name)

    def get_duration(self, filepath: Path) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(filepath)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def get_metadata(self, filepath: Path) -> dict:
        """Extract metadata using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format_tags=title,artist,album,date,genre,track',
            '-show_entries', 'format=duration,bit_rate',
            '-of', 'json',
            str(filepath)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)

        metadata = {}
        if 'format' in data:
            fmt = data['format']
            metadata['duration'] = float(fmt.get('duration', 0))
            metadata['bit_rate'] = int(fmt.get('bit_rate', 0))
            tags = fmt.get('tags', {})
            metadata['title'] = tags.get('title', '')
            metadata['artist'] = tags.get('artist', '')
            metadata['album'] = tags.get('album', '')
            metadata['date'] = tags.get('date', '')
            metadata['genre'] = tags.get('genre', '')
            metadata['track'] = tags.get('track', '')

        return metadata


def is_supported_format(filepath: Path) -> bool:
    """Check if file extension is supported."""
    return filepath.suffix.lower() in SUPPORTED_EXTENSIONS


# Global decoder instance
_decoder: Optional[AudioDecoder] = None


def get_decoder(target_sample_rate: int = 48000) -> AudioDecoder:
    """Get or create global decoder instance."""
    global _decoder
    if _decoder is None:
        _decoder = AudioDecoder(target_sample_rate)
    return _decoder