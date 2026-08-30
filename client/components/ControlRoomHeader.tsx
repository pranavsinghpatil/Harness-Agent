"use client";

import React from "react";
import {
  InvestigationSessionStatus,
  InvestigationPhase,
  HardwarePreset,
  ScenarioDefinition,
} from "../types/simulation";

interface ControlRoomHeaderProps {
  investigationId: string | null;
  status: InvestigationSessionStatus;
  phase: InvestigationPhase;
  objective: string;
  completedExperiments: number;
  budget: number;
  hardwarePreset?: HardwarePreset | null;
  scenario?: ScenarioDefinition | null;
  connectionStatus: "IDLE" | "CONNECTING" | "OPEN" | "CLOSED" | "ERROR";
  onNewInvestigationClick: () => void;
  onApproveClick?: () => void;
}

export const ControlRoomHeader: React.FC<ControlRoomHeaderProps> = ({
  investigationId,
  status,
  phase,
  objective,
  completedExperiments,
  budget,
  hardwarePreset,
  scenario,
  connectionStatus,
  onNewInvestigationClick,
  onApproveClick,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case "RUNNING":
        if (phase === "AWAITING_APPROVAL") {
          return (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              AWAITING HUMAN APPROVAL
            </span>
          );
        }
        if (phase === "VERIFYING") {
          return (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
              VERIFYING HARDENED PATCH
            </span>
          );
        }
        if (phase === "REGRESSING") {
          return (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              RUNNING REGRESSION SUITE
            </span>
          );
        }
        if (phase === "PATCH_REJECTED") {
          return (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
              <span className="w-2 h-2 rounded-full bg-rose-400"></span>
              PATCH REJECTED
            </span>
          );
        }
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            INVESTIGATING ({phase})
          </span>
        );

      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            PROVEN & CERTIFIED
          </span>
        );

      case "FAILED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
            <span className="w-2 h-2 rounded-full bg-rose-400"></span>
            INVESTIGATION FAILED
          </span>
        );

      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-slate-500"></span>
            STANDBY
          </span>
        );
    }
  };

  const progressPercent = budget > 0 ? Math.min(100, Math.round((completedExperiments / budget) * 100)) : 0;

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl transition-all">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Branding & Session ID */}
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-black text-xs text-white shadow-md shadow-indigo-500/30">
                TF
              </span>
              <h1 className="text-base font-bold text-white tracking-wide">
                Investigation Control Room
              </h1>
            </div>

            {investigationId && (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300">
                <span className="text-slate-500">ID:</span>
                <span className="font-semibold text-indigo-400">{investigationId}</span>
              </div>
            )}

            {getStatusBadge()}
          </div>

          <p className="text-xs text-slate-300 max-w-3xl line-clamp-1">
            <span className="text-slate-500 font-medium mr-1.5">Objective:</span>
            {objective || "Autonomous System 2 Reliability Exploration"}
          </p>
        </div>

        {/* Right: Progress & Controls */}
        <div className="flex flex-wrap items-center gap-3 sm:gap-4 self-start lg:self-center">
          {/* Hardware & Scenario Tags */}
          <div className="hidden sm:flex flex-col items-end text-[11px] font-mono text-slate-400 space-y-0.5">
            <div>
              <span className="text-slate-500">Hardware:</span>{" "}
              <span className="text-slate-200 font-semibold">{hardwarePreset?.name || "RDK X5"}</span>
            </div>
            <div>
              <span className="text-slate-500">Scenario:</span>{" "}
              <span className="text-slate-300">{scenario?.name || "Normal Baseline"}</span>
            </div>
          </div>

          {/* Experiment Progress Bar */}
          <div className="flex flex-col gap-1 min-w-[130px] sm:min-w-[160px] bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="text-slate-400">Experiments</span>
              <span className="text-indigo-300 font-bold">
                {completedExperiments} / {budget}
              </span>
            </div>
            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-linear-to-r from-indigo-500 to-purple-500 transition-all duration-300 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Human Approval Action Button if awaiting approval */}
          {phase === "AWAITING_APPROVAL" && onApproveClick && (
            <button
              onClick={onApproveClick}
              className="py-2.5 px-4 rounded-xl bg-linear-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 active:opacity-90 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-amber-500/20 cursor-pointer animate-bounce"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Review Patch
            </button>
          )}

          {/* New Investigation Button */}
          <button
            onClick={onNewInvestigationClick}
            className="py-2.5 px-4 rounded-xl bg-linear-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:opacity-90 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
            </svg>
            New Session
          </button>
        </div>
      </div>

      {/* Stream Connection Live Pulse */}
      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              connectionStatus === "OPEN"
                ? "bg-emerald-400 shadow-sm shadow-emerald-400 animate-ping"
                : connectionStatus === "CONNECTING"
                ? "bg-amber-400 animate-pulse"
                : "bg-slate-600"
            }`}
          />
          <span className="font-mono">
            {connectionStatus === "OPEN"
              ? "Live Investigation WebSocket Stream Connected"
              : connectionStatus === "CONNECTING"
              ? "Connecting Stream..."
              : "Stream Standby"}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-slate-500">Autonomous SIL Hardware Harness</span>
          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">v0.2.0</span>
        </div>
      </div>
    </header>
  );
};
