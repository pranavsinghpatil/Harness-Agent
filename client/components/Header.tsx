"use client";

import React, { useState } from "react";

interface HeaderProps {
  apiBase: string;
  onApiBaseChange: (url: string) => void;
  backendConnected: boolean;
  simStatusText: string;
  simStatusClass: string;
  activeTab: "workbench" | "investigator";
  onTabChange: (tab: "workbench" | "investigator") => void;
}

export const Header: React.FC<HeaderProps> = ({
  apiBase,
  onApiBaseChange,
  backendConnected,
  simStatusText,
  simStatusClass,
  activeTab,
  onTabChange,
}) => {
  const [showConfig, setShowConfig] = useState(false);
  const [tempUrl, setTempUrl] = useState(apiBase);

  const handleSaveApi = () => {
    onApiBaseChange(tempUrl.trim().replace(/\/+$/, ""));
    setShowConfig(false);
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
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
          <p className="text-xs text-slate-400">
            Deterministic Hardware Simulation Testbed & Closed-Loop Agent Reliability Harness
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
        <button
          onClick={() => onTabChange("workbench")}
          className={`px-3.5 py-1.5 rounded-md transition flex items-center gap-1.5 ${
            activeTab === "workbench"
              ? "bg-indigo-600 text-white shadow-sm font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>⚡ Evaluation Workbench</span>
        </button>
        <button
          onClick={() => onTabChange("investigator")}
          className={`px-3.5 py-1.5 rounded-md transition flex items-center gap-1.5 ${
            activeTab === "investigator"
              ? "bg-indigo-600 text-white shadow-sm font-semibold"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🔬 Autonomous Investigator</span>
        </button>
      </div>

      {/* Status Bar & Settings */}
      <div className="flex items-center space-x-3 text-xs font-mono">
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

        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-800 border border-slate-700">
          <span className="text-slate-400">Status:</span>
          <span className={`font-semibold uppercase ${simStatusClass}`}>
            {simStatusText}
          </span>
        </div>
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
                className="text-slate-400 hover:text-white text-xs"
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
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveApi}
                className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
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