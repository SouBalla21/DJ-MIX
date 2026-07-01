"""
Audio Device Management
Enumerates, selects, and configures PortAudio devices for Master and Cue outputs.
"""

import sounddevice as sd
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input/output device."""
    index: int
    name: str
    hostapi: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    is_default_output: bool = False
    is_default_input: bool = False

    def __str__(self) -> str:
        return f"{self.name} ({self.hostapi}) - {self.max_output_channels} out @ {self.default_samplerate:.0f}Hz"


class DeviceManager:
    """
    Manages audio device enumeration and selection for Master/Cue routing.

    The DJ platform requires TWO separate output devices:
    - Master: Main mix to speakers/PA
    - Cue: Pre-fader preview to headphones
    """

    def __init__(self, target_samplerate: int = 48000, blocksize: int = 256):
        self.target_samplerate = target_samplerate
        self.blocksize = blocksize
        self._master_device: Optional[AudioDevice] = None
        self._cue_device: Optional[AudioDevice] = None
        self._master_stream: Optional[sd.OutputStream] = None
        self._cue_stream: Optional[sd.OutputStream] = None

    def list_output_devices(self) -> List[AudioDevice]:
        """Return all devices with output channels > 0."""
        devices = []
        for idx, dev in enumerate(sd.query_devices()):
            if dev['max_output_channels'] > 0:
                audio_dev = AudioDevice(
                    index=idx,
                    name=dev['name'],
                    hostapi=sd.query_hostapis(dev['hostapi'])['name'],
                    max_input_channels=dev['max_input_channels'],
                    max_output_channels=dev['max_output_channels'],
                    default_samplerate=dev['default_samplerate'],
                    is_default_output=(idx == sd.default.device[1]),
                    is_default_input=(idx == sd.default.device[0]),
                )
                devices.append(audio_dev)
        return devices

    def get_device(self, index: int) -> Optional[AudioDevice]:
        """Get device by index."""
        for dev in self.list_output_devices():
            if dev.index == index:
                return dev
        return None

    def set_master_device(self, index: int) -> bool:
        """Set the Master output device."""
        dev = self.get_device(index)
        if dev is None:
            logger.error(f"Master device index {index} not found")
            return False
        if dev.max_output_channels < 2:
            logger.warning(f"Master device '{dev.name}' has only {dev.max_output_channels} channels, need 2+")
        self._master_device = dev
        logger.info(f"Master device set to: {dev}")
        return True

    def set_cue_device(self, index: int) -> bool:
        """Set the Cue (headphone) output device."""
        dev = self.get_device(index)
        if dev is None:
            logger.error(f"Cue device index {index} not found")
            return False
        if dev.max_output_channels < 2:
            logger.warning(f"Cue device '{dev.name}' has only {dev.max_output_channels} channels, need 2+")
        self._cue_device = dev
        logger.info(f"Cue device set to: {dev}")
        return True

    def auto_select_devices(self) -> bool:
        """Auto-select Master and Cue devices (prefer different physical devices)."""
        devices = self.list_output_devices()
        if not devices:
            logger.error("No output devices found")
            return False

        # Prefer default as Master
        default_out = next((d for d in devices if d.is_default_output), devices[0])
        self._master_device = default_out

        # Try to find a different device for Cue
        cue_candidates = [d for d in devices if d.index != default_out.index]
        if cue_candidates:
            # Prefer one with "headphone" or "headset" in name
            headphone = next((d for d in cue_candidates if 'headphone' in d.name.lower() or 'headset' in d.name.lower()), None)
            self._cue_device = headphone or cue_candidates[0]
        else:
            # Fallback: same device, different channel mapping (not ideal but works)
            self._cue_device = default_out
            logger.warning("Only one output device available; Master and Cue will share device")

        logger.info(f"Auto-selected: Master={self._master_device.name}, Cue={self._cue_device.name}")
        return True

    @property
    def master_device(self) -> Optional[AudioDevice]:
        return self._master_device

    @property
    def cue_device(self) -> Optional[AudioDevice]:
        return self._cue_device

    def get_output_config(self) -> dict:
        """Get configuration for opening output streams."""
        if not self._master_device or not self._cue_device:
            raise RuntimeError("Devices not selected. Call set_master_device() and set_cue_device() first.")

        # Use the higher of the two device sample rates, or target
        master_sr = self._master_device.default_samplerate
        cue_sr = self._cue_device.default_samplerate
        samplerate = int(max(self.target_samplerate, master_sr, cue_sr))

        return {
            'master': {
                'device': self._master_device.index,
                'samplerate': samplerate,
                'channels': 2,
                'blocksize': self.blocksize,
                'dtype': 'float32',
            },
            'cue': {
                'device': self._cue_device.index,
                'samplerate': samplerate,
                'channels': 2,
                'blocksize': self.blocksize,
                'dtype': 'float32',
            }
        }

    def open_streams(self, master_callback, cue_callback=None) -> tuple[sd.OutputStream, sd.OutputStream]:
        """
        Open Master and Cue output streams with the same callback.

        The callback receives (outdata_master, outdata_cue, frames, time, status)
        and should fill both buffers.
        """
        config = self.get_output_config()

        # We need a wrapper that splits the callback for two streams
        # sounddevice doesn't support multi-device callbacks directly
        # So we'll use a shared buffer approach in the mixer

        self._master_stream = sd.OutputStream(**config['master'], callback=master_callback)
        self._cue_stream = sd.OutputStream(**config['cue'], callback=cue_callback or master_callback)

        return self._master_stream, self._cue_stream

    def close_streams(self):
        """Close all open streams."""
        if self._master_stream:
            self._master_stream.close()
            self._master_stream = None
        if self._cue_stream:
            self._cue_stream.close()
            self._cue_stream = None

    def start_streams(self):
        """Start both output streams."""
        if self._master_stream:
            self._master_stream.start()
        if self._cue_stream:
            self._cue_stream.start()

    def stop_streams(self):
        """Stop both output streams."""
        if self._master_stream:
            self._master_stream.stop()
        if self._cue_stream:
            self._cue_stream.stop()


# Global instance for easy access
_device_manager: Optional[DeviceManager] = None


def get_device_manager(target_samplerate: int = 48000, blocksize: int = 256) -> DeviceManager:
    """Get or create the global device manager."""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager(target_samplerate, blocksize)
    return _device_manager
