
"use client";

import React, { useEffect, useRef, useMemo } from "react";
import { ScenarioDefinition, TelemetryFrame, Violation } from "../types/simulation";
import { drawEmptyArena, drawTelemetryFrame } from "../lib/canvas-renderer";

interface SimulationCanvasProps {
  currentFrame: TelemetryFrame | null;
  scenario: ScenarioDefinition | null;
  latestViolation: Violation | null;
  simTime: number;
  simStep: number;
  isLive?: boolean;
  experimentId?: string | null;
  experimentPhase?: string;
  experimentOutcome?: "PASS" | "VIOLATION" | string | null;
  activeFaults?: string[];
  playbackFrames?: TelemetryFrame[];
  currentFrameIdx?: number;
}

export const SimulationCanvas: React.FC<SimulationCanvasProps> = ({
  currentFrame,
  scenario,
  latestViolation,
  simTime,
  simStep,
  isLive = true,
  experimentId,
  experimentPhase,
  experimentOutcome,
  activeFaults = [],
  playbackFrames = [],
  currentFrameIdx = 0,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Compute trajectory trail from start of run up to current frame
  const trajectoryTrail = useMemo(() => {
    if (!playbackFrames || playbackFrames.length === 0) return undefined;
    const endIdx = Math.min(playbackFrames.length - 1, Math.max(0, currentFrameIdx));
    const trail: Array<{ x: number; y: number }> = [];
    const stepSample = Math.max(1, Math.floor(endIdx / 200)); // limit to ~200 points for speed
    for (let i = 0; i <= endIdx; i += stepSample) {
      const f = playbackFrames[i];
      const vs = f?.vehicle_state || (f as unknown as { vehicle?: { x: number; y: number } })?.vehicle;
      if (vs && vs.x !== undefined && vs.y !== undefined) {
        trail.push({ x: vs.x, y: vs.y });
      }
    }
    // Always include the current head frame
    const curVs = currentFrame?.vehicle_state || (currentFrame as unknown as { vehicle?: { x: number; y: number } })?.vehicle;
    if (curVs && curVs.x !== undefined && curVs.y !== undefined) {
      trail.push({ x: curVs.x, y: curVs.y });
    }
    return trail.length > 1 ? trail : undefined;
  }, [playbackFrames, currentFrameIdx, currentFrame]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (currentFrame) {
      drawTelemetryFrame(ctx, canvas.width, canvas.height, currentFrame, scenario, {
        trajectoryTrail,
      });
    } else {
      drawEmptyArena(ctx, canvas.width, canvas.height, scenario);
    }
  }, [currentFrame, scenario, trajectoryTrail]);

  const vehicleState = currentFrame?.vehicle_state || (currentFrame as unknown as { vehicle?: { x: number; y: number; heading: number; velocity: number } })?.vehicle;
  const currentFaults = currentFrame?.active_faults || activeFaults || [];

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-3.5 sm:p-4 shadow-2xl relative flex flex-col space-y-3">
      {/* Top Header Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center space-x-2">
          {isLive ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 font-mono text-[11px] font-bold">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span>LIVE EXPERIMENT</span>
              {experimentId && experimentId !== "LIVE" && (
                <span className="text-white ml-1 font-extrabold">{experimentId}</span>
              )}
              {experimentPhase && (
                <span className="text-slate-300 font-normal">({experimentPhase})</span>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 font-mono text-[11px] font-bold">
              <span>⏪ HISTORICAL REPLAY</span>
              {experimentId && (
                <span className="text-white ml-1 font-extrabold">{experimentId}</span>
              )}
              {experimentPhase && (
                <span className="text-slate-300 font-normal">({experimentPhase})</span>
              )}
              {experimentOutcome && (
                <span
                  className={`ml-1 px-1.5 py-0.2 rounded text-[10px] ${
                    experimentOutcome === "PASS"
                      ? "bg-emerald-500/30 text-emerald-300 border border-emerald-500/50"
                      : "bg-rose-500/30 text-rose-300 border border-rose-500/50"
                  }`}
                >
                  {experimentOutcome === "PASS" ? "✓ PASS" : "✗ VIOLATION"}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Sim Clock & Step */}
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <div>
            Time: <span className="text-indigo-300 font-bold">{simTime.toFixed(2)}s</span>
          </div>
          <div>
            Step: <span className="text-slate-200 font-bold">{simStep}</span>
          </div>
          {playbackFrames.length > 0 && (
            <div className="text-slate-400">
              Frame: <span className="text-slate-200 font-semibold">{currentFrameIdx + 1}</span> / {playbackFrames.length}
            </div>
          )}
        </div>
      </div>

      {/* Canvas Viewport Frame */}
      <div className="relative bg-slate-950 rounded-xl overflow-hidden border border-slate-800/90 aspect-square w-full flex items-center justify-center shadow-inner">
        <canvas
          ref={canvasRef}
          width={600}
          height={600}
          className="w-full h-full block object-contain"
        />

        {/* Top-Right Active Hazards / Faults Overlay */}
        {currentFaults.length > 0 && (
          <div className="absolute top-2.5 right-2.5 flex flex-col items-end gap-1 pointer-events-none z-10">
            {currentFaults.map((f, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/50 text-amber-300 font-mono text-[10px] font-semibold backdrop-blur shadow-md flex items-center gap-1"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                FAULT: {f}
              </span>
            ))}
          </div>
        )}

        {/* Safety Overlay Alert Banner */}
        {latestViolation && (
          <div className="absolute top-3 left-3 right-3 p-3 rounded-lg bg-rose-950/90 border border-rose-500/60 text-rose-200 text-xs flex items-center justify-between shadow-2xl backdrop-blur animate-bounce duration-1000 z-20">
            <div className="flex items-center space-x-2 overflow-hidden">
              <span className="text-rose-400 font-bold uppercase tracking-wider whitespace-nowrap">
                ⚠️ VIOLATION:
              </span>
              <span className="text-rose-100 font-mono truncate">
                {latestViolation.rule_name}: {latestViolation.description}
              </span>
            </div>
            <span className="px-2 py-0.5 rounded bg-rose-600 text-white font-black text-[10px] tracking-wider uppercase ml-2 flex-shrink-0">
              CRITICAL
            </span>
          </div>
        )}

        {/* Bottom HUD Telemetry Strip */}
        {vehicleState && (
          <div className="absolute bottom-2 left-2 right-2 px-3 py-1.5 rounded-lg bg-slate-900/85 backdrop-blur border border-slate-800/80 text-[11px] font-mono text-slate-300 flex flex-wrap items-center justify-between gap-2 shadow-lg pointer-events-none">
            <div className="flex items-center gap-3">
              <span>
                Pose: <span className="text-indigo-300 font-semibold">({vehicleState.x?.toFixed(2)}m, {vehicleState.y?.toFixed(2)}m)</span>
              </span>
              <span>
                Heading: <span className="text-sky-300 font-semibold">{((vehicleState.heading || 0) * (180 / Math.PI)).toFixed(1)}°</span>
              </span>
              <span>
                Vel: <span className="text-emerald-300 font-semibold">{(vehicleState.velocity || 0).toFixed(2)} m/s</span>
              </span>
            </div>

            <div>
              Clr:{" "}
              <span
                className={`font-bold ${
                  (currentFrame?.min_clearance ?? 2.0) < 1.0
                    ? "text-rose-400 animate-pulse"
                    : "text-indigo-300"
                }`}
              >
                {(currentFrame?.min_clearance ?? 2.0).toFixed(2)}m
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

