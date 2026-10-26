"""Domain-independent FailureCase schema and models."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class SourceSpec(BaseModel):
    """Origin of the failure event."""

    system: str = Field(..., description="Source system e.g. autter_runtime, local, trueforge, ci")
    reference: Optional[str] = Field(None, description="External reference, commit SHA, or incident ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata key-values")


class EnvironmentSpec(BaseModel):
    """Execution environment requirements and configuration."""

    seed: int = Field(default=42, description="PRNG seed for deterministic runs")
    workdir: Optional[str] = Field(None, description="Working directory for execution")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables injected into runtime")
    runtime: Optional[str] = Field(None, description="Runtime identifier (e.g. python3.11, node20)")


class ExecutionSpec(BaseModel):
    """Command execution parameters."""

    command: str = Field(..., description="Shell or CLI command to execute")
    timeout_seconds: float = Field(default=30.0, ge=0.1, le=600.0, description="Process timeout guard in seconds")
    input_payload: Optional[Dict[str, Any]] = Field(default=None, description="Structured input passed to target")


class ExpectedOutcomeSpec(BaseModel):
    """Specification of the failure or nominal condition to detect."""

    outcome: Literal["failure", "success", "timeout"] = Field(
        default="failure", description="Expected outcome to reproduce"
    )
    exit_code: Optional[int] = Field(None, description="Expected process exit code (e.g. 1 or 0)")
    error_match: Optional[str] = Field(
        None, description="Substring or regex pattern expected in process stderr or stdout"
    )


class FailureCase(BaseModel):
    """A portable, deterministic failure experiment specification."""

    version: str = Field(default="1.0", description="Contract specification version")
    id: str = Field(..., description="Unique slug identifier for the failure case")
    name: str = Field(..., description="Human-readable title describing the scenario")
    description: Optional[str] = Field(None, description="Detailed failure context and background")
    source: SourceSpec = Field(..., description="Telemetry or system provenance")
    environment: EnvironmentSpec = Field(default_factory=EnvironmentSpec)
    execution: ExecutionSpec = Field(..., description="Execution command and parameters")
    perturbations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Perturbation parameter map (e.g. latency, timeout, error flags, rates)",
    )
    expected: ExpectedOutcomeSpec = Field(default_factory=ExpectedOutcomeSpec)
    observed: Optional[Dict[str, Any]] = Field(
        default=None, description="Historical observed failure trace, exception, or telemetry snapshot"
    )
    tags: List[str] = Field(default_factory=list, description="Categorical tags")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("FailureCase ID must not be empty")
        return cleaned

    @property
    def digest(self) -> str:
        """Calculate canonical SHA-256 digest of the failure case contract."""
        contract = {
            "version": self.version,
            "id": self.id,
            "name": self.name,
            "source": self.source.model_dump(),
            "environment": self.environment.model_dump(),
            "execution": self.execution.model_dump(),
            "perturbations": self.perturbations,
            "expected": self.expected.model_dump(),
        }
        encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()
