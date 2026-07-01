"""Backend entry point for the DJ mixing application.

This module creates a FastAPI application with the following responsibilities:

* Initialise the SQLite database on startup (via ``database.session.init_db``).
* Provide graceful shutdown handling – we dispose of the underlying SQLAlchemy engine.
* Register a minimal API router (currently exposing a health‑check endpoint).
* Enable CORS for all origins – useful during development.

The ``audio_engine`` and ``database`` packages are treated as production‑ready
and are **not** modified.
"""

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.tracks import router as tracks_router # type: ignore
from backend.routes.playlists import router as playlists_router
from backend.routes.settings import router as settings_router
from backend.routes.history import router as history_router
from backend.routes.favorites import router as favorites_router
from backend.routes.library import router as library_router
from backend.websocket.audio_ws import router as audio_ws_router
from audio_engine.main import initialize_engine, shutdown_engine
from database.session import init_db

# Local imports – the database package contains the ``init_db`` helper.

# ---------------------------------------------------------------------------
# FastAPI application setup
# ---------------------------------------------------------------------------
app = FastAPI(title="DJ Mixer Backend", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS configuration – allow any origin for development purposes.
# In production you would restrict ``allow_origins`` to your front‑end domain.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accept requests from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router definition – a small placeholder router is registered.  Additional
# routers can be imported from other modules and included here as the project
# grows.
# ---------------------------------------------------------------------------
api_router = APIRouter()

@api_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple health‑check endpoint used by monitoring tools.

    Returns a JSON payload confirming that the service is alive.
    """
    return {"status": "ok"}

# Register the router under a common ``/api`` prefix.
app.include_router(api_router, prefix="/api")

app.include_router(tracks_router, prefix="/api")
app.include_router(playlists_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(favorites_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(audio_ws_router)

# ---------------------------------------------------------------------------
# Application lifecycle events
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    init_db()
    app.state.audio_error = None
    try:
        await initialize_engine()
        print("Backend and audio engine started")
    except Exception as exc:
        app.state.audio_error = str(exc)
        print(f"Backend started, but audio engine failed: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
    await shutdown_engine()
    print("Backend stopped")

# ---------------------------------------------------------------------------
# The ``app`` object is the ASGI callable used by ``uvicorn`` or any other ASGI
# server.  Example command to run the server locally:
#
#   uvicorn backend.main:app --reload
#
# This entry point purposefully contains only the essential scaffolding – the
# business logic lives in the ``audio_engine`` and ``database`` packages which
# are treated as immutable production code.
# ---------------------------------------------------------------------------
