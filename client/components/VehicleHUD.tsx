"use client";

import React from "react";
import { TelemetryFrame } from "../types/simulation";

interface VehicleHUDProps {
  frame: TelemetryFrame | null;
}

export const VehicleHUD: React.FC<VehicleHUDProps> = ({ frame }) => {
  const vel = frame?.vehicle_state.velocity ?? 0;
  const clearance = frame?.min_clearance ?? 999;
  const headingRad = frame?.vehicle_state.heading ?? 0;
  const headingDeg = ((headingRad * 180) / Math.PI).toFixed(1);
  const throttlePct = Math.round((frame?.actuator_command.throttle ?? 0) * 100);
  const brakePct = Math.round((frame?.actuator_command.brake ?? 0) * 100);

  const isLowClearance = clearance < 1.0;

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-emerald-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
        Vehicle Telemetry & Actuation
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs font-mono">
        {/* Velocity */}
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-sans">
            Velocity
          </div>
          <div className="text-base font-bold text-emerald-400 mt-1">
            {vel.toFixed(2)}{" "}
            <span className="text-[10px] text-slate-400 font-normal">m/s</span>
          </div>
        </div>

        {/* Clearance */}
        <div
          className={`bg-slate-950 p-3 rounded-lg border flex flex-col justify-between transition ${
            isLowClearance
              ? "border-rose-500/80 bg-rose-950/20"
              : "border-slate-800"
          }`}
        >
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-sans">
            Min Clearance
          </div>
          <div
            className={`text-base font-bold mt-1 ${
              isLowClearance ? "text-rose-400" : "text-indigo-400"
            }`}
          >
            {clearance < 100 ? `${clearance.toFixed(2)} m` : "-- m"}
          </div>
        </div>

        {/* Throttle / Brake */}
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-sans">
            Throttle / Brake
          </div>
          <div className="text-sm font-bold text-slate-200 mt-1 flex items-center justify-center gap-1.5">
            <span className="text-emerald-400">{throttlePct}%</span>
            <span className="text-slate-600">/</span>
            <span className="text-rose-400">{brakePct}%</span>
          </div>
        </div>

        {/* Heading */}
        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-sans">
            Heading
          </div>
          <div className="text-base font-bold text-slate-200 mt-1">
            {headingDeg}°
          </div>
        </div>
      </div>
    </div>
  );
};

