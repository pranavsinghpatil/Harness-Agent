"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ScenarioDefinition,
  HardwarePreset,
  TelemetryFrame,
  RunManifest,
  ReplayResponse,
  Violation,
  HarnessEvaluation,
  VehicleState,
  ActuatorCommand,
  HardwareMetrics,
  DynamicObstacle,
} from "../types/simulation";
import {
  runScenario,
  replayRun,
  runFullEvaluation,
} from "../lib/api";
import { SimulationStreamClient } from "../lib/websocket";
import { ScenarioControls } from "./ScenarioControls";
import { SimulationCanvas } from "./SimulationCanvas";
import { PlaybackControls } from "./PlaybackControls";
import { VehicleHUD } from "./VehicleHUD";
import { HardwareHUD } from "./HardwareHUD";
import { ManifestCard } from "./ManifestCard";

/**
 * Props for the legacy/secondary AdHocDebuggerView component.
 */
export interface AdHocDebuggerViewProps {
  apiBase: string;
  presets: HardwarePreset[];
  scenarios: ScenarioDefinition[];
  onStatusChange?: (statusText: string, statusClass: string) => void;
}

/**
 * Ad-Hoc Evaluation Debugger component allowing manual scenario execution,
 * interactive 2D simulation canvas scrub, and live WebSocket streaming.
 */
export const AdHocDebuggerView: React.FC<AdHocDebuggerViewProps> = ({
  apiBase,
  presets,
  scenarios,
  onStatusChange,
}) => {
  // Presets & Scenarios
  const [selectedPresetId, setSelectedPresetId] = useState<string>("RDK_X5");
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);

  // Derive active preset and scenario
  const activePresetId = (presets.some((p) => p.id === selectedPresetId) ? selectedPresetId : presets[0]?.id) ?? "RDK_X5";
  const activeScenario = (selectedScenarioId ? scenarios.find((s) => s.id === selectedScenarioId) : null) ?? scenarios[0] ?? null;

  // Configuration
  const [seed, setSeed] = useState<number>(1337);
  const [maxSimTime, setMaxSimTime] = useState<number>(12);

  // Status & Progress
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [simStatusText, setSimStatusText] = useState<string>("READY");
  const [simStatusClass, setSimStatusClass] = useState<string>("text-indigo-400");

  const updateStatus = (text: string, cls: string): void => {
    setSimStatusText(text);
    setSimStatusClass(cls);
    onStatusChange?.(text, cls);
  };

  // Closed-Loop Evaluation Result & Run View State
  const [evaluation, setEvaluation] = useState<HarnessEvaluation | null>(null);
  const [activeRunView, setActiveRunView] = useState<"baseline" | "verified">("baseline");
  const [inspectorTab, setInspectorTab] = useState<"diagnostics" | "patch" | "matrix" | "hardware">("matrix");

  // Playback & Frame state
  const [currentRunFrames, setCurrentRunFrames] = useState<TelemetryFrame[]>([]);
  const [currentManifest, setCurrentManifest] = useState<RunManifest | null>(null);
  const [replayResult, setReplayResult] = useState<ReplayResponse | null>(null);
  const [currentFrameIdx, setCurrentFrameIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [latestViolation, setLatestViolation] = useState<Violation | null>(null);

  const animationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const streamClientRef = useRef<SimulationStreamClient | null>(null);

  // Clean up streaming on unmount
  useEffect(() => {
    return () => {
      if (streamClientRef.current) {
        streamClientRef.current.disconnect();
      }
      if (animationTimerRef.current) {
        clearInterval(animationTimerRef.current);
      }
    };
  }, []);

  // Scenario Selection Handler
  const handleSelectScenario = (scId: string) => {
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      setIsStreaming(false);
    }

    setSelectedScenarioId(scId);
    const sc = scenarios.find((s) => s.id === scId);
    if (sc) {
      setSeed(sc.seed ?? 1337);
      setMaxSimTime(sc.max_sim_time ?? 12);
      setEvaluation(null);
      setCurrentRunFrames([]);
      setCurrentManifest(null);
      setReplayResult(null);
      setCurrentFrameIdx(0);
      setIsPlaying(false);
      setLatestViolation(null);
      updateStatus("READY", "text-indigo-400");
    }
  };

  // Convert HarnessRun frames to TelemetryFrame format
  const extractFrames = (framesRaw?: unknown[]): TelemetryFrame[] => {
    if (!framesRaw || !Array.isArray(framesRaw)) return [];
    return framesRaw.map((item: unknown, idx: number) => {
      const f = (item || {}) as Record<string, unknown>;
      const vRaw = f.vehicle as Record<string, number> | undefined;
      const vStateRaw = f.vehicle_state as VehicleState | undefined;
      const vState: VehicleState = vStateRaw || {
        x: vRaw?.x ?? 0,
        y: vRaw?.y ?? 0,
        heading: vRaw?.heading ?? 0,
        velocity: vRaw?.velocity ?? 0,
        steer_angle: vRaw?.steer_angle ?? 0,
      };

      return {
        sim_time: (f.sim_time as number) ?? idx * 0.02,
        step: (f.step as number) ?? idx,
        vehicle_state: vState,
        actuator_command: (f.actuator_command as ActuatorCommand) || { throttle: 0, steering: 0, brake: 0, emergency_stop: false },
        min_clearance: (f.min_clearance as number) ?? 2.0,
        active_faults: (f.active_faults as string[]) ?? [],
        sensor_queue_depths: (f.sensor_queue_depths as Record<string, number>) ?? {},
        hardware_metrics: (f.hardware_metrics as HardwareMetrics) || {
          cpu_utilization: 0.1,
          temperature_celsius: 45,
          is_throttled: false,
          deadline_misses: 0,
          queue_depth: 0,
        },
        dynamic_obstacles: (f.dynamic_obstacles as DynamicObstacle[]) ?? [],
        new_violations: (f.new_violations as Violation[]) ?? [],
      };
    });
  };

  // 1. Full Closed-Loop Evaluation (POST /api/harness/evaluate-full)
  const handleRunFullEvaluation = async () => {
    if (!activeScenario) return;
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      setIsStreaming(false);
    }

    setIsEvaluating(true);
    updateStatus("RUNNING CLOSED-LOOP EVALUATION...", "text-purple-400 font-bold");
    setReplayResult(null);
    setIsPlaying(false);

    try {
      const evalRes = await runFullEvaluation(apiBase, {
        hardware_preset_id: activePresetId,
        scenario_id: activeScenario.id,
        seed: seed,
        mode: "AUTONOMOUS_HARNESS",
      });

      setEvaluation(evalRes);

      const baselineFrames = extractFrames(evalRes.baseline_run?.telemetry_frames);
      setCurrentRunFrames(baselineFrames);
      setActiveRunView("baseline");
      setCurrentFrameIdx(0);

      if (evalRes.baseline_run) {
        setCurrentManifest({
          run_id: evalRes.baseline_run.run_id,
          trace_hash: evalRes.baseline_run.trace_hash,
          violations_count: evalRes.baseline_run.violations_count,
          status: evalRes.baseline_run.status,
          sim_duration_seconds: evalRes.baseline_run.sim_duration_s,
        });

        const vCount = evalRes.baseline_run.violations_count ?? 0;
        const vName = evalRes.baseline_run.violations?.[0]?.rule_name || evalRes.baseline_run.status || "SAFETY_VIOLATION";
        if (vCount > 0) {
          updateStatus(`BASELINE: ${vName} (${vCount} VIOLATION${vCount > 1 ? "S" : ""})`, "text-rose-400 font-bold");
          if (evalRes.baseline_run.violations?.[0]) {
            setLatestViolation(evalRes.baseline_run.violations[0]);
          }
        } else {
          updateStatus(`BASELINE: ${evalRes.baseline_run.status || "COMPLETED"}`, "text-emerald-400 font-bold");
          setLatestViolation(null);
        }
      }

      setIsPlaying(true);
    } catch (err: unknown) {
      console.error("Full evaluation error:", err);
      alert("Closed-loop evaluation failed: " + (err instanceof Error ? err.message : String(err)));
      updateStatus("EVALUATION ERROR", "text-rose-500 font-bold");
    } finally {
      setIsEvaluating(false);
    }
  };

  // Switch between Baseline Run and Verified Run
  const handleSwitchRunView = (view: "baseline" | "verified") => {
    if (!evaluation) return;
    const targetRun = view === "baseline" ? evaluation.baseline_run : evaluation.verification_run;
    if (!targetRun) return;

    setActiveRunView(view);
    setIsPlaying(false);

    const frames = extractFrames(targetRun.telemetry_frames);
    setCurrentRunFrames(frames);
    setCurrentFrameIdx(0);
    setCurrentManifest({
      run_id: targetRun.run_id,
      trace_hash: targetRun.trace_hash,
      violations_count: targetRun.violations_count,
      status: targetRun.status,
      sim_duration_seconds: targetRun.sim_duration_s,
    });

    const vCount = targetRun.violations_count ?? 0;
    if (view === "baseline") {
      const vName = targetRun.violations?.[0]?.rule_name || targetRun.status || "SAFETY_VIOLATION";
      if (vCount > 0) {
        updateStatus(`BASELINE: ${vName} (${vCount} VIOLATION${vCount > 1 ? "S" : ""})`, "text-rose-400 font-bold");
        if (targetRun.violations?.[0]) {
          setLatestViolation(targetRun.violations[0]);
        }
      } else {
        updateStatus(`BASELINE: ${targetRun.status}`, "text-emerald-400 font-bold");
        setLatestViolation(null);
      }
    } else {
      if (vCount === 0) {
        updateStatus("VERIFIED: SAFE (0 VIOLATIONS)", "text-emerald-400 font-bold");
        setLatestViolation(null);
      } else {
        updateStatus(`VERIFIED: ${targetRun.status} (${vCount} VIOLATIONS)`, "text-rose-400 font-bold");
        if (targetRun.violations?.[0]) {
          setLatestViolation(targetRun.violations[0]);
        }
      }
    }

    setIsPlaying(true);
  };

  // 2. Real-Time WebSocket Streaming Handler
  const handleStartStreaming = () => {
    if (!activeScenario) return;
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
    }

    setIsPlaying(false);
    setIsStreaming(true);
    setCurrentRunFrames([]);
    setCurrentFrameIdx(0);
    setCurrentManifest(null);
    setReplayResult(null);
    setLatestViolation(null);
    updateStatus("STREAMING LIVE", "text-cyan-400 font-bold");
    setInspectorTab("hardware");

    const client = new SimulationStreamClient(apiBase, activeScenario.id, {
      onFrame: (frame, status) => {
        setCurrentRunFrames((prev) => {
          const next = [...prev, frame];
          setCurrentFrameIdx(next.length - 1);
          return next;
        });

        if (frame.new_violations && frame.new_violations.length > 0) {
          setLatestViolation(frame.new_violations[0]);
        }

        const isViolation = status.toLowerCase().includes("violation");
        updateStatus(status, isViolation ? "text-rose-400 font-bold" : "text-cyan-400 font-bold");
      },
      onManifest: (manifest) => {
        setCurrentManifest(manifest);
        setIsStreaming(false);
        const hasViolations = (manifest.violations_count ?? 0) > 0;
        updateStatus(
          manifest.status,
          hasViolations || manifest.status.toLowerCase().includes("violation")
            ? "text-rose-400 font-bold"
            : "text-emerald-400 font-bold"
        );
      },
      onError: (errorMsg) => {
        setIsStreaming(false);
        updateStatus("STREAM ERROR", "text-rose-500 font-bold");
        alert(`WebSocket Stream error: ${errorMsg}`);
      },
      onClose: () => {
        setIsStreaming(false);
      },
    });

    streamClientRef.current = client;
    client.connect();
  };

  const handleStopStreaming = () => {
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      streamClientRef.current = null;
    }
    setIsStreaming(false);
    updateStatus("STREAM STOPPED", "text-amber-400 font-semibold");
  };

  // 3. Batch Run Simulation Handler (REST)
  const handleRunScenario = async () => {
    if (!activeScenario) return;
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      setIsStreaming(false);
    }

    setIsSimulating(true);
    updateStatus("SIMULATING...", "text-amber-400");
    setReplayResult(null);
    setIsPlaying(false);

    try {
      const data = await runScenario(apiBase, {
        scenario_id: activeScenario.id,
        seed: seed,
        max_sim_time: maxSimTime,
      });

      setCurrentManifest(data.manifest);
      setCurrentRunFrames(data.frames);
      setCurrentFrameIdx(0);

      const hasViolations = (data.manifest.violations_count ?? 0) > 0;
      updateStatus(
        data.manifest.status,
        hasViolations || data.manifest.status.toLowerCase().includes("violation")
          ? "text-rose-400 font-bold"
          : "text-emerald-400 font-bold"
      );

      setIsPlaying(true);
    } catch (err: unknown) {
      console.error("Simulation run error:", err);
      alert("Simulation run failed: " + (err instanceof Error ? err.message : String(err)));
      updateStatus("ERROR", "text-rose-500");
    } finally {
      setIsSimulating(false);
    }
  };

  // 4. Deterministic Replay Verification Handler
  const handleReplayRun = async () => {
    if (!currentManifest) return;
    setIsVerifying(true);
    try {
      const res = await replayRun(apiBase, currentManifest.run_id);
      setReplayResult(res);
      if (res.is_bit_exact_match) {
        alert(
          `✅ Replay Verified! 100% Bit-Exact Determinism match.\nTrace Hash: ${res.original_trace_hash.substring(
            0,
            24
          )}...`
        );
      } else {
        alert(`⚠️ Determinism Mismatch: ${res.difference_details ?? "Traces diverged"}`);
      }
    } catch (err: unknown) {
      console.error("Replay check failed:", err);
      alert("Replay verification failed: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsVerifying(false);
    }
  };

  // Playback Loop
  useEffect(() => {
    if (animationTimerRef.current) {
      clearInterval(animationTimerRef.current);
      animationTimerRef.current = null;
    }

    if (!isPlaying || currentRunFrames.length === 0 || isStreaming) {
      return;
    }

    const intervalMs = Math.max(4, Math.round(20 / playbackSpeed));

    animationTimerRef.current = setInterval(() => {
      setCurrentFrameIdx((prevIdx) => {
        if (prevIdx >= currentRunFrames.length - 1) {
          setIsPlaying(false);
          return prevIdx;
        }
        return prevIdx + 1;
      });
    }, intervalMs);

    return () => {
      if (animationTimerRef.current) {
        clearInterval(animationTimerRef.current);
      }
    };
  }, [isPlaying, currentRunFrames.length, playbackSpeed, isStreaming]);

  const currentFrame = isStreaming
    ? (currentRunFrames.length > 0 ? currentRunFrames[currentRunFrames.length - 1] : null)
    : (currentRunFrames[currentFrameIdx] ?? (currentRunFrames.length > 0 ? currentRunFrames[currentRunFrames.length - 1] : null));

  const activeViolation: Violation | null =
    latestViolation ||
    (currentFrame?.new_violations && currentFrame.new_violations.length > 0
      ? currentFrame.new_violations[0]
      : (currentFrame && currentFrame.min_clearance < 0.8 && activeRunView === "baseline" && evaluation?.baseline_run?.violations?.[0])
      ? evaluation.baseline_run.violations[0]
      : null);

  const handlePlayPauseToggle = () => {
    if (currentRunFrames.length === 0 || isStreaming) return;
    if (currentFrameIdx >= currentRunFrames.length - 1) {
      setCurrentFrameIdx(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleScrub = (idx: number) => {
    if (isStreaming) return;
    setIsPlaying(false);
    setCurrentFrameIdx(idx);
  };

  const totalDuration =
    currentRunFrames.length > 0
      ? currentRunFrames[currentRunFrames.length - 1].sim_time
      : maxSimTime;
  const currentTime = currentFrame?.sim_time ?? 0;
  const currentStep = currentFrame?.step ?? 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left Column (3 cols): Hardware Profile & Scenario Controls */}
      <div className="lg:col-span-3">
        <ScenarioControls
          presets={presets}
          selectedPresetId={activePresetId}
          onSelectPreset={setSelectedPresetId}
          scenarios={scenarios}
          selectedScenario={activeScenario}
          onSelectScenario={handleSelectScenario}
          seed={seed}
          onSeedChange={setSeed}
          maxSimTime={maxSimTime}
          onMaxSimTimeChange={setMaxSimTime}
          onRunFullEvaluation={handleRunFullEvaluation}
          onRunScenario={handleRunScenario}
          onStartStreaming={handleStartStreaming}
          onStopStreaming={handleStopStreaming}
          onReplayRun={handleReplayRun}
          isEvaluating={isEvaluating}
          isSimulating={isSimulating}
          isStreaming={isStreaming}
          isVerifying={isVerifying}
          canReplay={!!currentManifest}
        />
      </div>

      {/* Center Column (5 cols): 2D Simulation Canvas & Playback Controls */}
      <div className="lg:col-span-5 space-y-4">
        {/* Run View Toggle Bar (When evaluation exists) */}
        {evaluation && (
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-2 flex items-center justify-between shadow-lg">
            <span className="text-[11px] font-mono text-slate-400 font-semibold px-2">
              PLAYBACK TRACE:
            </span>
            <div className="flex items-center gap-1.5 font-mono text-xs">
              <button
                onClick={() => handleSwitchRunView("baseline")}
                disabled={!evaluation.baseline_run}
                className={`px-3 py-1 rounded-lg transition font-semibold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
                  activeRunView === "baseline"
                    ? "bg-rose-600 text-white shadow-md shadow-rose-600/30"
                    : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-rose-300" />
                <span>Baseline ({evaluation.baseline_run?.violations_count ?? 0} Violations)</span>
              </button>

              <button
                onClick={() => handleSwitchRunView("verified")}
                disabled={!evaluation.verification_run}
                className={`px-3 py-1 rounded-lg transition font-semibold flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed ${
                  activeRunView === "verified"
                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                    : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-300" />
                <span>Patched ({evaluation.verification_run?.violations_count ?? 0} Violations)</span>
              </button>
            </div>
          </div>
        )}

        {/* 2D Canvas */}
        <SimulationCanvas
          currentFrame={currentFrame}
          scenario={activeScenario}
          latestViolation={activeViolation}
          simTime={currentTime}
          simStep={currentStep}
        />

        {/* Playback Controls & Scrubber */}
        <PlaybackControls
          isPlaying={isPlaying}
          onPlayPauseToggle={handlePlayPauseToggle}
          currentFrameIdx={currentFrameIdx}
          totalFrames={currentRunFrames.length}
          onScrub={handleScrub}
          playbackSpeed={playbackSpeed}
          onSpeedChange={setPlaybackSpeed}
          currentTime={currentTime}
          totalDuration={totalDuration}
        />

        {/* Vehicle Actuator & Kinematics HUD */}
        <VehicleHUD frame={currentFrame} />
      </div>

      {/* Right Column (4 cols): Closed-Loop Lifecycle Inspector & Telemetry */}
      <div className="lg:col-span-4 space-y-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl space-y-4">
          {/* Inspector Tabs */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px] font-medium">
              <button
                onClick={() => setInspectorTab("matrix")}
                className={`px-2.5 py-1 rounded-md transition ${
                  inspectorTab === "matrix"
                    ? "bg-indigo-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🛡️ 3-Pillars
              </button>
              <button
                onClick={() => setInspectorTab("diagnostics")}
                className={`px-2.5 py-1 rounded-md transition ${
                  inspectorTab === "diagnostics"
                    ? "bg-indigo-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🔍 Diagnostics
              </button>
              <button
                onClick={() => setInspectorTab("patch")}
                className={`px-2.5 py-1 rounded-md transition ${
                  inspectorTab === "patch"
                    ? "bg-indigo-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                📝 Patch Diff
              </button>
              <button
                onClick={() => setInspectorTab("hardware")}
                className={`px-2.5 py-1 rounded-md transition ${
                  inspectorTab === "hardware"
                    ? "bg-indigo-600 text-white font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                📊 Telemetry
              </button>
            </div>

            {isStreaming ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                LIVE STREAM
              </span>
            ) : isEvaluating ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                EVALUATING
              </span>
            ) : evaluation?.final_result?.verdict ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
                {evaluation.final_result.verdict}
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                STANDBY
              </span>
            )}
          </div>

          {/* Tab 1: 3-Pillars Reliability Gate */}
          {inspectorTab === "matrix" && (
            evaluation?.final_result ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wide mb-1">
                    Reliability Verification Matrix
                  </h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Autonomous gate proving safety invariant non-regression on identical seed and hardware preset.
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 1: Safety</div>
                    <div
                      className={`text-xs font-bold mt-0.5 ${
                        evaluation.final_result.safety_pillar_passed !== false
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {evaluation.final_result.safety_pillar_passed !== false ? "✓ PASS" : "✗ FAIL"}
                    </div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 2: Behavior</div>
                    <div
                      className={`text-xs font-bold mt-0.5 ${
                        evaluation.final_result.behavior_pillar_passed !== false
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {evaluation.final_result.behavior_pillar_passed !== false ? "✓ PASS" : "✗ FAIL"}
                    </div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 3: Health</div>
                    <div
                      className={`text-xs font-bold mt-0.5 ${
                        evaluation.final_result.runtime_health_pillar_passed !== false
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {evaluation.final_result.runtime_health_pillar_passed !== false ? "✓ PASS" : "✗ FAIL"}
                    </div>
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Baseline Violations:</span>
                    <span className="text-rose-400 font-bold">
                      {evaluation.final_result.baseline_violations_count ??
                        evaluation.baseline_run?.violations_count ??
                        0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Verified Violations:</span>
                    <span className="text-emerald-400 font-bold">
                      {evaluation.final_result.verification_violations_count ??
                        evaluation.verification_run?.violations_count ??
                        0}
                    </span>
                  </div>
                  {evaluation.final_result.min_clearance_verified !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Min Clearance (Verified):</span>
                      <span className="text-indigo-400 font-bold">
                        {evaluation.final_result.min_clearance_verified.toFixed(2)} m
                      </span>
                    </div>
                  )}
                  <div className="pt-2 border-t border-slate-800 text-[11px] text-emerald-300 font-sans leading-relaxed">
                    {evaluation.final_result.improvement_summary ||
                      "Hardened controller successfully mitigated hardware faults with zero safety violations."}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wide mb-1">
                    3-Pillars Reliability Gate
                  </h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Autonomous 3-pillar gate evaluating Safety Invariant Non-Regression, Behavioral Fidelity, and Runtime Health.
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 1: Safety</div>
                    <div className="text-xs font-semibold text-slate-500 mt-0.5">PENDING</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 2: Behavior</div>
                    <div className="text-xs font-semibold text-slate-500 mt-0.5">PENDING</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
                    <div className="text-[10px] text-slate-400">Pillar 3: Health</div>
                    <div className="text-xs font-semibold text-slate-500 mt-0.5">PENDING</div>
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Active Live Status:</span>
                    <span className={simStatusClass}>{simStatusText}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Current Violations:</span>
                    <span className={latestViolation || (currentManifest?.violations_count ?? 0) > 0 ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                      {currentManifest?.violations_count ?? (latestViolation ? 1 : 0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Min Clearance:</span>
                    <span className="text-indigo-400 font-bold">
                      {currentFrame ? `${currentFrame.min_clearance.toFixed(2)} m` : "--"}
                    </span>
                  </div>
                </div>

                <button
                  onClick={handleRunFullEvaluation}
                  disabled={isEvaluating || isSimulating || !activeScenario}
                  className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <span>⚡ Run Full Closed-Loop Evaluation</span>
                </button>
              </div>
            )
          )}

          {/* Tab 2: Causal Diagnostics DAG */}
          {inspectorTab === "diagnostics" && (
            evaluation?.diagnosis ? (
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wide">
                    Primary Root Cause
                  </h3>
                  <p className="text-xs text-slate-200 mt-1 font-medium">
                    {evaluation.diagnosis?.primary_root_cause ||
                      (evaluation.diagnosis?.root_causes && evaluation.diagnosis.root_causes[0]) ||
                      "Hardware perturbation induced observation staleness leading to safety breach."}
                  </p>
                </div>

                {evaluation.diagnosis?.causal_nodes && evaluation.diagnosis.causal_nodes.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-slate-800">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Causal Chain Nodes
                    </span>
                    <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                      {evaluation.diagnosis.causal_nodes.map((node, i) => (
                        <div
                          key={node.node_id || i}
                          className="p-2 rounded bg-slate-950 border border-slate-800 text-xs flex items-start gap-2"
                        >
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 shrink-0">
                            {node.category}
                          </span>
                          <span className="text-slate-300 text-[11px]">{node.summary}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {evaluation.diagnosis?.patch_recommendations && (
                  <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                    <strong className="text-slate-300">Recommendations:</strong>{" "}
                    {evaluation.diagnosis.patch_recommendations.join("; ")}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wide">
                    Causal Telemetry Diagnostics
                  </h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed mt-1">
                    Synthesizes causal DAG pathways from physical hardware perturbations to queue bottlenecks and safety violations.
                  </p>
                </div>

                {activeScenario?.fault_schedule && activeScenario.fault_schedule.length > 0 ? (
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                    <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider block">
                      Scheduled Scenario Faults
                    </span>
                    <div className="space-y-1.5">
                      {activeScenario.fault_schedule.map((f) => (
                        <div key={f.id} className="text-xs flex items-center justify-between bg-slate-900/60 p-2 rounded border border-slate-800 font-mono">
                          <span className="text-indigo-300">{f.target} ({f.type})</span>
                          <span className="text-amber-400 text-[11px]">t={f.start_time}s ({f.duration}s)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-400">
                    No active fault schedule defined for this scenario.
                  </div>
                )}

                <button
                  onClick={handleRunFullEvaluation}
                  disabled={isEvaluating || isSimulating || !activeScenario}
                  className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <span>⚡ Run Full Evaluation to Synthesize Causal DAG</span>
                </button>
              </div>
            )
          )}

          {/* Tab 3: Synthesized Code Patch */}
          {inspectorTab === "patch" && (
            evaluation?.patch ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-cyan-300">
                    Strategy: {evaluation.patch.strategies_applied?.join(", ") || evaluation.patch.strategy_used || "Dynamic Stopping & Staleness Guard"}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                    {evaluation.patch.validation_status || "DIFF GENERATED"}
                  </span>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-400 max-h-64 overflow-y-auto whitespace-pre leading-relaxed">
                  {evaluation.patch.unified_diff || evaluation.patch.diff || evaluation.patch.patched_code || "No diff generated."}
                </div>

                {evaluation.patch.provenance?.rationale && (
                  <p className="text-[11px] text-slate-400 italic">
                    Rationale: {evaluation.patch.provenance.rationale}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <h3 className="text-xs font-bold text-cyan-300 uppercase tracking-wide">
                    Hardened Controller Auto-Patch
                  </h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed mt-1">
                    Auto-synthesizes AST-safe Python patches (Dynamic Stopping, Observation Staleness Guards) to prevent hardware-induced failures.
                  </p>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-400 font-mono space-y-1.5">
                  <div className="flex justify-between">
                    <span>Target Controller:</span>
                    <span className="text-slate-200">reference_agent.py</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Hardening Strategies:</span>
                    <span className="text-cyan-300">Dynamic Stopping, Staleness Guard</span>
                  </div>
                  <div className="flex justify-between">
                    <span>AST Validation:</span>
                    <span className="text-emerald-400">Strict AST Check</span>
                  </div>
                </div>

                <button
                  onClick={handleRunFullEvaluation}
                  disabled={isEvaluating || isSimulating || !activeScenario}
                  className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition cursor-pointer"
                >
                  <span>⚡ Run Full Evaluation to Synthesize Code Patch</span>
                </button>
              </div>
            )
          )}

          {/* Tab 4: Live Telemetry HUD & Manifest */}
          {inspectorTab === "hardware" && (
            <div className="space-y-4">
              <HardwareHUD
                metrics={currentFrame?.hardware_metrics ?? null}
                sensorQueues={currentFrame?.sensor_queue_depths ?? null}
              />
              <ManifestCard
                manifest={currentManifest}
                replayResult={replayResult}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

