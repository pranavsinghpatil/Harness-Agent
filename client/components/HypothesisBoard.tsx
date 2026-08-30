"use client";

import React from "react";
import { Hypothesis, FalsificationPlan } from "../types/simulation";

/**
 * Props for the HypothesisBoard component.
 */
export interface HypothesisBoardProps {
  hypotheses: Hypothesis[];
  falsificationPlans?: FalsificationPlan[];
  activeHypothesis?: Hypothesis | null;
  leadingHypothesis?: Hypothesis | null;
}

/**
 * Renders the Bayesian hypothesis ranking board with confidence meters,
 * support/contradiction experiment tags, and falsification status badges.
 */
export const HypothesisBoard: React.FC<HypothesisBoardProps> = ({
  hypotheses,
  falsificationPlans = [],
  activeHypothesis,
  leadingHypothesis,
}) => {
  const getStatusBadge = (status: string): string => {
    switch (status) {
      case "SUPPORTED":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "REFUTED":
        return "bg-rose-500/20 text-rose-300 border-rose-500/40 line-through opacity-70";
      case "ACTIVE":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const getConfidenceColor = (conf: number): string => {
    if (conf >= 0.75) return "from-emerald-500 to-teal-500";
    if (conf >= 0.4) return "from-amber-500 to-yellow-500";
    return "from-rose-500 to-orange-500";
  };

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
          <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            Competing Causal Hypotheses
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {hypotheses.length} formulated
        </span>
      </div>

      {/* Leading Hypothesis Highlight Banner */}
      {leadingHypothesis && (
        <div className="bg-linear-to-r from-purple-950/70 via-slate-950 to-indigo-950/70 border border-purple-500/30 rounded-xl p-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold text-purple-300 uppercase tracking-wider">
              ⭐ Leading Hypothesis
            </span>
            <span className="font-mono text-purple-200 font-bold">
              {Math.round((leadingHypothesis.confidence || 0) * 100)}% Confidence
            </span>
          </div>
          <p className="text-xs font-medium text-slate-100">
            {leadingHypothesis.statement}
          </p>
          <div className="flex items-center gap-2 text-[10px] text-slate-400 pt-1">
            <span>Variables:</span>
            {leadingHypothesis.variables?.map((v) => (
              <span key={v} className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Hypotheses Grid */}
      <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
        {hypotheses.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            Awaiting System 2 causal hypothesis formulation...
          </div>
        ) : (
          hypotheses.map((hypo) => {
            const confPercent = Math.round((hypo.confidence || 0) * 100);
            const isLeading = leadingHypothesis?.hypothesis_id === hypo.hypothesis_id;
            const isActive = activeHypothesis?.hypothesis_id === hypo.hypothesis_id;

            return (
              <div
                key={hypo.hypothesis_id}
                className={`bg-slate-950 border rounded-xl p-3 transition-all ${
                  isLeading
                    ? "border-purple-500/50 shadow-md shadow-purple-500/10"
                    : isActive
                    ? "border-indigo-500/50 ring-1 ring-indigo-500/30"
                    : "border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200">
                      {hypo.hypothesis_id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(
                        hypo.status
                      )}`}
                    >
                      {hypo.status}
                    </span>
                    {isActive && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        FOCUS
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-xs font-bold text-slate-300">
                    {confPercent}%
                  </span>
                </div>


                <p className="text-xs text-slate-300 mb-2 leading-relaxed">
                  {hypo.statement}
                </p>

                {/* Animated Confidence Bar */}
                <div className="w-full h-1.5 bg-slate-800/90 rounded-full overflow-hidden mb-2 ring-1 ring-slate-800">
                  <div
                    className={`h-full bg-linear-to-r ${getConfidenceColor(
                      hypo.confidence || 0
                    )} transition-[width] duration-700 ease-out rounded-full shadow-xs`}
                    style={{ width: `${confPercent}%` }}
                  />
                </div>

                {/* Supporting vs Contradicting Evidence Tags */}
                <div className="flex flex-wrap items-center gap-2 text-[10px]">
                  {hypo.supporting_experiment_ids?.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-emerald-400 font-medium">Supports:</span>
                      {hypo.supporting_experiment_ids.map((id) => (
                        <span
                          key={id}
                          className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-300 font-mono border border-emerald-500/20"
                        >
                          {id}
                        </span>
                      ))}
                    </div>
                  )}

                  {hypo.contradicting_experiment_ids?.length > 0 && (
                    <div className="flex items-center gap-1">
                      <span className="text-rose-400 font-medium">Refutes:</span>
                      {hypo.contradicting_experiment_ids.map((id) => (
                        <span
                          key={id}
                          className="px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-300 font-mono border border-rose-500/20"
                        >
                          {id}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Falsification Plans Section */}
      {falsificationPlans.length > 0 && (
        <div className="pt-3 border-t border-slate-800 space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Counterfactual Falsification Strategy
          </div>
          {falsificationPlans.map((plan, idx) => (
            <div
              key={idx}
              className="bg-slate-950/80 border border-slate-800 rounded-lg p-2 text-[11px] space-y-1"
            >
              <div className="flex items-center justify-between font-mono text-purple-300">
                <span>Target: {plan.hypothesis_id}</span>
              </div>
              <p className="text-slate-300">{plan.rationale}</p>
              {plan.expected_outcome && (
                <p className="text-slate-500 text-[10px]">
                  <span className="font-semibold text-slate-400">Expected:</span> {plan.expected_outcome}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
