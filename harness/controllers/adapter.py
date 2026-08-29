"""Dynamic controller loader compiling Python code into isolated BaseTargetAgent instances."""

from __future__ import annotations
import inspect
import math
from typing import Any, Dict, Optional, Type

from target_agents.base import BaseTargetAgent
from target_agents.baseline.reactive_agent import ReactiveBaselineAgent
from target_agents.reference_agent.agent import ReferenceAutonomousAgent
from sandbox.actuators.command import ActuatorCommand
from sandbox.sensors.packet import SensorPacket
from harness.controllers.validator import ControllerValidator
from harness.models.evaluation import ControllerHealth

# Alias VehicleCommand to ActuatorCommand for backward compatibility
VehicleCommand = ActuatorCommand


def _safe_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    """Restricted __import__ hook preventing forbidden modules from being imported dynamically."""
    mod_root = name.split(".")[0]
    if mod_root in ControllerValidator.DISALLOWED_MODULES:
        raise ImportError(f"Import of module '{name}' is disallowed by security policy.")
    return __import__(name, globals, locals, fromlist, level)


# Whitelisted execution built-ins for safe dynamic compilation
SAFE_BUILTINS: Dict[str, Any] = {
    "__import__": _safe_import,
    "__build_class__": __build_class__,
    "super": super,
    "classmethod": classmethod,
    "staticmethod": staticmethod,
    "property": property,
    "object": object,
    "abs": abs, "min": min, "max": max, "round": round, "len": len,
    "range": range, "enumerate": enumerate, "zip": zip,
    "isinstance": isinstance, "issubclass": issubclass, "hasattr": hasattr,
    "float": float, "int": int, "str": str, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "None": None, "True": True, "False": False,
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "IndexError": IndexError, "KeyError": KeyError, "AttributeError": AttributeError,
}


class ScriptFunctionAgentWrapper(BaseTargetAgent):
    """Wrapper adapting a standalone control or step function into the BaseTargetAgent lifecycle."""

    def __init__(self, agent_id: str, control_fn: Any) -> None:
        super().__init__(agent_id)
        self._control_fn = control_fn
        self._last_packets: list[Any] = []
        self.health: ControllerHealth = ControllerHealth.HEALTHY
        self.last_exception: Optional[str] = None
        self.failsafe_activated: bool = False
        try:
            self._param_count = len(inspect.signature(control_fn).parameters)
        except Exception:
            self._param_count = 1

    def reset(
        self,
        goal_x: float = 0.0,
        goal_y: float = 0.0,
        initial_x: float = 0.0,
        initial_y: float = 0.0,
        initial_heading: float = 0.0,
    ) -> None:
        """Reset internal packet buffer and controller health state."""
        self._last_packets = []
        self.health = ControllerHealth.HEALTHY
        self.last_exception = None
        self.failsafe_activated = False

    def receive_sensor_packets(self, packets: list[Any], current_sim_time: float) -> None:
        """Store delivered sensor packets for consumption in step()."""
        self._last_packets = packets

    def step(self, current_sim_time: float) -> ActuatorCommand:
        """Dispatch step call to the standalone function matching its parameter signature."""
        try:
            if self._param_count == 1:
                cmd = self._control_fn(current_sim_time)
            elif self._param_count == 2:
                cmd = self._control_fn(self._last_packets, current_sim_time)
            else:
                cmd = self._control_fn(current_sim_time)

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
        except Exception as e:
            self.health = ControllerHealth.EXCEPTION_RAISED
            self.last_exception = str(e)
            self.failsafe_activated = True
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
            "__builtins__": SAFE_BUILTINS,
            "math": math,
            "BaseTargetAgent": BaseTargetAgent,
            "ReactiveBaselineAgent": ReactiveBaselineAgent,
            "ReferenceAutonomousAgent": ReferenceAutonomousAgent,
            "ActuatorCommand": ActuatorCommand,
            "VehicleCommand": VehicleCommand,
            "SensorPacket": SensorPacket,
            "__name__": f"dynamic_controller_{agent_id}",
        }

        try:
            compiled_code = compile(source_code, f"<controller_{agent_id}>", "exec")
            exec(compiled_code, module_namespace)
        except Exception as e:
            raise ValueError(f"Failed to compile controller source code: {str(e)}") from e

        if val_result.entrypoint_class_name and val_result.entrypoint_class_name in module_namespace:
            target_cls = module_namespace[val_result.entrypoint_class_name]
            if isinstance(target_cls, type) and issubclass(target_cls, BaseTargetAgent):
                concrete_cls = _ensure_concrete_target_agent(target_cls)
                return concrete_cls(agent_id=agent_id)

        for name, obj in module_namespace.items():
            if isinstance(obj, type) and issubclass(obj, BaseTargetAgent) and obj not in (BaseTargetAgent, ReactiveBaselineAgent, ReferenceAutonomousAgent):
                concrete_cls = _ensure_concrete_target_agent(obj)
                return concrete_cls(agent_id=agent_id)

        for fn_name in ("control", "compute_control", "step"):
            if fn_name in module_namespace and callable(module_namespace[fn_name]):
                return ScriptFunctionAgentWrapper(agent_id=agent_id, control_fn=module_namespace[fn_name])

        return ReferenceAutonomousAgent(agent_id=agent_id)
