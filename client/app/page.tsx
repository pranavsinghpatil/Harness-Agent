"use client";

import React, { useState, useEffect } from "react";
import { ScenarioDefinition, HardwarePreset } from "../types/simulation";
import { getScenarios, getHardwarePresets, checkHealth } from "../lib/api";
import { useInvestigation } from "../hooks/useInvestigation";
import { Header } from "../components/Header";
import { InvestigatorView } from "../components/InvestigatorView";
import { AdHocDebuggerView } from "../components/AdHocDebuggerView";

export default function Home() {
  const [apiBase, setApiBase] = useState<string>("http://localhost:8000");
  const [activeTab, setActiveTab] = useState<"investigator" | "debugger">("investigator");

  // Presets & Scenarios
  const [presets, setPresets] = useState<HardwarePreset[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>([]);
  const [backendConnected, setBackendConnected] = useState<boolean>(false);

  // Debugger status text tracking
  const [debuggerStatusText, setDebuggerStatusText] = useState<string>("READY");
  const [debuggerStatusClass, setDebuggerStatusClass] = useState<string>("text-indigo-400");

  // Primary persistent Investigation lifecycle hook
  const investigation = useInvestigation(apiBase);

  // Load Presets and Scenarios on mount or API URL change
  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      try {
        const isHealthy = await checkHealth(apiBase);
        if (!isMounted) return;
        setBackendConnected(isHealthy);

        const [presetList, scenarioList] = await Promise.all([
          getHardwarePresets(apiBase).catch(() => []),
          getScenarios(apiBase).catch(() => []),
        ]);

        if (!isMounted) return;
        setPresets(presetList);
        setScenarios(scenarioList);
      } catch (err) {
        console.error("Failed to connect or fetch initial data:", err);
        if (isMounted) setBackendConnected(false);
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [apiBase]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation & Unified Session Header */}
      <Header
        apiBase={apiBase}
        onApiBaseChange={(newUrl) => {
          setApiBase(newUrl);
        }}
        backendConnected={backendConnected}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        investigationId={investigation.investigationId}
        investigationPhase={investigation.phase}
        investigationStatus={investigation.status}
        streamConnectionStatus={investigation.connectionStatus}
        debuggerStatusText={debuggerStatusText}
        debuggerStatusClass={debuggerStatusClass}
      />

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-6 max-w-[1700px] w-full mx-auto">
        {activeTab === "investigator" ? (
          /* Primary: Autonomous Investigation Control Room */
          <InvestigatorView
            apiBase={apiBase}
            presets={presets}
            scenarios={scenarios}
            investigation={investigation}
          />
        ) : (
          /* Secondary: Ad-Hoc Evaluation Debugger */
          <AdHocDebuggerView
            apiBase={apiBase}
            presets={presets}
            scenarios={scenarios}
            onStatusChange={(text, cls) => {
              setDebuggerStatusText(text);
              setDebuggerStatusClass(cls);
            }}
          />
        )}
      </main>
    </div>
  );
}