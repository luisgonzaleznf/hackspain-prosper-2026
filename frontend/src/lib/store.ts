// One store for everything live: the calls index polled every few seconds,
// and per-call detail refreshed while a call is in progress. Screens subscribe
// to a slice through useSyncExternalStore, so a board of twenty rows re-renders
// one row per change, not the board. The index polls the local recording snapshot;
// stable source revisions keep unchanged details cached.

import { useCallback, useEffect, useSyncExternalStore } from "react";
import { api, ApiError } from "./api.ts";
import { project, type Timeline } from "./timeline.ts";
import type { CallDetail, CallSummary } from "./types.ts";

export interface CallRecord {
  summary: CallSummary;
  detail: CallDetail | null;
  timeline: Timeline | null;
  detailError: string | null;
  detailAt: number;
  detailRevision: number | null;
}

interface State {
  calls: CallSummary[];
  byId: Record<string, CallRecord>;
  order: string[];
  loadedAt: number | null;
  error: string | null;
  loading: boolean;
  creditsExhausted: { provider: string; detail: string } | null;
}

const INDEX_INTERVAL_MS = 4000;
const ACTIVE_DETAIL_INTERVAL_MS = 1500;
let state: State = { calls: [], byId: {}, order: [], loadedAt: null, error: null, loading: true, creditsExhausted: null };
const listeners = new Set<() => void>();
const rowListeners = new Map<string, Set<() => void>>();

function emit(): void {
  for (const listener of listeners) listener();
}

function emitRow(id: string): void {
  const set = rowListeners.get(id);
  if (set) for (const listener of set) listener();
}

function setState(patch: Partial<State>): void {
  state = { ...state, ...patch };
  emit();
}

/** A socket the backend still reports open. Anything older than an hour is a
 * stale smoke-test file, not a call; it goes to the Calls table instead. */
export function isActive(summary: CallSummary): boolean {
  return summary.status === "in progress" && Date.now() / 1000 - summary.started_at < 3600;
}

const SUMMARY_FIELDS = ["call_id", "started_at", "modified_at", "modified_iso", "status", "action", "duration_seconds", "warnings", "has_audio", "credits"] as const;
const RUN_FIELDS = ["run_id", "mode", "problem_id", "case_id", "suite_position", "suite_total"] as const;

function sameSummary(a: CallSummary, b: CallSummary): boolean {
  return SUMMARY_FIELDS.every((key) => a[key] === b[key])
    && (a.run === b.run || (a.run != null && b.run != null && RUN_FIELDS.every((key) => a.run?.[key] === b.run?.[key])));
}

let indexRequest: Promise<void> | null = null;

function refreshIndex(): Promise<void> {
  if (!indexRequest) indexRequest = fetchIndex().finally(() => { indexRequest = null; });
  return indexRequest;
}

async function fetchIndex(): Promise<void> {
  try {
    const index = await api.calls();
    let byId = state.byId;
    const stale: string[] = [];
    const changed: string[] = [];
    const calls = index.calls.map((summary) => {
      const existing = byId[summary.call_id];
      if (existing?.detail && (existing.detailRevision !== summary.modified_at || existing.detail.summary.has_audio !== summary.has_audio)) stale.push(summary.call_id);
      if (existing && sameSummary(existing.summary, summary)) return existing.summary;
      if (byId === state.byId) byId = { ...byId };
      byId[summary.call_id] = existing ? { ...existing, summary } : { summary, detail: null, timeline: null, detailError: null, detailAt: 0, detailRevision: null };
      changed.push(summary.call_id);
      return summary;
    });
    const unchanged = calls.length === state.calls.length && calls.every((call, index) => call === state.calls[index]);
    const credits = calls.find((c) => c.credits)?.credits ?? null;
    setState({ calls: unchanged ? state.calls : calls, byId, order: unchanged ? state.order : calls.map((c) => c.call_id), loadedAt: Date.now(), error: null, loading: false, creditsExhausted: credits });
    for (const id of changed) emitRow(id);
    for (const id of stale) void loadDetail(id, true);
  } catch (error) {
    setState({ error: error instanceof Error ? error.message : String(error), loading: false });
  }
}

const inflight = new Map<string, Promise<void>>();

export function loadDetail(id: string, force = false): Promise<void> {
  const record = state.byId[id];
  if (!force && record?.detail && !isActive(record.summary)) return Promise.resolve();
  const pending = inflight.get(id);
  if (pending) return pending;
  const detailRevision = record?.summary.modified_at ?? null;
  const task = api
    .call(id)
    .then((detail) => {
      const summary = state.byId[id]?.summary ?? detail.summary;
      const next: CallRecord = { summary, detail, timeline: project(detail), detailError: null, detailAt: Date.now(), detailRevision };
      state = { ...state, byId: { ...state.byId, [id]: next } };
      emit();
      emitRow(id);
    })
    .catch((error: unknown) => {
      const message = error instanceof ApiError ? `${error.status}: ${error.message}` : error instanceof Error ? error.message : String(error);
      const prev = state.byId[id];
      // Unknown id (deep link to a call the backend does not have): keep a placeholder so the drawer can say so.
      const placeholder: CallSummary = {
        call_id: id,
        started_at: 0,
        modified_at: 0,
        modified_iso: null,
        status: "unknown",
        action: "",
        duration_seconds: null,
        warnings: 0,
        has_audio: false,
        credits: null,
        run: null,
      };
      const next: CallRecord = prev ? { ...prev, detailError: message, detailAt: Date.now() } : { summary: placeholder, detail: null, timeline: null, detailError: message, detailAt: Date.now(), detailRevision: null };
      state = { ...state, byId: { ...state.byId, [id]: next } };
      emit();
      emitRow(id);
    })
    .finally(() => inflight.delete(id));
  inflight.set(id, task);
  return task;
}

type Timer = number;
let indexTimer: Timer | null = null;
let detailTimer: Timer | null = null;
let consumers = 0;

function startPolling(): void {
  consumers += 1;
  if (indexTimer) return;
  void refreshIndex();
  indexTimer = window.setInterval(() => {
    if (document.visibilityState === "hidden") return;
    void refreshIndex();
  }, INDEX_INTERVAL_MS);
  detailTimer = window.setInterval(() => {
    if (document.visibilityState === "hidden") return;
    for (const summary of state.calls) if (isActive(summary)) void loadDetail(summary.call_id, true);
  }, ACTIVE_DETAIL_INTERVAL_MS);
}

function stopPolling(): void {
  consumers -= 1;
  if (consumers > 0) return;
  if (indexTimer) clearInterval(indexTimer);
  if (detailTimer) clearInterval(detailTimer);
  indexTimer = null;
  detailTimer = null;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function subscribeRow(id: string): (listener: () => void) => () => void {
  return (listener) => {
    let set = rowListeners.get(id);
    if (!set) {
      set = new Set();
      rowListeners.set(id, set);
    }
    set.add(listener);
    return () => {
      set?.delete(listener);
      if (set && set.size === 0) rowListeners.delete(id);
    };
  };
}

/** Keeps the index polling while any screen is mounted. */
export function usePolling(): void {
  useEffect(() => {
    startPolling();
    return stopPolling;
  }, []);
}

export function useCallsIndex(): State {
  return useSyncExternalStore(
    subscribe,
    () => state,
    () => state,
  );
}

/** True while any call reports voice-provider credit exhaustion. */
export function useCreditsExhausted(): { provider: string; detail: string } | null {
  return useSyncExternalStore(
    subscribe,
    () => state.creditsExhausted,
    () => state.creditsExhausted,
  );
}

/** Per-row subscription: re-renders only when this call's record changes. */
export function useCallRecord(id: string | null): CallRecord | null {
  const sub = useCallback((listener: () => void) => (id ? subscribeRow(id)(listener) : () => {}), [id]);
  const get = useCallback(() => (id ? (state.byId[id] ?? null) : null), [id]);
  return useSyncExternalStore(sub, get, get);
}

/** Loads a call's detail once (or keeps it fresh while active) and returns the record. */
export function useCallDetail(id: string | null): CallRecord | null {
  const record = useCallRecord(id);
  useEffect(() => {
    if (id) void loadDetail(id);
  }, [id]);
  return record;
}

export function refreshNow(): Promise<void> {
  return refreshIndex();
}

/** Test seam: the current state. */
export function __state(): State {
  return state;
}
