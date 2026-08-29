
"use client";

import React, { useEffect, useRef } from "react";
import { ScenarioDefinition, TelemetryFrame, Violation } from "../types/simulation";
import { drawEmptyArena, drawTelemetryFrame } from "../lib/canvas-renderer";

interface SimulationCanvasProps {
  currentFrame: TelemetryFrame | null;
  scenario: ScenarioDefinition | null;
  latestViolation: Violation | null;
  simTime: number;
  simStep: number;
}

export const SimulationCanvas: React.FC<SimulationCanvasProps> = ({
  currentFrame,
  scenario,
  latestViolation,
  simTime,
  simStep,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (currentFrame) {
      drawTelemetryFrame(ctx, canvas.width, canvas.height, currentFrame, scenario);
    } else {
      drawEmptyArena(ctx, canvas.width, canvas.height, scenario);
    }
  }, [currentFrame, scenario]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-2xl relative flex flex-col">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
          <h3 className="text-xs font-semibold text-white tracking-wide">
            2D Physical World View (50m × 50m Arena)
          </h3>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Time:{" "}
          <span className="text-indigo-400 font-bold">
            {simTime.toFixed(2)}s
          </span>{" "}
          / Step:{" "}
          <span className="text-slate-300 font-bold">{simStep}</span>
        </div>
      </div>

      {/* Canvas Viewport Frame */}
      <div className="relative bg-slate-950 rounded-lg overflow-hidden border border-slate-800 aspect-square flex items-center justify-center shadow-inner">
        <canvas
          ref={canvasRef}
          width={600}
          height={600}
          className="w-full h-full block object-contain"
        />

        {/* Safety Overlay Alert Banner */}
        {latestViolation && (
          <div className="absolute top-3 left-3 right-3 p-3 rounded-lg bg-rose-950/90 border border-rose-500/60 text-rose-200 text-xs flex items-center justify-between shadow-2xl backdrop-blur animate-bounce duration-1000">
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
      </div>
    </div>
  );
};

