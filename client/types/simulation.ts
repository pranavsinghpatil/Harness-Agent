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

// ==========================================
// System 1 & System 2 Autonomous Investigator Types
// ==========================================
export type ExperimentPhase = "BASELINE" | "SCREEN" | "BOUNDARY" | "INTERACTION";
export type HypothesisStatus = "ACTIVE" | "SUPPORTED" | "REFUTED";
export type InvestigationStatus = "COMPLETE" | "BUDGET_EXHAUSTED" | "PARTIAL" | "IN_PROGRESS";

export interface PlannerDimension {
  id: string;
  baseline: number;
  minimum: number;
  maximum: number;
  higher_is_worse: boolean;
  unit: string;
}

export interface ExperimentCandidate {
  experiment_id: string;
  values: Record<string, number>;
  phase: ExperimentPhase;
  rationale: string;
  parent_experiment_ids: string[];
}

export interface ExperimentOutcome {
  passed: boolean;
  violation_count: number;
  min_clearance: number;
  trace_hash: string;
  details: {
    run_id?: string;
    status?: string;
    controller_health?: string;
    task_completed?: boolean;
    execution_error?: string;
    execution_stage?: string;
    metrics?: Record<string, unknown>;
  };
}

export interface EvidenceSignal {
  name: string;
  value: number;
  unit: string;
  sim_time: number;
  frame_index: number;
  step: number;
  source: string;
}

export interface EvidenceLink {
  event_id: string;
  evaluation_id: string;
  episode_id: string;
  event_type: string;
  source: string;
  sim_time: number;
  severity: string;
  wall_time: number;
  payload: Record<string, unknown>;
}

export interface EvidenceSnapshot {
  run_id: string;
  trace_hash: string;
  signals: EvidenceSignal[];
  event_links: EvidenceLink[];
}

export interface DecisionTrace {
  experiment_id: string;
  phase: ExperimentPhase;
  action: string;
  pre_execution_hypothesis_ids: string[];
  post_observation_hypothesis_ids: string[];
  refuted_hypothesis_ids: string[];
  post_observation_leading_hypothesis_id: string | null;
  information_gain_estimate: number;
  outcome_classification: "PASS" | "SAFETY_VIOLATION" | "RUN_FAILURE" | "CONTROLLER_UNHEALTHY" | "TASK_INCOMPLETE" | "EXECUTION_ERROR" | "UNCLASSIFIED_FAILURE";
  observation: string;
  rationale: string;
  next_experiment_id: string | null;
  next_action: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  statement: string;
  variables: string[];
  supporting_experiment_ids: string[];
  contradicting_experiment_ids: string[];
  confidence: number;
  predicted_outcome: string;
  status: HypothesisStatus;
}

export interface FalsificationPlan {
  hypothesis_id: string;
  values: Record<string, number>;
  rationale: string;
  expected_outcome: string;
}

export interface InvestigationRun {
  evaluation_id: string;
  experiment: ExperimentCandidate;
  outcome: ExperimentOutcome;
  evidence: EvidenceSnapshot | null;
  decision_trace: DecisionTrace | null;
}

export interface InvestigationResult {
  investigation_id: string;
  objective: string;
  scenario_id: string;
  hardware_preset_id: string;
  seed: number;
  status: InvestigationStatus;
  run_limit: number | null;
  runs: InvestigationRun[];
  planner: {
    budget: number;
    remaining_budget: number;
    seed: number;
    pending_experiment: ExperimentCandidate | null;
    summary: {
      total_experiments: number;
      passed_experiments: number;
      failed_experiments: number;
      tested_dimensions: string[];
      unproven_dimensions: string[];
    };
  };
  evidence: {
    total_experiments: number;
    passed_experiments: number;
    failed_experiments: number;
    tested_dimensions: string[];
    unproven_dimensions: string[];
  };
  hypotheses: {
    hypotheses: Hypothesis[];
  };
  falsification_plans: FalsificationPlan[];
  decision_trace: DecisionTrace[];
}
