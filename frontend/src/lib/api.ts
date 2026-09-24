import { parseCalendarFeed, type CalendarFeed } from "./calendar.ts";
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

/** Logs from before the clinic database (or the recording library) lack the write lists. */
function withDefaults(detail: CallDetail): CallDetail {
  return {
    ...detail,
    writes: Array.isArray(detail.writes) ? detail.writes : [],
    provenance: Array.isArray(detail.provenance) ? detail.provenance : [],
    staged_actions: Array.isArray(detail.staged_actions) ? detail.staged_actions : [],
  };
}

export const api = {
  /** One window of the clinic diary, `from`/`to` inclusive (YYYY-MM-DD, Madrid). */
  calendar: async (from: string, to: string, signal?: AbortSignal): Promise<CalendarFeed> =>
    parseCalendarFeed(await getJson<unknown>(`/api/clinic/calendar?from=${from}&to=${to}`, signal)),
  calls: (signal?: AbortSignal) => getJson<CallsIndex>("/api/calls", signal),
  call: async (id: string, signal?: AbortSignal) => withDefaults(await getJson<CallDetail>(`/api/calls/${encodeURIComponent(id)}`, signal)),
  audioUrl: (id: string) => `/api/calls/${encodeURIComponent(id)}/audio`,
};
