"use client";

import React from "react";
import { HardwareMetrics } from "../types/simulation";

interface HardwareHUDProps {
  metrics: HardwareMetrics | null;
  sensorQueues: Record<string, number> | null;
}

export const HardwareHUD: React.FC<HardwareHUDProps> = ({
  metrics,
  sensorQueues,
}) => {
  const cpuPct = Math.round((metrics?.cpu_utilization ?? 0) * 100);
  const temp = metrics?.temperature_celsius ?? 35.0;
  const isThrottled = metrics?.is_throttled ?? false;
  const misses = metrics?.deadline_misses ?? 0;

  let totalPackets = 0;
  if (sensorQueues) {
    for (const q in sensorQueues) {
      totalPackets += sensorQueues[q] || 0;
    }
  }

  // CPU bar color
  const cpuColorClass =
    cpuPct > 85
      ? "bg-rose-500"
      : cpuPct > 65
      ? "bg-amber-500"
      : "bg-cyan-500";

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-cyan-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
          />
        </svg>
        Virtual Edge Hardware HUD
      </h2>

      <div className="space-y-3 text-xs font-mono">
        {/* CPU Utilization */}
        <div>
          <div className="flex justify-between text-slate-400 mb-1.5">
            <span>CPU Utilization:</span>
            <span className="text-cyan-400 font-semibold">{cpuPct}%</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-150 ${cpuColorClass}`}
              style={{ width: `${Math.min(100, Math.max(0, cpuPct))}%` }}
            />
          </div>
        </div>

        {/* Temperature */}
        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
          <span className="text-slate-400">Core Temp:</span>
          <span
            className={`font-semibold ${
              temp > 75
                ? "text-rose-400"
                : temp > 60
                ? "text-amber-400"
                : "text-slate-300"
            }`}
          >
            {temp.toFixed(1)} °C
          </span>
        </div>

        {/* Thermal Throttling */}
        <div className="flex justify-between py-1.5 border-b border-slate-800/80 items-center">
          <span className="text-slate-400">Thermal Throttling:</span>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              isThrottled
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/40 animate-pulse"
                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
            }`}
          >
            {isThrottled ? "THROTTLED" : "NORMAL"}
          </span>
        </div>

        {/* Deadline Misses */}
        <div className="flex justify-between py-1.5 border-b border-slate-800/80">
          <span className="text-slate-400">Deadline Misses:</span>
          <span
            className={`font-semibold ${
              misses > 0 ? "text-amber-400" : "text-slate-300"
            }`}
          >
            {misses}
          </span>
        </div>

        {/* Sensor Queues */}
        <div className="flex justify-between py-1">
          <span className="text-slate-400">In-Flight Queue:</span>
          <span className="text-slate-300">{totalPackets} packets</span>
        </div>
      </div>
    </div>
  );
};

