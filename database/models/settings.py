"""Settings model.

Holds user‑adjustable preferences for the DJ application.
"""

from typing import Optional

from sqlmodel import Field, SQLModel


class Settings(SQLModel, table=True):
    """Persistent user settings.

    * ``id`` – singleton primary key (only one row expected).
    * ``master_volume`` – Master output gain (0.0‑1.0).
    * ``cue_volume`` – Cue (headphone) output gain (0.0‑1.0).
    * ``theme`` – UI theme identifier (e.g., "light" or "dark").
    * ``master_device`` – Identifier for the selected master output device.
    * ``cue_device`` – Identifier for the selected cue output device.
    * ``waveform_zoom`` – Zoom factor for waveform display.
    """

    id: Optional[int] = Field(default=1, primary_key=True)
    master_volume: float = Field(default=1.0, ge=0.0, le=1.0, index=True)
    cue_volume: float = Field(default=1.0, ge=0.0, le=1.0, index=True)
    theme: Optional[str] = Field(default="light")
    master_device: Optional[str] = Field(default=None, index=True)
    cue_device: Optional[str] = Field(default=None, index=True)
    waveform_zoom: float = Field(default=1.0, ge=0.1, le=10.0, index=True)
