"""Isolated process sandbox and execution controller."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any, Dict, Optional

from universal_harness.case.schema import FailureCase
from universal_harness.runner.executor import ExecutionResult, compute_trace_hash


class ExecutionSandbox:
    """Executes failure cases in an isolated subprocess with perturbation injection."""

    def __init__(self, default_workdir: Optional[str] = None):
        self.default_workdir = default_workdir or os.getcwd()

    def run(
        self,
        case: FailureCase,
        perturbation_overrides: Optional[Dict[str, Any]] = None,
        command_override: Optional[str] = None,
        seed_override: Optional[int] = None,
    ) -> ExecutionResult:
        """Run a single execution trial under the given case configuration."""
        command = command_override or case.execution.command
        timeout = case.execution.timeout_seconds
        seed = seed_override if seed_override is not None else case.environment.seed
        workdir = case.environment.workdir or self.default_workdir

        # Set active perturbations
        if perturbation_overrides is not None:
            active_perturbations = dict(perturbation_overrides)
        else:
            active_perturbations = dict(case.perturbations)

        # Build environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["HARNESS_SEED"] = str(seed)
        env["HARNESS_CASE_ID"] = case.id
        env["HARNESS_PERTURBATIONS"] = json.dumps(active_perturbations, sort_keys=True)

        for k, v in case.environment.env_vars.items():
            env[str(k)] = str(v)

        for k, v in active_perturbations.items():
            env[f"HARNESS_PARAM_{k.upper()}"] = str(v)

        # Prepare input stdin payload (always close stdin with EOF so child does not block)
        stdin_data = b""
        if case.execution.input_payload is not None:
            stdin_data = json.dumps(case.execution.input_payload).encode("utf-8")

        start_time = time.perf_counter()
        timed_out = False
        stdout_str = ""
        stderr_str = ""
        exit_code = 0

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                env=env,
                input=stdin_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            stdout_str = proc.stdout.decode("utf-8", errors="replace")
            stderr_str = proc.stderr.decode("utf-8", errors="replace")
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            if exc.stdout:
                stdout_str = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout
            if exc.stderr:
                stderr_str = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        except Exception as exc:
            exit_code = -2
            stderr_str = f"Internal sandbox error executing command: {exc}"

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Classify outcome
        matched_error = False
        combined_output = stdout_str + "\n" + stderr_str
        if case.expected.error_match:
            try:
                matched_error = bool(re.search(case.expected.error_match, combined_output, re.IGNORECASE))
            except re.error:
                matched_error = case.expected.error_match in combined_output

        if timed_out:
            outcome = "timeout"
        elif exit_code != 0 or matched_error:
            outcome = "failure"
        else:
            outcome = "success"

        trace_hash = compute_trace_hash(exit_code, stdout_str, stderr_str, seed)

        return ExecutionResult(
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
            duration_ms=duration_ms,
            timed_out=timed_out,
            matched_error=matched_error,
            outcome=outcome,
            trace_hash=trace_hash,
            metadata={
                "command": command,
                "seed": seed,
                "active_perturbations": active_perturbations,
            },
        )
