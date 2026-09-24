// Regression: detail responses have no file revision. Only successful fetches
// acknowledge the index revision seen when they started.
import assert from "node:assert/strict";
import { test } from "node:test";
import * as store from "../store.ts";

const detailOf = (rev: number, status: string, writes: unknown[]) => ({
  call_id: "c1",
  summary: { call_id: "c1", started_at: 100, modified_at: rev, modified_iso: null, status, action: writes.length ? "BOOK" : String.fromCodePoint(0x2014), duration_seconds: null, warnings: 0, has_audio: false, run: null },
  run: null, warnings: [], audio: null, transcript: [], tools: [], staged_actions: [], writes, errors: [], provenance: [],
  events: [{ t: 100, kind: "call_started", _line: 1 }, ...(status === "in progress" ? [] : [{ t: 120, kind: "stop_received", _line: 2 }, ...writes.map((s, i) => ({ ...(s as object), _line: 3 + i }))])],
});

test("detail refresh follows index revisions and retries failures", async (t) => {
  const write = { t: 114, kind: "local_write", action: { action: "BOOK" }, result: { appointment_id: "LA1", patient_id: "P00001" } };
  let phase = 1;
  let detailFailOnce = true;
  let detailRequests = 0;
  let pendingDetail: Promise<void> | null = null;
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url) => {
    const json = (body: unknown, status = 200) => Response.json(body, { status });
    if (url === "/api/calls") {
      const summary = detailOf(phase, phase === 1 ? "in progress" : "saved", phase === 1 ? [] : [write]).summary;
      return json({ calls_dir: "", calls: [{ ...summary, started_at: Date.now() / 1000 - 60 }] });
    }
    detailRequests += 1;
    if (phase === 2 && detailFailOnce) {
      detailFailOnce = false;
      return json({ detail: "busy" }, 503);
    }
    const detail = detailOf(0, phase === 1 ? "in progress" : "saved", phase === 1 ? [] : [write]);
    if (pendingDetail) await pendingDetail;
    return json(detail);
  };
  const settle = () => new Promise<void>((resolve) => setImmediate(resolve));
  await store.refreshNow();
  await store.loadDetail("c1");
  assert.equal(store.__state().byId.c1?.detail?.writes.length, 0);
  assert.equal(store.__state().byId.c1?.summary.modified_at, 1);

  phase = 2;
  await store.refreshNow();
  await settle();
  assert.equal(store.__state().byId.c1?.detail?.writes.length, 0);
  assert.match(store.__state().byId.c1?.detailError ?? "", /503/);

  await store.refreshNow();
  await settle();
  assert.equal(store.__state().byId.c1?.detail?.writes.length, 1);
  assert.equal(store.__state().byId.c1?.detailError, null);
  assert.equal(store.__state().byId.c1?.summary.modified_at, 2);
  assert.equal(detailRequests, 3);

  await store.refreshNow();
  await settle();
  assert.equal(detailRequests, 3, "an unchanged index must not refetch a completed call with detail revision zero");

  // An index poll can advance while an older detail request is still pending.
  let releaseDetail!: () => void;
  pendingDetail = new Promise<void>((resolve) => { releaseDetail = resolve; });
  phase = 3;
  await store.refreshNow();
  phase = 4;
  await store.refreshNow();
  assert.equal(detailRequests, 4, "concurrent polls share the pending detail request");
  releaseDetail();
  pendingDetail = null;
  await settle();
  assert.equal(store.__state().byId.c1?.summary.modified_at, 4, "a detail response must not downgrade the latest index summary");

  await store.refreshNow();
  await settle();
  assert.equal(detailRequests, 5, "the revision that arrived during the pending request still needs a refresh");
  await store.refreshNow();
  await settle();
  assert.equal(detailRequests, 5, "the successful refresh acknowledges the new index revision");
});

test("overlapping refreshes share a slow response and recover after a failed refresh", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  const releases: ((response: Response) => void)[] = [];
  let requests = 0;
  globalThis.fetch = async () => {
    requests += 1;
    return new Promise<Response>((resolve) => { releases.push(resolve); });
  };
  const respond = (body: unknown, status = 200) => {
    for (const release of releases.splice(0)) release(Response.json(body, { status }));
  };
  const first = store.refreshNow();
  const second = store.refreshNow();
  respond({ calls: [{ ...detailOf(20, "saved", []).summary, call_id: "slow-refresh" }] });
  await Promise.all([first, second]);
  assert.equal(requests, 1, "slow refreshes must not pile up competing snapshots");
  assert.equal(store.__state().calls[0]?.modified_at, 20);

  const failed = store.refreshNow();
  respond({ detail: "temporarily unavailable" }, 503);
  await failed;
  assert.equal(store.__state().calls[0]?.modified_at, 20, "failed polling preserves the last usable records");
  assert.match(store.__state().error ?? "", /temporarily unavailable/);

  const recovered = store.refreshNow();
  respond({ calls: [{ ...detailOf(21, "saved", []).summary, call_id: "slow-refresh" }] });
  await recovered;
  assert.equal(store.__state().calls[0]?.modified_at, 21);
  assert.equal(store.__state().error, null);
});
