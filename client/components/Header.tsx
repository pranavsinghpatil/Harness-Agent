"use client";

import React, { useState } from "react";
import { InvestigationPhase, InvestigationSessionStatus } from "../types/simulation";

/**
 * Props for the application-wide top navigation header.
 */
export interface HeaderProps {
  apiBase: string;
  onApiBaseChange: (url: string) => void;
  backendConnected: boolean;
  activeTab: "investigator" | "debugger";
  onTabChange: (tab: "investigator" | "debugger") => void;
  investigationId?: string | null;
  investigationPhase?: InvestigationPhase | string | null;
  investigationStatus?: InvestigationSessionStatus | string | null;
  investigationOutcome?: string | null;
  streamConnectionStatus?: "IDLE" | "CONNECTING" | "OPEN" | "CLOSED" | "ERROR";
  debuggerStatusText?: string;
  debuggerStatusClass?: string;
}

/**
 * Top navigation bar rendering system status, tab switching, and investigation phase badges.
 */
export const Header: React.FC<HeaderProps> = ({
  apiBase,
  onApiBaseChange,
  backendConnected,
  activeTab,
  onTabChange,
  investigationId,
  investigationPhase,
  investigationStatus,
  investigationOutcome,
  streamConnectionStatus = "IDLE",
  debuggerStatusText = "READY",
  debuggerStatusClass = "text-indigo-400",
}) => {
  const [showConfig, setShowConfig] = useState(false);
  const [tempUrl, setTempUrl] = useState(apiBase);

  const handleSaveApi = (): void => {
    onApiBaseChange(tempUrl.trim().replace(/\/+$/, ""));
    setShowConfig(false);
  };

  const getPhaseBadge = (): React.ReactNode => {
    if (!investigationPhase && !investigationStatus && !investigationOutcome) return null;

    if (investigationPhase === "AWAITING_APPROVAL") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          Awaiting Approval
        </span>
      );
    }
    if (investigationPhase === "VERIFYING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          Verifying Patch
        </span>
      );
    }
    if (investigationPhase === "REGRESSING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          Regressing
        </span>
      );
    }
    if (investigationPhase === "PATCH_REJECTED" || investigationOutcome === "PATCH_REJECTED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
          Patch Rejected
        </span>
      );
    }
    if (investigationOutcome === "PROVEN_SAFE") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          Proven Safe
        </span>
      );
    }
    if (investigationOutcome === "PROVEN_REPAIRED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          Proven Repaired
        </span>
      );
    }
    if (investigationOutcome === "NOT_PROVEN_SAFE") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          Not Proven Safe
        </span>
      );
    }
    if (investigationStatus === "COMPLETED" || investigationPhase === "COMPLETED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          Completed
        </span>
      );
    }
    if (investigationStatus === "FAILED" || investigationPhase === "FAILED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
          Failed
        </span>
      );
    }
    if (investigationPhase === "DIAGNOSING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          Diagnosing
        </span>
      );
    }
    if (investigationPhase === "PATCH_PROPOSED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          Patch Proposed
        </span>
      );
    }
    if (investigationPhase === "INVESTIGATING") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          Investigating
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
        <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
        Standby
      </span>
    );
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
      {/* Brand & Title */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 via-indigo-500 to-purple-600 flex items-center justify-center font-black text-white shadow-lg shadow-indigo-500/25 tracking-wider">
          TF
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-white">
              TrueForge Harness-Agent
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              v0.2.0
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            Deterministic Hardware Simulation Testbed & Closed-Loop Agent Reliability Harness
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
        <button
          onClick={() => onTabChange("investigator")}
          className={`px-3.5 py-1.5 rounded-md transition flex items-center gap-1.5 cursor-pointer ${
            activeTab === "investigator"
              ? "bg-indigo-600 text-white shadow-sm font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🔬 Investigation Control Room</span>
        </button>
        <button
          onClick={() => onTabChange("debugger")}
          className={`px-3.5 py-1.5 rounded-md transition flex items-center gap-1.5 cursor-pointer ${
            activeTab === "debugger"
              ? "bg-indigo-600 text-white shadow-sm font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>⚡ Ad-Hoc Evaluation Debugger</span>
        </button>
      </div>

      {/* Status Bar & Settings */}
      <div className="flex flex-wrap items-center space-x-2 sm:space-x-3 text-xs font-mono">
        {/* Active Investigation Session Badge if available */}
        {investigationId && (
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 text-[11px] text-slate-300">
            <span className="text-slate-500">ID:</span>
            <span className="font-semibold text-indigo-400">{investigationId.substring(0, 16)}</span>
          </div>
        )}

        {/* Unified Phase Badge */}
        {investigationId ? (
          getPhaseBadge()
        ) : activeTab === "debugger" ? (
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800 border border-slate-700">
            <span className="text-slate-400">Debugger:</span>
            <span className={`font-semibold uppercase ${debuggerStatusClass}`}>
              {debuggerStatusText}
            </span>
          </div>
        ) : (
          getPhaseBadge()
        )}

        {/* Live WebSocket Stream Indicator */}
        <div
          title={
            streamConnectionStatus === "OPEN"
              ? "Live WebSocket Stream Connected"
              : streamConnectionStatus === "CONNECTING"
              ? "Connecting Stream..."
              : "Stream Standby"
          }
          className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/80 text-[11px]"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              streamConnectionStatus === "OPEN"
                ? "bg-emerald-400 shadow-sm shadow-emerald-400 animate-ping"
                : streamConnectionStatus === "CONNECTING"
                ? "bg-amber-400 animate-pulse"
                : "bg-slate-500"
            }`}
          />
          <span className="text-slate-400 font-sans">
            {streamConnectionStatus === "OPEN"
              ? "Stream Live"
              : streamConnectionStatus === "CONNECTING"
              ? "Connecting..."
              : "Stream Standby"}
          </span>
        </div>

        {/* API Connection & Config Button */}
        <button
          onClick={() => setShowConfig(!showConfig)}
          title="Configure API Base URL"
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 transition text-slate-300 cursor-pointer"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              backendConnected ? "bg-emerald-400 animate-pulse" : "bg-rose-400"
            }`}
          />
          <span className="text-slate-400">API:</span>
          <span
            className={`font-semibold ${
              backendConnected ? "text-emerald-400" : "text-rose-400"
            }`}
          >
            {backendConnected ? "CONNECTED" : "OFFLINE"}
          </span>
          <svg
            className="w-3.5 h-3.5 ml-1 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
      </div>

      {/* API Config Popover Modal */}
      {showConfig && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">
                Backend Server Configuration
              </h3>
              <button
                onClick={() => setShowConfig(false)}
                className="text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                FastAPI Server URL
              </label>
              <input
                type="text"
                value={tempUrl}
                onChange={(e) => setTempUrl(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
                placeholder="http://localhost:8000"
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowConfig(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs hover:bg-slate-700 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveApi}
                className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer"
              >
                Save & Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};