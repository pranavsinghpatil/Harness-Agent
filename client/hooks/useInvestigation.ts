"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  InvestigationSessionSnapshot,
  InvestigationSessionStatus,
  InvestigationPhase,
  HarnessEvent,
  Hypothesis,
  ExperimentCandidate,
  DecisionTrace,
  InvestigationRun,
  FalsificationPlan,
  CausalDiagnosticReport,
  PatchResult,
  PatchApproval,
  InvestigationConclusion,
  RegressionCase,
  TelemetryFrame,
  VehicleState,
  ExperimentOutcome,
  EvidenceSnapshot,
  ExperimentPhase,
} from "../types/simulation";
import {
  startInvestigation,
  getInvestigation,
  getInvestigationEvents,
  approveInvestigationPatch,
  getEvaluation,
  InvestigationPayload,
} from "../lib/api";
import { InvestigationStreamClient } from "../lib/websocket";

export const MAX_EVENTS_BUFFER = 500;
export const BATCH_FLUSH_INTERVAL_MS = 50;

export interface UseInvestigationState {
  investigationId: string | null;
  snapshot: InvestigationSessionSnapshot | null;
  status: InvestigationSessionStatus;
  phase: InvestigationPhase;
  objective: string;
  hardwarePresetId: string;
  scenarioId: string;
  seed: number;
  budget: number;
  completedExperiments: number;
  currentExperiment: ExperimentCandidate | null;
  activeHypothesis: Hypothesis | null;
  leadingHypothesis: Hypothesis | null;
  hypotheses: Hypothesis[];
  runs: InvestigationRun[];
  decisionTraces: DecisionTrace[];
  falsificationPlans: FalsificationPlan[];
  events: HarnessEvent[];
  latestFailure: Record<string, unknown> | InvestigationRun | null;
  diagnosis: CausalDiagnosticReport | null;
  patch: PatchResult | null;
  approval: PatchApproval | null;
  verification: Record<string, unknown> | null;
  regression: RegressionCase[];
  conclusion: InvestigationConclusion | null;
  connectionStatus: "IDLE" | "CONNECTING" | "OPEN" | "CLOSED" | "ERROR";
  error: string | null;
  isLoading: boolean;
  activeExperimentFrames: TelemetryFrame[];
  allExperimentFrames: Record<string, TelemetryFrame[]>;
  latestTelemetry: TelemetryFrame | null;
}

interface EventPayloadData {
  experiment?: ExperimentCandidate;
  experiment_id?: string;
  values?: Record<string, number>;
  phase?: ExperimentPhase;
  rationale?: string;
  parent_experiment_ids?: string[];
  frame?: TelemetryFrame;
  telemetry_frame?: TelemetryFrame;
  vehicle_state?: { x: number; y: number; heading: number; velocity: number; steer_angle?: number };
  vehicle_x?: number;
  vehicle_y?: number;
  heading?: number;
  velocity?: number;
  steer_angle?: number;
  sim_time?: number;
  step?: number;
  min_clearance?: number;
  actuator_command?: { throttle: number; steering: number; brake: number; emergency_stop: boolean };
  hardware_metrics?: { cpu_utilization: number; temperature_celsius: number; is_throttled: boolean; deadline_misses: number };
  sensor_queue_depths?: Record<string, number>;
  active_faults?: string[];
  violations?: { rule_name: string; description: string; sim_time: number; severity?: string }[];
  dynamic_obstacles?: { obstacle_id: string; obstacle_type: string; x: number; y: number; radius: number }[];
  evaluation_id?: string;
  outcome?: ExperimentOutcome;
  passed?: boolean;
  violation_count?: number;
  trace_hash?: string;
  details?: Record<string, unknown>;
  evidence?: EvidenceSnapshot;
  decision_trace?: DecisionTrace;
  run_id?: string;
  signals?: { name: string; value: number; unit: string; sim_time: number; frame_index: number; step: number; source: string }[];
  event_links?: { event_id: string; evaluation_id: string; episode_id: string; event_type: string; source: string; sim_time: number; severity: string; wall_time: number; payload: Record<string, unknown> }[];
  hypothesis?: Hypothesis;
  hypotheses?: Hypothesis[] | { hypotheses?: Hypothesis[] };
  falsification_plan?: FalsificationPlan;
  hypothesis_id?: string;
  action?: string;
  next_experiment?: ExperimentCandidate;
  patch_id?: string;
  patched_code?: string;
  unified_diff?: string;
  cases?: RegressionCase[];
  error?: string;
  [key: string]: unknown;
}

// Critical milestone events that require immediate synchronous state flush
const CRITICAL_EVENT_TYPES = new Set<string>([
  "INVESTIGATION_CREATED",
  "INVESTIGATION_STARTED",
  "EXPERIMENT_PLANNED",
  "EXPERIMENT_STARTED",
  "EXPERIMENT_COMPLETED",
  "HYPOTHESIS_UPDATED",
  "FALSIFICATION_PROPOSED",
  "DECISION_RECORDED",
  "NEXT_EXPERIMENT_SELECTED",
  "DIAGNOSIS_COMPLETED",
  "PATCH_GENERATED",
  "PATCH_APPROVAL_REQUESTED",
  "PATCH_APPROVED",
  "PATCH_REJECTED",
  "VERIFICATION_PASSED",
  "VERIFICATION_FAILED",
  "REGRESSION_STARTED",
  "REGRESSION_COMPLETED",
  "CONCLUSION_RECORDED",
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
]);

/**
 * Pure batch reducer that folds multiple events into state in a single pass.
 */
function reduceBatch(prev: UseInvestigationState, batch: HarnessEvent[]): UseInvestigationState {
  if (batch.length === 0) return prev;

  let newStatus = prev.status;
  let newPhase = prev.phase;
  let newCurrentExp = prev.currentExperiment;
  let newCompletedExp = prev.completedExperiments;
  let newHypotheses = [...prev.hypotheses];
  let newLeadingHypothesis = prev.leadingHypothesis;
  let newActiveHypothesis = prev.activeHypothesis;
  let newTraces = [...prev.decisionTraces];
  let newRuns = [...prev.runs];
  let newFalsification = [...prev.falsificationPlans];
  let newDiagnosis = prev.diagnosis;
  let newPatch = prev.patch;
  let newApproval = prev.approval;
  let newVerification = prev.verification;
  let newRegression = [...prev.regression];
  let newConclusion = prev.conclusion;
  let newLatestFailure = prev.latestFailure;
  let newError = prev.error;
  let newActiveFrames = [...prev.activeExperimentFrames];
  const newAllFrames = { ...prev.allExperimentFrames };
  let newLatestTelemetry = prev.latestTelemetry;

  // Append batch to display events: preserve all System 2 & Safety events while capping high-frequency System 1 ticks
  const isHighValueEvent = (type: string, severity?: string) => {
    if (severity === "CRITICAL" || severity === "ERROR" || severity === "WARNING") return true;
    return (
      type.startsWith("INVESTIGATION_") ||
      type.startsWith("EXPERIMENT_") ||
      type.startsWith("HYPOTHESIS_") ||
      type.startsWith("EVIDENCE_") ||
      type.startsWith("DECISION_") ||
      type.startsWith("NEXT_") ||
      type.startsWith("DIAGNOSIS_") ||
      type.startsWith("PATCH_") ||
      type.startsWith("VERIFICATION_") ||
      type.startsWith("REGRESSION_") ||
      type.startsWith("CONCLUSION_") ||
      type.includes("VIOLATION") ||
      type.includes("BREACH") ||
      type.includes("COLLISION")
    );
  };

  const highValue = prev.events.filter((e) => isHighValueEvent(e.type, e.severity));
  const newHighValue = batch.filter((e) => isHighValueEvent(e.type, e.severity));
  const newSystem1 = batch.filter((e) => !isHighValueEvent(e.type, e.severity));
  const prevSystem1 = prev.events.filter((e) => !isHighValueEvent(e.type, e.severity));
  const combinedSystem1 = [...prevSystem1, ...newSystem1].slice(-100);
  const combinedHighValue = [...highValue, ...newHighValue].slice(-300);
  let newEvents = [...combinedHighValue, ...combinedSystem1];

  for (const event of batch) {
    const p = (event.payload || {}) as unknown as EventPayloadData;

    switch (event.type) {
      case "INVESTIGATION_CREATED":
        newStatus = "CREATED";
        newPhase = "INVESTIGATING";
        break;

      case "INVESTIGATION_STARTED":
        newStatus = "RUNNING";
        newPhase = "INVESTIGATING";
        break;

      case "EXPERIMENT_PLANNED":
        if (p.experiment) {
          newCurrentExp = p.experiment as ExperimentCandidate;
        } else if (p.experiment_id) {
          newCurrentExp = {
            experiment_id: p.experiment_id,
            values: p.values || {},
            phase: p.phase || "SCREEN",
            rationale: p.rationale || "",
            parent_experiment_ids: p.parent_experiment_ids || [],
          };
        }
        newActiveFrames = [];
        break;

      case "EXPERIMENT_STARTED":
        if (p.experiment) {
          newCurrentExp = p.experiment as ExperimentCandidate;
        } else if (p.experiment_id || event.experiment_id) {
          const eid = (p.experiment_id as string) || event.experiment_id || "";
          newCurrentExp = {
            experiment_id: eid,
            values: p.values || {},
            phase: (p.phase as any) || (eid === "exp_001" ? "BASELINE" : "SCREEN"),
            rationale: (p.rationale as string) || "",
            parent_experiment_ids: p.parent_experiment_ids || [],
          };
        }
        newActiveFrames = [];
        break;

      case "SIMULATION_STEP":
      case "SENSOR_SAMPLED":
      case "COMMAND_ISSUED":
      case "INVARIANT_BREACHED":
      case "CLEARANCE_WARNING":
      case "FAULT_INJECTED":
      case "FAULT_REVERTED":
      case "COLLISION_DETECTED":
      case "ACTUATOR_APPLIED":
      case "TASK_SCHEDULED":
      case "COMPUTE_STARTED":
      case "TASK_COMPLETED":
      case "DEADLINE_MISSED":
      case "THERMAL_THROTTLED":
        if (p.frame || p.telemetry_frame) {
          const f = (p.frame || p.telemetry_frame) as TelemetryFrame;
          newActiveFrames.push(f);
        } else if (p.vehicle_state || p.sim_time !== undefined || event.sim_time !== undefined) {
          const curSimTime = p.sim_time ?? event.sim_time ?? (newLatestTelemetry?.sim_time ? newLatestTelemetry.sim_time + 0.01 : 0);
          const prevSimTime = newLatestTelemetry?.sim_time ?? 0;
          const dt = Math.max(0, Math.min(0.1, curSimTime - prevSimTime));

          const lastVState: VehicleState = newLatestTelemetry?.vehicle_state || {
            x: 5.0,
            y: 5.0,
            heading: 0,
            velocity: 1.5,
          };

          let vState: VehicleState;
          if (p.vehicle_state) {
            vState = p.vehicle_state;
          } else if (p.vehicle_x !== undefined && p.vehicle_y !== undefined) {
            vState = {
              x: p.vehicle_x,
              y: p.vehicle_y,
              heading: p.heading ?? lastVState.heading,
              velocity: p.velocity ?? lastVState.velocity,
              steer_angle: p.steer_angle ?? lastVState.steer_angle,
            };
          } else {
            // Live dead-reckoning approximation from commands / velocity so the 2D rover animates smoothly in real time
            const cmdThrottle = (p.throttle as number) ?? (p.actuator_command?.throttle as number) ?? newLatestTelemetry?.actuator_command?.throttle ?? 0.6;
            const cmdBrake = (p.brake as number) ?? (p.actuator_command?.brake as number) ?? newLatestTelemetry?.actuator_command?.brake ?? 0;
            const cmdSteer = (p.steering as number) ?? (p.actuator_command?.steering as number) ?? newLatestTelemetry?.actuator_command?.steering ?? 0;
            
            const currentSpeed = (p.velocity as number) ?? Math.max(0, (lastVState.velocity || 1.5) + (cmdThrottle * 2.0 - cmdBrake * 4.0) * dt);
            const currentHeading = (p.heading as number) ?? (lastVState.heading + cmdSteer * 0.2 * dt);
            const posX = (lastVState.x ?? 5.0) + currentSpeed * Math.cos(currentHeading) * dt;
            const posY = (lastVState.y ?? 5.0) + currentSpeed * Math.sin(currentHeading) * dt;

            vState = {
              x: Number(posX.toFixed(3)),
              y: Number(posY.toFixed(3)),
              heading: Number(currentHeading.toFixed(3)),
              velocity: Number(currentSpeed.toFixed(3)),
              steer_angle: cmdSteer,
            };
          }

          let activeFaultsList = p.active_faults || (newLatestTelemetry?.active_faults ? [...newLatestTelemetry.active_faults] : []);
          if (event.type === "FAULT_INJECTED" && p.fault_id) {
            const fid = String(p.fault_id);
            if (!activeFaultsList.includes(fid)) {
              activeFaultsList.push(fid);
            }
          } else if (event.type === "FAULT_REVERTED" && p.fault_id) {
            activeFaultsList = activeFaultsList.filter((f) => f !== p.fault_id);
          }

          let newVioList = p.violations || [];
          if (event.type === "COLLISION_DETECTED") {
            newVioList = [
              ...newVioList,
              {
                rule_name: "COLLISION",
                description: `Collision with obstacle ${p.obstacle_id || "unknown"}`,
                sim_time: event.sim_time,
                severity: "CRITICAL",
              },
            ];
          } else if (event.type === "INVARIANT_BREACHED") {
            newVioList = [
              ...newVioList,
              {
                rule_name: (p.rule_name as string) || "INVARIANT_BREACHED",
                description: (p.description as string) || "Safety invariant breached",
                sim_time: event.sim_time,
                severity: "CRITICAL",
              },
            ];
          }

          const synthesizedFrame: TelemetryFrame = {
            sim_time: p.sim_time ?? event.sim_time,
            step: p.step ?? newActiveFrames.length,
            vehicle_state: {
              x: vState.x ?? lastVState.x,
              y: vState.y ?? lastVState.y,
              heading: vState.heading ?? lastVState.heading,
              velocity: vState.velocity ?? lastVState.velocity,
              steer_angle: vState.steer_angle ?? lastVState.steer_angle,
            },
            min_clearance:
              p.min_clearance ??
              (p.clearance as number) ??
              newLatestTelemetry?.min_clearance ??
              2.0,
            actuator_command: p.actuator_command || {
              throttle:
                (p.throttle as number) ??
                newLatestTelemetry?.actuator_command?.throttle ??
                0,
              steering:
                (p.steering as number) ??
                newLatestTelemetry?.actuator_command?.steering ??
                0,
              brake:
                (p.brake as number) ??
                newLatestTelemetry?.actuator_command?.brake ??
                0,
              emergency_stop:
                (p.emergency_stop as boolean) ??
                newLatestTelemetry?.actuator_command?.emergency_stop ??
                false,
            },
            hardware_metrics: p.hardware_metrics || {
              cpu_utilization:
                (p.cpu_utilization as number) ??
                newLatestTelemetry?.hardware_metrics?.cpu_utilization ??
                0.1,
              temperature_celsius:
                (p.temperature_celsius as number) ??
                newLatestTelemetry?.hardware_metrics?.temperature_celsius ??
                45,
              is_throttled:
                (p.is_throttled as boolean) ??
                (event.type === "THERMAL_THROTTLED"
                  ? true
                  : newLatestTelemetry?.hardware_metrics?.is_throttled ?? false),
              deadline_misses:
                (p.deadline_misses as number) ??
                (event.type === "DEADLINE_MISSED"
                  ? (newLatestTelemetry?.hardware_metrics?.deadline_misses || 0) + 1
                  : newLatestTelemetry?.hardware_metrics?.deadline_misses ?? 0),
            },
            sensor_queue_depths:
              p.sensor_queue_depths || newLatestTelemetry?.sensor_queue_depths || {},
            active_faults: activeFaultsList,
            new_violations: newVioList,
            dynamic_obstacles:
              p.dynamic_obstacles || newLatestTelemetry?.dynamic_obstacles || [],
          };
          newActiveFrames.push(synthesizedFrame);
          newLatestTelemetry = synthesizedFrame;
        }
        break;

      case "EXPERIMENT_COMPLETED": {
        newCompletedExp += 1;
        const expId =
          (p.experiment_id as string) ||
          event.experiment_id ||
          p.experiment?.experiment_id ||
          newCurrentExp?.experiment_id ||
          `exp_${newCompletedExp}`;

        if (newActiveFrames.length > 0 && !newAllFrames[expId]) {
          newAllFrames[expId] = newActiveFrames;
        }

        const expCandidate: ExperimentCandidate =
          (p.experiment as ExperimentCandidate) ||
          (newCurrentExp && newCurrentExp.experiment_id === expId
            ? newCurrentExp
            : {
                experiment_id: expId,
                values: p.values || {},
                phase: (p.phase as any) || (expId === "exp_001" ? "BASELINE" : "SCREEN"),
                rationale: (p.rationale as string) || "",
                parent_experiment_ids: p.parent_experiment_ids || [],
              });

        const runOutcome: ExperimentOutcome =
          (p.outcome as ExperimentOutcome) || {
            passed: (p.passed as boolean) ?? true,
            violation_count: (p.violation_count as number) ?? 0,
            min_clearance: (p.min_clearance as number) ?? 2.0,
            trace_hash: (p.trace_hash as string) ?? "",
            details: (p.details as Record<string, unknown>) || {},
          };

        const runItem: InvestigationRun = {
          evaluation_id: (p.evaluation_id as string) || event.evaluation_id || "",
          experiment: expCandidate,
          outcome: runOutcome,
          evidence: (p.evidence as EvidenceSnapshot) || null,
          decision_trace: (p.decision_trace as DecisionTrace) || null,
        };

        newRuns = [...newRuns.filter((r) => r.experiment.experiment_id !== expId), runItem];

        if (!runOutcome.passed && !newLatestFailure) {
          newLatestFailure = runItem;
        }
        break;
      }

      case "EVIDENCE_CAPTURED": {
        const targetExpId = (p.experiment_id as string) || "";
        const evidenceObj: EvidenceSnapshot = (p.evidence || {
          run_id: (p.run_id as string) || "",
          trace_hash: (p.trace_hash as string) || "",
          signals: p.signals || [],
          event_links: p.event_links || [],
        }) as EvidenceSnapshot;

        if (targetExpId) {
          const runIdx = newRuns.findIndex((r) => r.experiment.experiment_id === targetExpId);
          if (runIdx >= 0) {
            newRuns[runIdx] = { ...newRuns[runIdx], evidence: evidenceObj };
          }
        } else if (newRuns.length > 0) {
          const lastIdx = newRuns.length - 1;
          newRuns[lastIdx] = { ...newRuns[lastIdx], evidence: evidenceObj };
        }
        break;
      }

      case "HYPOTHESIS_UPDATED": {
        if (p.hypothesis) {
          const h = p.hypothesis as Hypothesis;
          const idx = newHypotheses.findIndex((item) => item.hypothesis_id === h.hypothesis_id);
          if (idx >= 0) {
            newHypotheses[idx] = h;
          } else {
            newHypotheses.push(h);
          }
        } else if (p.hypotheses) {
          const hypoList: Hypothesis[] = Array.isArray(p.hypotheses)
            ? (p.hypotheses as Hypothesis[])
            : (p.hypotheses as { hypotheses?: Hypothesis[] })?.hypotheses || [];
          if (hypoList.length > 0) {
            newHypotheses = hypoList;
          }
        }
        // Compute leading hypothesis by highest confidence
        if (newHypotheses.length > 0) {
          newLeadingHypothesis = [...newHypotheses].sort(
            (a, b) => (b.confidence ?? 0) - (a.confidence ?? 0)
          )[0];
          newActiveHypothesis =
            newHypotheses.find((h) => h.status === "ACTIVE") || newLeadingHypothesis;
        }
        break;
      }

      case "FALSIFICATION_PROPOSED": {
        if (p.falsification_plan || p.hypothesis_id) {
          const fPlan = (p.falsification_plan || p) as FalsificationPlan;
          newFalsification = [...newFalsification, fPlan];
        }
        break;
      }

      case "DECISION_RECORDED": {
        const trace = (p.decision_trace || (p.action ? p : null)) as DecisionTrace | null;
        if (trace) {
          newTraces = [
            ...newTraces.filter((t) => t.experiment_id !== trace.experiment_id),
            trace,
          ];
          const runIdx = newRuns.findIndex((r) => r.experiment.experiment_id === trace.experiment_id);
          if (runIdx >= 0) {
            newRuns[runIdx] = { ...newRuns[runIdx], decision_trace: trace };
          }
        }
        break;
      }

      case "NEXT_EXPERIMENT_SELECTED":
        if (p.next_experiment) {
          newCurrentExp = p.next_experiment as ExperimentCandidate;
        }
        break;

      case "DIAGNOSIS_COMPLETED":
        newPhase = "DIAGNOSING";
        newDiagnosis = p as unknown as CausalDiagnosticReport;
        break;

      case "PATCH_GENERATED":
        newPhase = "PATCH_PROPOSED";
        newPatch = p as unknown as PatchResult;
        break;

      case "PATCH_APPROVAL_REQUESTED":
        newPhase = "AWAITING_APPROVAL";
        if (!newPatch && p.patch_id) {
          newPatch = {
            patch_id: p.patch_id,
            patched_code: p.patched_code || "",
            unified_diff: p.unified_diff || "",
          };
        }
        break;

      case "PATCH_APPROVED":
        newPhase = "VERIFYING";
        newApproval = p as unknown as PatchApproval;
        break;

      case "PATCH_REJECTED":
        newPhase = "PATCH_REJECTED";
        newApproval = p as unknown as PatchApproval;
        break;

      case "VERIFICATION_PASSED":
      case "VERIFICATION_FAILED":
        newVerification = p;
        break;

      case "REGRESSION_STARTED":
        newPhase = "REGRESSING";
        break;

      case "REGRESSION_COMPLETED":
        if (p.cases && Array.isArray(p.cases)) {
          newRegression = p.cases;
        }
        break;

      case "CONCLUSION_RECORDED":
        newConclusion = p as unknown as InvestigationConclusion;
        break;

      case "INVESTIGATION_COMPLETED":
        newStatus = "COMPLETED";
        newPhase = "COMPLETED";
        break;

      case "INVESTIGATION_FAILED":
        newStatus = "FAILED";
        newPhase = "FAILED";
        newError = p.error || "Investigation failed";
        break;

      default:
        break;
    }
  }

  return {
    ...prev,
    status: newStatus,
    phase: newPhase,
    currentExperiment: newCurrentExp,
    completedExperiments: newCompletedExp,
    hypotheses: newHypotheses,
    leadingHypothesis: newLeadingHypothesis,
    activeHypothesis: newActiveHypothesis,
    decisionTraces: newTraces,
    runs: newRuns,
    falsificationPlans: newFalsification,
    events: newEvents,
    latestFailure: newLatestFailure,
    diagnosis: newDiagnosis,
    patch: newPatch,
    approval: newApproval,
    verification: newVerification,
    regression: newRegression,
    conclusion: newConclusion,
    error: newError,
    activeExperimentFrames: newActiveFrames,
    allExperimentFrames: newAllFrames,
    latestTelemetry: newLatestTelemetry,
  };
}

export function useInvestigation(apiBase: string) {
  const [state, setState] = useState<UseInvestigationState>({
    investigationId: null,
    snapshot: null,
    status: "CREATED",
    phase: "INVESTIGATING",
    objective: "",
    hardwarePresetId: "RDK_X5",
    scenarioId: "showcase_normal_baseline",
    seed: 1337,
    budget: 12,
    completedExperiments: 0,
    currentExperiment: null,
    activeHypothesis: null,
    leadingHypothesis: null,
    hypotheses: [],
    runs: [],
    decisionTraces: [],
    falsificationPlans: [],
    events: [],
    latestFailure: null,
    diagnosis: null,
    patch: null,
    approval: null,
    verification: null,
    regression: [],
    conclusion: null,
    connectionStatus: "IDLE",
    error: null,
    isLoading: false,
    activeExperimentFrames: [],
    allExperimentFrames: {},
    latestTelemetry: null,
  });

  const streamClientRef = useRef<InvestigationStreamClient | null>(null);
  const stateRef = useRef(state);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const pendingQueueRef = useRef<HarnessEvent[]>([]);
  const batchTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Flush pending batch queue to React state in a single pass
  const flushPendingEvents = useCallback(() => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
      batchTimerRef.current = null;
    }

    const batch = pendingQueueRef.current;
    if (batch.length === 0) return;
    pendingQueueRef.current = [];

    setState((prev) => reduceBatch(prev, batch));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (batchTimerRef.current) {
        clearTimeout(batchTimerRef.current);
        batchTimerRef.current = null;
      }
      if (streamClientRef.current) {
        streamClientRef.current.disconnect();
      }
    };
  }, []);

  const hydratingEvaluationsRef = useRef<Set<string>>(new Set());

  // Automatically hydrate full 100Hz telemetry frames from evaluation store
  const hydrateExperimentFrames = useCallback(
    async (experimentId: string, evaluationId: string) => {
      if (!evaluationId || !experimentId) return;
      if (hydratingEvaluationsRef.current.has(evaluationId)) return;

      hydratingEvaluationsRef.current.add(evaluationId);
      try {
        const evaluation = await getEvaluation(apiBase, evaluationId);
        const frames = (evaluation.baseline_run?.telemetry_frames as TelemetryFrame[]) || [];
        if (frames.length > 0) {
          setState((prev) => {
            const updatedAll = {
              ...prev.allExperimentFrames,
              [experimentId]: frames,
            };
            const isCurrent = prev.currentExperiment?.experiment_id === experimentId || !prev.currentExperiment;
            return {
              ...prev,
              allExperimentFrames: updatedAll,
              activeExperimentFrames: isCurrent ? frames : prev.activeExperimentFrames,
              latestTelemetry: isCurrent && frames.length > 0 ? frames[frames.length - 1] : prev.latestTelemetry,
            };
          });
        }
      } catch (err) {
        console.warn(`[useInvestigation] Failed to hydrate frames for ${experimentId} (${evaluationId}):`, err);
      } finally {
        hydratingEvaluationsRef.current.delete(evaluationId);
      }
    },
    [apiBase]
  );

  // Ingest incoming events with O(1) deduplication and high-throughput batching
  const handleEvent = useCallback((event: HarnessEvent) => {
    if (event.event_id) {
      if (seenEventIdsRef.current.has(event.event_id)) {
        return;
      }
      seenEventIdsRef.current.add(event.event_id);
    }

    pendingQueueRef.current.push(event);

    if (event.type === "EXPERIMENT_COMPLETED") {
      const p = (event.payload || {}) as unknown as EventPayloadData;
      const evalId = (p.evaluation_id as string) || event.evaluation_id;
      const expId = (p.experiment_id as string) || p.experiment?.experiment_id || stateRef.current.currentExperiment?.experiment_id;
      if (evalId && expId) {
        hydrateExperimentFrames(expId, evalId);
      }
    }

    if (CRITICAL_EVENT_TYPES.has(event.type)) {
      flushPendingEvents();
    } else {
      if (!batchTimerRef.current) {
        batchTimerRef.current = setTimeout(flushPendingEvents, BATCH_FLUSH_INTERVAL_MS);
      }
    }
  }, [flushPendingEvents, hydrateExperimentFrames]);

  // Connect WebSocket stream
  const connectStream = useCallback((investigationId: string) => {
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
    }

    const client = new InvestigationStreamClient(apiBase, investigationId, {
      onEvent: (event) => handleEvent(event),
      onStatusChange: (status) => {
        setState((prev) => ({ ...prev, connectionStatus: status }));
      },
      onError: (errMsg) => {
        console.warn("[useInvestigation] Stream error:", errMsg);
      },
      onClose: () => {
        console.log("[useInvestigation] Stream connection closed");
      },
    });

    streamClientRef.current = client;
    client.connect();
  }, [apiBase, handleEvent]);

  // Start new Investigation
  const start = useCallback(async (payload: InvestigationPayload) => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
      batchTimerRef.current = null;
    }
    pendingQueueRef.current = [];
    seenEventIdsRef.current.clear();

    setState((prev) => ({
      ...prev,
      isLoading: true,
      error: null,
      events: [],
      runs: [],
      hypotheses: [],
      decisionTraces: [],
      falsificationPlans: [],
      activeExperimentFrames: [],
      allExperimentFrames: {},
      latestTelemetry: null,
      diagnosis: null,
      patch: null,
      approval: null,
      verification: null,
      regression: [],
      conclusion: null,
      objective: payload.objective,
      hardwarePresetId: payload.hardware_preset_id || "RDK_X5",
      scenarioId: payload.scenario_id || "showcase_normal_baseline",
      seed: payload.seed || 1337,
      budget: payload.budget || 12,
      completedExperiments: 0,
      status: "RUNNING",
      phase: "INVESTIGATING",
    }));

    try {
      const snapshot = await startInvestigation(apiBase, payload);
      setState((prev) => ({
        ...prev,
        investigationId: snapshot.investigation_id,
        snapshot: snapshot,
        status: snapshot.status || "RUNNING",
        phase: snapshot.phase || "INVESTIGATING",
        isLoading: false,
      }));

      // Immediately connect live WebSocket
      connectStream(snapshot.investigation_id);
      return snapshot;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start investigation";
      setState((prev) => ({
        ...prev,
        isLoading: false,
        status: "FAILED",
        phase: "FAILED",
        error: msg,
      }));
      throw err;
    }
  }, [apiBase, connectStream]);

  // Load existing Investigation by ID
  const load = useCallback(async (investigationId: string) => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
      batchTimerRef.current = null;
    }
    pendingQueueRef.current = [];
    seenEventIdsRef.current.clear();

    setState((prev) => ({ ...prev, isLoading: true, error: null, investigationId }));
    try {
      const snapshot = await getInvestigation(apiBase, investigationId);
      const rawEvents = await getInvestigationEvents(apiBase, investigationId).catch(() => []);

      for (const ev of rawEvents) {
        if (ev.event_id) {
          seenEventIdsRef.current.add(ev.event_id);
        }
      }

      const events = rawEvents.length > MAX_EVENTS_BUFFER ? rawEvents.slice(-MAX_EVENTS_BUFFER) : rawEvents;

      const result = snapshot.result;
      setState((prev) => ({
        ...prev,
        investigationId,
        snapshot,
        status: snapshot.status,
        phase: snapshot.phase,
        objective: snapshot.objective || "",
        hardwarePresetId: snapshot.hardware_preset_id || "RDK_X5",
        scenarioId: snapshot.scenario_id || "",
        seed: snapshot.seed || 1337,
        budget: snapshot.budget || 12,
        completedExperiments: snapshot.completed_experiments || result?.runs?.length || 0,
        currentExperiment: snapshot.current_experiment || null,
        activeHypothesis: snapshot.active_hypothesis || null,
        leadingHypothesis: snapshot.leading_hypothesis || null,
        hypotheses: result?.hypotheses?.hypotheses || [],
        runs: result?.runs || [],
        decisionTraces: result?.decision_trace || [],
        falsificationPlans: result?.falsification_plans || [],
        events: events,
        diagnosis: snapshot.diagnosis || null,
        patch: snapshot.patch || null,
        approval: snapshot.approval || null,
        verification: snapshot.verification || null,
        regression: snapshot.regression || [],
        conclusion: snapshot.conclusion || null,
        isLoading: false,
      }));

      connectStream(investigationId);

      // Asynchronously hydrate telemetry frames for all completed runs in snapshot
      const existingRuns = result?.runs || [];
      for (const r of existingRuns) {
        if (r.evaluation_id && r.experiment?.experiment_id) {
          hydrateExperimentFrames(r.experiment.experiment_id, r.evaluation_id);
        }
      }

      return snapshot;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load investigation";
      setState((prev) => ({ ...prev, isLoading: false, error: msg }));
      throw err;
    }
  }, [apiBase, connectStream, hydrateExperimentFrames]);

  // Approve or Reject proposed patch
  const approvePatch = useCallback(async (
    decision: "APPROVE" | "REJECT",
    reason: string = "",
    token: string = "test-reviewer-token"
  ) => {
    const invId = stateRef.current.investigationId;
    const patchId = stateRef.current.patch?.patch_id;
    if (!invId || !patchId) {
      throw new Error("No active investigation or pending patch to approve.");
    }

    try {
      const updatedSnapshot = await approveInvestigationPatch(
        apiBase,
        invId,
        { patch_id: patchId, decision, reason },
        token
      );
      setState((prev) => ({
        ...prev,
        snapshot: updatedSnapshot,
        phase: updatedSnapshot.phase,
        status: updatedSnapshot.status,
        approval: updatedSnapshot.approval || null,
      }));
      return updatedSnapshot;
    } catch (err: unknown) {
      console.error("Patch approval error:", err);
      throw err;
    }
  }, [apiBase]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
      batchTimerRef.current = null;
    }
    flushPendingEvents();
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      streamClientRef.current = null;
    }
    setState((prev) => ({ ...prev, connectionStatus: "CLOSED" }));
  }, [flushPendingEvents]);

  // Clear State
  const clear = useCallback(() => {
    if (batchTimerRef.current) {
      clearTimeout(batchTimerRef.current);
      batchTimerRef.current = null;
    }
    pendingQueueRef.current = [];
    seenEventIdsRef.current.clear();
    disconnect();
    setState({
      investigationId: null,
      snapshot: null,
      status: "CREATED",
      phase: "INVESTIGATING",
      objective: "",
      hardwarePresetId: "RDK_X5",
      scenarioId: "showcase_normal_baseline",
      seed: 1337,
      budget: 12,
      completedExperiments: 0,
      currentExperiment: null,
      activeHypothesis: null,
      leadingHypothesis: null,
      hypotheses: [],
      runs: [],
      decisionTraces: [],
      falsificationPlans: [],
      events: [],
      latestFailure: null,
      diagnosis: null,
      patch: null,
      approval: null,
      verification: null,
      regression: [],
      conclusion: null,
      connectionStatus: "IDLE",
      error: null,
      isLoading: false,
      activeExperimentFrames: [],
      allExperimentFrames: {},
      latestTelemetry: null,
    });
  }, [disconnect]);

  return {
    ...state,
    start,
    load,
    approvePatch,
    hydrateExperimentFrames,
    disconnect,
    clear,
  };
}
