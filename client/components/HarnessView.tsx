"use client";

import React from "react";
import { AdHocDebuggerView } from "./AdHocDebuggerView";
import { HardwarePreset, ScenarioDefinition } from "../types/simulation";

export interface HarnessViewProps {
  apiBase: string;
  presets?: HardwarePreset[];
  scenarios: ScenarioDefinition[];
  onStatusChange?: (statusText: string, statusClass: string) => void;
}

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
