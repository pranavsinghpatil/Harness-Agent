"""Syntax, interface, and security validation for user-submitted target controller code."""

from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class ControllerValidationResult:
    """Outcome of controller source code validation.

    Attributes:
        is_valid: True if syntax and security checks pass.
        has_base_agent_class: True if a subclass of BaseTargetAgent was found.
        has_control_function: True if a top-level or method control() exists.
        entrypoint_class_name: Name of the controller class if found.
        errors: List of syntax or validation error strings.
        warnings: List of advisory warnings.
    """
    is_valid: bool
    has_base_agent_class: bool = False
    has_control_function: bool = False
    entrypoint_class_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ControllerValidator:
    """Validates Python controller code against syntax rules and target agent contracts."""

    DISALLOWED_MODULES: Set[str] = {
        "os", "sys", "subprocess", "socket", "shutil", "requests", "urllib",
        "http", "importlib", "ctypes", "threading", "multiprocessing", "pty",
    }
    DISALLOWED_CALLS: Set[str] = {
        "__import__", "eval", "exec", "open", "compile", "getattr", "setattr",
        "delattr", "globals", "locals", "input", "breakpoint",
    }
    DISALLOWED_ATTRS: Set[str] = {
        "__subclasses__", "__bases__", "__mro__", "__globals__", "__code__", "__builtins__",
    }

    @classmethod
    def validate_code(cls, source_code: str) -> ControllerValidationResult:
        """Parse and validate controller code against security rules and structural contracts.

        Args:
            source_code: Python script string to inspect.

        Returns:
            ControllerValidationResult containing validity boolean, errors, and metadata.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not source_code or not source_code.strip():
            return ControllerValidationResult(
                is_valid=False, errors=["Empty controller source code supplied."]
            )

        try:
            tree = ast.parse(source_code, filename="<target_controller>")
        except SyntaxError as e:
            return ControllerValidationResult(
                is_valid=False,
                errors=[f"Syntax error at line {e.lineno}, col {e.offset}: {e.msg}"],
            )

        has_base_agent_class = False
        has_control_function = False
        entrypoint_class = ""

        for node in ast.walk(tree):
            cls._check_disallowed_imports(node, errors)
            cls._check_disallowed_calls_and_attrs(node, errors)

            if isinstance(node, ast.ClassDef):
                if cls._is_target_agent_class(node):
                    has_base_agent_class = True
                    entrypoint_class = node.name
                if any(isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in ("step", "control", "compute_action") for item in node.body):
                    has_control_function = True

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ("control", "compute_control", "step"):
                has_control_function = True

        if not has_base_agent_class and not has_control_function:
            warnings.append("Code does not explicitly subclass BaseTargetAgent or define a control function.")

        return ControllerValidationResult(
            is_valid=(len(errors) == 0),
            has_base_agent_class=has_base_agent_class,
            has_control_function=has_control_function,
            entrypoint_class_name=entrypoint_class,
            errors=errors,
            warnings=warnings,
        )

    @classmethod
    def _check_disallowed_imports(cls, node: ast.AST, errors: List[str]) -> None:
        """Inspects import nodes against the restricted module blacklist."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split(".")[0]
                if mod_root in cls.DISALLOWED_MODULES:
                    errors.append(f"Disallowed import detected: '{alias.name}'.")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_root = node.module.split(".")[0]
                if mod_root in cls.DISALLOWED_MODULES:
                    errors.append(f"Disallowed from-import detected: '{node.module}'.")

    @classmethod
    def _check_disallowed_calls_and_attrs(cls, node: ast.AST, errors: List[str]) -> None:
        """Inspects AST calls and attribute accesses for sandbox escape attempts."""
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", None)
            if func_name in cls.DISALLOWED_CALLS:
                errors.append(f"Disallowed built-in function call: '{func_name}()'.")
        elif isinstance(node, ast.Attribute) and node.attr in cls.DISALLOWED_ATTRS:
            errors.append(f"Disallowed dunder attribute access: '{node.attr}'.")

    @classmethod
    def _is_target_agent_class(cls, node: ast.ClassDef) -> bool:
        """Determines if a class definition subclasses a recognized BaseTargetAgent variant."""
        for base in node.bases:
            base_id = getattr(base, "id", None) or getattr(base, "attr", None)
            if base_id in ("BaseTargetAgent", "ReactiveBaselineAgent", "ReferenceAutonomousAgent"):
                return True
        return False
