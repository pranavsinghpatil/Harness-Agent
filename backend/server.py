"""FastAPI application entrypoint for Harness-Agent Simulation Sandbox."""

from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import load_env_file, get_settings
from backend.routes.scenarios import router as scenarios_router
from backend.routes.telemetry import router as telemetry_router
from backend.routes.harness import router as harness_router
from backend.routes.llm import router as llm_router
from backend.ws.live_stream import router as ws_router

# Ensure .env is loaded on startup
load_env_file()
settings = get_settings()

app = FastAPI(
    title="Harness-Agent: Virtual Hardware Simulation Sandbox & Agent Harness",
    version="0.2.0",
    description="Software-in-the-loop deterministic hardware testbed and reliability engineering harness.",
)

# Enable CORS for local dev visualizer (Vite / React / Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios_router)
app.include_router(telemetry_router)
app.include_router(harness_router)
app.include_router(llm_router)
app.include_router(ws_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint returning server liveness and LLM status."""
    return {
        "status": "ok",
        "service": "harness-agent-sandbox",
        "groq_configured": settings.has_groq,
        "groq_model": settings.groq_model,
    }
