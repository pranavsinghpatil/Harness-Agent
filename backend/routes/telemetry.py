"""FastAPI routes for querying run manifests and telemetry frames."""

from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from sandbox.api.tools import get_run


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{run_id}")
def get_run_details(run_id: str) -> dict[str, Any]:
    cached = get_run(run_id)
    if not cached:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    manifest, frames = cached
    return {
        "manifest": manifest.model_dump(),
        "total_frames": len(frames),
        "frames": [f.to_dict() for f in frames],
    }


@router.get("/{run_id}/manifest")
def get_run_manifest(run_id: str) -> dict[str, Any]:
    cached = get_run(run_id)
    if not cached:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    manifest, _ = cached
    return manifest.model_dump()
