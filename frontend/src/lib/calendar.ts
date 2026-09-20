import type { CallDetail, ClinicAction, SubmitEvent } from "./types.ts";

export type SchedulingKind = "BOOK" | "RESCHEDULE" | "CANCEL";

/** An accepted report, never proof that the read-only clinic diary changed. */
export interface SchedulingRecord {
  id: string;
  callId: string;
  kind: SchedulingKind;
  recordedAt: number;
  slot: string | null;
  previousSlot: string | null;
  day: string | null;
  patient: string;
  patientId: string | null;
  caller: string | null;
  provider: string | null;
  site: string | null;
  appointmentId: string | null;
  supersededBy: SchedulingKind | null;
  practice: boolean;
  persisted?: boolean;
  /** Set by the console server: "local" is a booking saved on this host, "prosper" an action Prosper accepted. */
  source?: "local" | "prosper";
  /** False when the source call was served from another host, so this console holds no log for it. */
  callLogged?: boolean;
}

export interface CalendarSources {
  local: number;
  prosper: { ok: boolean; count: number; detail: string | null } | null;
}

const madridDate = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" });

export function calendarDay(date: Date): string {
  const parts = madridDate.formatToParts(date);
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function object(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function objects(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row ? [row] : []; }) : [];
}

function validSlot(value: unknown): string | null {
  const slot = text(value);
  // A clinic slot requires an explicit offset. Never interpret it in the visitor's timezone.
  return slot && /T\d{2}:\d{2}.*(?:Z|[+-]\d{2}:\d{2})$/.test(slot) && Number.isFinite(Date.parse(slot)) ? slot : null;
}

function schedulingKind(action: ClinicAction): SchedulingKind | null {
  return action.action === "BOOK" || action.action === "RESCHEDULE" || action.action === "CANCEL" ? action.action : null;
}

/** Reconcile only within a call. Separate practice calls report independent scenarios,
 * even when they mention the same patient, slot, or static appointment ID. */
export function schedulingRecords(details: readonly CallDetail[]): SchedulingRecord[] {
  const records: SchedulingRecord[] = [];
  for (const detail of details) {
    const seen = new Set<string>();
    const appointmentRecords = new Map<string, SchedulingRecord>();
    const submissions = detail.submissions
      .filter((event) => event.status >= 200 && event.status < 300 && schedulingKind(event.action))
      .toSorted((a, b) => a.t - b.t || (a._line ?? 0) - (b._line ?? 0));
    for (const [index, submission] of submissions.entries()) {
      const action = submission.action;
      const key = JSON.stringify([action.action, action.appointment_id, action.patient_id, action.provider_id, action.location_id, action.appointment_type_id, action.slot, action.policy_id]);
      if (seen.has(key)) continue;
      seen.add(key);
      const record = projectSubmission(detail, submission, index);
      if (!record) continue;
      const previous = record.appointmentId ? appointmentRecords.get(record.appointmentId) : undefined;
      if (previous && record.kind !== "BOOK") {
        previous.supersededBy = record.kind;
        record.previousSlot = previous.slot ?? record.previousSlot;
        if (!record.patientId && previous.patientId) {
          record.patientId = previous.patientId;
          record.patient = previous.patient;
        }
        if (record.kind === "CANCEL") {
          record.slot = previous.slot ?? record.slot;
          record.day = record.slot ? calendarDay(new Date(record.slot)) : null;
          record.provider = previous.provider ?? record.provider;
          record.site = previous.site ?? record.site;
        }
      }
      if (record.appointmentId) appointmentRecords.set(record.appointmentId, record);
      records.push(record);
    }
  }
  return records.toSorted((a, b) => (a.slot ? Date.parse(a.slot) : 0) - (b.slot ? Date.parse(b.slot) : 0) || a.recordedAt - b.recordedAt);
}

function projectSubmission(detail: CallDetail, submission: SubmitEvent, index: number): SchedulingRecord | null {
  const action = submission.action;
  const kind = schedulingKind(action);
  if (!kind) return null;
  const appointmentId = text(action.appointment_id);
  const tools = detail.tools.filter((tool) => tool.t <= submission.t);
  const appointments = tools.filter((tool) => tool.name === "list_appointments")
    .flatMap((tool) => objects(object(tool.result)?.appointments));
  const appointment = appointmentId ? appointments.findLast((row) => row.appointment_id === appointmentId) : undefined;
  const patientId = text(action.patient_id) ?? text(appointment?.patient_id);
  const patients = tools.filter((tool) => tool.name === "find_patient")
    .flatMap((tool) => objects(object(tool.result)?.matches));
  const patient = patientId ? patients.findLast((row) => row.patient_id === patientId) : undefined;
  const slot = kind === "CANCEL" ? validSlot(appointment?.start_time) : validSlot(action.slot);
  const providerId = text(action.provider_id) ?? text(appointment?.provider_id);
  const locationId = text(action.location_id) ?? text(appointment?.location_id);
  const slots = tools.filter((tool) => tool.name === "search_availability")
    .flatMap((tool) => objects(object(tool.result)?.earliest_slots));
  const matchingSlot = slots.findLast((row) => row.provider_id === providerId && row.location_id === locationId && row.slot === slot);
  // A reschedule can change provider/site. Never borrow the old appointment's names for new IDs.
  const provider = text(matchingSlot?.provider_name) ?? (appointment?.provider_id === providerId ? text(appointment?.provider_name) : null) ?? providerId;
  const site = text(matchingSlot?.site) ?? (appointment?.location_id === locationId ? text(appointment?.site) : null) ?? locationId;
  const started = detail.events.find((event) => event.kind === "call_started");
  return {
    id: `${detail.call_id}:${submission._line ?? index}`,
    callId: detail.call_id,
    kind,
    recordedAt: submission.t,
    slot,
    previousSlot: kind === "RESCHEDULE" ? validSlot(appointment?.start_time) : null,
    day: slot ? calendarDay(new Date(slot)) : null,
    patient: text(patient?.name) ?? patientId ?? "Patient not identified in record",
    patientId,
    caller: text(started?.from_number),
    provider,
    site,
    appointmentId,
    supersededBy: null,
    practice: detail.run?.mode === "practice",
  };
}
