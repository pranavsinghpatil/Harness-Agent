"use client";

import React from "react";
import { CausalDiagnosticReport } from "../types/simulation";

/**
 * Props for the CausalDAGView component.
 */
export interface CausalDAGViewProps {
  diagnosis: CausalDiagnosticReport | null;
}

/**
 * Visualizes the causal Directed Acyclic Graph (DAG) explaining failure propagation from fault to invariant breach.
 */
export const CausalDAGView: React.FC<CausalDAGViewProps> = ({ diagnosis }) => {
  if (!diagnosis) {
    return (
      <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-2xl text-center">
        <div className="text-slate-500 text-xs py-8">
          No failure diagnostics recorded. Causal DAG is computed automatically upon detecting a safety violation.
        </div>
      </div>
    );
  }

  const nodes = diagnosis.causal_nodes || [];
  const links = diagnosis.causal_links || [];

  const getNodeColor = (category: string): string => {
    switch (category) {
      case "HARDWARE_FAULT":
        return "border-amber-500/50 bg-amber-500/10 text-amber-300";
      case "COMPUTE_BOTTLENECK":
        return "border-purple-500/50 bg-purple-500/10 text-purple-300";
      case "TRANSPORT_STALENESS":
        return "border-blue-500/50 bg-blue-500/10 text-blue-300";
      case "CONTROLLER_DECISION":
        return "border-indigo-500/50 bg-indigo-500/10 text-indigo-300";
      case "SAFETY_BREACH":
        return "border-rose-500/50 bg-rose-500/10 text-rose-300";
      default:
        return "border-slate-700 bg-slate-800 text-slate-300";
    }
  };

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
          <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            Causal Failure Diagnostic DAG
          </h3>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {nodes.length} Causal Nodes
        </span>
      </div>

      {/* Root Cause Banner */}
      <div className="bg-linear-to-r from-rose-950/60 via-slate-950 to-purple-950/60 border border-rose-500/30 rounded-xl p-3 sm:p-4 space-y-1.5">
        <div className="text-[11px] font-bold text-rose-300 uppercase tracking-wider">
          Primary Diagnosed Root Cause
        </div>
        <p className="text-xs text-slate-200 leading-relaxed font-medium">
          {diagnosis.primary_root_cause || "Hardware transport latency induced stale observation delivery."}
        </p>
      </div>

      {/* Causal Chain Nodes */}
      {nodes.length > 0 && (
        <div className="space-y-3">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Causal Propagation Path
          </div>
          <div className="space-y-2">
            {nodes.map((node, idx) => (
              <div
                key={node.node_id || idx}
                className={`border rounded-xl p-3 text-xs space-y-1.5 transition-all ${getNodeColor(
                  node.category
                )}`}
              >
                <div className="flex items-center justify-between font-mono text-[10px]">
                  <span className="font-bold">{node.category}</span>
                  <span className="text-slate-400">T+{node.timestamp?.toFixed(2)}s</span>
                </div>
                <p className="text-slate-200 font-sans">{node.summary}</p>
                {node.metrics && Object.keys(node.metrics).length > 0 && (
                  <div className="text-[10px] font-mono text-slate-400 pt-1 flex flex-wrap gap-2">
                    {Object.entries(node.metrics).map(([k, v]) => (
                      <span key={k} className="px-1.5 py-0.5 rounded bg-slate-950/80">
                        {k}: {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {links.length > 0 && (
            <div className="pt-2 text-[10px] text-slate-400 font-mono space-y-1">
              <span className="text-slate-500 font-semibold uppercase">Causal Links:</span>
              {links.map((link, lIdx) => (
                <div key={lIdx} className="flex items-center gap-1.5 text-slate-300">
                  <span className="text-indigo-400">{link.source}</span>
                  <span className="text-slate-500">──({link.relation})──&gt;</span>
                  <span className="text-indigo-400">{link.target}</span>
                  {link.confidence && (
                    <span className="text-emerald-400 font-bold">({Math.round(link.confidence * 100)}%)</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}


      {/* Recommendations */}
      {(diagnosis.patch_recommendations?.length || diagnosis.recommendations?.length) ? (
        <div className="pt-3 border-t border-slate-800 space-y-2">
          <div className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">
            Auto-Patcher Recommendations
          </div>
          <ul className="space-y-1.5 text-xs text-slate-300 pl-4 list-disc">
            {(diagnosis.patch_recommendations || diagnosis.recommendations || []).map(
              (rec, idx) => (
                <li key={idx}>{rec}</li>
              )
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
};
