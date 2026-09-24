// The clinic diary as the console reads it: GET /api/clinic/calendar?from=&to=
// returns one window of the clinic database (every appointment, who is away,
// which sites are closed). Parsing is tolerant: a missing field becomes null,
// never a crash, and a slot without an explicit offset is not trusted.

export interface DiaryRecord {
  id: string;
  appointmentId: string | null;
  /** The call that made or last changed this appointment; null for the seeded diary. */
  callId: string | null;
  kind: "BOOK" | "CANCEL";
  status: "booked" | "cancelled";
  /** "call" when Rosario wrote it on a call, "diary" for the clinic's own bookings. */
  source: "call" | "diary";
  recordedAt: number | null;
  slot: string | null;
  end: string | null;
  /** Epoch milliseconds of `slot` and `end`, for sorting and labels. */
  startMs: number | null;
  endMs: number | null;
  day: string | null;
  durationMinutes: number | null;
  patient: string;
  patientId: string | null;
  provider: string | null;
  providerId: string | null;
  specialtyId: string | null;
  site: string | null;
  locationId: string | null;
  appointmentType: string | null;
  /** False when the call log lives on another host, so there is nothing to open here. */
  callLogged: boolean;
}

export interface DiaryProvider {
  id: string;
  name: string;
  specialtyId: string | null;
  specialtyName: string | null;
}

export interface DiaryLocation {
  id: string;
  name: string;
}

/** Inclusive date range; both times null means whole days. */
export interface DiaryAbsence {
  providerId: string;
  start: string;
  end: string;
  startTime: string | null;
  endTime: string | null;
  reason: string;
}

/** `locationId` null closes every site that day. */
export interface DiaryClosure {
  date: string;
  locationId: string | null;
  name: string;
}

export interface CalendarFeed {
  from: string;
  to: string;
  providers: DiaryProvider[];
  locations: DiaryLocation[];
  absences: DiaryAbsence[];
  closures: DiaryClosure[];
  records: DiaryRecord[];
}

export interface DiaryFilter {
  providerId: string;
  locationId: string;
  rosarioOnly: boolean;
}

const madridDate = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" });
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const TIME = /^\d{2}:\d{2}$/;

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

function date(value: unknown): string | null {
  const day = text(value);
  return day && DATE.test(day) ? day : null;
}

function time(value: unknown): string | null {
  const clock = text(value);
  return clock && TIME.test(clock) ? clock : null;
}

function validSlot(value: unknown): string | null {
  const slot = text(value);
  // A clinic slot requires an explicit offset. Never interpret it in the visitor's timezone.
  return slot && /T\d{2}:\d{2}.*(?:Z|[+-]\d{2}:\d{2})$/.test(slot) && Number.isFinite(Date.parse(slot)) ? slot : null;
}

function positive(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : null;
}

function parseRecord(row: Record<string, unknown>, providers: DiaryProvider[], locations: DiaryLocation[]): DiaryRecord | null {
  const appointmentId = text(row.appointmentId);
  const id = text(row.id) ?? appointmentId;
  if (!id) return null;
  const slot = validSlot(row.slot);
  const startMs = slot ? Date.parse(slot) : null;
  const durationMinutes = positive(row.durationMinutes);
  const end = validSlot(row.end);
  const endMs = end ? Date.parse(end) : startMs != null && durationMinutes != null ? startMs + durationMinutes * 60_000 : null;
  const cancelled = row.status === "cancelled" || (row.status == null && row.kind === "CANCEL");
  const callId = text(row.callId);
  const provider = text(row.provider);
  const site = text(row.site);
  return {
    id,
    appointmentId,
    callId,
    kind: cancelled ? "CANCEL" : "BOOK",
    status: cancelled ? "cancelled" : "booked",
    source: row.source === "call" || (row.source !== "diary" && callId) ? "call" : "diary",
    recordedAt: typeof row.recordedAt === "number" && Number.isFinite(row.recordedAt) ? row.recordedAt : null,
    slot,
    end,
    startMs,
    endMs,
    day: date(row.day) ?? (slot ? calendarDay(new Date(slot)) : null),
    durationMinutes,
    patient: text(row.patient) ?? text(row.patientId) ?? "Patient not recorded",
    patientId: text(row.patientId),
    provider,
    providerId: text(row.providerId) ?? providers.find((item) => item.name === provider)?.id ?? null,
    specialtyId: text(row.specialtyId),
    site,
    locationId: text(row.locationId) ?? locations.find((item) => item.name === site || item.id === site)?.id ?? null,
    appointmentType: text(row.appointmentType),
    callLogged: row.callLogged !== false,
  };
}

/** Sort key: start time, then doctor, then patient, so one hour reads the same on every poll. */
function compareRecords(a: DiaryRecord, b: DiaryRecord): number {
  return (a.startMs ?? 0) - (b.startMs ?? 0)
    || (a.provider ?? "").localeCompare(b.provider ?? "")
    || a.patient.localeCompare(b.patient)
    || a.id.localeCompare(b.id);
}

export function parseCalendarFeed(raw: unknown): CalendarFeed {
  const body = object(raw) ?? {};
  const providers = objects(body.providers).flatMap((row) => {
    const id = text(row.id);
    return id ? [{ id, name: text(row.name) ?? id, specialtyId: text(row.specialtyId), specialtyName: text(row.specialtyName) }] : [];
  });
  const locations = objects(body.locations).flatMap((row) => {
    const id = text(row.id);
    return id ? [{ id, name: text(row.name) ?? id }] : [];
  });
  const records = objects(body.records).flatMap((row) => {
    const record = parseRecord(row, providers, locations);
    return record ? [record] : [];
  }).sort(compareRecords);
  // An older server without the directory lists: rebuild them from the rows.
  if (providers.length === 0) {
    for (const record of records) {
      if (record.providerId && !providers.some((item) => item.id === record.providerId)) {
        providers.push({ id: record.providerId, name: record.provider ?? record.providerId, specialtyId: record.specialtyId, specialtyName: null });
      }
    }
  }
  if (locations.length === 0) {
    for (const record of records) {
      const id = record.locationId ?? record.site;
      if (id && !locations.some((item) => item.id === id)) locations.push({ id, name: record.site ?? id });
      if (!record.locationId) record.locationId = id;
    }
  }
  providers.sort((a, b) => a.name.localeCompare(b.name));
  const absences = objects(body.absences).flatMap((row) => {
    const providerId = text(row.providerId);
    const start = date(row.start);
    const end = date(row.end) ?? start;
    return providerId && start && end ? [{ providerId, start, end, startTime: time(row.startTime), endTime: time(row.endTime), reason: text(row.reason) ?? "away" }] : [];
  });
  const closures = objects(body.closures).flatMap((row) => {
    const day = date(row.date);
    return day ? [{ date: day, locationId: text(row.locationId), name: text(row.name) ?? "Closed" }] : [];
  });
  return { from: date(body.from) ?? "", to: date(body.to) ?? "", providers, locations, absences, closures, records };
}

/** Monday-first weeks that cover a month (`YYYY-MM`), 35 or 42 dates. */
export function monthGrid(month: string): string[] {
  const first = new Date(`${month}-01T12:00:00Z`);
  const offset = (first.getUTCDay() + 6) % 7;
  const last = new Date(first);
  last.setUTCMonth(last.getUTCMonth() + 1, 0);
  const count = Math.ceil((offset + last.getUTCDate()) / 7) * 7;
  return Array.from({ length: count }, (_, index) => {
    const day = new Date(first);
    day.setUTCDate(index - offset + 1);
    return day.toISOString().slice(0, 10);
  });
}

/** The feed window for a month view: every date the grid shows, at most 42 days. */
export function monthWindow(month: string): { from: string; to: string } {
  const days = monthGrid(month);
  return { from: days[0] ?? `${month}-01`, to: days.at(-1) ?? `${month}-28` };
}

export function shiftDay(day: string, days: number): string {
  const next = new Date(`${day}T12:00:00Z`);
  next.setUTCDate(next.getUTCDate() + days);
  return next.toISOString().slice(0, 10);
}

export function filterRecords(records: readonly DiaryRecord[], filter: DiaryFilter): DiaryRecord[] {
  return records.filter((record) => (!filter.providerId || record.providerId === filter.providerId)
    && (!filter.locationId || record.locationId === filter.locationId)
    && (!filter.rosarioOnly || record.source === "call"));
}

export function absencesOn(absences: readonly DiaryAbsence[], day: string, providerId = ""): DiaryAbsence[] {
  return absences.filter((absence) => absence.start <= day && day <= absence.end && (!providerId || absence.providerId === providerId));
}

/** Closures that affect a day: every-site closures, plus the chosen site's own (or all sites' when none is chosen). */
export function closuresOn(closures: readonly DiaryClosure[], day: string, locationId = ""): DiaryClosure[] {
  return closures.filter((closure) => closure.date === day && (!locationId || closure.locationId == null || closure.locationId === locationId));
}

export function wholeDay(absence: DiaryAbsence): boolean {
  return absence.startTime == null && absence.endTime == null;
}

export interface DaySummary {
  booked: number;
  cancelled: number;
  /** Call-made bookings still in the diary, earliest first. */
  rosario: DiaryRecord[];
}

export function summarizeDays(records: readonly DiaryRecord[]): Record<string, DaySummary> {
  const days: Record<string, DaySummary> = {};
  for (const record of records) {
    if (!record.day) continue;
    const summary = days[record.day] ??= { booked: 0, cancelled: 0, rosario: [] };
    if (record.status === "cancelled") summary.cancelled += 1;
    else {
      summary.booked += 1;
      if (record.source === "call") summary.rosario.push(record);
    }
  }
  return days;
}

/** A day's agenda grouped under each doctor, doctors by name, each list by time. */
export function groupByProvider(records: readonly DiaryRecord[], providers: readonly DiaryProvider[]): { id: string; name: string; specialty: string | null; records: DiaryRecord[] }[] {
  const groups = new Map<string, { id: string; name: string; specialty: string | null; records: DiaryRecord[] }>();
  for (const record of records) {
    const id = record.providerId ?? record.provider ?? "unknown";
    let group = groups.get(id);
    if (!group) {
      const provider = providers.find((item) => item.id === id);
      group = { id, name: provider?.name ?? record.provider ?? "Doctor not recorded", specialty: provider?.specialtyName ?? null, records: [] };
      groups.set(id, group);
    }
    group.records.push(record);
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/** "dermatology_review" -> "Dermatology review"; a name the server already formatted is kept. */
export function appointmentTypeLabel(value: string | null): string | null {
  if (!value) return null;
  if (!/^[a-z0-9_]+$/.test(value)) return value;
  const words = value.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
