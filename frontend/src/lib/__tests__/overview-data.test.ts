import assert from "node:assert/strict";
import { test } from "node:test";
import { aggregateOverview, detailSample, outcomeKey, selectCalls } from "../../screens/metrics/overview-data.ts";
import type { CallSummary } from "../types.ts";

const DAY = 86400;
const NOW = Date.parse("2026-09-20T10:00:00Z") / 1000;

function call(id: string, startedAt: number, status = "submitted", action = "BOOK"): CallSummary {
  return { call_id: id, started_at: startedAt, modified_at: startedAt + 120, modified_iso: null, status, action, duration_seconds: 120, warnings: 0, has_audio: false, credits: null, run: null };
}

test("live and imported submission labels retain their accepted or failed outcome", () => {
  for (const status of ["submitted", "submitted 200", "submitted 201"]) {
    for (const action of ["BOOK", "RESCHEDULE", "CANCEL", "NO_ACTION", "ESCALATE"]) {
      assert.equal(outcomeKey(call("accepted", NOW, status, action)), action);
    }
  }
  for (const status of ["rejected", "submitted 400", "submitted 500"]) {
    assert.equal(outcomeKey(call("failed", NOW, status)), "failed");
  }
  assert.equal(outcomeKey(call("ended", NOW, "ended")), "unknown");
  assert.equal(outcomeKey(call("active", NOW, "in progress")), "unknown");
});

test("the fourteen-day range includes older history and excludes future and out-of-range calls", () => {
  const calls = [call("yesterday", NOW - DAY), call("older", NOW - 10 * DAY), call("boundary", NOW - 14 * DAY), call("too-old", NOW - 14 * DAY - 1), call("future", NOW + 1)];
  const selected = selectCalls(calls, "14d", NOW);
  assert.deepEqual(selected.map((item) => item.call_id), ["yesterday", "older", "boundary"]);
  const stats = aggregateOverview(selected, {}, "14d", NOW);
  assert.equal(stats.start, NOW - 14 * DAY);
  assert.equal(stats.step, DAY);
  assert.equal(stats.buckets.reduce((sum, bucket) => sum + bucket.calls, 0), 3);
  assert.equal(selectCalls(calls, "7d", NOW).length, 1);
});

test("busy recent days cannot crowd all historical days out of the detail sample", () => {
  const calls = Array.from({ length: 14 }, (_, day) => Array.from({ length: day % 7 > 4 ? 5 : 45 }, (_, index) => call(`${day}-${index}`, NOW - day * DAY - index * 60))).flat();
  const sample = detailSample(calls);
  assert.equal(sample.length, 60);
  assert.equal(new Set(sample.map((item) => item.call_id)).size, 60);
  assert.equal(new Set(sample.map((item) => item.call_id.split("-")[0])).size, 14);
  assert.deepEqual(sample.slice(0, 4).map((item) => item.call_id), calls.slice(0, 4).map((item) => item.call_id));
  assert.deepEqual(aggregateOverview(calls, {}, "14d", NOW).sample, sample);
  const sparse = Array.from({ length: 120 }, (_, index) => call(`sparse-${index}`, NOW - index * DAY));
  const allTime = detailSample(sparse);
  assert.equal(allTime.length, 60);
  assert.equal(allTime.at(-1)?.call_id, "sparse-119");
});
