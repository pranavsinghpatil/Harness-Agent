"use client";

import React from "react";
import { ScenarioDefinition } from "../types/simulation";

interface ScenarioControlsProps {
  scenarios: ScenarioDefinition[];
  selectedScenario: ScenarioDefinition | null;
  onSelectScenario: (scId: string) => void;
  seed: number;
  onSeedChange: (seed: number) => void;
  maxSimTime: number;
  onMaxSimTimeChange: (time: number) => void;
  onRunScenario: () => void;
  onStartStreaming: () => void;
  onStopStreaming: () => void;
  onReplayRun: () => void;
  isSimulating: boolean;
  isStreaming: boolean;
  isVerifying: boolean;
  canReplay: boolean;
}

export const ScenarioControls: React.FC<ScenarioControlsProps> = ({
  scenarios,
  selectedScenario,
  onSelectScenario,
  seed,
  onSeedChange,
  maxSimTime,
  onMaxSimTimeChange,
  onRunScenario,
  onStartStreaming,
  onStopStreaming,
  onReplayRun,
  isSimulating,
  isStreaming,
  isVerifying,
  canReplay,
}) => {
  const faults = selectedScenario?.fault_schedule ?? [];

  return (
    <div className="space-y-5">
      {/* Scenario Selector Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <svg
            className="w-4 h-4 text-indigo-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          Scenario & Simulation Mode
        </h2>

        <label
          htmlFor="scenario-select"
          className="block text-xs text-slate-400 mb-1 font-medium"
        >
          Select Preset Scenario
        </label>
        <select
          id="scenario-select"
          value={selectedScenario?.id ?? ""}
          onChange={(e) => onSelectScenario(e.target.value)}
          disabled={isStreaming || isSimulating}
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 mb-3 disabled:opacity-50"
        >
          {scenarios.map((sc) => (
            <option key={sc.id} value={sc.id}>
              {sc.name ?? sc.id}
            </option>
          ))}
        </select>

        <div className="text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 mb-4 leading-relaxed min-h-[48px]">
          {selectedScenario?.description ?? "No scenario description available."}
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4">
          <div>
            <label
              htmlFor="seed-input"
              className="text-[11px] text-slate-400 block mb-1"
            >
              RNG Seed
            </label>
            <input
              id="seed-input"
              type="number"
              value={seed}
              onChange={(e) => onSeedChange(parseInt(e.target.value, 10) || 0)}
              disabled={isStreaming || isSimulating}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            />
          </div>
          <div>
            <label
              htmlFor="sim-time-input"
              className="text-[11px] text-slate-400 block mb-1"
            >
              Max Time (s)
            </label>
            <input
              id="sim-time-input"
              type="number"
              value={maxSimTime}
              onChange={(e) => onMaxSimTimeChange(parseFloat(e.target.value) || 1)}
              disabled={isStreaming || isSimulating}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            />
          </div>
        </div>

        <div className="space-y-2.5">
          {/* Primary Action: Real-time WebSocket Stream */}
          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="w-full py-2.5 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-rose-600/30 transition cursor-pointer animate-pulse"
            >
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              <span>Stop WebSocket Stream</span>
            </button>
          ) : (
            <button
              onClick={onStartStreaming}
              disabled={isSimulating || !selectedScenario}
              className="w-full py-2.5 px-4 rounded-lg bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:opacity-90 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition cursor-pointer"
            >
              <svg className="w-4 h-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Stream Live (WebSocket)</span>
            </button>
          )}

          {/* Secondary Action: Fast Batch Run */}
          <button
            onClick={onRunScenario}
            disabled={isStreaming || isSimulating || !selectedScenario}
            className="w-full py-2 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-900 disabled:opacity-40 text-slate-300 font-medium text-xs flex items-center justify-center gap-2 border border-slate-700 transition cursor-pointer"
          >
            {isSimulating ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  />
                </svg>
                Executing Batch Run...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>Batch Simulation (REST API)</span>
              </>
            )}
          </button>

          {/* Deterministic Replay Check */}
          <button
            onClick={onReplayRun}
            disabled={!canReplay || isVerifying || isSimulating || isStreaming}
            className="w-full py-2 px-4 rounded-lg bg-slate-950 hover:bg-slate-900 active:bg-slate-950 disabled:opacity-30 text-slate-400 hover:text-slate-200 font-medium text-[11px] flex items-center justify-center gap-2 border border-slate-800 transition cursor-pointer"
          >
            {isVerifying ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-indigo-400"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  />
                </svg>
                Verifying Replay Bit-by-Bit...
              </>
            ) : (
              <>
                <svg
                  className="w-3.5 h-3.5 text-emerald-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                <span>Deterministic Replay Check</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Fault Injection Schedule Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <svg
            className="w-4 h-4 text-amber-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          Fault Injection Schedule
        </h2>
        <div className="space-y-2 text-xs max-h-52 overflow-y-auto pr-1">
          {faults.length > 0 ? (
            faults.map((f, idx) => (
              <div
                key={f.id ?? idx}
                className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 hover:border-slate-700 transition"
              >
                <div className="flex justify-between items-center font-mono text-[11px] mb-1">
                  <span className="text-amber-400 font-semibold">{f.id}</span>
                  <span className="text-slate-400">
                    {f.start_time.toFixed(1)}s - {(f.start_time + f.duration).toFixed(1)}s
                  </span>
                </div>
                <div className="text-[10px] text-slate-400">
                  Target: <code className="text-indigo-300">{f.target}</code> (
                  <span className="text-slate-300 font-mono">{f.type}</span>)
                </div>
              </div>
            ))
          ) : (
            <div className="text-slate-500 italic text-xs py-2 text-center bg-slate-950/40 rounded border border-dashed border-slate-800">
              No active perturbations scheduled (Safe Baseline)
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
