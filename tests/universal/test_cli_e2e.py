"""End-to-end integration tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from universal_harness.cli import main


def test_cli_replay_command(capsys) -> None:
    exit_code = main(["replay", "examples/cases/checkout_case.yaml", "--trials", "2", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["case_id"] == "checkout-type-error"
    assert data["reproduced_count"] == 2
    assert data["reproduction_rate"] == 1.0


def test_cli_minimize_command(capsys) -> None:
    exit_code = main(["minimize", "examples/cases/checkout_case.yaml", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["reproduced_with_minimal"] is True


def test_cli_verify_command(capsys) -> None:
    exit_code = main([
        "verify",
        "examples/cases/checkout_case.yaml",
        "--candidate",
        "python -m examples.fixtures.payment_service_fixed",
        "--json",
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["overall_verdict"] == "VERIFIED"
    assert data["failure_resolved"] is True


def test_cli_import_command(tmp_path: Path) -> None:
    out_file = tmp_path / "imported.yaml"
    exit_code = main([
        "import",
        "--source",
        "autter",
        "examples/cases/autter_incident.json",
        "--out",
        str(out_file),
    ])
    assert exit_code == 0
    assert out_file.exists()


def test_cli_report_command(tmp_path: Path) -> None:
    exit_code = main([
        "report",
        "examples/cases/checkout_case.yaml",
        "--candidate",
        "python -m examples.fixtures.payment_service_fixed",
        "--out-dir",
        str(tmp_path),
    ])
    assert exit_code == 0
    manifests = list(tmp_path.rglob("manifest.json"))
    reports = list(tmp_path.rglob("report.md"))
    assert len(manifests) == 1
    assert len(reports) == 1
