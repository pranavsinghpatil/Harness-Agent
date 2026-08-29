"""Model Context Protocol (MCP) server exposing canonical TrueForge Agent Harness tools."""

from __future__ import annotations
import json
import sys
from typing import Any, Dict, List, Optional

from harness.tools.canonical_tools import (
    list_hardware_profiles,
    inspect_scenario,
    inspect_safety_policy,
    create_experiment,
    run_experiment,
    diagnose_failure,
    auto_patch_controller,
    verify_patch,
    investigate_reliability,
)


class MCPServerHandler:
    """Dispatches JSON-RPC requests for MCP tools."""

    TOOLS_MANIFEST: List[Dict[str, Any]] = [
        {
            "name": "list_hardware_profiles",
            "description": "List all target edge hardware presets (e.g. D-Robotics RDK X5, NVIDIA Jetson Orin Nano, Raspberry Pi 5).",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "inspect_scenario",
            "description": "Inspect world layout, goal, obstacles, and default fault injection schedule for a scenario.",
            "inputSchema": {
                "type": "object",
                "properties": {"scenario_id": {"type": "string", "description": "Scenario ID to inspect"}},
                "required": ["scenario_id"],
            },
        },
        {
            "name": "inspect_safety_policy",
            "description": "Inspect invariant safety thresholds (clearance min, speed max, observation age max).",
            "inputSchema": {
                "type": "object",
                "properties": {"policy_id": {"type": "string", "default": "default"}},
            },
        },
        {
            "name": "create_experiment",
            "description": "Initialize a new Harness evaluation experiment binding target hardware, scenario, and controller code.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hardware_preset_id": {"type": "string", "default": "RDK_X5"},
                    "scenario_id": {"type": "string", "default": "showcase_perturbed_failure"},
                    "controller_code": {"type": "string", "description": "Optional target controller Python code"},
                    "seed": {"type": "integer", "default": 1337},
                },
            },
        },
        {
            "name": "run_experiment",
            "description": "Execute baseline simulation run for an evaluation experiment and record high-rate telemetry.",
            "inputSchema": {
                "type": "object",
                "properties": {"evaluation_id": {"type": "string", "description": "Unique evaluation ID"}},
                "required": ["evaluation_id"],
            },
        },
        {
            "name": "diagnose_failure",
            "description": "Reconstruct structured causal failure chain from telemetry frames and identify root causes.",
            "inputSchema": {
                "type": "object",
                "properties": {"evaluation_id": {"type": "string", "description": "Unique evaluation ID"}},
                "required": ["evaluation_id"],
            },
        },
        {
            "name": "auto_patch_controller",
            "description": "Synthesize a hardened, fail-safe Python controller with dynamic stopping distance and staleness guards.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "original_code": {"type": "string", "description": "Baseline controller code"},
                    "evaluation_id": {"type": "string", "description": "Optional evaluation ID for diagnostic context"},
                },
                "required": ["original_code"],
            },
        },
        {
            "name": "verify_patch",
            "description": "Re-execute simulation with patched controller on identical seed and fault schedule to verify safety.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "evaluation_id": {"type": "string", "description": "Unique evaluation ID"},
                    "patched_code": {"type": "string", "description": "Hardened controller source code"},
                },
                "required": ["evaluation_id", "patched_code"],
            },
        },
        {
            "name": "investigate_reliability",
            "description": "Autonomously choose, execute, and compare baseline, perturbation, boundary, and interaction experiments within a hard budget.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "objective": {"type": "string", "description": "Reliability question to investigate"},
                    "hardware_preset_id": {"type": "string", "default": "RDK_X5"},
                    "scenario_id": {"type": "string", "default": "showcase_normal_baseline"},
                    "controller_code": {"type": "string", "description": "Optional target controller Python code"},
                    "seed": {"type": "integer", "default": 1337},
                    "budget": {"type": "integer", "default": 12},
                    "max_boundary_steps": {"type": "integer", "default": 3},
                },
                "required": ["objective"],
            },
        },
    ]

    @classmethod
    def handle_call(cls, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Dispatch tool call to canonical Python implementation.

        Args:
            tool_name: Registered name of the tool to execute.
            arguments: Dictionary of arguments conforming to tool's inputSchema.

        Returns:
            Any: Serialized tool execution result dictionary or list.

        Raises:
            ValueError: If tool_name is unrecognized or required arguments are missing.
        """
        if tool_name == "list_hardware_profiles":
            return list_hardware_profiles()
        elif tool_name == "inspect_scenario":
            return inspect_scenario(arguments.get("scenario_id", "showcase_perturbed_failure"))
        elif tool_name == "inspect_safety_policy":
            return inspect_safety_policy(arguments.get("policy_id", "default"))
        elif tool_name == "create_experiment":
            return create_experiment(
                hardware_preset_id=arguments.get("hardware_preset_id", "RDK_X5"),
                scenario_id=arguments.get("scenario_id", "showcase_perturbed_failure"),
                controller_code=arguments.get("controller_code"),
                seed=arguments.get("seed", 1337),
            )
        elif tool_name == "run_experiment":
            return run_experiment(arguments["evaluation_id"])
        elif tool_name == "diagnose_failure":
            return diagnose_failure(arguments["evaluation_id"])
        elif tool_name == "auto_patch_controller":
            return auto_patch_controller(
                original_code=arguments["original_code"],
                evaluation_id=arguments.get("evaluation_id"),
            )
        elif tool_name == "verify_patch":
            return verify_patch(
                evaluation_id=arguments["evaluation_id"],
                patched_code=arguments["patched_code"],
            )
        elif tool_name == "investigate_reliability":
            return investigate_reliability(
                objective=arguments["objective"],
                hardware_preset_id=arguments.get("hardware_preset_id", "RDK_X5"),
                scenario_id=arguments.get("scenario_id", "showcase_normal_baseline"),
                controller_code=arguments.get("controller_code"),
                seed=arguments.get("seed", 1337),
                budget=arguments.get("budget", 12),
                max_boundary_steps=arguments.get("max_boundary_steps", 3),
            )
        else:
            raise ValueError(f"Unknown tool: '{tool_name}'")


def run_stdio_server() -> None:
    """Run JSON-RPC stdio loop for MCP clients.

    Reads newline-delimited JSON-RPC request objects from sys.stdin, dispatches
    matching tool calls, and writes JSON-RPC 2.0 response objects to sys.stdout.

    Side Effects:
        Reads standard input and writes standard output until EOF.
    """
    for line in sys.stdin:
        if not line.strip():
            continue
        msg_id: Optional[Any] = None
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")

            if method == "tools/list":
                response = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": MCPServerHandler.TOOLS_MANIFEST}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name", "")
                args = params.get("arguments", {})
                result = MCPServerHandler.handle_call(tool_name, args)
                response = {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
            else:
                response = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
