"use client";

import React from "react";
import { RunManifest, ReplayResponse } from "../types/simulation";

interface ManifestCardProps {
  manifest: RunManifest | null;
  replayResult: ReplayResponse | null;
}

export const ManifestCard: React.FC<ManifestCardProps> = ({
  manifest,
  replayResult,
}) => {
  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 shadow-xl">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
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
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          />
        </svg>
        Deterministic Run Manifest
      </h2>

      <div className="space-y-3 text-[11px] font-mono">
        <div>
          <span className="text-slate-400 block mb-1">Run Identifier:</span>
          <span className="text-slate-300 break-all bg-slate-950 p-2 rounded-lg border border-slate-800/80 block font-mono">
            {manifest?.run_id ?? "--"}
          </span>
        </div>

        <div>
          <span className="text-slate-400 block mb-1">
            Trace Checksum (SHA-256):
          </span>
          <span className="text-indigo-400 break-all bg-slate-950 p-2 rounded-lg border border-slate-800/80 block font-mono text-[10px] select-all">
            {manifest?.trace_hash ?? "--"}
          </span>
        </div>

        <div className="pt-2 border-t border-slate-800 flex justify-between items-center text-xs">
          <span className="text-slate-400 font-sans">Total Violations:</span>
          <span
            className={`font-bold px-2 py-0.5 rounded ${
              (manifest?.violations_count ?? 0) > 0
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
            }`}
          >
            {manifest?.violations_count ?? 0}
          </span>
        </div>

        {/* Determinism Check Alert if Replay Executed */}
        {replayResult && (
          <div
            className={`p-3 rounded-lg border text-xs mt-2 ${
              replayResult.is_bit_exact_match
                ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-300"
                : "bg-amber-950/40 border-amber-500/50 text-amber-300"
            }`}
          >
            <div className="font-bold flex items-center gap-1.5 mb-1 font-sans">
              {replayResult.is_bit_exact_match ? (
                <>
                  <span>✅</span> 100% Bit-Exact Determinism Match
                </>
              ) : (
                <>
                  <span>⚠️</span> Determinism Mismatch Detected
                </>
              )}
            </div>
            <div className="text-[10px] text-slate-300 font-mono break-all">
              {replayResult.is_bit_exact_match
                ? `Original & Replayed SHA-256 match bit-for-bit (${replayResult.original_trace_hash.substring(
                    0,
                    16
                  )}...)`
                : replayResult.difference_details ?? "Replay traces diverged."}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

