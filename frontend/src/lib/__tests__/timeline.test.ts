// Regression: lifecycle labels are event-backed. Run with `pnpm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { actionVerbs, callerLabel, outcomeOf, project } from "../timeline.ts";
import { turnsUntil } from "../replay.ts";
import type { CallDetail, RawEvent } from "../types.ts";

function detail(events: RawEvent[], writes: CallDetail["writes"] = []): CallDetail {
  const summary = {
    call_id: "c1",
    started_at: 100,
    modified_at: 0,
    modified_iso: null,
    status: "in progress",
    action: String.fromCodePoint(0x2014),
    duration_seconds: null,
    warnings: 0,
    has_audio: false,
    run: null,
  };
  return { call_id: "c1", summary, run: null, warnings: [], audio: null, transcript: [], tools: [], staged_actions: [], writes, errors: [], provenance: [], events };
}

const base: RawEvent[] = [
  { t: 100, kind: "call_started", from_number: "+34711330529", _line: 1 },
  { t: 101, kind: "transcript", role: "agent", text: "Clínica Arenal, good morning.", _line: 2 },
  { t: 102, kind: "speech_boundary", role: "user", state: "started", _line: 3 },
  { t: 104, kind: "speech_boundary", role: "user", state: "stopped", _line: 4 },
  { t: 104.2, kind: "transcript", role: "user", text: "Hello, I need an appointment.", _line: 5 },
  { t: 105, kind: "transcript", role: "agent", text: "One moment while I check.", _line: 6 },
];

test("caller ID supplies a display name without claiming a patient lookup", () => {
  const events = [...base, { t: 100.5, kind: "caller_id_lookup", matches: ["P1"], _line: 7 }, { t: 110, kind: "stop_received", _line: 8 }];
  const call = { ...detail(events), caller_id: { patient_id: "P1", name: "Ana García López", source: "caller_id" as const } };
  const timeline = project(call);
  assert.equal(callerLabel(timeline), "Ana García López");
  assert.equal(timeline.identified, null);
  assert.equal(timeline.matchCount, null);
  assert.equal(callerLabel(project({ ...call, caller_id: { ...call.caller_id, patient_id: "P2" } })), "unknown caller");
  assert.equal(callerLabel(project(detail(events))), "unknown caller");
  assert.equal(callerLabel(project(detail([...base, { t: 110, kind: "call_ended", _line: 8 }]))), "unknown caller");
  const patient = { t: 108, kind: "tool", name: "find_patient", args: {}, result: { matches: [{ patient_id: "P2", name: "Juan López" }], count: 1 }, _line: 9 };
  assert.equal(callerLabel(project({ ...call, events: [...events, patient] })), "Juan López");
});

test("a saved registration supplies the name after an empty lookup", () => {
  const events = [...base,
    { t: 107, kind: "tool", name: "find_patient", args: {}, result: { matches: [], count: 0 }, _line: 7 },
    { t: 109, kind: "local_write", action: { action: "REGISTER", given_name: "Ana", first_surname: "García", second_surname: "López" }, result: { patient_id: "LP1" }, _line: 8 },
    { t: 110, kind: "call_ended", _line: 9 },
  ];
  assert.equal(callerLabel(project(detail(events))), "Ana García López");
  assert.equal(callerLabel(project(detail(events.map((e) => e.kind === "local_write" ? { ...e, result: { error: "Not saved" } } : e)))), "not in records");
});

test("a persisted local registration identifies the caller before any other write", () => {
  const registration = {
    t: 107, kind: "tool", name: "record_registration", args: {}, _line: 8,
    result: { persisted: true, patient: { patient_id: "LP1", given_name: "Ana", first_surname: "García", second_surname: "López", insurer: "privado", note: "" } },
  };
  const events = [...base,
    { t: 106, kind: "tool", name: "find_patient", args: {}, result: { matches: [], count: 0 }, _line: 7 },
    registration,
    { t: 109, kind: "call_ended", _line: 9 },
  ];
  const timeline = project(detail(events));
  assert.equal(timeline.identified?.name, "Ana García López");
  assert.equal(timeline.identified?.patient_id, "LP1");
  assert.equal(timeline.matchCount, 1);
  assert.equal(timeline.writes.length, 0);
  const correction = { ...registration, t: 108, _line: 10, result: { ...registration.result, patient: { ...registration.result.patient, given_name: "María" } } };
  assert.equal(project(detail([...events, correction])).identified?.name, "María García López");
  assert.equal(project(detail([...base, { ...registration, result: { error: "Not saved" } }])).identified, null);
  assert.equal(project(detail([...base, { ...registration, result: { ...registration.result, persisted: false } }])).identified, null);
});

test("a finished call without an action is not labelled in progress", () => {
  for (const action of ["", String.fromCodePoint(0x2014)]) {
    assert.equal(outcomeOf(null, { status: "in progress", action }).verb, "in progress");
    assert.equal(outcomeOf(null, { status: "ended", action }).verb, "Ended");
  }
});

test("every hang-up event stops the live indicator and elapsed clock", () => {
  for (const kind of ["stop_received", "socket_closed", "closed_by_agent", "call_ended"]) {
    const timeline = project(detail([...base, { t: 107, kind, _line: 7 }]));
    assert.equal(timeline.endedAt, 107, kind);
  }
});

test("an ordinary caller reply does not mark the agent turn as cut off", () => {
  const tl = project(detail(base));
  assert.equal(
    tl.turns.every((t) => !t.interrupted),
    true,
  );
});

test("a tool call after the last utterance on an active call renders as working, not call ended", () => {
  const tl = project(detail([...base, { t: 106, kind: "tool", name: "find_patient", args: {}, result: { matches: [], count: 0 }, _line: 7 }]));
  const last = tl.turns[tl.turns.length - 1];
  assert.equal(last?.key, "turn-open");
  assert.equal(last?.decisions[0]?.label, "find_patient");
  assert.equal(tl.endedAt, null);
});

test("a legacy submission after a real stop attaches to a closing turn", () => {
  const submit = { t: 130, kind: "submit" as const, action: { action: "NO_ACTION", reason: "out_of_scope" }, status: 200, response: {}, _line: 9 };
  const tl = project(detail([...base, { t: 120, kind: "stop_received", _line: 8 }, submit]));
  const last = tl.turns[tl.turns.length - 1];
  assert.equal(last?.key, "turn-close");
  assert.equal(tl.endedAt, 120);
  assert.equal(tl.stage, "CLOSE");
  assert.deepEqual(last?.decisions.map((d) => d.label), ["submit NO_ACTION"]);
});

test("recorded response medians preserve zero and missing values without changing the recording clock", () => {
  const report: RawEvent = { t: 107, kind: "audio.timeline", turns: { responses: 5, latency_p50_s: 6.46 }, caller: { talk_s: 10.2 }, agent: { talk_s: 20.3 }, _line: 8 };
  const recording = detail([...base, { t: 106, kind: "tool", name: "find_patient", args: {}, result: { matches: [], count: 0 }, _line: 7 }, report]);
  recording.summary.has_audio = true;
  recording.audio = {
    url: "/api/calls/c1/audio", channels: 2, sample_rate: 48000, sample_width: null,
    frames: 480000, duration_seconds: 10, timeline_clock: "monotonic",
    timeline_origin_at: 98, caller_carrier_drift_seconds: null,
  };
  const timeline = project(recording);
  assert.equal(timeline.medianResponseGapMs, 6460);
  assert.equal(timeline.callerSeconds, 10.2);
  assert.equal(timeline.agentSeconds, 20.3);
  assert.equal(report.t, 107);
  assert.equal(timeline.turns[0]?.offset, 3);
  assert.equal(timeline.turns[0]?.t, 101);
  assert.equal(timeline.decisions[0]?.offset, 8);
  assert.equal(timeline.markers[0]?.offset, 3);
  assert.equal(timeline.horizon, 8);
  for (const [value, expected] of [[0, 0], [null, null], [undefined, null], [-1, null], [NaN, null], [Infinity, null], ["6.46", null]] as const) {
    report.turns = { latency_p50_s: value };
    assert.equal(project(recording).medianResponseGapMs, expected);
  }
  assert.equal(project(detail(base)).medianResponseGapMs, null);
});

test("recorded messages appear at speech end even when publication order differs, and seeking back hides them", () => {
  const recording = detail([
    { t: 100, kind: "call_started", _line: 1 },
    { t: 105, kind: "transcript", role: "agent", text: "I can help.", _line: 2 },
    { t: 106, kind: "transcript", role: "user", text: "Hello.", _line: 3 },
  ]);
  recording.audio = {
    url: "/api/calls/c1/audio", channels: 2, sample_rate: 8000, sample_width: 2,
    frames: 48000, duration_seconds: 6, timeline_clock: "wire_monotonic",
    timeline_origin_at: 100, caller_carrier_drift_seconds: null,
    transcript_end_seconds: { "2": 4, "3": 2 },
  };
  const timeline = project(recording);
  assert.deepEqual(turnsUntil(timeline, 1.99).map((turn) => turn.text), []);
  assert.deepEqual(turnsUntil(timeline, 2).map((turn) => turn.text), ["Hello."]);
  assert.deepEqual(turnsUntil(timeline, 4).map((turn) => turn.text), ["Hello.", "I can help."]);
  assert.deepEqual(turnsUntil(timeline, 1).map((turn) => turn.text), []);
  assert.equal(timeline.horizon, 6);
  assert.deepEqual(recording.events.map((event) => event.t), [100, 105, 106]);
  recording.events = [{ t: 103, kind: "transcript", role: "agent", text: "I can help.", _line: 2 }];
  const earlyPublication = project(recording);
  assert.equal(earlyPublication.horizon, 4);
  assert.deepEqual(turnsUntil(earlyPublication, earlyPublication.horizon).map((turn) => turn.text), ["I can help."]);
});

test("a submission 14s after hangup extends the replay horizon past the socket stop", () => {
  const submit = { t: 134, kind: "submit" as const, action: { action: "BOOK", patient_id: "P00001" }, status: 200, response: {}, _line: 9 };
  const tl = project(detail([...base, { t: 120, kind: "stop_received", _line: 8 }, submit]));
  assert.equal(tl.endedAt, 120);
  assert.equal(tl.horizon, 34);
  assert.equal(tl.turns[tl.turns.length - 1]?.offset, 34);
});

test("caller-number lookup remains a visible decision even without a recording or tool result", () => {
  const lookup: RawEvent = { t: 100.2, kind: "caller_id_lookup", matches: ["P00001"], _line: 2 };
  const timeline = project(detail([base[0]!, lookup]));
  assert.deepEqual(timeline.decisions.map((decision) => [decision.label, decision.fields]), [["caller_id_lookup", [["matches", '["P00001"]']]]]);
  assert.equal(timeline.markers[0]?.kind, "decision");
  assert.equal(timeline.decisions[0]?.raw, lookup);
  assert.equal(timeline.identified, null);
});

test("legacy brain steps retain distinct executions and remove only their matching raw tool echoes", () => {
  const args = { patient_id: "P00001", when: "upcoming" };
  const result = { appointments: [] };
  const raw: RawEvent = { t: 106, kind: "tool", name: "list_appointments", args, result, _line: 7 };
  const brain: RawEvent = { t: 107, kind: "proxy_brain", request: "Check appointments", response: "No appointments", steps: [
    { tool: "list_appointments", arguments: args, result },
    { tool: "list_appointments", arguments: args, result },
  ], _line: 8 };
  const timeline = project(detail([...base, raw, brain]));
  const tools = timeline.decisions.filter((decision) => decision.kind === "tool");
  assert.deepEqual(tools.map((decision) => decision.label), ["list_appointments", "list_appointments"]);
  assert.deepEqual(tools.map((decision) => decision.offset), [6, 7]);
  assert.equal(tools[1]?.raw, brain);
  assert.equal(timeline.turns.at(-1)?.decisions.filter((decision) => decision.kind === "tool").length, 2);
});

test("Codex invocation IDs keep repeated calls separate while started, completed, and raw echoes describe one execution", () => {
  const args = { patient_id: "P00001", when: "upcoming" };
  const result = { appointments: [] };
  const started: RawEvent = { t: 106, kind: "codex", event: "item/started", detail: JSON.stringify({ item: { type: "dynamicToolCall", id: "exec-1", tool: "list_appointments", arguments: args, status: "inProgress", contentItems: null } }), _line: 7 };
  const raw: RawEvent = { t: 106.2, kind: "tool", name: "list_appointments", args, result, _line: 8 };
  const completed: RawEvent = { t: 106.3, kind: "codex", event: "item/completed", detail: JSON.stringify({ item: { type: "dynamicToolCall", id: "exec-1", tool: "list_appointments", arguments: args, status: "completed", contentItems: [{ type: "inputText", text: JSON.stringify(result) }] } }), _line: 9 };
  const second: RawEvent = { ...started, t: 108, _line: 10, detail: JSON.stringify({ item: { type: "dynamicToolCall", id: "exec-2", tool: "list_appointments", arguments: args, status: "inProgress", contentItems: null } }) };
  const truncated: RawEvent = { ...completed, t: 109, _line: 11, detail: '{"item":{"type":"dynamicToolCall","id":"exec-2","contentItems":[' };
  const tools = project(detail([...base, started, raw, completed, second, truncated])).decisions.filter((decision) => decision.kind === "tool");
  assert.deepEqual(tools.map((decision) => decision.t), [106.2, 108]);
  assert.equal(tools[0]?.raw, raw);
  assert.equal(tools[1]?.raw, second);
  assert.deepEqual(tools[1]?.fields, [["args.patient_id", "P00001"], ["args.when", "upcoming"], ["execution", "inProgress"]]);
});

test("local writes are collected in order, apart from the decisions", () => {
  const register = { t: 107, kind: "local_write" as const, action: { action: "REGISTER", given_name: "Ana", first_surname: "Gil" }, result: { patient_id: "LP1", patient: { patient_id: "LP1" } }, _line: 7 };
  const book = { t: 110, kind: "local_write" as const, action: { action: "BOOK", patient_id: "LP1" }, result: { appointment_id: "LA1", patient_id: "LP1", appointment: { status: "booked" } }, _line: 8 };
  const tl = project(detail([...base, register, book], [register, book]));
  assert.deepEqual(tl.writes.map((write) => write.action.action), ["REGISTER", "BOOK"]);
  assert.equal(tl.writes[1]?.result?.appointment_id, "LA1");
  // The write itself is not a second decision next to its tool call.
  assert.equal(tl.decisions.length, 0);
});

test("call status and action map to one outcome", () => {
  const summary = (status: string, action: string) => ({ status, action });
  assert.deepEqual(actionVerbs("REGISTER+BOOK"), ["REGISTER", "BOOK"]);
  assert.deepEqual(actionVerbs(String.fromCodePoint(0x2014)), []);
  assert.deepEqual(outcomeOf(null, summary("saved", "REGISTER+BOOK")), { verb: "BOOK", reason: null, failed: false });
  assert.deepEqual(outcomeOf(null, summary("saved", "BOOK+CANCEL")), { verb: "CANCEL", reason: null, failed: false });
  assert.deepEqual(outcomeOf(null, summary("write failed", "BOOK")), { verb: "BOOK", reason: null, failed: true });
  assert.equal(outcomeOf(null, summary("in progress", "")).verb, "in progress");
  assert.equal(outcomeOf(null, summary("ended", String.fromCodePoint(0x2014))).verb, "Ended");

  // With the detail loaded, the last successful write wins and a staged refusal keeps its reason.
  const writes = [
    { t: 1, kind: "local_write" as const, action: { action: "BOOK" }, result: { appointment_id: "LA1" } },
    { t: 2, kind: "local_write" as const, action: { action: "RESCHEDULE" }, result: { error: "slot taken" } },
  ];
  assert.equal(outcomeOf(detail([], writes), summary("saved", "BOOK+RESCHEDULE")).verb, "BOOK");
  const refused = detail([]);
  refused.staged_actions = [{ t: 3, kind: "action_staged", action: { action: "NO_ACTION", reason: "referral_required" }, all_staged: [] }];
  assert.deepEqual(outcomeOf(refused, summary("ended", "NO_ACTION")), { verb: "NO_ACTION", reason: "referral_required", failed: false });
});
