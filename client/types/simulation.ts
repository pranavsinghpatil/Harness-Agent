export interface FaultScheduleItem {
  id: string;
  start_time: number;
  duration: number;
  target: string;
  type: string;
  intensity?: number;
  parameters?: Record<string, unknown>;
}

export interface Obstacle {
  id?: string;
  type: string;
  x: number;
  y: number;
  length?: number;
  width?: number;
  radius?: number;
  heading?: number;
  target_speed?: number;
  waypoints?: [number, number][];
}

export interface ScenarioDefinition {
  id: string;
  name?: string;
  description?: string;
  seed?: number;
  max_sim_time?: number;
  fault_schedule?: FaultScheduleItem[];
  world?: {
    goal?: [number, number];
    obstacles?: Obstacle[];
    arena_size?: [number, number];
    width?: number;
    height?: number;
    initial_state?: {
      x: number;
      y: number;
      heading: number;
      velocity: number;
    };
  };
  safety_thresholds?: {
    min_clearance?: number;
    speed_limit?: number;
    max_observation_age_s?: number;
  };
}

export interface VehicleState {
  x: number;
  y: number;
  velocity: number;
  heading: number;
  steering_angle?: number;
  steer_angle?: number;
}

export interface ActuatorCommand {
  throttle?: number;
  brake?: number;
  steering?: number;
  emergency_stop?: boolean;
}

export interface HardwareMetrics {
  cpu_utilization: number;
  temperature_celsius: number;
  is_throttled: boolean;
  deadline_misses: number;
  memory_used_mb?: number;
  queue_depth?: number;
}

export interface Violation {
  rule_name: string;
  description: string;
  sim_time?: number;
  timestamp?: number;
  step?: number;
  severity?: string;
  details?: Record<string, unknown>;
}

export interface DynamicObstacle {
  id: string;
  x: number;
  y: number;
  velocity?: number;
  heading?: number;
}

export interface TelemetryFrame {
  sim_time: number;
  step: number;
  vehicle_state: VehicleState;
  min_clearance: number;
  actuator_command: ActuatorCommand;
  hardware_metrics: HardwareMetrics;
  sensor_queue_depths: Record<string, number>;
  active_faults?: string[];
  new_violations?: Violation[];
  dynamic_obstacles?: DynamicObstacle[];
}

export interface RunManifest {
  run_id: string;
  trace_hash: string;
  violations_count: number;
  status: string;
  termination_reason?: string;
  duration?: number;
  steps?: number;
  sim_duration_seconds?: number;
  total_steps?: number;
}

export interface RunDetailsResponse {
  manifest: RunManifest;
  total_frames: number;
  frames: TelemetryFrame[];
}

export interface ReplayResponse {
  replayed_manifest: RunManifest;
  is_bit_exact_match: boolean;
  original_trace_hash: string;
  replayed_trace_hash: string;
  difference_details?: string | null;
  frames: TelemetryFrame[];
}

export interface HardwarePreset {
  id: string;
  name: string;
  architecture?: string;
  description?: string;
  cpu_cores?: number;
  frequency_ghz?: number;
  base_frequency_ghz?: number;
  tdp_watts?: number;
  thermal_limit_celsius?: number;
  thermal_throttle_temp_celsius?: number;
  memory_mb?: number;
  npu_tops?: number;
  transport_latencies_ms?: Record<string, number>;
  jitter_std_ms?: Record<string, number>;
}

export interface CausalChainNode {
  node_id: string;
  timestamp: number;
  category: string;
  summary: string;
  metrics?: Record<string, unknown>;
  evidence_event_ids?: string[];
}

export interface CausalLink {
  source: string;
  target: string;
  relation: string;
  confidence?: number;
  evidence?: Record<string, unknown>;
}

export interface CausalDiagnosticReport {
  report_id?: string;
  run_id?: string;
  evaluation_id?: string;
  created_at?: number;
  primary_root_cause?: string;
  root_causes?: string[];
  failure_chain?: string[];
  recommendations?: string[];
  patch_recommendations?: string[];
  causal_nodes?: CausalChainNode[];
  causal_links?: CausalLink[];
  causal_graph?: Record<string, string[]>;
  markdown_summary?: string;
}

export interface PatchProvenance {
  source_controller_hash?: string;
  diagnostic_report_id?: string;
  evidence_event_ids?: string[];
  strategy?: string;
  transformations_applied?: string[];
  rationale?: string;
}

export interface PatchResult {
  patch_id?: string;
  report_id?: string;
  patched_code: string;
  diff?: string;
  unified_diff?: string;
  strategies_applied?: string[];
  strategy_used?: string;
  explanation?: string;
  validation_status?: string;
  validation_message?: string;
  provenance?: PatchProvenance | null;
  is_valid_python?: boolean;
}

export interface HarnessRunData {
  run_id: string;
  evaluation_id?: string;
  episode_id?: string;
  status: string;
  controller_health?: string;
  task_completed?: boolean;
  distance_traveled_m?: number;
  sim_duration_s: number;
  wall_duration_s?: number;
  trace_hash: string;
  violations_count: number;
  violations?: Violation[];
  metrics?: Record<string, unknown>;
  events_count?: number;
  telemetry_frames?: Array<{
    sim_time: number;
    vehicle: {
      x: number;
      y: number;
      heading: number;
      velocity: number;
    };
    min_clearance: number;
    active_faults?: string[];
  }>;
}

export interface HarnessEvaluationResultData {
  evaluation_id: string;
  verdict?: "VERIFIED_SAFE" | "NOT_PROVEN_SAFE" | "SAFETY_VIOLATION" | "CONTROLLER_CRASHED" | "TASK_INCOMPLETE";
  is_safe_under_test_conditions: boolean;
  safety_pillar_passed?: boolean;
  behavior_pillar_passed?: boolean;
  runtime_health_pillar_passed?: boolean;
  baseline_passed: boolean;
  verification_passed: boolean;
  baseline_violations_count: number;
  verification_violations_count: number;
  min_clearance_baseline: number;
  min_clearance_verified: number;
  improvement_summary: string;
  audit_timestamp: number;
}

export interface VerificationResult {
  verification_run?: HarnessRunData;
  final_result?: HarnessEvaluationResultData | null;
}

export interface HarnessEvaluation {
  evaluation_id: string;
  created_at?: number;
  hardware_preset_id: string;
  scenario_id: string;
  seed: number;
  mode: string;
  status?: string;
  baseline_run?: HarnessRunData | null;
  diagnosis?: CausalDiagnosticReport | null;
  patch?: PatchResult | null;
  verification_run?: HarnessRunData | null;
  final_result?: HarnessEvaluationResultData | null;
}

// WebSocket Stream Message Interfaces
export interface WSFrameMessage {
  type: "frame";
  data: TelemetryFrame;
  status: string;
  is_finished: boolean;
}

export interface WSManifestMessage {
  type: "manifest";
  run_id: string;
  status: string;
  termination_reason?: string;
  duration: number;
  steps: number;
  violations_count: number;
  trace_hash: string;
}

export interface WSErrorMessage {
  type?: "error";
  error?: string;
  message?: string;
}

export type WSStreamMessage = WSFrameMessage | WSManifestMessage | WSErrorMessage;
