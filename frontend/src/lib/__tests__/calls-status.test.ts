// Overview outcomes and booking counts come from what the clinic database saved. Run with `pnpm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { bookingCount, completed, outcomeKey, outcomeLabel } from "../../screens/metrics/overview-data.ts";
import type { CallRecord } from "../store.ts";
import type { CallSummary, LocalWriteEvent } from "../types.ts";

function summary(status: string, action: string, duration: number | null = 60): CallSummary {
  return { call_id: "c1", started_at: 100, modified_at: 1, modified_iso: null, status, action, duration_seconds: duration, warnings: 0, has_audio: false, credits: null, run: null };
}

function withWrites(writes: LocalWriteEvent[]): CallRecord {
  const base = summary("saved", "BOOK");
  return {
    summary: base,
    detail: { call_id: "c1", summary: base, run: null, warnings: [], audio: null, transcript: [], tools: [], staged_actions: [], writes, errors: [], provenance: [], events: [] },
    timeline: null, detailError: null, detailAt: 0, detailRevision: 1,
  };
}

const write = (t: number, action: Record<string, unknown>, result: Record<string, unknown> | null): LocalWriteEvent =>
  ({ t, kind: "local_write", action: { action: "BOOK", ...action }, result });

test("each call status maps to one overview outcome", () => {
  assert.equal(outcomeKey(summary("saved", "BOOK")), "BOOK");
  assert.equal(outcomeKey(summary("saved", "REGISTER+BOOK")), "BOOK");
  assert.equal(outcomeKey(summary("saved", "REGISTER")), "REGISTER");
  assert.equal(outcomeKey(summary("saved", "BOOK+CANCEL")), "CANCEL");
  assert.equal(outcomeKey(summary("write failed", "BOOK")), "failed");
  assert.equal(outcomeLabel(summary("write failed", "BOOK")), "Write failed");
  // A refusal or escalation needs no write; a staged booking that never saved is not a booking.
  assert.equal(outcomeKey(summary("ended", "NO_ACTION")), "NO_ACTION");
  assert.equal(outcomeKey(summary("ended", "ESCALATE")), "ESCALATE");
  assert.equal(outcomeKey(summary("ended", "BOOK")), "unknown");
  assert.equal(outcomeKey(summary("ended", String.fromCodePoint(0x2014))), "unknown");
  assert.equal(outcomeLabel(summary("ended", String.fromCodePoint(0x2014))), "Nothing saved");
  // Logs from the old platform are not treated as saved.
  assert.equal(outcomeKey(summary("submitted 200", "BOOK")), "unknown");
});

test("only finished calls count, even without a measured duration when something was saved", () => {
  assert.equal(completed(summary("in progress", "BOOK")), false);
  assert.equal(completed(summary("ended", "", 42)), true);
  assert.equal(completed(summary("ended", "", null)), false);
  assert.equal(completed(summary("saved", "BOOK", null)), true);
  assert.equal(completed(summary("write failed", "BOOK", null)), true);
});

test("bookings are successful BOOK and RESCHEDULE writes, one per appointment", () => {
  assert.equal(bookingCount(withWrites([])), 0);
  assert.equal(bookingCount(withWrites([
    write(1, { action: "REGISTER" }, { patient_id: "LP1" }),
    write(2, {}, { appointment_id: "LA1" }),
    write(3, { action: "RESCHEDULE", appointment_id: "LA1" }, { appointment_id: "LA1" }),
    write(4, { action: "RESCHEDULE", appointment_id: "A100010" }, { appointment_id: "A100010" }),
    write(5, { action: "CANCEL", appointment_id: "A100011" }, { appointment_id: "A100011" }),
    write(6, { slot: "2026-10-06T09:15:00+02:00" }, { error: "slot taken" }),
    write(7, { slot: "2026-10-06T09:30:00+02:00" }, null),
  ])), 2);
  const legacy = withWrites([]);
  (legacy.detail as unknown as { writes?: unknown }).writes = undefined;
  assert.equal(bookingCount(legacy), 0, "a detail without writes counts nothing");
});
