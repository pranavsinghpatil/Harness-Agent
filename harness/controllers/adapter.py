"""Dynamic controller loader compiling Python code into isolated BaseTargetAgent instances."""

from __future__ import annotations
from typing import Any, Dict, Optional, Type
import sys
import types

from target_agents.base import BaseTargetAgent
from target_agents.baseline.reactive_agent import ReactiveBaselineAgent
from target_agents.reference_agent.agent import ReferenceAutonomousAgent
from sandbox.actuators.command import ActuatorCommand
from harness.controllers.validator import ControllerValidator

# Alias VehicleCommand to ActuatorCommand for backward compatibility
VehicleCommand = ActuatorCommand


class ScriptFunctionAgentWrapper(BaseTargetAgent):
    """Wrapper adapting a standalone control(obs) function into the BaseTargetAgent lifecycle."""

    def __init__(self, agent_id: str, control_fn: Any) -> None:
        super().__init__(agent_id)
        self._control_fn = control_fn
        self._last_packets: list[Any] = []

    def reset(
        self,
        goal_x: float,
        goal_y: float,
        initial_x: float = 0.0,
        initial_y: float = 0.0,
        initial_heading: float = 0.0,
    ) -> None:
        pass

    def receive_sensor_packets(self, packets: list[Any], current_sim_time: float) -> None:
        self._last_packets = packets

    def step(self, current_sim_time: float) -> ActuatorCommand:
        try:
            cmd = self._control_fn(self._last_packets, current_sim_time)
            if isinstance(cmd, ActuatorCommand):
                return cmd
            if isinstance(cmd, dict):
                return ActuatorCommand(
                    throttle=float(cmd.get("throttle", 0.0)),
                    steering=float(cmd.get("steering", 0.0)),
                    brake=float(cmd.get("brake", 0.0)),
                    emergency_stop=bool(cmd.get("emergency_stop", False)),
                )
            return ActuatorCommand()
        except Exception:
            return ActuatorCommand(brake=1.0)


def _ensure_concrete_target_agent(cls_obj: Type[Any]) -> Type[BaseTargetAgent]:
    """Ensures class implements all abstract methods of BaseTargetAgent by supplying default stubs if omitted."""
    if not hasattr(cls_obj, "reset") or getattr(getattr(cls_obj, "reset", None), "__isabstractmethod__", False):
        def default_reset(
            self: Any,
            goal_x: float = 0.0,
            goal_y: float = 0.0,
            initial_x: float = 0.0,
            initial_y: float = 0.0,
            initial_heading: float = 0.0,
        ) -> None:
            pass
        cls_obj.reset = default_reset  # type: ignore

    if not hasattr(cls_obj, "receive_sensor_packets") or getattr(getattr(cls_obj, "receive_sensor_packets", None), "__isabstractmethod__", False):
        def default_receive_sensor_packets(self: Any, packets: list[Any], current_sim_time: float) -> None:
            pass
        cls_obj.receive_sensor_packets = default_receive_sensor_packets  # type: ignore

    if not hasattr(cls_obj, "step") or getattr(getattr(cls_obj, "step", None), "__isabstractmethod__", False):
        def default_step(self: Any, current_sim_time: float) -> ActuatorCommand:
            return ActuatorCommand()
        cls_obj.step = default_step  # type: ignore

    # Clear abstract methods set so Python's ABCMeta allows instantiation
    cls_obj.__abstractmethods__ = frozenset()
    return cls_obj


class DynamicControllerLoader:
    """Safely compiles and instantiates BaseTargetAgent implementations from Python code."""

    @classmethod
    def load_from_code(cls, source_code: str, agent_id: str = "custom_controller") -> BaseTargetAgent:
        """Compile and instantiate a target controller from code.

        Args:
            source_code: Python source code string.
            agent_id: Assigned agent identifier string.

        Returns:
            Instantiated BaseTargetAgent instance ready for simulation.

        Raises:
            ValueError: If code fails validation or cannot be compiled.
        """
        val_result = ControllerValidator.validate_code(source_code)
        if not val_result.is_valid:
            raise ValueError(f"Controller code validation failed: {'; '.join(val_result.errors)}")

        module_namespace: Dict[str, Any] = {
            "BaseTargetAgent": BaseTargetAgent,
            "ReactiveBaselineAgent": ReactiveBaselineAgent,
            "ReferenceAutonomousAgent": ReferenceAutonomousAgent,
            "ActuatorCommand": ActuatorCommand,
            "VehicleCommand": VehicleCommand,
            "__name__": f"dynamic_controller_{agent_id}",
        }

        try:
            compiled_code = compile(source_code, f"<controller_{agent_id}>", "exec")
            exec(compiled_code, module_namespace)
        except Exception as e:
            raise ValueError(f"Failed to compile controller source code: {str(e)}") from e

        # 1. Look for BaseTargetAgent subclass
        if val_result.entrypoint_class_name and val_result.entrypoint_class_name in module_namespace:
            target_cls = module_namespace[val_result.entrypoint_class_name]
            if isinstance(target_cls, type) and issubclass(target_cls, BaseTargetAgent):
                concrete_cls = _ensure_concrete_target_agent(target_cls)
                return concrete_cls(agent_id=agent_id)

        # 2. Search all classes in module namespace
        for name, obj in module_namespace.items():
            if isinstance(obj, type) and issubclass(obj, BaseTargetAgent) and obj is not BaseTargetAgent:
                concrete_cls = _ensure_concrete_target_agent(obj)
                return concrete_cls(agent_id=agent_id)

        # 3. Look for standalone control function
        for fn_name in ("control", "compute_control", "step"):
            if fn_name in module_namespace and callable(module_namespace[fn_name]):
                return ScriptFunctionAgentWrapper(agent_id=agent_id, control_fn=module_namespace[fn_name])

        # Fallback to reference agent
        return ReferenceAutonomousAgent(agent_id=agent_id)
