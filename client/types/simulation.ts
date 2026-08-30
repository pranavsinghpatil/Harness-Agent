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
  id?: string;
  obstacle_id?: string;
  x: number;
  y: number;
  radius?: number;
  velocity?: number;
  heading?: number;
  obstacle_type?: string;
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
  telemetry_frames?: TelemetryFrame[];
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
export type InvestigationSessionStatus = "CREATED" | "RUNNING" | "COMPLETED" | "FAILED";

export type InvestigationPhase =
  | "INVESTIGATING"
  | "DIAGNOSING"
  | "PATCH_PROPOSED"
  | "AWAITING_APPROVAL"
  | "VERIFYING"
  | "REGRESSING"
  | "PATCH_REJECTED"
  | "COMPLETED"
  | "FAILED";

export type HarnessEventType =
  | "INVESTIGATION_CREATED"
  | "INVESTIGATION_STARTED"
  | "EXPERIMENT_PLANNED"
  | "EXPERIMENT_STARTED"
  | "EXPERIMENT_COMPLETED"
  | "EVIDENCE_CAPTURED"
  | "HYPOTHESIS_UPDATED"
  | "FALSIFICATION_PROPOSED"
  | "DECISION_RECORDED"
  | "NEXT_EXPERIMENT_SELECTED"
  | "INVESTIGATION_COMPLETED"
  | "INVESTIGATION_FAILED"
  | "SIMULATION_STARTED"
  | "SIMULATION_STEP"
  | "SIMULATION_TERMINATED"
  | "FAULT_INJECTED"
  | "FAULT_REVERTED"
  | "SENSOR_SAMPLED"
  | "PACKET_QUEUED"
  | "PACKET_DELIVERED"
  | "PACKET_DROPPED"
  | "TASK_SCHEDULED"
  | "PERCEPTION_TASK_SCHEDULED"
  | "CONTROLLER_TASK_SCHEDULED"
  | "OBSERVATION_AVAILABLE"
  | "TASK_REJECTED"
  | "COMPUTE_STARTED"
  | "TASK_COMPLETED"
  | "DEADLINE_MISSED"
  | "THERMAL_THROTTLED"
  | "COMMAND_ISSUED"
  | "ACTUATOR_APPLIED"
  | "CONTROLLER_EXCEPTION"
  | "CONTROLLER_CRASHED"
  | "INVARIANT_BREACHED"
  | "COLLISION_DETECTED"
  | "CLEARANCE_WARNING"
  | "DIAGNOSIS_COMPLETED"
  | "PATCH_GENERATED"
  | "PATCH_APPROVAL_REQUESTED"
  | "PATCH_APPROVED"
  | "PATCH_REJECTED"
  | "VERIFICATION_PASSED"
  | "VERIFICATION_FAILED"
  | "REGRESSION_STARTED"
  | "REGRESSION_COMPLETED"
  | "CONCLUSION_RECORDED";

export type EventSeverity = "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface HarnessEvent {
  evaluation_id: string;
  run_id: string;
  episode_id: string;
  event_id: string;
  sim_time: number;
  wall_time: number;
  investigation_id: string;
  experiment_id?: string;
  source: string;
  type: HarnessEventType;
  severity: EventSeverity;
  payload: Record<string, unknown>;
}

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

export interface PatchApproval {
  investigation_id: string;
  patch_id: string;
  decision: "APPROVE" | "REJECT" | string;
  reviewed_by: string;
  reason?: string;
  decided_at?: number;
}

export interface RegressionCase {
  evaluation_id: string;
  passed: boolean;
  violations_count: number;
  status: string;
  trace_hash: string;
  scenario_id?: string;
  experiment_id?: string;
  min_clearance?: number;
  [key: string]: unknown;
}

export interface InvestigationConclusion {
  outcome: string;
  leading_hypothesis?: Hypothesis | Record<string, unknown> | null;
  failure_boundary?: Record<string, unknown> | null;
  causal_chain?: CausalChainNode[];
  counterexample?: Record<string, unknown> | null;
  proposed_patch?: PatchResult | null;
  approval?: PatchApproval | null;
  verification?: Record<string, unknown> | null;
  regression?: RegressionCase[];
  limitations?: string[];
  completed_at?: number;
}

export interface AuditReceipt {
  receipt_version: string;
  generated_at: number;
  investigation: {
    investigation_id: string;
    objective: string;
    scenario_id: string;
    hardware_preset_id: string;
    seed: number;
    outcome: string;
    completed_at?: number;
  };
  leading_hypothesis?: {
    hypothesis_id?: string;
    statement?: string;
    confidence?: number;
    variables?: string[];
    supporting_experiments?: string[];
    contradicting_experiments?: string[];
  } | null;
  diagnosis?: {
    primary_root_cause?: string;
    causal_nodes?: CausalChainNode[];
    recommendations?: string[];
  } | null;
  patch?: {
    patch_id?: string;
    strategy?: string;
    transformations_applied?: string[];
    unified_diff?: string;
    diff?: string;
  } | null;
  approval?: {
    reviewed_by?: string;
    decision?: string;
    reason?: string;
    decided_at?: number;
  } | null;
  three_pillars: {
    pillar_1_safety: {
      name: string;
      status: "PASS" | "FAIL" | "PENDING";
      details: string;
      min_clearance?: number;
      violations_count?: number;
    };
    pillar_2_behavior: {
      name: string;
      status: "PASS" | "FAIL" | "PENDING";
      details: string;
    };
    pillar_3_health: {
      name: string;
      status: "PASS" | "FAIL" | "PENDING";
      details: string;
      controller_health?: string;
    };
  };
  verification?: {
    evaluation_id?: string;
    run_id?: string;
    trace_hash?: string;
    status?: string;
    violations_count?: number;
    min_clearance?: number;
  } | null;
  regression_matrix: RegressionCase[];
  cryptographic_proof: {
    verification_trace_hash?: string;
    regression_trace_hashes: { case_id: string; trace_hash: string; passed: boolean }[];
    bit_exact_reproducible: boolean;
    verification_statement: string;
  };
  limitations: string[];
}

export interface InvestigationSessionSnapshot {
  investigation_id: string;
  status: InvestigationSessionStatus;
  phase: InvestigationPhase;
  objective: string;
  scenario_id: string;
  hardware_preset_id: string;
  seed: number;
  budget: number;
  max_sim_time?: number | null;
  created_at: number;
  started_at?: number | null;
  finished_at?: number | null;
  event_count: number;
  error?: string | null;
  current_phase?: string | null;
  current_experiment?: ExperimentCandidate | null;
  completed_experiments?: number;
  budget_remaining?: number;
  active_hypothesis?: Hypothesis | null;
  leading_hypothesis?: Hypothesis | null;
  latest_decision?: DecisionTrace | null;
  latest_failure?: Record<string, unknown> | null;
  diagnosis?: CausalDiagnosticReport | null;
  patch?: PatchResult | null;
  approval?: PatchApproval | null;
  verification?: Record<string, unknown> | null;
  regression?: RegressionCase[];
  conclusion?: InvestigationConclusion | null;
  result?: InvestigationResult | null;
}


