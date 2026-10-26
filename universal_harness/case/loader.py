"""Loader and serializer for FailureCase specifications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union
import yaml

from universal_harness.case.schema import FailureCase


def load_failure_case(source: Union[str, Path]) -> FailureCase:
    """Load a FailureCase from a file path or serialized string."""
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        path = Path(source)
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    else:
        # String content
        try:
            data = json.loads(source)
        except Exception:
            data = yaml.safe_load(source)

    if not isinstance(data, dict):
        raise ValueError("Invalid FailureCase document: root must be a mapping dictionary")

    return FailureCase.model_validate(data)


def save_failure_case(case: FailureCase, path: Union[str, Path], format: str = "yaml") -> Path:
    """Serialize a FailureCase to a file path."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    data = case.model_dump(exclude_none=True)
    if format.lower() in ("yaml", "yml"):
        content = yaml.dump(data, sort_keys=False, indent=2)
    elif format.lower() == "json":
        content = json.dumps(data, indent=2)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'yaml' or 'json'.")

    dest.write_text(content, encoding="utf-8")
    return dest
