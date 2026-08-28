"""FastAPI application entrypoint for Harness-Agent Simulation Sandbox."""

from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.scenarios import router as scenarios_router
from backend.routes.telemetry import router as telemetry_router
from backend.ws.live_stream import router as ws_router


app = FastAPI(
    title="Harness-Agent: Virtual Hardware Simulation Sandbox",
    version="0.1.0",
    description="Software-in-the-loop deterministic hardware-semantic testbed for AI agents.",
)

# Enable CORS for local dev visualizer (Vite / React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path
from fastapi.staticfiles import StaticFiles

app.include_router(scenarios_router)
app.include_router(telemetry_router)
app.include_router(ws_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint returning server liveness status."""
    return {"status": "ok", "service": "harness-agent-sandbox"}


frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

