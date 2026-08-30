"""FastAPI routes for LLM reasoning, Groq model status, and AI diagnosis explanation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.config import get_settings
from harness.llm.groq_client import SUPPORTED_GROQ_MODELS, get_groq_client

router = APIRouter(prefix="/api/harness/llm", tags=["llm"])


class ExplainDiagnosisPayload(BaseModel):
    summary: str = Field(default="Hardware fault induced collision")
    primary_fault_category: str = Field(default="TRANSPORT_LATENCY")
    causal_chain: List[Dict[str, Any]] = Field(default_factory=list)


class PatchGuidancePayload(BaseModel):
    original_code: str = Field(description="Target controller Python source code")
    diagnostic_report: Optional[Dict[str, Any]] = Field(default=None)


@router.get("/status")
def get_llm_status() -> Dict[str, Any]:
    """Retrieve the current Groq LLM integration status, model selection, and readiness."""
    settings = get_settings()
    client = get_groq_client()
    return {
        "provider": "groq",
        "configured": client.is_configured,
        "model": settings.groq_model,
        "base_url": settings.groq_base_url,
        "supported_models": SUPPORTED_GROQ_MODELS,
        "message": (
            f"Groq LLM is ready using {settings.groq_model}"
            if client.is_configured
            else "Groq API key not set. Running in deterministic heuristic mode. Add GROQ_API_KEY to .env to activate."
        ),
    }


@router.get("/models")
def get_supported_models() -> List[str]:
    """List available supported Groq models."""
    return SUPPORTED_GROQ_MODELS


@router.post("/explain")
def explain_diagnosis(payload: ExplainDiagnosisPayload) -> Dict[str, Any]:
    """Generate an AI/Groq-powered explanation from a Causal DAG diagnostic report."""
    client = get_groq_client()
    report_dict = payload.model_dump()
    explanation = client.explain_diagnostic_report(report_dict)
    return {
        "explanation": explanation,
        "model": client.model,
        "is_ai_generated": client.is_configured,
    }


@router.post("/patch-guidance")
def get_patch_guidance(payload: PatchGuidancePayload) -> Dict[str, Any]:
    """Generate AI-assisted hardening recommendations for controller code."""
    client = get_groq_client()
    guidance = client.synthesize_patch_guidance(
        original_code=payload.original_code,
        diagnostic_report=payload.diagnostic_report,
    )
    return guidance
