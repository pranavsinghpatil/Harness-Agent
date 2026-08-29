"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  ScenarioDefinition,
  TelemetryFrame,
  RunManifest,
  ReplayResponse,
  Violation,
} from "../types/simulation";
import { getScenarios, runScenario, replayRun, checkHealth } from "../lib/api";
import { Header } from "../components/Header";
import { ScenarioControls } from "../components/ScenarioControls";
import { SimulationCanvas } from "../components/SimulationCanvas";
import { PlaybackControls } from "../components/PlaybackControls";
import { VehicleHUD } from "../components/VehicleHUD";
import { HardwareHUD } from "../components/HardwareHUD";
import { ManifestCard } from "../components/ManifestCard";
import { HarnessView } from "../components/HarnessView";

export default function Home() {
  const [apiBase, setApiBase] = useState<string>("http://localhost:8000");
  const [activeTab, setActiveTab] = useState<"visualizer" | "harness">("visualizer");
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioDefinition | null>(null);
  const [seed, setSeed] = useState<number>(1337);
  const [maxSimTime, setMaxSimTime] = useState<number>(12);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [simStatusText, setSimStatusText] = useState<string>("READY");
  const [simStatusClass, setSimStatusClass] = useState<string>("text-indigo-400");

  // Playback & Frame state
  const [currentRunFrames, setCurrentRunFrames] = useState<TelemetryFrame[]>([]);
  const [currentManifest, setCurrentManifest] = useState<RunManifest | null>(null);
  const [replayResult, setReplayResult] = useState<ReplayResponse | null>(null);
  const [currentFrameIdx, setCurrentFrameIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [latestViolation, setLatestViolation] = useState<Violation | null>(null);

  const animationTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch scenarios and check backend connection
  const loadScenarios = useCallback(async (base: string) => {
    try {
      const isHealthy = await checkHealth(base);
      setBackendConnected(isHealthy);
      const list = await getScenarios(base);
      setScenarios(list);
      if (list.length > 0) {
        setSelectedScenario(list[0]);
        setSeed(list[0].seed ?? 1337);
        setMaxSimTime(list[0].max_sim_time ?? 12);
      }
    } catch (err) {
      console.error("Failed to connect or fetch scenarios:", err);
      setBackendConnected(false);
    }
  }, []);

  useEffect(() => {
    loadScenarios(apiBase);
  }, [apiBase, loadScenarios]);

  // Scenario change handler
  const handleSelectScenario = (scId: string) => {
    const sc = scenarios.find((s) => s.id === scId);
    if (sc) {
      setSelectedScenario(sc);
      setSeed(sc.seed ?? 1337);
      setMaxSimTime(sc.max_sim_time ?? 12);
      setCurrentRunFrames([]);
      setCurrentManifest(null);
      setReplayResult(null);
      setCurrentFrameIdx(0);
      setIsPlaying(false);
      setLatestViolation(null);
      setSimStatusText("READY");
      setSimStatusClass("text-indigo-400");
    }
  };

  // Run scenario episode
  const handleRunScenario = async () => {
    if (!selectedScenario) return;
    setIsSimulating(true);
    setSimStatusText("SIMULATING...");
    setSimStatusClass("text-amber-400");
    setReplayResult(null);
    setIsPlaying(false);

    try {
      const data = await runScenario(apiBase, {
        scenario_id: selectedScenario.id,
        seed: seed,
        max_sim_time: maxSimTime,
      });

      setCurrentManifest(data.manifest);
      setCurrentRunFrames(data.frames);
      setCurrentFrameIdx(0);

      const hasViolations = (data.manifest.violations_count ?? 0) > 0;
      setSimStatusText(data.manifest.status);
      setSimStatusClass(
        hasViolations || data.manifest.status.toLowerCase().includes("violation")
          ? "text-rose-400 font-bold"
          : "text-emerald-400 font-bold"
      );

      // Start playback automatically
      setIsPlaying(true);
    } catch (err: unknown) {
      console.error("Simulation run error:", err);
      alert("Simulation run failed: " + (err instanceof Error ? err.message : String(err)));
      setSimStatusText("ERROR");
      setSimStatusClass("text-rose-500");
    } finally {
      setIsSimulating(false);
    }
  };

  // Deterministic replay
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

    if (!isPlaying || currentRunFrames.length === 0) {
      return;
    }

    // 50Hz base update rate = 20ms per frame. Adjusted by playbackSpeed.
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
  }, [isPlaying, currentRunFrames.length, playbackSpeed]);

  // Sync violation detection on current frame
  const currentFrame = currentRunFrames[currentFrameIdx] ?? null;

  useEffect(() => {
    if (currentFrame?.new_violations && currentFrame.new_violations.length > 0) {
      setLatestViolation(currentFrame.new_violations[0]);
    } else if (currentFrame && currentFrame.min_clearance > 1.5) {
      setLatestViolation(null);
    }
  }, [currentFrame]);

  const handlePlayPauseToggle = () => {
    if (currentRunFrames.length === 0) return;
    if (currentFrameIdx >= currentRunFrames.length - 1) {
      setCurrentFrameIdx(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleScrub = (idx: number) => {
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation & Status Bar */}
      <Header
        apiBase={apiBase}
        onApiBaseChange={(newUrl) => {
          setApiBase(newUrl);
          loadScenarios(newUrl);
        }}
        backendConnected={backendConnected}
        simStatusText={simStatusText}
        simStatusClass={simStatusClass}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-6 max-w-[1600px] w-full mx-auto">
        {activeTab === "visualizer" ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column (3 cols): Controls & Fault Schedule */}
            <div className="lg:col-span-3">
              <ScenarioControls
                scenarios={scenarios}
                selectedScenario={selectedScenario}
                onSelectScenario={handleSelectScenario}
                seed={seed}
                onSeedChange={setSeed}
                maxSimTime={maxSimTime}
                onMaxSimTimeChange={setMaxSimTime}
                onRunScenario={handleRunScenario}
                onReplayRun={handleReplayRun}
                isSimulating={isSimulating}
                isVerifying={isVerifying}
                canReplay={!!currentManifest}
              />
            </div>

            {/* Center Column (6 cols): 2D Simulation Canvas & Telemetry Controls */}
            <div className="lg:col-span-6 space-y-4">
              <SimulationCanvas
                currentFrame={currentFrame}
                scenario={selectedScenario}
                latestViolation={latestViolation}
                simTime={currentTime}
                simStep={currentStep}
              />

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

              <VehicleHUD frame={currentFrame} />
            </div>

            {/* Right Column (3 cols): Hardware Metrics & Deterministic Manifest */}
            <div className="lg:col-span-3 space-y-5">
              <HardwareHUD
                metrics={currentFrame?.hardware_metrics ?? null}
                sensorQueues={currentFrame?.sensor_queue_depths ?? null}
              />

              <ManifestCard
                manifest={currentManifest}
                replayResult={replayResult}
              />
            </div>
          </div>
        ) : (
          /* Autonomous Reliability Loop Tab */
          <HarnessView apiBase={apiBase} scenarios={scenarios} />
        )}
      </main>
    </div>
  );
}