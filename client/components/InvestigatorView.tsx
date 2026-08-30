"use client";

import React, { useState } from "react";
import {
  HardwarePreset,
  ScenarioDefinition,
  InvestigationResult,
} from "../types/simulation";
import { runInvestigation } from "../lib/api";

interface InvestigatorViewProps {
  apiBase: string;
  presets: HardwarePreset[];
  scenarios: ScenarioDefinition[];
}

export const InvestigatorView: React.FC<InvestigatorViewProps> = ({
  apiBase,
  presets,
  scenarios,
}) => {
  const [objective, setObjective] = useState<string>(
    "Investigate vehicle safety boundary under camera latency and compute degradation"
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
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRunInvestigation = async () => {
    if (!objective.trim()) return;
    setIsRunning(true);
    setErrorMsg(null);
    try {
      const data = await runInvestigation(apiBase, {
        objective: objective.trim(),
        hardware_preset_id: selectedPresetId,
        scenario_id: selectedScenarioId,
        seed: seed,
        budget: budget,
        max_boundary_steps: maxBoundarySteps,
      });
      setResult(data);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Investigation failed");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-linear-to-r from-purple-950/80 via-slate-900 to-indigo-950/80 border border-purple-500/30 rounded-2xl p-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono text-[11px] border border-purple-500/40 font-semibold">
                SYSTEM 2 AUTONOMOUS INVESTIGATOR
              </span>
              <span className="text-xs text-slate-400">
                Scientific Hypothesis Search & Bounded Stress Testing
              </span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Adaptive Perturbation & Causal Exploration Engine
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl mt-1 leading-relaxed">
              Formulates competing causal hypotheses, schedules bounded System 1 perturbation experiments
              (Screening $\to$ Boundary Bracketing $\to$ Interaction), and tracks auditable decision traces.
            </p>
          </div>

          <button
            onClick={handleRunInvestigation}
            disabled={isRunning}
            className="py-3 px-6 rounded-xl bg-linear-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:opacity-90 disabled:opacity-50 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30 transition cursor-pointer"
          >
            {isRunning ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
                Investigating (System 2)...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                <span>Launch Autonomous Investigation</span>
              </>
            )}
          </button>
        </div>

        {/* Objective & Constraint Form */}
        <div className="mt-5 space-y-3 pt-4 border-t border-slate-800/80">
          <div>
            <label className="block text-[11px] font-semibold text-slate-300 mb-1">
              Investigation Objective
            </label>
            <input
              type="text"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="e.g. Determine failure boundaries under camera latency and CPU throttling"
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1 font-medium">
                Hardware Preset
              </label>
              <select
                value={selectedPresetId}
                onChange={(e) => setSelectedPresetId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              >
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name || p.id}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1 font-medium">
                Baseline Scenario
              </label>
              <select
                value={selectedScenarioId}
                onChange={(e) => setSelectedScenarioId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              >
                {scenarios.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.name || sc.id}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1 font-medium">
                Experiment Budget ({budget})
              </label>
              <input
                type="range"
                min={2}
                max={20}
                value={budget}
                onChange={(e) => setBudget(parseInt(e.target.value, 10))}
                className="w-full accent-purple-500"
              />
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1 font-medium">
                RNG Seed
              </label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-500 text-rose-200 text-xs">
          <strong>Investigation Error:</strong> {errorMsg}
        </div>
      )}

      {/* Results Dashboard */}
      {result && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-[11px] text-slate-400 font-medium">Status</div>
              <div className="text-lg font-bold text-purple-400 uppercase mt-1">
                {result.status}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                ID: {result.investigation_id}
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-[11px] text-slate-400 font-medium">Experiments Run</div>
              <div className="text-lg font-bold text-white mt-1">
                {result.planner?.summary?.total_experiments ?? result.runs?.length ?? 0} / {result.planner?.budget ?? budget}
              </div>
              <div className="text-[10px] text-emerald-400 mt-0.5">
                {result.planner?.summary?.passed_experiments ?? 0} Passed | {result.planner?.summary?.failed_experiments ?? 0} Failed
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-[11px] text-slate-400 font-medium">Tested Dimensions</div>
              <div className="text-lg font-bold text-indigo-400 mt-1">
                {result.planner?.summary?.tested_dimensions?.length ?? 0}
              </div>
              <div className="text-[10px] text-slate-400 truncate mt-0.5">
                {result.planner?.summary?.tested_dimensions?.join(", ") || "None"}
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-[11px] text-slate-400 font-medium">Hypotheses Tracked</div>
              <div className="text-lg font-bold text-cyan-400 mt-1">
                {result.hypotheses?.hypotheses?.length ?? 0}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                {result.falsification_plans?.length ?? 0} Counterfactual Plans
              </div>
            </div>
          </div>

          {/* Competing Hypotheses Board */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              Competing Causal Hypotheses & Belief States
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.hypotheses?.hypotheses?.map((h) => {
                const isSupported = h.status === "SUPPORTED";
                const isRefuted = h.status === "REFUTED";
                return (
                  <div
                    key={h.hypothesis_id}
                    className={`p-4 rounded-xl border transition ${
                      isSupported
                        ? "bg-emerald-950/30 border-emerald-500/40"
                        : isRefuted
                        ? "bg-rose-950/20 border-rose-500/30 opacity-75"
                        : "bg-slate-950 border-slate-800"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono text-xs font-bold text-indigo-300">
                        {h.hypothesis_id}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                          isSupported
                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            : isRefuted
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 line-through"
                            : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                        }`}
                      >
                        {h.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 mb-3 font-medium">
                      {h.statement}
                    </p>

                    {/* Confidence Meter */}
                    <div className="space-y-1 mb-3">
                      <div className="flex justify-between text-[10px] text-slate-400">
                        <span>Confidence Score</span>
                        <span className="font-mono font-bold text-indigo-300">
                          {(h.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            isSupported
                              ? "bg-emerald-500"
                              : isRefuted
                              ? "bg-rose-500"
                              : "bg-indigo-500"
                          }`}
                          style={{ width: `${Math.round(h.confidence * 100)}%` }}
                        />
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-400 space-y-1 font-mono">
                      <div>
                        Supporting Runs:{" "}
                        <span className="text-emerald-400">
                          {h.supporting_experiment_ids?.join(", ") || "None"}
                        </span>
                      </div>
                      <div>
                        Contradicting Runs:{" "}
                        <span className="text-rose-400">
                          {h.contradicting_experiment_ids?.join(", ") || "None"}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Decision Trace Timeline */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
              Auditable Decision Trace Timeline
            </h3>

            <div className="space-y-3">
              {result.decision_trace?.map((trace, idx) => (
                <div
                  key={trace.experiment_id || idx}
                  className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition space-y-2"
                >
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {trace.experiment_id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30 font-semibold">
                        {trace.action}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        Phase: {trace.phase}
                      </span>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                        trace.outcome_classification === "PASS"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      }`}
                    >
                      {trace.outcome_classification}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {trace.rationale}
                  </p>

                  <div className="pt-2 border-t border-slate-800/80 flex flex-wrap justify-between text-[11px] text-slate-400 font-mono gap-2">
                    <span>
                      Observation: <strong className="text-slate-200">{trace.observation}</strong>
                    </span>
                    <span className="text-purple-300">
                      {trace.next_action}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

