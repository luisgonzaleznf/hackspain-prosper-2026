import type { VoiceSettings, VoiceSettingsDocument } from "@/lib/voice-settings";

// Roleplay Studio and its saved voice configuration share the same backend.
export interface Persona {
  id: string;
  title: string;
  name: string;
  phone: string;
  facts: [string, string][];
  objective: string;
  opening_hint: string;
}
export interface Milestone { label: string; state: string }
export interface Turn { role: string; text: string; interrupted?: boolean }
export interface ToolEvent { name: string; summary: string; status: string }
export interface Evidence { action: string; label: string; fields: [string, string][]; checks: string[] }
export interface Snapshot {
  status: string;
  milestones?: Milestone[];
  transcript?: Turn[];
  tools?: ToolEvent[];
  evidence?: Evidence[];
  error?: string | null;
}
export interface LedgerEntry {
  session_id: string;
  completed_at: string;
  status: string;
  evidence?: Evidence[];
  error?: string | null;
}

const json = async <T,>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
};

/** One row of the live feed, projected by the backend from the durable JSONL. */
export interface StreamEvent {
  id: number | string;
  type: string;
  participant: string;
  label: string;
  summary: string;
  status: string;
}

export const demo = {
  settings: () => json<VoiceSettingsDocument>("/api/demo/settings", { signal: AbortSignal.timeout(15_000) }),
  saveSettings: (settings: VoiceSettings) => json<VoiceSettings>("/api/demo/settings", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(settings), signal: AbortSignal.timeout(15_000),
  }),
  scenarios: () => json<Persona[]>("/api/demo/scenarios"),
  ledger: () => json<LedgerEntry[]>("/api/demo/ledger"),
  snapshot: (id: string) => json<Snapshot>(`/api/demo/sessions/${encodeURIComponent(id)}`),
  open: (id: string, scenarioId: string) => json<Snapshot>(`/api/demo/sessions/${encodeURIComponent(id)}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_id: scenarioId }),
  }),
  reviewUrl: (id: string) => `/demo/review.html?call=${encodeURIComponent(id)}`,
  eventsUrl: (id: string) => `/api/demo/sessions/${encodeURIComponent(id)}/events`,
};

/** The server nests the session id differently per callback, so search the payload. */
export function sessionIdOf(value: unknown, seen = new Set<unknown>()): string | null {
  if (!value || typeof value !== "object" || seen.has(value)) return null;
  seen.add(value);
  const record = value as Record<string, unknown>;
  if (typeof record.session_id === "string") return record.session_id;
  if (typeof record.sessionId === "string") return record.sessionId;
  for (const nested of Object.values(record)) {
    const found = sessionIdOf(nested, seen);
    if (found) return found;
  }
  return null;
}

export function describeError(error: unknown): string {
  const name = (error as { name?: string })?.name ?? "";
  const message = String((error as { message?: string })?.message ?? error ?? "");
  if (name === "NotAllowedError" || /permission|denied|notallowed/i.test(message)) return "Microphone access was denied. Allow it in your browser, then try again.";
  if (name === "NotFoundError" || /no.*microphone|device.*not found/i.test(message)) return "No microphone was found. Connect one and try again.";
  return message ? `Could not start the call: ${message}` : "Could not start the call. Check the server and try again.";
}
