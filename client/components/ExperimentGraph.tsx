"use client";

import React from "react";
import {
  InvestigationRun,
  DecisionTrace,
  ExperimentPhase,
} from "../types/simulation";

/**
 * Props for the ExperimentGraph component.
 */
export interface ExperimentGraphProps {
  runs: InvestigationRun[];
  decisionTraces?: DecisionTrace[];
  selectedExperimentId?: string | null;
  onSelectExperiment?: (experimentId: string) => void;
}

/**
 * Renders the deterministic 4-phase experiment tree (Baseline -> Screen -> Boundary -> Interaction)
 * and Bayesian falsification history.
 */
export const ExperimentGraph: React.FC<ExperimentGraphProps> = ({
  runs,
  decisionTraces = [],
  selectedExperimentId,
  onSelectExperiment,
}) => {
  const getPhaseBadge = (phase: ExperimentPhase | string): string => {
    switch (phase) {
      case "BASELINE":
        return "bg-blue-500/20 text-blue-300 border-blue-500/40";
      case "SCREEN":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "BOUNDARY":
        return "bg-indigo-500/20 text-indigo-300 border-indigo-500/40";
      case "INTERACTION":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
          <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            System 2 Experiment Graph & Falsification Tree
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {runs.length} experiments executed
        </span>
      </div>

      {runs.length === 0 ? (
        <div className="py-8 text-center text-slate-500 text-xs">
          No experiments executed yet. System 2 will schedule baseline and perturbation experiments.
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-linear-to-b before:from-blue-500 before:via-purple-500 before:to-emerald-500">
          {runs.map((run, idx) => {
            const exp = run.experiment;
            const outcome = run.outcome;
            const trace =
              run.decision_trace ||
              decisionTraces.find((t) => t.experiment_id === exp.experiment_id);
            const isSelected = selectedExperimentId === exp.experiment_id;

            return (
              <div
                key={exp.experiment_id || idx}
                onClick={() => onSelectExperiment?.(exp.experiment_id)}
                className={`relative bg-slate-950 border rounded-xl p-3 sm:p-4 transition-all cursor-pointer ${
                  isSelected
                    ? "border-indigo-500 ring-2 ring-indigo-500/20 shadow-lg shadow-indigo-500/10"
                    : "border-slate-800/80 hover:border-slate-700"
                }`}
              >
                {/* Node Connector Bullet */}
                <div
                  className={`absolute -left-[27px] top-4 w-3.5 h-3.5 rounded-full border-2 border-slate-900 ${
                    outcome.passed ? "bg-emerald-400 ring-2 ring-emerald-500/30" : "bg-rose-500 ring-2 ring-rose-500/30"
                  }`}
                />

                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200">
                      {exp.experiment_id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getPhaseBadge(
                        exp.phase
                      )}`}
                    >
                      {exp.phase}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        outcome.passed
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                      }`}
                    >
                      {outcome.passed ? "✓ PASS" : "✗ SAFETY VIOLATION"}
                    </span>

                    <span className="text-[11px] font-mono text-slate-400">
                      Clr: {outcome.min_clearance?.toFixed(2)}m
                    </span>
                  </div>
                </div>

                {/* Perturbation parameter values */}
                <div className="bg-slate-900/60 rounded-lg p-2 mb-2 font-mono text-[11px] text-slate-300 grid grid-cols-1 sm:grid-cols-2 gap-1">
                  {Object.entries(exp.values || {}).length === 0 ? (
                    <span className="text-slate-500 italic col-span-2">
                      Nominal Baseline (Zero Perturbations)
                    </span>
                  ) : (
                    Object.entries(exp.values).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-slate-400">{k}:</span>
                        <span className="text-indigo-300 font-semibold">{v}</span>
                      </div>
                    ))
                  )}
                </div>

                {/* Rationale & Observation */}
                {exp.rationale && (
                  <p className="text-xs text-slate-300 mb-1">
                    <span className="text-slate-500 font-medium">Goal:</span> {exp.rationale}
                  </p>
                )}

                {trace && trace.observation && (
                  <p className="text-xs text-slate-400">
                    <span className="text-slate-500 font-medium">Observation:</span> {trace.observation}
                  </p>
                )}

                {/* Information Gain & Decision Link */}
                {trace && (
                  <div className="mt-2 pt-2 border-t border-slate-900 flex flex-wrap items-center justify-between text-[10px] text-slate-400 font-mono">
                    <div>
                      <span>Info Gain (ΔI): </span>
                      <span className="text-purple-300 font-bold">
                        +{((trace.information_gain_estimate || 0.5) * 100).toFixed(0)}%
                      </span>
                    </div>
                    {trace.next_action && (
                      <div className="text-indigo-400 truncate max-w-xs">
                        Next: {trace.next_action}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
