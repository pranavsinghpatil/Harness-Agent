"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  HardwarePreset,
  ScenarioDefinition,
  TelemetryFrame,
} from "../types/simulation";
import { useInvestigation } from "../hooks/useInvestigation";
import { ControlRoomHeader } from "./ControlRoomHeader";
import { LiveEventStream } from "./LiveEventStream";
import { HypothesisBoard } from "./HypothesisBoard";
import { ExperimentGraph } from "./ExperimentGraph";
import { CausalDAGView } from "./CausalDAGView";
import { CloseLoopCertification } from "./CloseLoopCertification";
import { PatchApprovalModal } from "./PatchApprovalModal";
import { SimulationCanvas } from "./SimulationCanvas";
import { PlaybackControls } from "./PlaybackControls";
import { VehicleHUD } from "./VehicleHUD";
import { HardwareHUD } from "./HardwareHUD";

interface InvestigatorViewProps {
  apiBase: string;
  presets: HardwarePreset[];
  scenarios: ScenarioDefinition[];
  investigation?: ReturnType<typeof useInvestigation>;
}

type InspectorTab = "hypotheses" | "experiments" | "causal_dag" | "certification";

export const InvestigatorView: React.FC<InvestigatorViewProps> = ({
  apiBase,
  presets,
  scenarios,
  investigation: propInvestigation,
}) => {
  // Launch parameters
  const [objective, setObjective] = useState<string>(
    "Investigate vehicle safety boundary under camera frame latency and compute degradation"
  );
  const [selectedPresetId, setSelectedPresetId] = useState<string>(
    presets[0]?.id ?? "RDK_X5"
  );
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(
    scenarios[0]?.id ?? "showcase_normal_baseline"
  );
  const [budget, setBudget] = useState<number>(12);
  const [maxBoundarySteps, setMaxBoundarySteps] = useState<number>(3);
  const [seed, setSeed] = useState<number>(1337);

  // Inspector & Canvas selection state
  const [activeInspectorTab, setActiveInspectorTab] = useState<InspectorTab>("hypotheses");
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState<boolean>(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);

  // Frame Scrubber & Playback state
  const [currentFrameIdx, setCurrentFrameIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);

  // Use the reactive investigation hook (or shared instance from page root)
  const localInvestigation = useInvestigation(propInvestigation ? "" : apiBase);
  const investigation = propInvestigation || localInvestigation;

  // Auto-open modal on entering AWAITING_APPROVAL phase with a patch
  const lastAutoOpenedPatchIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (investigation.phase === "AWAITING_APPROVAL" && investigation.patch) {
      const patchId = investigation.patch.patch_id || "pending_patch";
      if (lastAutoOpenedPatchIdRef.current !== patchId) {
        lastAutoOpenedPatchIdRef.current = patchId;
        setIsApprovalModalOpen(true);
      }
    } else if (investigation.phase !== "AWAITING_APPROVAL") {
      setIsApprovalModalOpen(false);
      lastAutoOpenedPatchIdRef.current = null;
    }
  }, [investigation.phase, investigation.patch]);

  // Auto-switch to Certification tab on investigation completion
  const hasAutoSwitchedCertRef = useRef<string | null>(null);

  useEffect(() => {
    if (investigation.phase === "COMPLETED" || investigation.status === "COMPLETED") {
      const invId = investigation.investigationId || "completed";
      if (hasAutoSwitchedCertRef.current !== invId) {
        hasAutoSwitchedCertRef.current = invId;
        setActiveInspectorTab("certification");
      }
    }
  }, [investigation.phase, investigation.status, investigation.investigationId]);

  // Derive playback frames directly from store with fallback to active frames
  const playbackFrames: TelemetryFrame[] =
    (selectedExperimentId && investigation.allExperimentFrames[selectedExperimentId]?.length > 0)
      ? investigation.allExperimentFrames[selectedExperimentId]
      : (investigation.allExperimentFrames[investigation.currentExperiment?.experiment_id || ""]?.length > 0
          ? investigation.allExperimentFrames[investigation.currentExperiment?.experiment_id || ""]
          : (investigation.runs.length > 0 && investigation.allExperimentFrames[investigation.runs[investigation.runs.length - 1].experiment.experiment_id]?.length > 0
              ? investigation.allExperimentFrames[investigation.runs[investigation.runs.length - 1].experiment.experiment_id]
              : investigation.activeExperimentFrames));

  // Handle Experiment Selection (LIVE vs Historical Replay)
  const handleSelectExperiment = (expId: string | null) => {
    setSelectedExperimentId(expId);
    if (expId) {
      setCurrentFrameIdx(0);
      setIsPlaying(true);
      const run = investigation.runs.find((r) => r.experiment.experiment_id === expId);
      if (run?.evaluation_id) {
        investigation.hydrateExperimentFrames(expId, run.evaluation_id);
      }
    } else {
      setIsPlaying(false);
      if (investigation.activeExperimentFrames.length > 0) {
        setCurrentFrameIdx(investigation.activeExperimentFrames.length - 1);
      }
    }
  };

  // Auto-hydrate frames for selected experiment if not yet loaded
  useEffect(() => {
    if (!selectedExperimentId) return;
    if (investigation.allExperimentFrames[selectedExperimentId]?.length > 0) return;

    const run = investigation.runs.find(
      (r) => r.experiment.experiment_id === selectedExperimentId
    );
    if (run?.evaluation_id) {
      investigation.hydrateExperimentFrames(selectedExperimentId, run.evaluation_id);
    }
  }, [
    selectedExperimentId,
    investigation,
  ]);

  // Handle Launch
  const handleLaunch = async () => {
    if (!objective.trim()) return;
    try {
      await investigation.start({
        objective: objective.trim(),
        hardware_preset_id: selectedPresetId,
        scenario_id: selectedScenarioId,
        seed: seed,
        budget: budget,
        max_boundary_steps: maxBoundarySteps,
      });
      setSelectedExperimentId(null);
      setCurrentFrameIdx(0);
      setIsPlaying(false);
    } catch (err) {
      console.error("Failed to launch investigation:", err);
    }
  };

  // High-performance requestAnimationFrame playback ticker
  useEffect(() => {
    if (!isPlaying || playbackFrames.length <= 1) return;

    let animId: number;
    let lastTime = performance.now();
    let accumulatedFrames = 0;

    const tick = (now: number) => {
      const dtSeconds = (now - lastTime) / 1000;
      lastTime = now;

      // 100 Hz physics simulation = 100 frames per simulated second
      const framesToAdvance = dtSeconds * 100 * playbackSpeed;
      accumulatedFrames += framesToAdvance;

      if (accumulatedFrames >= 1) {
        const stepCount = Math.floor(accumulatedFrames);
        accumulatedFrames -= stepCount;

        setCurrentFrameIdx((prev) => {
          const next = prev + stepCount;
          if (next >= playbackFrames.length) {
            return 0; // loop replay smoothly
          }
          return next;
        });
      }

      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, playbackFrames.length, playbackSpeed]);

  const isLive = !selectedExperimentId;
  const effectiveFrameIdx = (isLive && !isPlaying && playbackFrames.length > 0)
    ? Math.max(0, playbackFrames.length - 1)
    : Math.min(Math.max(0, playbackFrames.length - 1), Math.max(0, currentFrameIdx));

  const activeFrame: TelemetryFrame | null =
    playbackFrames[effectiveFrameIdx] ||
    investigation.latestTelemetry ||
    null;

  const currentPreset = presets.find((p) => p.id === (investigation.hardwarePresetId || selectedPresetId));
  const currentScenario = scenarios.find((s) => s.id === (investigation.scenarioId || selectedScenarioId));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Control Room Hero Header */}
      <ControlRoomHeader
        investigationId={investigation.investigationId}
        status={investigation.status}
        phase={investigation.phase}
        objective={investigation.objective || objective}
        completedExperiments={investigation.completedExperiments}
        budget={investigation.budget}
        hardwarePreset={currentPreset}
        scenario={currentScenario}
        connectionStatus={investigation.connectionStatus}
        onNewInvestigationClick={() => investigation.clear()}
        onApproveClick={() => setIsApprovalModalOpen(true)}
      />

      {/* Mode A: If no investigation has started, show the New Investigation Launch Form */}
      {!investigation.investigationId ? (
        <div className="bg-linear-to-r from-purple-950/80 via-slate-900 to-indigo-950/80 border border-purple-500/30 rounded-2xl p-6 shadow-2xl space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono text-[11px] border border-purple-500/40 font-semibold">
                  SYSTEM 2 AUTONOMOUS INVESTIGATOR STUDIO
                </span>
                <span className="text-xs text-slate-400">
                  Persistent Closed-Loop Scientific Search
                </span>
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Launch Autonomous Reliability Investigation
              </h2>
              <p className="text-xs text-slate-300 max-w-2xl mt-1 leading-relaxed">
                System 2 will formulate competing causal hypotheses, execute bounded System 1 perturbation
                experiments, stream real-time events over WebSocket, auto-synthesize AST code repairs, and request human approval.
              </p>
            </div>

            <button
              onClick={handleLaunch}
              disabled={investigation.isLoading || !objective.trim()}
              className="py-3 px-6 rounded-xl bg-linear-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:opacity-90 disabled:opacity-50 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30 transition cursor-pointer"
            >
              {investigation.isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Starting Session (202 Accepted)...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  START INVESTIGATION
                </>
              )}
            </button>
          </div>

          {/* Configuration Form */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-slate-800">
            {/* Objective Input */}
            <div className="md:col-span-2">
              <label className="block text-[11px] text-slate-400 mb-1">
                Investigation Scientific Objective
              </label>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                rows={2}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500 font-sans leading-relaxed"
                placeholder="State the reliability question to investigate..."
              />
            </div>

            {/* Target Hardware */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Target Edge Hardware Board
              </label>
              <select
                value={selectedPresetId}
                onChange={(e) => setSelectedPresetId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              >
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.id} ({p.cpu_cores || 8}c, {p.npu_tops || 10} TOPS)
                  </option>
                ))}
              </select>
            </div>

            {/* Scenario */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Baseline Scenario Template
              </label>
              <select
                value={selectedScenarioId}
                onChange={(e) => setSelectedScenarioId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              >
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name || s.id}
                  </option>
                ))}
              </select>
            </div>

            {/* Budget */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Experiment Budget (Max Runs)
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Boundary Steps */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Max Boundary Refinements
              </label>
              <input
                type="number"
                min={0}
                max={10}
                value={maxBoundarySteps}
                onChange={(e) => setMaxBoundarySteps(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Seed */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">
                Deterministic Seed
              </label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>
        </div>
      ) : (
        /* Mode B: Live Investigation Control Room Workspace */
        <div className="space-y-6">
          {/* Active Lifecycle Flow Banner */}
          {investigation.phase === "AWAITING_APPROVAL" && (
            <div className="bg-linear-to-r from-amber-950/90 via-amber-900/40 to-slate-950 border-2 border-amber-500/70 rounded-2xl p-4 sm:p-5 shadow-2xl shadow-amber-500/10 animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-500/30 text-amber-200 font-mono text-[11px] font-bold border border-amber-500/50 flex items-center gap-1.5 animate-pulse">
                      <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                      HUMAN-IN-THE-LOOP SAFETY GATE
                    </span>
                    <span className="text-xs text-amber-300 font-mono font-semibold">
                      Patch: {investigation.patch?.patch_id || "patch_auto_01"}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-white tracking-wide">
                    ⚠️ Safety Fault Detected & Hardened Patch Generated — Human Review Required
                  </h3>
                  <p className="text-xs text-amber-200/90 max-w-3xl leading-relaxed">
                    System 2 formulated an AST code repair addressing the observed failure boundary. Review the proposed diff to authorize dual-run verification and the multi-case regression suite.
                  </p>
                </div>

                <button
                  onClick={() => setIsApprovalModalOpen(true)}
                  className="self-start md:self-center py-2.5 px-6 rounded-xl bg-linear-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 active:opacity-90 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-amber-500/30 transition cursor-pointer shrink-0 animate-bounce"
                >
                  <span className="text-sm">🛡️</span>
                  <span>Review & Authorize Patch</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {investigation.phase === "VERIFYING" && (
            <div className="bg-linear-to-r from-indigo-950/90 via-blue-900/40 to-slate-950 border border-indigo-500/50 rounded-2xl p-4 shadow-xl animate-in fade-in duration-300">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 flex items-center justify-center font-bold text-base shadow-sm">
                    🔬
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono text-[10px] font-bold border border-indigo-500/30 animate-pulse">
                        PHASE: DUAL-RUN VERIFICATION
                      </span>
                      <span className="text-xs font-semibold text-white">
                        Verifying Hardened Controller on Edge Hardware
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Operator authorized repair. Running dual-run comparative verification against the baseline failure counterexample...
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-indigo-300 shrink-0">
                  <svg className="animate-spin h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span className="hidden sm:inline">Executing SIL Verification...</span>
                </div>
              </div>
            </div>
          )}

          {investigation.phase === "REGRESSING" && (
            <div className="bg-linear-to-r from-purple-950/90 via-indigo-900/40 to-slate-950 border border-purple-500/50 rounded-2xl p-4 shadow-xl animate-in fade-in duration-300">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center justify-center font-bold text-base shadow-sm">
                    🔄
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono text-[10px] font-bold border border-purple-500/30 animate-pulse">
                        PHASE: MULTI-CASE REGRESSION
                      </span>
                      <span className="text-xs font-semibold text-white">
                        Replaying Discovered Perturbation Schedules
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Replaying regression suite across all discovered perturbation schedules to certify zero regression...
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-purple-300 shrink-0">
                  <svg className="animate-spin h-4 w-4 text-purple-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span className="hidden sm:inline">Replaying Test Matrix...</span>
                </div>
              </div>
            </div>
          )}

          {(investigation.phase === "COMPLETED" || investigation.status === "COMPLETED") && (
            <div className="bg-linear-to-r from-emerald-950/90 via-teal-900/40 to-slate-950 border border-emerald-500/50 rounded-2xl p-4 shadow-xl animate-in fade-in duration-300">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center justify-center font-bold text-base shadow-sm">
                    🛡️
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px] font-bold border border-emerald-500/30">
                        PROVEN & CERTIFIED
                      </span>
                      <span className="text-xs font-semibold text-white">
                        Autonomous Reliability Investigation Complete
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Safety invariant proven under latency perturbations. 3-Pillar Certification generated.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveInspectorTab("certification")}
                  className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 shadow-md shadow-emerald-600/30"
                >
                  <span>View Certificate</span>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {investigation.phase === "PATCH_REJECTED" && (
            <div className="bg-linear-to-r from-rose-950/90 via-rose-900/40 to-slate-950 border border-rose-500/50 rounded-2xl p-4 shadow-xl animate-in fade-in duration-300">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center justify-center font-bold text-base shadow-sm">
                  🛑
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono text-[10px] font-bold border border-rose-500/30">
                      PATCH REJECTED
                    </span>
                    <span className="text-xs font-semibold text-white">
                      Human Reviewer Rejected Proposed Patch
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Investigation session concluded without controller repair. Review decision rationale in certificate tab.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Main Stage Grid: Center Stage Visualizer + Right Inspector Rail */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left / Center Column (7 Cols): 2D Canvas + Scrubber + HUDs */}
            <div className="lg:col-span-7 space-y-4">
              {/* Experiment Selector Bar */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Viewing Experiment:
                  </span>
                  <select
                    value={selectedExperimentId || "LIVE"}
                    onChange={(e) => {
                      const val = e.target.value;
                      handleSelectExperiment(val === "LIVE" ? null : val);
                    }}
                    className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-indigo-300 font-mono focus:outline-none focus:border-indigo-500"
                  >
                    <option value="LIVE">
                      🔴 Live Stream (Active Run) {investigation.activeExperimentFrames.length > 0 ? `[${investigation.activeExperimentFrames.length} frames]` : ""}
                    </option>
                    {investigation.runs.map((r) => {
                      const cachedCount = investigation.allExperimentFrames[r.experiment.experiment_id]?.length;
                      return (
                        <option key={r.experiment.experiment_id} value={r.experiment.experiment_id}>
                          {r.experiment.experiment_id} ({r.experiment.phase}) - {r.outcome.passed ? "PASS" : "VIOLATION"} {cachedCount ? `[${cachedCount} frames]` : ""}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div className="flex items-center gap-2 text-[11px] font-mono">
                  {selectedExperimentId ? (
                    <button
                      onClick={() => handleSelectExperiment(null)}
                      className="px-2 py-0.5 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-[10px] font-semibold transition cursor-pointer flex items-center gap-1"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                      Back to Live Stream
                    </button>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">
                      Live Mode
                    </span>
                  )}
                  <span className="text-slate-400">
                    Frames: {playbackFrames.length}
                  </span>
                </div>
              </div>

              {/* 2D Canvas Engine */}
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-3 sm:p-4 shadow-2xl relative overflow-hidden flex flex-col items-center justify-center">
                <SimulationCanvas
                  currentFrame={activeFrame}
                  scenario={currentScenario || null}
                  latestViolation={activeFrame?.new_violations?.[0] || null}
                  simTime={activeFrame?.sim_time || 0}
                  simStep={activeFrame?.step || 0}
                  isLive={!selectedExperimentId}
                  experimentId={selectedExperimentId || investigation.currentExperiment?.experiment_id || "LIVE"}
                  experimentPhase={
                    selectedExperimentId
                      ? investigation.runs.find((r) => r.experiment.experiment_id === selectedExperimentId)?.experiment.phase
                      : investigation.currentExperiment?.phase
                  }
                  experimentOutcome={
                    selectedExperimentId
                      ? (investigation.runs.find((r) => r.experiment.experiment_id === selectedExperimentId)?.outcome.passed ? "PASS" : "VIOLATION")
                      : null
                  }
                  activeFaults={activeFrame?.active_faults}
                  playbackFrames={playbackFrames}
                  currentFrameIdx={effectiveFrameIdx}
                />
              </div>

              {/* Scrubber & Playback Controls */}
              {playbackFrames.length > 0 && (
                <PlaybackControls
                  isPlaying={isPlaying}
                  onPlayPauseToggle={() => setIsPlaying(!isPlaying)}
                  currentFrameIdx={effectiveFrameIdx}
                  totalFrames={playbackFrames.length}
                  onScrub={(idx: number) => {
                    setIsPlaying(false);
                    setCurrentFrameIdx(idx);
                  }}
                  playbackSpeed={playbackSpeed}
                  onSpeedChange={(speed: number) => setPlaybackSpeed(speed)}
                  currentTime={activeFrame?.sim_time || (effectiveFrameIdx * 0.01)}
                  totalDuration={playbackFrames[playbackFrames.length - 1]?.sim_time || Math.max(12, playbackFrames.length * 0.01)}
                />
              )}

              {/* Vehicle & Hardware HUDs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <VehicleHUD frame={activeFrame} />
                <HardwareHUD
                  metrics={activeFrame?.hardware_metrics || null}
                  sensorQueues={activeFrame?.sensor_queue_depths || null}
                />
              </div>

            </div>

            {/* Right Column (5 Cols): Inspector Tabs (Hypotheses, Experiment Tree, Causal DAG, Certification) */}
            <div className="lg:col-span-5 space-y-4">
              {/* Tab Navigation */}
              <div className="bg-slate-900 p-1 rounded-xl border border-slate-800 flex items-center justify-between text-xs font-semibold">
                <button
                  onClick={() => setActiveInspectorTab("hypotheses")}
                  className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
                    activeInspectorTab === "hypotheses"
                      ? "bg-purple-600 text-white shadow-md"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  🔬 Hypotheses ({investigation.hypotheses.length})
                </button>
                <button
                  onClick={() => setActiveInspectorTab("experiments")}
                  className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
                    activeInspectorTab === "experiments"
                      ? "bg-indigo-600 text-white shadow-md"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  🌳 Graph ({investigation.runs.length})
                </button>
                <button
                  onClick={() => setActiveInspectorTab("causal_dag")}
                  className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
                    activeInspectorTab === "causal_dag"
                      ? "bg-rose-600 text-white shadow-md"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  🔍 Causal DAG
                </button>
                <button
                  onClick={() => setActiveInspectorTab("certification")}
                  className={`flex-1 py-2 rounded-lg transition cursor-pointer ${
                    activeInspectorTab === "certification"
                      ? "bg-emerald-600 text-white shadow-md"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  🛡️ Certificate
                </button>
              </div>

              {/* Tab Content Panels */}
              {activeInspectorTab === "hypotheses" && (
                <HypothesisBoard
                  hypotheses={investigation.hypotheses}
                  falsificationPlans={investigation.falsificationPlans}
                  activeHypothesis={investigation.activeHypothesis}
                  leadingHypothesis={investigation.leadingHypothesis}
                />
              )}

              {activeInspectorTab === "experiments" && (
                <ExperimentGraph
                  runs={investigation.runs}
                  decisionTraces={investigation.decisionTraces}
                  selectedExperimentId={selectedExperimentId}
                  onSelectExperiment={(id) => handleSelectExperiment(id)}
                />
              )}

              {activeInspectorTab === "causal_dag" && (
                <CausalDAGView diagnosis={investigation.diagnosis} />
              )}

              {activeInspectorTab === "certification" && (
                <CloseLoopCertification
                  investigationId={investigation.investigationId}
                  objective={investigation.objective || objective}
                  scenarioId={investigation.scenarioId || selectedScenarioId}
                  hardwarePresetId={investigation.hardwarePresetId || selectedPresetId}
                  seed={investigation.seed || seed}
                  leadingHypothesis={investigation.leadingHypothesis}
                  diagnosis={investigation.diagnosis}
                  conclusion={investigation.conclusion}
                  verification={investigation.verification}
                  regression={investigation.regression}
                  approval={investigation.approval}
                  patch={investigation.patch}
                  runs={investigation.runs}
                />
              )}
            </div>
          </div>

          {/* Bottom Stage: Live Event Stream Log */}
          <div className="w-full">
            <LiveEventStream events={investigation.events} />
          </div>
        </div>
      )}

      {/* Human Approval Modal (When phase is AWAITING_APPROVAL) */}
      <PatchApprovalModal
        patch={investigation.patch}
        diagnosis={investigation.diagnosis}
        leadingHypothesis={investigation.leadingHypothesis}
        objective={investigation.objective || objective}
        isOpen={isApprovalModalOpen && investigation.phase === "AWAITING_APPROVAL"}
        onClose={() => setIsApprovalModalOpen(false)}
        onApprove={async (decision, reason, token) => {
          await investigation.approvePatch(decision, reason, token);
        }}
      />
    </div>
  );
};
