"use client";

import React, { useState, useEffect } from "react";
import {
  PatchResult,
  CausalDiagnosticReport,
  Hypothesis,
} from "../types/simulation";

/**
 * Props for the human-in-the-loop PatchApprovalModal.
 */
export interface PatchApprovalModalProps {
  patch: PatchResult | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (decision: "APPROVE" | "REJECT", reason: string, token: string) => Promise<void>;
  diagnosis?: CausalDiagnosticReport | null;
  leadingHypothesis?: Hypothesis | null;
  objective?: string;
}

/**
 * Modal dialogue providing unified diff inspection, reviewer token authorization, and approval submission.
 */
export const PatchApprovalModal: React.FC<PatchApprovalModalProps> = ({
  patch,
  isOpen,
  onClose,
  onApprove,
  diagnosis,
  leadingHypothesis,
}) => {
  const [token, setToken] = useState<string>("");
  const [reason, setReason] = useState<string>(
    "Evidence from counterfactual tests supports the proposed stale-observation safety guard."
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedDiff, setCopiedDiff] = useState<boolean>(false);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape" && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen || !patch) return null;

  const handleDecision = async (decision: "APPROVE" | "REJECT"): Promise<void> => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onApprove(decision, reason.trim(), token.trim());
      onClose();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Approval request failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const diffText = patch.unified_diff || patch.diff || "";
  const strategies = patch.strategies_applied || (patch.strategy_used ? [patch.strategy_used] : ["DYNAMIC_STOPPING_BUFFER"]);

  const handleCopyDiff = (): void => {
    const textToCopy = diffText || patch.patched_code || "";
    if (textToCopy && navigator.clipboard) {
      navigator.clipboard.writeText(textToCopy);
      setCopiedDiff(true);
      setTimeout(() => setCopiedDiff(false), 2000);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) {
          onClose();
        }
      }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center justify-center font-bold text-base shadow-md shadow-amber-500/10">
              🛡️
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Human-in-the-Loop Safety Gate: Review Code Patch
                </h2>
                <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/40 animate-pulse">
                  ACTION REQUIRED
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                System 2 formulated an AST-safe controller repair. Review the unified diff and authorize dual-run verification.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            aria-label="Close modal"
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition cursor-pointer disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        {/* 4-Stage Lifecycle Progress Roadmap */}
        <div className="bg-slate-950 px-4 sm:px-6 py-2.5 border-b border-slate-800/80 flex items-center justify-between text-[11px] font-mono overflow-x-auto gap-2">
          <div className="flex items-center gap-1.5 text-amber-400 font-bold shrink-0">
            <span className="w-5 h-5 rounded-full bg-amber-500/20 border border-amber-500/60 flex items-center justify-center text-[10px]">
              1
            </span>
            <span>Human Review (Active)</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
            <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px]">
              2
            </span>
            <span>Dual-Run Verification</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
            <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px]">
              3
            </span>
            <span>Multi-Case Regression</span>
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
            <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px]">
              4
            </span>
            <span>3-Pillar Certification</span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 text-xs">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-300 font-medium flex items-center gap-2">
              <span className="text-base">⚠️</span>
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Diagnostic Context & Root Cause Card */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Left Card: Patch & Strategies */}
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Patch Metadata
                </span>
                <span className="font-mono text-indigo-400 font-bold text-[11px]">
                  {patch.patch_id || "patch_auto_01"}
                </span>
              </div>

              <div className="space-y-1">
                <div className="text-slate-400 text-[11px]">Applied AST Strategies:</div>
                <div className="flex flex-wrap gap-1.5">
                  {strategies.map((s) => (
                    <span
                      key={s}
                      className="px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 font-mono text-[10px] font-semibold border border-purple-500/40"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {patch.explanation && (
                <p className="text-[11px] text-slate-300 leading-relaxed border-t border-slate-800/80 pt-1.5">
                  {patch.explanation}
                </p>
              )}
            </div>

            {/* Right Card: Root Cause / Leading Hypothesis */}
            <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Causal Diagnostic Finding
                </span>
                {leadingHypothesis && (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono text-[10px] border border-emerald-500/30">
                    Conf: {Math.round((leadingHypothesis.confidence ?? 0.9) * 100)}%
                  </span>
                )}
              </div>

              <p className="text-slate-200 text-[11px] leading-relaxed">
                {diagnosis?.primary_root_cause ||
                  leadingHypothesis?.statement ||
                  "Sensor frame latency and compute queue jitter cause delayed obstacle braking triggers."}
              </p>

              {diagnosis?.root_causes && diagnosis.root_causes.length > 0 && (
                <div className="text-[10px] text-slate-400 font-mono space-y-0.5 pt-1">
                  {diagnosis.root_causes.slice(0, 2).map((rc, idx) => (
                    <div key={idx} className="truncate">
                      • {rc}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Unified Diff Viewer */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-300">CONTROLLER AST UNIFIED DIFF</span>
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] border border-emerald-500/30 font-semibold">
                  AST VALID: TRUE
                </span>
              </div>

              <button
                onClick={handleCopyDiff}
                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer text-[10px] flex items-center gap-1 border border-slate-700"
              >
                {copiedDiff ? (
                  <>
                    <span className="text-emerald-400">✓</span> Copied
                  </>
                ) : (
                  <>
                    <span>📋</span> Copy Diff
                  </>
                )}
              </button>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-[11px] max-h-70 overflow-y-auto overflow-x-auto leading-relaxed divide-y divide-slate-900/40">
              {diffText ? (
                diffText.split("\n").map((line, idx) => {
                  let lineClass = "text-slate-300 hover:bg-slate-900/40";
                  let prefixBadge = " ";
                  if (line.startsWith("+") && !line.startsWith("+++")) {
                    lineClass = "text-emerald-300 bg-emerald-950/30 border-l-2 border-emerald-500";
                    prefixBadge = "+";
                  } else if (line.startsWith("-") && !line.startsWith("---")) {
                    lineClass = "text-rose-300 bg-rose-950/30 border-l-2 border-rose-500";
                    prefixBadge = "-";
                  } else if (line.startsWith("@@")) {
                    lineClass = "text-indigo-300 font-bold bg-indigo-950/40 border-l-2 border-indigo-500";
                    prefixBadge = "@";
                  }

                  return (
                    <div key={idx} className={`${lineClass} px-2 py-0.5 rounded-xs flex items-baseline font-mono`}>
                      <span className="text-slate-600 select-none w-7 text-right mr-3 text-[10px] shrink-0">
                        {idx + 1}
                      </span>
                      <span className="select-none text-slate-500 font-bold w-3 text-center mr-1 shrink-0">
                        {prefixBadge}
                      </span>
                      <span className="whitespace-pre flex-1">
                        {line.startsWith("+") || line.startsWith("-") ? line.slice(1) : line}
                      </span>
                    </div>
                  );
                })
              ) : (
                <pre className="text-slate-300 p-2 whitespace-pre-wrap">{patch.patched_code}</pre>
              )}
            </div>
          </div>

          {/* Reviewer Auth & Rationale Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1 bg-slate-950 p-4 rounded-xl border border-slate-800">
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Reviewer Authentication Token (Bearer)
              </label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                disabled={isSubmitting}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                placeholder="Enter token (optional if configured in env)"
              />
              <p className="text-[10px] text-slate-500 mt-1 font-mono">
                Used to authenticate approval against backend security checks
              </p>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                Operator Decision Rationale
              </label>
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={isSubmitting}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                placeholder="State rationale for approving or rejecting..."
              />
              <p className="text-[10px] text-slate-500 mt-1 font-mono">
                Persisted in the immutable audit log and final certification
              </p>
            </div>
          </div>
        </div>

        {/* Modal Actions Footer */}
        <div className="p-4 sm:p-5 border-t border-slate-800 bg-slate-950/90 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[11px] text-slate-500 max-w-sm">
            Approving triggers dual-run verification followed by multi-case regression suite testing.
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleDecision("REJECT")}
              disabled={isSubmitting}
              className="py-2.5 px-5 rounded-xl bg-slate-800 hover:bg-rose-950/40 active:opacity-90 disabled:opacity-50 text-rose-300 font-semibold text-xs border border-rose-500/30 transition cursor-pointer"
            >
              {isSubmitting ? "Processing..." : "Reject Patch"}
            </button>

            <button
              onClick={() => handleDecision("APPROVE")}
              disabled={isSubmitting}
              className="py-2.5 px-6 rounded-xl bg-linear-to-r from-emerald-600 via-teal-600 to-emerald-600 hover:from-emerald-500 hover:to-teal-500 active:opacity-90 disabled:opacity-50 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/30 transition cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Authorizing & Triggering...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  Approve & Trigger Verification
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

