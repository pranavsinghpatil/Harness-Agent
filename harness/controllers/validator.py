"""Syntax, interface, and safety validation for user-submitted target controller code."""

from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import List, Tuple, Set


@dataclass
class ControllerValidationResult:
    """Outcome of controller source code validation.

    Attributes:
        is_valid: True if syntax and safety checks pass.
        has_base_agent_class: True if a subclass of BaseTargetAgent was found.
        has_control_function: True if a top-level or method control() exists.
        entrypoint_class_name: Name of the controller class if found.
        errors: List of syntax or validation error strings.
        warnings: List of advisory warnings (e.g. unhandled sensor types).
    """
    is_valid: bool
    has_base_agent_class: bool = False
    has_control_function: bool = False
    entrypoint_class_name: str = ""
    errors: List[str] = ()
    warnings: List[str] = ()


class ControllerValidator:
    """Validates Python controller code against syntax rules and target agent contracts."""

    # Disallowed dangerous built-ins and libraries
    DISALLOWED_MODULES: Set[str] = {"subprocess", "socket", "os.system", "shutil", "requests", "urllib"}

    @classmethod
    def validate_code(cls, source_code: str) -> ControllerValidationResult:
        """Parse and validate controller code.

        Args:
            source_code: Python script string.

        Returns:
            ControllerValidationResult containing validity status and details.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not source_code or not source_code.strip():
            return ControllerValidationResult(
                is_valid=False, errors=["Empty controller source code supplied."]
            )

        # 1. Syntax Check via AST
        try:
            tree = ast.parse(source_code, filename="<target_controller>")
        except SyntaxError as e:
            return ControllerValidationResult(
                is_valid=False,
                errors=[f"Syntax error at line {e.lineno}, col {e.offset}: {e.msg}"],
            )

        # 2. Inspect AST nodes for safety and structure
        has_base_agent_class = False
        has_control_function = False
        entrypoint_class = ""

        for node in ast.walk(tree):
            # Check for disallowed imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.DISALLOWED_MODULES:
                        errors.append(f"Disallowed import detected: '{alias.name}'.")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in cls.DISALLOWED_MODULES:
                    errors.append(f"Disallowed from-import detected: '{node.module}'.")

            # Check for BaseTargetAgent or controller classes
            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_id = getattr(base, "id", None) or getattr(base, "attr", None)
                    if base_id in ("BaseTargetAgent", "ReactiveBaselineAgent", "ReferenceAutonomousAgent"):
                        has_base_agent_class = True
                        entrypoint_class = node.name

                # Check methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in ("step", "control", "compute_action"):
                        has_control_function = True

            # Check for standalone control function
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in ("control", "compute_control", "step"):
                    has_control_function = True

        if not has_base_agent_class and not has_control_function:
            warnings.append(
                "Code does not explicitly subclass BaseTargetAgent or define a control() function. A generic wrapper will be applied."
            )

        is_valid = len(errors) == 0
        return ControllerValidationResult(
            is_valid=is_valid,
            has_base_agent_class=has_base_agent_class,
            has_control_function=has_control_function,
            entrypoint_class_name=entrypoint_class,
            errors=errors,
            warnings=warnings,
        )
