import type { CallRecord } from "../../lib/store.ts";
import { actionVerbs, savedWrite } from "../../lib/timeline.ts";
import type { CallSummary } from "../../lib/types.ts";

export type OverviewRange = "24h" | "7d" | "all";
export type OverviewSeries = "calls" | "bookings" | "duration";
export const DETAIL_SAMPLE_SIZE = 60;

export function measured(value: number | null | undefined): value is number {
  return value != null && Number.isFinite(value) && value >= 0;
}

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2;
}

export function completed(call: CallSummary): boolean {
  return call.status !== "in progress" && (measured(call.duration_seconds) || call.status === "saved" || call.status === "write failed");
}

export function selectCalls(calls: CallSummary[], range: OverviewRange, now: number) {
  const start = range === "all" ? 0 : now - (range === "24h" ? 86400 : 7 * 86400);
  return calls.filter((call) => Number.isFinite(call.started_at) && call.started_at > 0 && call.started_at >= start && call.started_at <= now)
    .sort((a, b) => b.started_at - a.started_at);
}

export function currentDetail(call: CallSummary, byId: Record<string, CallRecord>) {
  const record = byId[call.call_id];
  return record?.detail && record.detailRevision === call.modified_at ? record : null;
}

/** Appointments Rosario saved: successful BOOK and RESCHEDULE writes, one per appointment,
 * so a booking moved again in the same call counts once. */
export function bookingCount(record: CallRecord): number {
  const bookings = new Set<string>();
  for (const write of record.detail?.writes ?? []) {
    const action = write.action;
    if ((action?.action !== "BOOK" && action?.action !== "RESCHEDULE") || !savedWrite(write)) continue;
    const id = write.result?.appointment_id;
    bookings.add(typeof id === "string" && id ? id : JSON.stringify([action.action, action.appointment_id, action.patient_id, action.provider_id, action.location_id, action.slot]));
  }
  return bookings.size;
}

const OUTCOMES = [
  ["BOOK", "Booked"], ["RESCHEDULE", "Rescheduled"], ["CANCEL", "Cancelled"],
  ["REGISTER", "Registered"], ["NO_ACTION", "No change"], ["ESCALATE", "Escalated"],
  ["failed", "Write failed"], ["unknown", "Nothing saved"],
] as const;

const WRITE_VERBS = new Set(["BOOK", "RESCHEDULE", "CANCEL", "REGISTER"]);

/** A write verb counts only when the call saved it; declining or escalating needs no write. */
export function outcomeKey(call: CallSummary): string {
  if (call.status === "write failed") return "failed";
  const verb = actionVerbs(call.action).at(-1);
  if (!verb) return "unknown";
  if (WRITE_VERBS.has(verb)) return call.status === "saved" ? verb : "unknown";
  return verb === "NO_ACTION" || verb === "ESCALATE" ? verb : "unknown";
}

export function outcomeLabel(call: CallSummary): string {
  return OUTCOMES.find(([key]) => key === outcomeKey(call))?.[1] ?? "Nothing saved";
}

export function aggregateOverview(calls: CallSummary[], byId: Record<string, CallRecord>, range: OverviewRange, now: number) {
  const finished = calls.filter(completed);
  const sample = finished.slice(0, DETAIL_SAMPLE_SIZE);
  const sampleIds = new Set(sample.map((call) => call.call_id));
  const bookingsByCall = new Map<string, number>();
  let totalSeconds = 0;
  let durationCount = 0;
  const latencies: number[] = [];
  let loaded = 0;
  let bookings = 0;
  let detailErrors = 0;
  const outcomes = new Map<string, number>();
  for (const call of finished) {
    const key = outcomeKey(call);
    outcomes.set(key, (outcomes.get(key) ?? 0) + 1);
    if (measured(call.duration_seconds)) {
      totalSeconds += call.duration_seconds;
      durationCount += 1;
    }
    if (!sampleIds.has(call.call_id)) continue;
    const record = currentDetail(call, byId);
    if (byId[call.call_id]?.detailError) detailErrors += 1;
    if (!record) continue;
    loaded += 1;
    const accepted = bookingCount(record);
    bookingsByCall.set(call.call_id, accepted);
    bookings += accepted;
    if (measured(record.timeline?.medianResponseGapMs)) latencies.push(record.timeline.medianResponseGapMs);
  }

  const start = range === "all" ? (calls.at(-1)?.started_at ?? now - 86400) : now - (range === "24h" ? 86400 : 7 * 86400);
  const span = now - start;
  const step = span <= 86400 ? 3600 : span <= 7 * 86400 ? 6 * 3600 : Math.ceil(span / (30 * 86400)) * 86400;
  const first = Math.floor(start / step) * step;
  const buckets = Array.from({ length: Math.floor((now - first) / step) + 1 }, (_, index) => ({
    time: first + index * step, calls: 0, bookings: 0, loaded: 0, seconds: 0, durations: 0,
  }));
  for (const call of finished) {
    const bucket = buckets[Math.floor((call.started_at - first) / step)];
    if (!bucket) continue;
    bucket.calls += 1;
    if (measured(call.duration_seconds)) {
      bucket.seconds += call.duration_seconds;
      bucket.durations += 1;
    }
    const accepted = bookingsByCall.get(call.call_id);
    if (accepted != null) {
      bucket.loaded += 1;
      bucket.bookings += accepted;
    }
  }
  return {
    finished, sample, loaded, bookings: loaded > 0 ? bookings : null, detailErrors,
    duration: durationCount ? totalSeconds / durationCount : null,
    durationCount, latency: median(latencies), latencyCount: latencies.length,
    outcomes: OUTCOMES.map(([key, label]) => ({ key, label, count: outcomes.get(key) ?? 0 })).filter((outcome) => outcome.count > 0),
    buckets: buckets.map((bucket) => ({ ...bucket,
      bookings: bucket.calls === 0 || bucket.loaded > 0 ? bucket.bookings : null,
      duration: bucket.durations ? bucket.seconds / bucket.durations : null,
    })),
    start, step,
  };
}
