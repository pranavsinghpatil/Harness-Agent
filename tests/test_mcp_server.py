"""Unit tests for MCP server tools dispatch and canonical tool contracts."""

from __future__ import annotations
from mcp_server.server import MCPServerHandler


def test_mcp_list_hardware_profiles() -> None:
    """Verify MCP list_hardware_profiles tool."""
    res = MCPServerHandler.handle_call("list_hardware_profiles", {})
    assert isinstance(res, list)
    assert any(p["id"] == "RDK_X5" for p in res)


def test_mcp_inspect_scenario() -> None:
    """Verify MCP inspect_scenario tool."""
    res = MCPServerHandler.handle_call(
        "inspect_scenario", {"scenario_id": "showcase_perturbed_failure"}
    )
    assert res["id"] == "showcase_perturbed_failure"
    assert "world" in res
    assert len(res["fault_schedule"]) > 0


def test_mcp_create_run_diagnose_patch_verify_flow() -> None:
    """Verify full step-by-step MCP tool calls pipeline."""
    # 1. create_experiment
    exp = MCPServerHandler.handle_call(
        "create_experiment",
        {
            "hardware_preset_id": "RDK_X5",
            "scenario_id": "showcase_perturbed_failure",
            "seed": 1337,
        },
    )
    eval_id = exp["evaluation_id"]
    assert eval_id.startswith("eval_")

    # 2. run_experiment
    run_res = MCPServerHandler.handle_call("run_experiment", {"evaluation_id": eval_id})
    assert run_res["status"] == "SAFETY_VIOLATION"

    # 3. diagnose_failure
    diag_res = MCPServerHandler.handle_call("diagnose_failure", {"evaluation_id": eval_id})
    assert diag_res["report_id"].startswith("diag_")
    assert len(diag_res["causal_nodes"]) > 0

    # 4. auto_patch_controller
    patch_res = MCPServerHandler.handle_call(
        "auto_patch_controller",
        {"original_code": "# Original controller", "evaluation_id": eval_id},
    )
    assert patch_res["patched_code"] != ""

    # 5. verify_patch
    verify_res = MCPServerHandler.handle_call(
        "verify_patch",
        {"evaluation_id": eval_id, "patched_code": patch_res["patched_code"]},
    )
    assert verify_res["verification_run"]["status"] == "COMPLETED"
    assert verify_res["final_result"]["is_safe_under_test_conditions"] is True
