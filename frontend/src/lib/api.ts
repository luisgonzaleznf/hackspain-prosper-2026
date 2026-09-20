import type { CalendarSources, SchedulingRecord } from "./calendar.ts";
import type { CallDetail, CallsIndex } from "./types.ts";

// Same-origin `/api/calls`: live local console when configured, otherwise imported recordings.
// Errors carry the HTTP status so screens can say what happened.

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const timeout = new AbortController();
  const deadline = setTimeout(() => timeout.abort(new DOMException("Request timed out.", "TimeoutError")), 15_000);
  try {
    const response = await fetch(path, {
      signal: signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal,
      headers: { accept: "application/json" },
    });
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // A missing JSON error body does not hide the HTTP status.
      }
      throw new ApiError(response.status, detail || `HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(deadline);
  }
}

export const api = {
  calendar: (signal?: AbortSignal) => getJson<{ records: SchedulingRecord[]; sources?: CalendarSources }>("/api/clinic/calendar", signal),
  calls: (signal?: AbortSignal) => getJson<CallsIndex>("/api/calls", signal),
  call: (id: string, signal?: AbortSignal) => getJson<CallDetail>(`/api/calls/${encodeURIComponent(id)}`, signal),
  audioUrl: (id: string) => `/api/calls/${encodeURIComponent(id)}/audio`,
};
