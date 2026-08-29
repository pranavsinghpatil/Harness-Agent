"""Validated experiment and perturbation-space models for System 1.

System 2 chooses values from a perturbation space. This module turns those
values into deterministic ``FaultDefinition`` overrides without allowing the
planner to reach into sandbox internals.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from sandbox.faults.schema import FaultDefinition


class PerturbationDimension(BaseModel):
    """One bounded, independently testable execution perturbation."""

    id: str = Field(min_length=1, description="Stable dimension identifier")
    target: str = Field(min_length=1, description="Sandbox boundary receiving the fault")
    fault_type: str = Field(min_length=1, description="FaultController perturbation type")
    parameter_name: str = Field(min_length=1, description="Fault parameter populated by the selected value")
    minimum: float
    maximum: float
    baseline: float
    start_time: float = Field(default=2.0, ge=0.0)
    duration: float = Field(default=3.5, gt=0.0)
    unit: str = ""
    higher_is_worse: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> PerturbationDimension:
        """Reject malformed ranges before an experiment can reach the sandbox."""
        if self.minimum > self.maximum:
            raise ValueError("minimum must be less than or equal to maximum")
        if not self.minimum <= self.baseline <= self.maximum:
            raise ValueError("baseline must be within minimum and maximum")
        return self

    def validate_value(self, value: float) -> float:
        """Validate and normalize a planner-selected value."""
        numeric_value = float(value)
        if not self.minimum <= numeric_value <= self.maximum:
            raise ValueError(
                f"Perturbation '{self.id}' value {numeric_value} is outside "
                f"[{self.minimum}, {self.maximum}]"
            )
        return numeric_value

    def stress_value(self) -> float:
        """Return the adverse endpoint used for initial dimension screening."""
        return self.maximum if self.higher_is_worse else self.minimum

    def to_fault(self, value: float, experiment_id: str) -> FaultDefinition:
        """Compile a selected value into an immutable sandbox fault definition."""
        selected_value = self.validate_value(value)
        return FaultDefinition(
            id=f"{experiment_id}:{self.id}",
            target=self.target,
            type=self.fault_type,
            start_time=self.start_time,
            duration=self.duration,
            parameters={self.parameter_name: selected_value},
        )


class PerturbationSpace(BaseModel):
    """Complete bounded search space available to an autonomous investigator."""

    dimensions: list[PerturbationDimension] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> PerturbationSpace:
        """Keep dimension identifiers stable and unambiguous in evidence."""
        ids = [dimension.id for dimension in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("perturbation dimension IDs must be unique")
        return self

    def get_dimension(self, dimension_id: str) -> PerturbationDimension:
        """Return a dimension by stable ID or raise a useful validation error."""
        for dimension in self.dimensions:
            if dimension.id == dimension_id:
                return dimension
        raise ValueError(f"Unknown perturbation dimension '{dimension_id}'")

    def build_fault_overrides(
        self,
        values: dict[str, float],
        experiment_id: str,
    ) -> list[dict[str, Any]]:
        """Compile selected non-baseline values into session fault overrides.

        Values are sorted by dimension ID so the generated fault schedule is
        stable even when a planner supplies a regular dictionary.
        """
        unknown_ids = set(values).difference(dimension.id for dimension in self.dimensions)
        if unknown_ids:
            raise ValueError(f"Unknown perturbation dimensions: {sorted(unknown_ids)}")

        overrides: list[dict[str, Any]] = []
        for dimension_id in sorted(values):
            dimension = self.get_dimension(dimension_id)
            value = dimension.validate_value(values[dimension_id])
            if value == dimension.baseline:
                continue
            overrides.append(dimension.to_fault(value, experiment_id).model_dump())
        return overrides


def default_perturbation_space() -> PerturbationSpace:
    """Return the small, high-signal search space for the first demo loop."""
    return PerturbationSpace(
        dimensions=[
            PerturbationDimension(
                id="sensor.camera.latency_ms",
                target="transport.camera",
                fault_type="added_latency",
                parameter_name="latency_ms",
                minimum=0.0,
                maximum=500.0,
                baseline=0.0,
                unit="ms",
            ),
            PerturbationDimension(
                id="hardware.compute.availability",
                target="hardware.compute",
                fault_type="cpu_availability",
                parameter_name="factor",
                minimum=0.1,
                maximum=1.0,
                baseline=1.0,
                unit="ratio",
                higher_is_worse=False,
            ),
            PerturbationDimension(
                id="actuator.brake.effectiveness",
                target="actuator.brake",
                fault_type="reduced_effectiveness",
                parameter_name="factor",
                minimum=0.2,
                maximum=1.0,
                baseline=1.0,
                unit="ratio",
                higher_is_worse=False,
            ),
        ]
    )
