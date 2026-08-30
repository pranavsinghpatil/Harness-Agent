"use client";

import React from "react";
import { ScenarioDefinition, HardwarePreset } from "../types/simulation";

interface ScenarioControlsProps {
  presets: HardwarePreset[];
  selectedPresetId: string;
  onSelectPreset: (presetId: string) => void;
  scenarios: ScenarioDefinition[];
  selectedScenario: ScenarioDefinition | null;
  onSelectScenario: (scId: string) => void;
  seed: number;
  onSeedChange: (seed: number) => void;
  maxSimTime: number;
  onMaxSimTimeChange: (time: number) => void;
  onRunFullEvaluation: () => void;
  onRunScenario: () => void;
  onStartStreaming: () => void;
  onStopStreaming: () => void;
  onReplayRun: () => void;
  isEvaluating: boolean;
  isSimulating: boolean;
  isStreaming: boolean;
  isVerifying: boolean;
  canReplay: boolean;
}

export const ScenarioControls: React.FC<ScenarioControlsProps> = ({
  presets,
  selectedPresetId,
  onSelectPreset,
  scenarios,
  selectedScenario,
  onSelectScenario,
  seed,
  onSeedChange,
  maxSimTime,
  onMaxSimTimeChange,
  onRunFullEvaluation,
  onRunScenario,
  onStartStreaming,
  onStopStreaming,
  onReplayRun,
  isEvaluating,
  isSimulating,
  isStreaming,
  isVerifying,
  canReplay,
}) => {
  const faults = selectedScenario?.fault_schedule ?? [];
  const selectedPreset = presets.find((p) => p.id === selectedPresetId);

  return (
    <div className="space-y-5">
      {/* Target Hardware Board Preset Card */}
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
              d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
            />
          </svg>
          Target Edge Hardware Preset
        </h2>

        <label
          htmlFor="preset-select"
          className="block text-[11px] text-slate-400 mb-1 font-medium"
        >
          Select Virtual Edge Board
        </label>
        <select
          id="preset-select"
          value={selectedPresetId}
          onChange={(e) => onSelectPreset(e.target.value)}
          disabled={isStreaming || isSimulating || isEvaluating}
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 mb-2.5 disabled:opacity-50"
        >
          {presets.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name || p.id}
            </option>
          ))}
        </select>

        {selectedPreset && (
          <div className="text-[11px] text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 space-y-1 font-mono">
            <div className="flex justify-between">
              <span>Arch:</span>
              <span className="text-indigo-300 font-semibold">{selectedPreset.architecture || "ARM"}</span>
            </div>
            <div className="flex justify-between">
              <span>CPU / Throttle:</span>
              <span className="text-slate-300">
                {selectedPreset.cpu_cores || 4} cores @ {selectedPreset.thermal_throttle_temp_celsius ?? selectedPreset.thermal_limit_celsius ?? 85}°C
              </span>
            </div>
            {selectedPreset.npu_tops !== undefined && selectedPreset.npu_tops > 0 && (
              <div className="flex justify-between">
                <span>NPU Acceleration:</span>
                <span className="text-emerald-400">{selectedPreset.npu_tops} TOPS</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Scenario & Execution Controls Card */}
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
          Fault Scenario & Seed
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
          disabled={isStreaming || isSimulating || isEvaluating}
          className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 mb-3 disabled:opacity-50"
        >
          {scenarios.map((sc) => (
            <option key={sc.id} value={sc.id}>
              {sc.name ?? sc.id}
            </option>
          ))}
        </select>

        <div className="text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 mb-4 leading-relaxed min-h-[44px]">
          {selectedScenario?.description ?? "No scenario description available."}
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4">
          <div>
            <label
              htmlFor="seed-input"
              className="text-[11px] text-slate-400 block mb-1 font-medium"
            >
              RNG Seed
            </label>
            <input
              id="seed-input"
              type="number"
              value={seed}
              onChange={(e) => onSeedChange(parseInt(e.target.value, 10) || 0)}
              disabled={isStreaming || isSimulating || isEvaluating}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            />
          </div>
          <div>
            <label
              htmlFor="sim-time-input"
              className="text-[11px] text-slate-400 block mb-1 font-medium"
            >
              Max Time (s)
            </label>
            <input
              id="sim-time-input"
              type="number"
              value={maxSimTime}
              onChange={(e) => onMaxSimTimeChange(parseFloat(e.target.value) || 1)}
              disabled={isStreaming || isSimulating || isEvaluating}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            />
          </div>
        </div>

        <div className="space-y-2.5">
          {/* PRIMARY ONE-CLICK ACTION: Full Closed-Loop Evaluation */}
          <button
            onClick={onRunFullEvaluation}
            disabled={isEvaluating || isSimulating || isStreaming || !selectedScenario}
            className="w-full py-3 px-4 rounded-xl bg-linear-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:opacity-90 disabled:opacity-50 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition cursor-pointer"
          >
            {isEvaluating ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-1.5 h-4 w-4 text-white"
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
                Running Closed Loop (System 2)...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 text-cyan-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>⚡ Run Full Closed-Loop Evaluation</span>
              </>
            )}
          </button>

          {/* SECONDARY ACTION: WebSocket Live Stream */}
          {isStreaming ? (
            <button
              onClick={onStopStreaming}
              className="w-full py-2 px-3 rounded-lg bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-rose-600/30 transition cursor-pointer animate-pulse"
            >
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              <span>Stop WebSocket Stream</span>
            </button>
          ) : (
            <button
              onClick={onStartStreaming}
              disabled={isEvaluating || isSimulating || !selectedScenario}
              className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-900 disabled:opacity-40 text-slate-200 font-medium text-xs flex items-center justify-center gap-2 border border-slate-700 transition cursor-pointer"
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>Live Stream (WebSocket)</span>
            </button>
          )}

          {/* TERTIARY ACTIONS: Batch Run & Replay Check */}
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              onClick={onRunScenario}
              disabled={isStreaming || isSimulating || isEvaluating || !selectedScenario}
              className="py-1.5 px-2 rounded-lg bg-slate-950 hover:bg-slate-900 active:bg-slate-950 disabled:opacity-30 text-slate-400 hover:text-slate-200 font-medium text-[11px] flex items-center justify-center gap-1.5 border border-slate-800 transition cursor-pointer"
            >
              {isSimulating ? (
                <>
                  <svg className="animate-spin h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Simulating...
                </>
              ) : (
                <span>Batch Physics Only</span>
              )}
            </button>

            <button
              onClick={onReplayRun}
              disabled={!canReplay || isVerifying || isSimulating || isStreaming || isEvaluating}
              className="py-1.5 px-2 rounded-lg bg-slate-950 hover:bg-slate-900 active:bg-slate-950 disabled:opacity-30 text-slate-400 hover:text-slate-200 font-medium text-[11px] flex items-center justify-center gap-1.5 border border-slate-800 transition cursor-pointer"
            >
              {isVerifying ? (
                <>
                  <svg className="animate-spin h-3 w-3 text-indigo-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Replaying...
                </>
              ) : (
                <>
                  <svg className="w-3 h-3 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Replay Check</span>
                </>
              )}
            </button>
          </div>
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
        <div className="space-y-2 text-xs max-h-48 overflow-y-auto pr-1">
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
