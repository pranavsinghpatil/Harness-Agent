"use client";

import React from "react";
import { AdHocDebuggerView } from "./AdHocDebuggerView";
import { HardwarePreset, ScenarioDefinition } from "../types/simulation";

/**
 * Props for the HarnessView compatibility wrapper.
 */
export interface HarnessViewProps {
  /** Root URL for the backend FastAPI service */
  apiBase: string;
  /** Available hardware presets for manual scenario execution */
  presets?: HardwarePreset[];
  /** Available simulation scenarios */
  scenarios: ScenarioDefinition[];
  /** Callback fired whenever the simulation status text or styling changes */
  onStatusChange?: (statusText: string, statusClass: string) => void;
}

/**
 * Backward compatibility wrapper component delegating manual scenario debugging
 * and interactive simulation scrubbing to AdHocDebuggerView.
 */
export const HarnessView: React.FC<HarnessViewProps> = ({
  apiBase,
  presets = [],
  scenarios,
  onStatusChange,
}) => {
  return (
    <AdHocDebuggerView
      apiBase={apiBase}
      presets={presets}
      scenarios={scenarios}
      onStatusChange={onStatusChange}
    />
  );
};

export { AdHocDebuggerView };
