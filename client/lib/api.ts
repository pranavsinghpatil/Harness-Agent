import {
  ScenarioDefinition,
  RunDetailsResponse,
  ReplayResponse,
  HardwarePreset,
  HarnessEvaluation,
  CausalDiagnosticReport,
  PatchResult,
  VerificationResult,
  InvestigationSessionSnapshot,
} from "../types/simulation";

export interface RunScenarioPayload {
  scenario_id?: string;
  scenario_spec?: Record<string, unknown>;
  seed?: number;
  max_sim_time?: number;
}

export interface CreateEvaluationPayload {
  hardware_preset_id: string;
  scenario_id: string;
  controller_code?: string | null;
  seed: number;
  mode?: string;
}

export interface PatchControllerPayload {
  original_code: string;
  strategy?: string;
}

export interface VerifyPatchPayload {
  patched_code: string;
}

export async function checkHealth(apiBase: string): Promise<boolean> {
  try {
    const res = await fetch(`${apiBase}/health`, { method: "GET" });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === "ok";
  } catch {
    return false;
  }
}

export async function getScenarios(apiBase: string): Promise<ScenarioDefinition[]> {
  const res = await fetch(`${apiBase}/api/scenarios/`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenarios (${res.status} ${res.statusText})`);
  }
  return res.json();
}

export async function getScenarioById(apiBase: string, id: string): Promise<ScenarioDefinition> {
  const res = await fetch(`${apiBase}/api/scenarios/${encodeURIComponent(id)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch scenario ${id} (${res.status} ${res.statusText})`);
  }
  return res.json();
}

export async function runScenario(
  apiBase: string,
  payload: RunScenarioPayload
): Promise<RunDetailsResponse> {
  const res = await fetch(`${apiBase}/api/scenarios/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Run failed with status ${res.status}`);
  }
  return res.json();
}

export async function replayRun(apiBase: string, runId: string): Promise<ReplayResponse> {
  const res = await fetch(`${apiBase}/api/scenarios/replay/${encodeURIComponent(runId)}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Replay failed with status ${res.status}`);
  }
  return res.json();
}

export async function getRunDetails(apiBase: string, runId: string): Promise<RunDetailsResponse> {
  const res = await fetch(`${apiBase}/api/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run ${runId} (${res.status} ${res.statusText})`);
  }
  return res.json();
}

export async function getHardwarePresets(apiBase: string): Promise<HardwarePreset[]> {
  const res = await fetch(`${apiBase}/api/harness/hardware-presets`);
  if (!res.ok) {
    throw new Error(`Failed to fetch hardware presets (${res.status} ${res.statusText})`);
  }
  return res.json();
}

export async function createEvaluation(
  apiBase: string,
  payload: CreateEvaluationPayload
): Promise<HarnessEvaluation> {
  const res = await fetch(`${apiBase}/api/harness/evaluations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Evaluation creation failed (${res.status})`);
  }
  return res.json();
}

export async function getEvaluation(
  apiBase: string,
  evaluationId: string
): Promise<HarnessEvaluation> {
  const res = await fetch(`${apiBase}/api/harness/evaluations/${encodeURIComponent(evaluationId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch evaluation (${res.status})`);
  }
  return res.json();
}

export async function diagnoseEvaluation(
  apiBase: string,
  evaluationId: string
): Promise<CausalDiagnosticReport> {
  const res = await fetch(
    `${apiBase}/api/harness/evaluations/${encodeURIComponent(evaluationId)}/diagnose`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Diagnostics failed (${res.status})`);
  }
  return res.json();
}

export async function generatePatch(
  apiBase: string,
  evaluationId: string,
  payload: PatchControllerPayload
): Promise<PatchResult> {
  const res = await fetch(
    `${apiBase}/api/harness/evaluations/${encodeURIComponent(evaluationId)}/patch`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Patch generation failed (${res.status})`);
  }
  return res.json();
}

export async function verifyPatch(
  apiBase: string,
  evaluationId: string,
  payload: VerifyPatchPayload
): Promise<VerificationResult> {
  const res = await fetch(
    `${apiBase}/api/harness/evaluations/${encodeURIComponent(evaluationId)}/verify`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Verification failed (${res.status})`);
  }
  return res.json();
}

export async function runFullEvaluation(
  apiBase: string,
  payload: CreateEvaluationPayload
): Promise<HarnessEvaluation> {
  const res = await fetch(`${apiBase}/api/harness/evaluate-full`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Full evaluation loop failed (${res.status})`);
  }
  return res.json();
}

export interface InvestigationPayload {
  objective: string;
  hardware_preset_id?: string;
  scenario_id?: string;
  controller_code?: string | null;
  seed?: number;
  budget?: number;
  max_boundary_steps?: number;
  max_sim_time?: number;
}

export interface PatchApprovalPayload {
  patch_id: string;
  decision: "APPROVE" | "REJECT" | string;
  reason?: string;
}

/**
 * Creates an asynchronous, persistent InvestigationSession on the backend.
 * Returns HTTP 202 Accepted with the initial session snapshot (including investigation_id).
 */
export async function startInvestigation(
  apiBase: string,
  payload: InvestigationPayload
): Promise<import("../types/simulation").InvestigationSessionSnapshot> {
  const res = await fetch(`${apiBase}/api/harness/investigations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Failed to start investigation (${res.status})`);
  }
  return res.json();
}

/**
 * Polls the current session snapshot (status, phase, hypotheses, traces, patch, verification, conclusion).
 */
export async function getInvestigation(
  apiBase: string,
  investigationId: string
): Promise<import("../types/simulation").InvestigationSessionSnapshot> {
  const res = await fetch(
    `${apiBase}/api/harness/investigations/${encodeURIComponent(investigationId)}`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Failed to fetch investigation (${res.status})`);
  }
  return res.json();
}

/**
 * Retrieves the full ordered history of canonical HarnessEvent items for an investigation session.
 */
export async function getInvestigationEvents(
  apiBase: string,
  investigationId: string
): Promise<import("../types/simulation").HarnessEvent[]> {
  const res = await fetch(
    `${apiBase}/api/harness/investigations/${encodeURIComponent(investigationId)}/events`
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Failed to fetch investigation events (${res.status})`);
  }
  return res.json();
}

/**
 * Submits a reviewer decision (APPROVE or REJECT) for a pending patch.
 * Requires bearer authentication (e.g. HARNESS_APPROVAL_TOKEN).
 */
export async function approveInvestigationPatch(
  apiBase: string,
  investigationId: string,
  payload: PatchApprovalPayload,
  token: string = "test-reviewer-token"
): Promise<import("../types/simulation").InvestigationSessionSnapshot> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token.trim()}`;
  }

  const res = await fetch(
    `${apiBase}/api/harness/investigations/${encodeURIComponent(investigationId)}/approval`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        patch_id: payload.patch_id,
        decision: payload.decision,
        reason: payload.reason || "",
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Patch approval failed (${res.status})`);
  }
  return res.json();
}

/**
 * Backward compatibility wrapper that starts an investigation and returns the snapshot.
 */
export async function runInvestigation(
  apiBase: string,
  payload: InvestigationPayload
): Promise<InvestigationSessionSnapshot> {
  return startInvestigation(apiBase, payload);
}


