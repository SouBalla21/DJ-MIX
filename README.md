# DJ Mix

DJ Mix is a lightweight real-time DJ mixing and audio processing system. It provides a two-deck browser dashboard backed by a Python audio engine for playback, mixing, routing, metadata storage, and track analysis.

The project is intentionally focused on audio systems engineering: low-latency playback, separate deck state, mixer controls, device routing, and practical track-library workflows.

## Features

- Dual-deck playback with independent load, play, pause, seek, volume, rate, cue, and EQ controls.
- Master mixer with crossfader, master gain, cue gain, and live output meters.
- Interactive deck waveform area with a moving playhead and playback position timer.
- Multi-device routing for Master and Cue outputs using available system audio devices.
- Local track library backed by SQLite.
- Browser-based song import using the **Browse files** button.
- Metadata extraction through FFmpeg/ffprobe.
- BPM and waveform analysis hooks through librosa.
- FastAPI backend with REST routes and a WebSocket control channel.
- React + TypeScript frontend with a compact DJ dashboard.

## Tech Stack

- Frontend: React, TypeScript, Vite, Zustand, CSS.
- Backend: Python, FastAPI, SQLModel, SQLite.
- Audio engine: sounddevice/PortAudio, FFmpeg, NumPy, SciPy, librosa.
- Communication: REST for library operations, WebSocket for audio engine commands and monitoring.

## Requirements

- Python 3.11 or newer.
- Node.js 20 or newer.
- FFmpeg installed and available on PATH.
- Working audio output device supported by PortAudio.

Recommended Python packages:

```bash
pip install fastapi uvicorn sqlmodel sounddevice numpy scipy librosa websockets python-multipart requests
```

Install FFmpeg:

- Windows: install from https://ffmpeg.org/download.html or use a package manager, then add `ffmpeg` and `ffprobe` to PATH.
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Run The Project

From the project root:

```bash
cd DJ-KOTTU-main
```

Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

Start the backend:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

## Testing Checklist

1. Confirm the header shows **Audio engine connected**.
2. Open the Routing panel and select a Master output device.
3. Click **Browse files** in Track Library and choose one or more audio files.
4. Click **Load A** or **Load B** for an imported track.
5. Press **Play** and verify:
   - The deck status changes to Playing.
   - The time counter advances.
   - The progress slider/playhead moves.
   - Master meters react to audio.
6. Move the crossfader, deck volume, EQ, and rate controls.
7. Try assigning Cue output to a different device if headphones are available.

## Build Commands

Frontend production build:

```bash
cd frontend
npm run build
```

Python syntax check:

```bash
python -m compileall backend database audio_engine
```

Backend health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Track library check:

```bash
curl http://127.0.0.1:8000/api/tracks/
```

## Assumptions

- The app is designed for local testing on one machine.
- Uploaded songs are copied into the local `imported_tracks/` folder.
- Browser security does not expose the original local file path, so file import uses upload instead of direct path browsing.
- FFmpeg is required for metadata extraction and decoding.
- The best low-latency behavior depends on the system audio driver and selected output device.
- If only one output device is available, Master and Cue may use the same device.

## Verification-Friendly Additions

- Browser upload flow for adding songs without manually editing the database.
- Real-time WebSocket control for playback, mixer, and monitoring state.
- Device routing dashboard for Master and Cue output selection.
- BPM and waveform analysis support in the backend audio pipeline.
- SQLite-backed library with metadata fields for title, artist, duration, BPM, key, waveform, and beat positions.
- Clean dashboard showing deck state, timing, output meters, mixer state, and routing status in one place.

## Troubleshooting

- If the UI says the audio engine is unavailable, make sure the backend is running on `127.0.0.1:8000`.
- If files import but do not play, verify FFmpeg is installed and the imported file format is supported.
- If the timer does not move, check that the track is loaded into a deck and the WebSocket status says connected.
- If no sound is heard, check Master volume, deck volume, crossfader position, selected output device, and system volume.
- If a port is already in use, stop the old process or run the backend/frontend on another port and update the frontend API URLs.
