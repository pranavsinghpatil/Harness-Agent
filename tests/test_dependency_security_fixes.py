"""Guards the CVE-fix dependency bumps applied in this change.

Fails on the pre-fix manifests and passes once the listed packages are pinned
to their fixed versions (next, sharp, source-map-js, zod, brace-expansion,
fastapi).
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENT = REPO_ROOT / "client"


def _read_json(path):
    return json.loads(path.read_text())


def test_next_pinned_to_fixed_version():
    pkg = _read_json(CLIENT / "package.json")
    assert pkg["dependencies"]["next"] == "15.5.28"


def test_lockfile_resolves_vulnerable_packages_to_fixed_versions():
    lock = _read_json(CLIENT / "package-lock.json")
    pkgs = lock["packages"]
    assert pkgs["node_modules/next"]["version"] == "15.5.28"
    assert pkgs["node_modules/sharp"]["version"] == "0.35.5"
    assert pkgs["node_modules/source-map-js"]["version"] == "1.2.2"
    assert pkgs["node_modules/zod"]["version"] == "4.6.6"
    assert pkgs["node_modules/brace-expansion"]["version"] == "5.0.10"


def test_fastapi_pinned_to_security_fix_commit():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    assert "9d34ad0ee8a0dfbbcce06f76c2d5d851085024fc" in pyproject
