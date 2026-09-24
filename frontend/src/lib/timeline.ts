// The one projection every screen renders: raw JSONL events -> ordered turns,
// each agent turn carrying the decisions (tool calls, staged actions, guards,
// errors) recorded since the previous agent turn. Writes to the clinic database
// (`local_write`) are collected separately: their tool call is already a decision.
// Raw timestamps remain intact; recorded speech endings set transcript replay positions.

import type { CallDetail, ClinicAction, LocalWriteEvent, RawEvent, SubmitEvent, ToolEvent, TranscriptEvent } from "./types.ts";

export type Stage = "GREET" | "IDENTIFY" | "LOOKUP" | "OFFER" | "CONFIRM" | "WRITE" | "CLOSE" | "ESCALATE";

export type DecisionKind = "tool" | "staged" | "fallback" | "guard" | "submit" | "error" | "lookup" | "engine";

export interface Decision {
  key: string;
  kind: DecisionKind;
  /** Mono header: tool name, event kind, verb. */
  label: string;
  t: number;
  /** Seconds on the replay clock. */
  offset: number;
  /** A refusal, guard, error, or result requiring attention. */
  attention: boolean;
  /** Key-value grid, in display order. Values are already stringified. */
  fields: [string, string][];
  raw: RawEvent;
}

export interface Turn {
  key: string;
  role: "agent" | "caller";
  text: string;
  t: number;
  offset: number;
  /** Turn was cut off by the caller (speech started while the agent was talking). */
  interrupted: boolean;
  decisions: Decision[];
}

export interface Marker {
  t: number;
  offset: number;
  kind: "decision" | "submit" | "turn";
  label: string;
}

export interface Timeline {
  startedAt: number;
  endedAt: number | null;
  /** Seconds from start to the last thing that happened (stop, turn or decision), for replay. */
  horizon: number;
  turns: Turn[];
  decisions: Decision[];
  markers: Marker[];
  stage: Stage;
  pending: ClinicAction[];
  /** Writes committed to the clinic database during the call, in order. */
  writes: { t: number; action: ClinicAction; result: Record<string, unknown> | null }[];
  fromNumber: string | null;
  callerIdMatches: string[];
  callerIdName: string | null;
  identified: { patient_id: string; name: string; note?: string; plan?: string } | null;
  matchCount: number | null;
  engine: string | null;
  model: string | null;
  /** Recorded per-call p50 response gap from audio.timeline, in milliseconds. */
  medianResponseGapMs: number | null;
  callerSeconds: number | null;
  agentSeconds: number | null;
}

/** Reason codes are a closed vocabulary; the gloss is the only place they are rephrased. */
export const REASON_GLOSS: Record<string, string> = {
  not_eligible_age: "outside the age range for this service",
  referral_required: "a referral is required first",
  provider_not_in_network: "provider not in the caller's network",
  specialty_not_covered: "specialty not covered by the policy",
  location_not_covered: "site not covered by the policy",
  insurer_referral_required: "insurer requires a referral",
  allowance_exhausted: "policy allowance used up",
  provider_on_leave: "provider on leave",
  location_hours: "outside the site's opening hours",
  type_not_offered: "appointment type not offered there",
  patient_history: "record history does not allow it",
  no_availability: "nothing free in the window",
  clinic_closed: "clinic closed",
  patient_not_found: "no matching patient record",
  provider_not_found: "no such provider",
  caller_not_authorised: "caller not authorised for this record",
  out_of_scope: "outside what the front desk does",
  medical_emergency: "medical emergency, routed to a doctor",
};

export const TOOL_GLOSS: Record<string, string> = {
  find_patient: "looked up the patient record",
  search_availability: "queried real availability",
  record_booking: "recorded a booking",
  record_reschedule: "recorded a reschedule",
  record_cancellation: "recorded a cancellation",
  record_registration: "recorded a new patient",
  validate_registration_details: "validated registration details",
  list_appointments: "looked up existing appointments",
  clear_recorded_actions: "cleared pending actions",
  record_no_action: "recorded no action",
  record_escalation: "recorded an escalation",
};

const NOISE_KINDS: Record<string, true> = {
  vercel_realtime_event: true,
  speech_boundary: true,
  recording: true,
  platform_run: true,
  vercel_realtime_connected: true,
  stop_received: true,
  socket_closed: true,
  call_started: true,
  call_ended: true,
  caller_id_lookup: true,
  voice_engine: true,
};

function str(value: unknown): string {
  if (value == null) return "\u2013";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function actionFields(action: ClinicAction): [string, string][] {
  const fields: [string, string][] = [];
  for (const [key, value] of Object.entries(action)) {
    if (key === "action" || value == null) continue;
    if (key === "new_patient" && typeof value === "object") {
      for (const [k, v] of Object.entries(value as Record<string, unknown>)) fields.push([k, str(v)]);
      continue;
    }
    fields.push([key, str(value)]);
  }
  return fields;
}

function toolFields(event: ToolEvent): [string, string][] {
  const fields: [string, string][] = [];
  for (const [key, value] of Object.entries(event.args ?? {})) fields.push([`args.${key}`, str(value)]);
  const result = event.result as Record<string, unknown> | null | undefined;
  if (result && typeof result === "object") {
    if (event.name === "find_patient") {
      const matches = (result.matches as Record<string, unknown>[] | undefined) ?? [];
      fields.push(["matches", String(result.count ?? matches.length)]);
      for (const m of matches.slice(0, 4)) fields.push([str(m.patient_id), `${str(m.name)} \u00b7 ${str(m.date_of_birth)} \u00b7 ${str(m.plan_on_file)}`]);
    } else if (event.name === "search_availability") {
      fields.push(["slots_found", str(result.slots_found)]);
      const type = result.appointment_type as Record<string, unknown> | undefined;
      if (type) fields.push(["appointment_type", str(type.id)]);
      const earliest = (result.earliest_slots as Record<string, unknown>[] | undefined) ?? [];
      for (const s of earliest.slice(0, 3)) fields.push([str(s.spoken), `${str(s.provider_name)} \u00b7 ${str(s.site)}`]);
      const blocked = (result.blocked as Record<string, unknown>[] | undefined) ?? [];
      for (const b of blocked.slice(0, 3)) fields.push([`blocked ${str(b.reason ?? b.kind)}`, str(b.provider_name ?? b.site ?? b.detail ?? "")]);
    } else if ("recorded" in result) {
      const recorded = result.recorded as ClinicAction;
      fields.push(["recorded", str(recorded.action)]);
      fields.push(...actionFields(recorded).map(([k, v]) => [`recorded.${k}`, v] as [string, string]));
    } else {
      for (const [key, value] of Object.entries(result)) fields.push([`result.${key}`, str(value)]);
    }
  } else if (result != null) {
    fields.push(["result", str(result)]);
  }
  return fields;
}

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function nonnegativeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}

function decoded(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    // Codex detail strings are capped at 600 characters by the logger.
    // A cut-off result is not valid evidence; keep its original Raw-tab entry.
    return null;
  }
}

function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((value, index) => sameValue(value, b[index]));
  const left = object(a);
  const right = object(b);
  if (!left || !right) return false;
  const keys = Object.keys(left);
  return keys.length === Object.keys(right).length && keys.every((key) => Object.hasOwn(right, key) && sameValue(left[key], right[key]));
}

/** Recover actual executions embedded in engine logs without counting their raw tool echo twice. */
function projectionEvents(events: RawEvent[]): { event: RawEvent; raw: RawEvent; key?: string }[] {
  const projected = events.map((event) => ({ event, raw: event, key: undefined as string | undefined }));
  const claimedTools = new Set<RawEvent>();
  const codexItems = new Map<string, { event: RawEvent; raw: RawEvent; key: string | undefined }>();
  let brainStart = 0;
  events.forEach((raw, index) => {
    if (raw.kind === "proxy_brain") {
      const candidates = events.slice(brainStart, index).filter((event) => event.kind === "tool");
      brainStart = index + 1;
      if (!Array.isArray(raw.steps)) return;
      raw.steps.forEach((value, stepIndex) => {
        const step = object(value);
        if (!step || typeof step.tool !== "string") return;
        const args = object(step.arguments) ?? {};
        const duplicate = candidates.find((event) => !claimedTools.has(event) && event.name === step.tool && sameValue(event.args, args) && sameValue(event.result, step.result));
        if (duplicate) {
          claimedTools.add(duplicate);
          return;
        }
        projected.push({
          event: { ...raw, kind: "tool", name: step.tool, args, result: step.result },
          raw,
          key: `proxy-tool-${raw._line ?? index}-${stepIndex}`,
        });
      });
      return;
    }
    if (raw.kind !== "codex" || !["item/started", "item/completed"].includes(String(raw.event))) return;
    const item = object(object(decoded(raw.detail))?.item);
    if (item?.type !== "dynamicToolCall" || typeof item.id !== "string" || typeof item.tool !== "string") return;
    const args = object(item.arguments) ?? {};
    const content = Array.isArray(item.contentItems) ? item.contentItems.map(object).find((part) => part?.type === "inputText" && typeof part.text === "string") : null;
    const result = content ? decoded(content.text) ?? content.text : undefined;
    const previous = codexItems.get(item.id);
    if (previous) {
      if (raw.event === "item/completed" && previous.key) {
        previous.event = { ...previous.event, result, execution_status: item.status };
      }
      return;
    }
    // An invocation's raw result sits between its started/completed wrappers.
    // Claim one echo only; a later identical invocation is a separate decision.
    const candidates: RawEvent[] = [];
    if (raw.event === "item/started") {
      for (let next = index + 1; next < events.length; next++) {
        const candidate = events[next]!;
        if (candidate.kind === "codex" && candidate.event === "item/completed") break;
        if (candidate.kind === "tool") candidates.push(candidate);
      }
    }
    const duplicate = candidates.find((event) => !claimedTools.has(event) && event.name === item.tool && sameValue(event.args, args));
    if (duplicate) {
      claimedTools.add(duplicate);
      codexItems.set(item.id, { event: duplicate, raw: duplicate, key: undefined });
      return;
    }
    const entry = {
      event: { ...raw, kind: "tool", name: item.tool, args, result, execution_status: item.status },
      raw,
      key: `codex-tool-${item.id}`,
    };
    codexItems.set(item.id, entry);
    projected.push(entry);
  });
  return projected.sort((a, b) => a.event.t - b.event.t || (a.event._line ?? 0) - (b.event._line ?? 0));
}

function decisionOf(event: RawEvent, startedAt: number, index: number): Decision | null {
  const base = { key: `${event.kind}-${event._line ?? index}`, t: event.t, offset: event.t - startedAt, raw: event };
  switch (event.kind) {
    case "tool": {
      const tool = event as ToolEvent;
      const result = tool.result as Record<string, unknown> | undefined;
      const blocked = Array.isArray(result?.blocked) && (result.blocked as unknown[]).length > 0;
      const zeroMatches = tool.name === "find_patient" && result?.count === 0;
      const fields = toolFields(tool);
      if (typeof event.execution_status === "string") fields.push(["execution", event.execution_status]);
      return { ...base, kind: "tool", label: tool.name, attention: blocked || zeroMatches || result?.valid === false, fields };
    }
    case "caller_id_lookup":
      return { ...base, kind: "lookup", label: "caller_id_lookup", attention: false, fields: [["matches", str(event.matches ?? [])]] };
    case "action_staged": {
      const action = (event as unknown as { action: ClinicAction }).action;
      return { ...base, kind: "staged", label: `staged ${action.action}`, attention: false, fields: actionFields(action) };
    }
    case "fallback": {
      const action = (event as unknown as { action: ClinicAction }).action;
      const fields = actionFields(action);
      if (action.reason && REASON_GLOSS[action.reason]) fields.push(["gloss", REASON_GLOSS[action.reason] ?? ""]);
      return { ...base, kind: "fallback", label: `fallback ${action.action}`, attention: true, fields };
    }
    case "guard_blocked":
    case "guard": {
      const fields: [string, string][] = Object.entries(event)
        .filter(([k]) => !["t", "kind", "_line"].includes(k))
        .map(([k, v]) => [k, str(v)]);
      return { ...base, kind: "guard", label: "guard blocked", attention: true, fields };
    }
    case "submit": {
      const submit = event as SubmitEvent;
      const fields = actionFields(submit.action);
      fields.unshift(["status", String(submit.status)]);
      if (submit.action.reason) fields.push(["gloss", REASON_GLOSS[submit.action.reason] ?? "reason outside the vocabulary"]);
      return {
        ...base,
        kind: "submit",
        label: `submit ${submit.action.action}`,
        attention: submit.status >= 400 || submit.action.action === "NO_ACTION" || submit.action.action === "ESCALATE",
        fields,
      };
    }
    case "lookup":
      return { ...base, kind: "lookup", label: `lookup ${str(event.path)}`, attention: false, fields: [["path", str(event.path)]] };
    case "proxy_brain":
      return {
        ...base,
        kind: "engine",
        label: "proxy brain",
        attention: false,
        fields: [
          ["request", str(event.request)],
          ["response", str(event.response)],
        ],
      };
    default: {
      if (event.kind.endsWith("_error") || event.kind === "error") {
        const fields: [string, string][] = Object.entries(event)
          .filter(([k]) => !["t", "kind", "_line"].includes(k))
          .map(([k, v]) => [k, str(v)]);
        return { ...base, kind: "error", label: event.kind, attention: true, fields };
      }
      return null;
    }
  }
}

const WRITE_TOOLS: Record<string, true> = { record_booking: true, record_reschedule: true, record_cancellation: true, record_registration: true };

export function project(detail: CallDetail): Timeline {
  const events = [...detail.events].sort((a, b) => a.t - b.t || (a._line ?? 0) - (b._line ?? 0));
  const startedAt = detail.audio?.timeline_origin_at ?? events[0]?.t ?? detail.summary.started_at;
  const turns: Turn[] = [];
  const decisions: Decision[] = [];
  const markers: Marker[] = [];
  let pendingDecisions: Decision[] = [];
  let stage = "GREET" as Stage;
  let endedAt: number | null = null;
  let fromNumber: string | null = null;
  let callerIdMatches: string[] = [];
  let identified: Timeline["identified"] = null;
  let matchCount: number | null = null;
  let engine: string | null = null;
  let model: string | null = null;
  let staged: ClinicAction[] = [];
  const writes: Timeline["writes"] = [];
  let medianResponseGapMs: number | null = null;
  let callerSeconds: number | null = null;
  let agentSeconds: number | null = null;

  projectionEvents(events).forEach(({ event, raw, key }, index) => {
    switch (event.kind) {
      case "call_started":
        fromNumber = typeof event.from_number === "string" ? event.from_number : null;
        return;
      case "caller_id_lookup":
        callerIdMatches = Array.isArray(event.matches) ? (event.matches as string[]) : [];
        break;
      case "voice_engine":
        engine = str(event.engine);
        model = str(event.model);
        return;
      case "transcript": {
        const tr = event as TranscriptEvent;
        const role = tr.role === "agent" ? "agent" : "caller";
        const speechEnd = tr._line == null ? null : nonnegativeNumber(detail.audio?.transcript_end_seconds?.[tr._line]);
        const turn: Turn = { key: `turn-${tr._line ?? index}`, role, text: tr.text, t: tr.t, offset: speechEnd ?? tr.t - startedAt, interrupted: false, decisions: [] };
        if (role === "agent") {
          turn.decisions = pendingDecisions;
          pendingDecisions = [];
          if (stage === "GREET" && turns.length > 0) stage = "IDENTIFY";
        }
        turns.push(turn);
        markers.push({ t: tr.t, offset: turn.offset, kind: "turn", label: role });
        return;
      }
      case "stop_received":
      case "socket_closed":
      case "closed_by_agent":
        if (endedAt == null) endedAt = event.t;
        if (stage !== "ESCALATE") stage = "CLOSE";
        return;
      case "call_ended":
        endedAt = endedAt ?? event.t;
        return;
      case "local_write": {
        const write = event as LocalWriteEvent;
        if (write.action && typeof write.action === "object") writes.push({ t: write.t, action: write.action, result: object(write.result) });
        return;
      }
      case "audio.timeline": {
        const seconds = nonnegativeNumber(object(event.turns)?.latency_p50_s);
        medianResponseGapMs = seconds == null ? null : nonnegativeNumber(seconds * 1000);
        callerSeconds = nonnegativeNumber(object(event.caller)?.talk_s);
        agentSeconds = nonnegativeNumber(object(event.agent)?.talk_s);
        return;
      }
      default:
        break;
    }

    const decision = decisionOf(event, startedAt, index);
    if (!decision) return;
    decision.raw = raw;
    if (key) decision.key = key;
    decisions.push(decision);
    pendingDecisions.push(decision);
    markers.push({ t: decision.t, offset: decision.offset, kind: decision.kind === "submit" ? "submit" : "decision", label: decision.label });

    if (decision.kind === "tool") {
      const tool = event as ToolEvent;
      const result = tool.result as Record<string, unknown> | undefined;
      if (tool.name === "find_patient") {
        stage = "LOOKUP";
        if (Array.isArray(result?.matches)) {
          const matches = result.matches as Record<string, unknown>[];
          matchCount = typeof result.count === "number" ? result.count : matches.length;
          const first = matches[0];
          if (matches.length === 1 && first) {
            identified = { patient_id: str(first.patient_id), name: str(first.name) };
            if (typeof first.note === "string") identified.note = first.note;
            if (typeof first.plan_on_file === "string") identified.plan = first.plan_on_file;
          }
        }
      } else if (tool.name === "search_availability") {
        stage = "OFFER";
      } else if (tool.name === "record_registration") {
        stage = "WRITE";
        const patient = object(result?.patient);
        const patientId = patient && str(patient.patient_id);
        const name = patient && [patient.given_name, patient.first_surname, patient.second_surname].map(str).filter(Boolean).join(" ");
        if (result?.persisted === true && patientId && name) {
          identified = { patient_id: patientId, name, plan: str(patient.insurer), note: str(patient.note) };
          matchCount = 1;
        }
      } else if (tool.name in WRITE_TOOLS) {
        stage = "WRITE";
      } else if (tool.name === "validate_registration_details") {
        stage = "IDENTIFY";
      }
    } else if (decision.kind === "staged") {
      staged = (event as unknown as { all_staged?: ClinicAction[] }).all_staged ?? [(event as unknown as { action: ClinicAction }).action];
      stage = "CONFIRM";
    } else if (decision.kind === "submit") {
      // Legacy logs only: the old platform submission closed the call.
      if ((event as SubmitEvent).action.action === "ESCALATE") stage = "ESCALATE";
      staged = [];
    } else if (decision.kind === "fallback") {
      const action = (event as unknown as { action: ClinicAction }).action;
      if (action.action === "ESCALATE") stage = "ESCALATE";
    }
  });

  // Decisions after the last utterance. On a finished call (real stop in the
  // log) they hang off a closing pseudo-turn; on an active call they belong to
  // the agent turn still being produced, so they attach to a placeholder that
  // renders as "working" rather than "call ended".
  if (pendingDecisions.length > 0) {
    const last = pendingDecisions[pendingDecisions.length - 1];
    if (last) turns.push({ key: endedAt != null ? "turn-close" : "turn-open", role: "agent", text: "", t: last.t, offset: last.offset, interrupted: false, decisions: pendingDecisions });
  }

  const lastT = Math.max(endedAt ?? startedAt, turns[turns.length - 1]?.t ?? startedAt, decisions[decisions.length - 1]?.t ?? startedAt);
  turns.sort((a, b) => a.offset - b.offset);
  markers.sort((a, b) => a.offset - b.offset);
  return {
    startedAt,
    endedAt,
    horizon: Math.max(lastT - startedAt, turns.at(-1)?.offset ?? 0),
    turns,
    decisions,
    markers,
    stage,
    pending: staged,
    writes,
    fromNumber,
    callerIdMatches,
    callerIdName: detail.caller_id?.source === "caller_id" && callerIdMatches.length === 1 && callerIdMatches[0] === detail.caller_id.patient_id ? detail.caller_id.name : null,
    identified,
    matchCount,
    engine,
    model,
    medianResponseGapMs,
    callerSeconds,
    agentSeconds,
  };
}

/** Display names may use caller ID; only lookup events populate `identified`. */
export function callerLabel(timeline: Timeline | null): string {
  if (!timeline) return "connecting";
  if (timeline.identified) return timeline.identified.name;
  const registered = timeline.writes.find((write) => write.action.action === "REGISTER" && savedWrite(write))?.action;
  if (registered) {
    const name = [registered.given_name, registered.first_surname, registered.second_surname].filter(Boolean).join(" ");
    if (name) return name;
  }
  if (timeline.matchCount != null && timeline.matchCount > 1) return `${timeline.matchCount} matches`;
  if (timeline.matchCount === 0) return "not in records";
  if (timeline.callerIdName) return timeline.callerIdName;
  return timeline.endedAt == null && (timeline.stage === "GREET" || timeline.stage === "IDENTIFY") ? "identifying" : "unknown caller";
}

/** The raw log minus the transport chatter, for the Raw tab's default filter. */
export function isNoise(event: RawEvent): boolean {
  return event.kind in NOISE_KINDS;
}

/** The verbs in a summary's action column: "REGISTER+BOOK" -> ["REGISTER", "BOOK"]. */
export function actionVerbs(action: string): string[] {
  return action.split("+").map((verb) => verb.trim()).filter((verb) => /^[A-Z_]+$/.test(verb));
}

/** A write the clinic database accepted: it returned a record, not an error. */
export function savedWrite(write: { result: unknown }): boolean {
  const result = object(write.result);
  return result != null && result.error == null;
}

/** Outcome verb for a call: the last verb saved to the clinic database, else what the summary reports. */
export function outcomeOf(detail: CallDetail | null, summary: { action: string; status: string }): { verb: string; reason: string | null; failed: boolean } {
  const failed = summary.status === "write failed";
  const saved = (detail?.writes ?? []).filter(savedWrite).map((write) => String(write.action?.action ?? "")).filter(Boolean);
  // The backend writes U+2014 as the action of a call with nothing staged.
  const verb = saved.at(-1) ?? actionVerbs(summary.action).at(-1) ?? (summary.status === "in progress" ? "in progress" : "Ended");
  const staged = detail?.staged_actions.findLast((event) => event.action?.action === verb);
  return { verb, reason: typeof staged?.action.reason === "string" ? staged.action.reason : null, failed };
}
