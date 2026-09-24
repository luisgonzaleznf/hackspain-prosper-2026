import { CaretLeftIcon } from "@phosphor-icons/react/dist/csr/CaretLeft";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { ArrowUpRightIcon } from "@phosphor-icons/react/dist/csr/ArrowUpRight";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/csr/CalendarDots";
import { CalendarSlashIcon } from "@phosphor-icons/react/dist/csr/CalendarSlash";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react/dist/csr/ArrowsClockwise";
import { PhoneCallIcon } from "@phosphor-icons/react/dist/csr/PhoneCall";
import { UserMinusIcon } from "@phosphor-icons/react/dist/csr/UserMinus";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { api } from "@/lib/api";
import { ScreenHeader } from "@/app";
import { KeyValue, PillSelect } from "@/components/primitives";
import { SelectionIndicator } from "@/components/selection-indicator";
import {
  absencesOn, appointmentTypeLabel, calendarDay, closuresOn, filterRecords, groupByProvider, monthGrid, monthWindow, shiftDay, summarizeDays, wholeDay,
  type CalendarFeed, type DaySummary, type DiaryAbsence, type DiaryClosure, type DiaryRecord,
} from "@/lib/calendar";
import { dayLabel, wallClock } from "@/lib/format";
import "./calendar.css";

const monthFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", month: "long", year: "numeric" });
const dayFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric" });
const shortDate = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", day: "numeric", month: "short" });
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
// The diary changes only when someone books; a month window is ~1 MB, so poll gently.
const POLL_MS = 10_000;

type GroupBy = "time" | "doctor";

function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}

/** "Arenal Centro" -> "Centro": the sites share the clinic name, the last word tells them apart. */
function shortSite(name: string | null): string {
  return name?.split(" ").at(-1) ?? "Site not recorded";
}

function clock(ms: number | null): string {
  return ms == null ? "--:--" : wallClock(ms / 1000);
}

function absenceSpan(absence: DiaryAbsence): string {
  const days = absence.start === absence.end ? "" : `${shortDate.format(new Date(`${absence.start}T12:00:00Z`))} to ${shortDate.format(new Date(`${absence.end}T12:00:00Z`))}`;
  if (wholeDay(absence)) return days ? `away ${days}` : "away all day";
  const hours = `${absence.startTime ?? "start"}–${absence.endTime ?? "close"}`;
  return days ? `away ${hours}, ${days}` : `away ${hours}`;
}

export function CalendarScreen() {
  const today = calendarDay(new Date());
  const [month, setMonth] = useState(today.slice(0, 7));
  const [selectedDay, setSelectedDay] = useState(today);
  const [providerId, setProviderId] = useState("");
  const [locationId, setLocationId] = useState("");
  const [rosarioOnly, setRosarioOnly] = useState(false);
  const [groupBy, setGroupBy] = useState<GroupBy>("time");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [feed, setFeed] = useState<{ key: string; data: CalendarFeed } | null>(null);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { from, to } = useMemo(() => monthWindow(month), [month]);
  const windowKey = `${from}:${to}`;
  const currentWindow = useRef(windowKey);
  currentWindow.current = windowKey;

  const load = useCallback(async (signal?: AbortSignal) => {
    const key = `${from}:${to}`;
    try {
      const data = await api.calendar(from, to, signal);
      if (signal?.aborted || currentWindow.current !== key) return;
      setFeed({ key, data });
      setError(false);
    } catch {
      if (!signal?.aborted && currentWindow.current === key) setError(true);
    }
  }, [from, to]);

  // Month and day navigation move the window; the poll follows it.
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      await load(controller.signal);
      if (!controller.signal.aborted) timer = setTimeout(poll, POLL_MS);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [load]);

  const current = feed?.key === windowKey ? feed.data : null;
  // Doctors and sites do not change between windows; keep the filters usable while a new month loads.
  const directory = feed?.data ?? null;
  const providers = useMemo(() => directory?.providers ?? [], [directory]);
  const locations = useMemo(() => directory?.locations ?? [], [directory]);
  const loading = current == null && !error;

  const records = useMemo(() => current ? filterRecords(current.records, { providerId, locationId, rosarioOnly }) : [], [current, providerId, locationId, rosarioOnly]);
  const byDay = useMemo(() => {
    const days: Record<string, DiaryRecord[]> = {};
    for (const record of records) if (record.day) (days[record.day] ??= []).push(record);
    return days;
  }, [records]);
  const summaries = useMemo(() => summarizeDays(records), [records]);

  const days = useMemo(() => monthGrid(month), [month]);
  const monthTotals = useMemo(() => {
    let booked = 0, cancelled = 0, rosario = 0;
    for (const [day, summary] of Object.entries(summaries)) {
      if (!day.startsWith(month)) continue;
      booked += summary.booked;
      cancelled += summary.cancelled;
      rosario += summary.rosario.length;
    }
    return { booked, cancelled, rosario };
  }, [summaries, month]);

  const agenda = byDay[selectedDay] ?? [];
  const daySummary = summaries[selectedDay];
  const groups = useMemo(() => groupBy === "doctor" ? groupByProvider(agenda, providers) : [], [agenda, groupBy, providers]);
  const dayClosures = current ? closuresOn(current.closures, selectedDay, locationId) : [];
  const dayAbsences = current ? absencesOn(current.absences, selectedDay, providerId) : [];
  const providerName = useCallback((id: string) => providers.find((provider) => provider.id === id)?.name ?? id, [providers]);
  const siteName = useCallback((id: string | null) => locations.find((location) => location.id === id)?.name ?? id ?? "Every site", [locations]);
  const monthTitle = monthFormat.format(new Date(`${month}-01T12:00:00Z`));
  const selectedTitle = dayFormat.format(new Date(`${selectedDay}T12:00:00Z`));
  const toggle = useCallback((id: string) => setExpanded((open) => open === id ? null : id), []);

  function changeMonth(direction: number) {
    const date = new Date(`${month}-01T12:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() + direction);
    const next = date.toISOString().slice(0, 7);
    setMonth(next);
    setSelectedDay(today.startsWith(next) ? today : `${next}-01`);
  }

  function selectDay(day: string) {
    setSelectedDay(day);
    setMonth(day.slice(0, 7));
  }

  async function refresh() {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await load();
    } finally {
      setRefreshing(false);
    }
  }

  const status = loading ? "Loading the diary…"
    : !current ? "Diary unavailable. Start the local console server and refresh."
      : `${plural(monthTotals.booked, "appointment")} in ${monthTitle} · ${monthTotals.rosario} booked by Rosario · ${monthTotals.cancelled} cancelled`;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ScreenHeader title="Calendar" action={
        <button type="button" className="pill pill-ghost calendar-refresh" onClick={refresh} disabled={refreshing} aria-busy={refreshing}><ArrowsClockwiseIcon size={14} aria-hidden="true" />{refreshing ? "Refreshing…" : "Refresh"}</button>
      } />
      <div className="scroll-y calendar-scroll flex-1 px-4 pb-24 pt-5 md:px-8 md:pb-8">
        <div className="measure">
          <section className="calendar-source" aria-labelledby="calendar-source-title">
            <CalendarDotsIcon size={20} aria-hidden="true" />
            <div>
              <h2 id="calendar-source-title">Clinic diary</h2>
              <p>Every appointment in the clinic database{directory ? ` across ${plural(locations.length, "site")} and ${plural(providers.length, "doctor")}` : ""}. Bookings Rosario made on a call carry a phone mark and open that call.</p>
            </div>
          </section>

          <div className="calendar-filters">
            <div className="calendar-filter-doctor">
              <PillSelect value={providerId} onChange={setProviderId} label="Filter by doctor" options={[{ value: "", label: "All doctors" }, ...providers.map((provider) => ({ value: provider.id, label: provider.name, hint: provider.specialtyName ?? undefined }))]} />
            </div>
            <div className="calendar-filter-site">
              <PillSelect value={locationId} onChange={setLocationId} label="Filter by site" options={[{ value: "", label: "All sites" }, ...locations.map((location) => ({ value: location.id, label: location.name }))]} />
            </div>
            <button type="button" className="tab calendar-toggle" aria-pressed={rosarioOnly} onClick={() => setRosarioOnly((value) => !value)}><PhoneCallIcon size={14} aria-hidden="true" />Booked by Rosario</button>
          </div>

          <div className="calendar-loading">
            <p className="calendar-status" role="status">{status}</p>
            <p className="calendar-status-note" role="status">{error && current ? "Updates paused" : ""}</p>
          </div>

          <div className="calendar-layout">
            <section className="calendar-month card" aria-labelledby="calendar-month-title">
              <div className="calendar-toolbar">
                <div>
                  <h2 className="t-title" id="calendar-month-title" aria-live="polite">{monthTitle}</h2>
                  <p>{current ? `${plural(monthTotals.booked, "appointment")} · Madrid` : loading ? "Loading · Madrid" : "Unavailable · Madrid"}</p>
                </div>
                <div className="calendar-controls">
                  <button type="button" className="pill pill-ghost" onClick={() => selectDay(today)}>Today</button>
                  <button type="button" className="calendar-arrow" aria-label="Previous month" onClick={() => changeMonth(-1)}><CaretLeftIcon size={18} aria-hidden="true" /></button>
                  <button type="button" className="calendar-arrow" aria-label="Next month" onClick={() => changeMonth(1)}><CaretRightIcon size={18} aria-hidden="true" /></button>
                </div>
              </div>
              <table className="calendar-table" aria-label={monthTitle}>
                <thead><tr>{weekdays.map((day) => <th key={day} scope="col">{day}</th>)}</tr></thead>
                <tbody>{Array.from({ length: days.length / 7 }, (_, week) => (
                  <tr key={week}>{days.slice(week * 7, week * 7 + 7).map((day) => (
                    <td key={day}>
                      <DayTile day={day} today={today} month={month} selected={day === selectedDay} summary={summaries[day]}
                        closures={current ? closuresOn(current.closures, day, locationId) : []}
                        away={current ? absencesOn(current.absences, day, providerId).length : 0}
                        locationId={locationId} siteName={siteName} onSelect={selectDay} />
                    </td>
                  ))}</tr>
                ))}</tbody>
              </table>
            </section>

            <section className="calendar-agenda card" aria-labelledby="calendar-agenda-title">
              <div className="calendar-agenda-heading">
                <div className="calendar-agenda-title">
                  <h2 id="calendar-agenda-title">{selectedTitle}</h2>
                  <div className="calendar-controls">
                    <button type="button" className="calendar-arrow" aria-label="Previous day" onClick={() => selectDay(shiftDay(selectedDay, -1))}><CaretLeftIcon size={18} aria-hidden="true" /></button>
                    <button type="button" className="calendar-arrow" aria-label="Next day" onClick={() => selectDay(shiftDay(selectedDay, 1))}><CaretRightIcon size={18} aria-hidden="true" /></button>
                  </div>
                </div>
                <p>{current ? `${plural(daySummary?.booked ?? 0, "appointment")} · ${daySummary?.rosario.length ?? 0} by Rosario${daySummary?.cancelled ? ` · ${daySummary.cancelled} cancelled` : ""}` : loading ? "Loading" : "Unavailable"}</p>
                <div className="calendar-group relative isolate" role="group" aria-label="Order appointments">
                  <SelectionIndicator activeKey={groupBy} />
                  <button type="button" className="tab sliding-tab" aria-pressed={groupBy === "time"} onClick={() => setGroupBy("time")}>By time</button>
                  <button type="button" className="tab sliding-tab" aria-pressed={groupBy === "doctor"} onClick={() => setGroupBy("doctor")}>By doctor</button>
                </div>
              </div>
              <DayNotes closures={dayClosures} absences={dayAbsences} providerName={providerName} siteName={siteName} />
              <div className="calendar-agenda-content" aria-busy={loading}>
                {agenda.length > 0 ? groupBy === "time" ? (
                  <ol className="diary-list">{agenda.map((record) => <DiaryRow key={record.id} record={record} showDoctor expanded={expanded === record.id} onToggle={toggle} siteName={siteName} />)}</ol>
                ) : groups.map((group) => (
                  <section key={group.id} className="diary-group" aria-label={group.name}>
                    <h3><span>{group.name}</span>{group.specialty ? <span className="diary-group-specialty">{group.specialty}</span> : null}<span className="diary-group-count mono">{group.records.filter((record) => record.status === "booked").length}</span></h3>
                    <ol className="diary-list">{group.records.map((record) => <DiaryRow key={record.id} record={record} showDoctor={false} expanded={expanded === record.id} onToggle={toggle} siteName={siteName} />)}</ol>
                  </section>
                )) : loading ? (
                  <div className="diary-placeholder" role="status" aria-label="Loading appointments for this date">
                    {[0, 1, 2, 3, 4, 5].map((row) => <span key={row} className="loading-skeleton" aria-hidden="true" />)}
                  </div>
                ) : (
                  <div className="calendar-empty"><CalendarDotsIcon size={28} aria-hidden="true" /><h3>{current ? "No appointments for this date" : "Diary unavailable"}</h3><p>{current ? providerId || locationId || rosarioOnly ? "Nothing matches the filters on this date." : dayClosures.length > 0 ? "The clinic is closed." : "Nothing is booked yet." : "Refresh to try again."}</p></div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

function DayTile({ day, today, month, selected, summary, closures, away, locationId, siteName, onSelect }: {
  day: string; today: string; month: string; selected: boolean; summary: DaySummary | undefined;
  closures: DiaryClosure[]; away: number; locationId: string; siteName: (id: string | null) => string; onSelect: (day: string) => void;
}) {
  // With a site chosen, that site's own closure closes the whole view.
  const closed = closures.find((closure) => closure.locationId == null || (locationId !== "" && closure.locationId === locationId));
  const siteClosures = closed ? [] : closures.filter((closure) => closure.locationId != null);
  const rosario = summary?.rosario ?? [];
  const first = rosario[0];
  const title = dayFormat.format(new Date(`${day}T12:00:00Z`));
  const facts = [
    closed ? `closed, ${closed.name}` : `${plural(summary?.booked ?? 0, "appointment")}`,
    rosario.length > 0 ? `${rosario.length} booked by Rosario` : "",
    siteClosures.length > 0 ? `${siteClosures.map((closure) => siteName(closure.locationId)).join(", ")} closed` : "",
    away > 0 ? `${plural(away, "doctor")} away` : "",
  ].filter(Boolean).join(", ");
  return (
    <div className="calendar-day" data-outside={!day.startsWith(month)} data-selected={selected} data-closed={closed ? "true" : undefined}>
      <button type="button" className="calendar-day-select" aria-pressed={selected} aria-current={day === today ? "date" : undefined} aria-label={`${title}, ${facts}`} onClick={() => onSelect(day)}>
        <span className="calendar-date">{Number(day.slice(-2))}{day === today ? <span className="calendar-today-word">Today</span> : null}</span>
        {closed ? <span className="calendar-day-count">Closed</span> : summary && summary.booked > 0 || away > 0 ? (
          <span className="calendar-day-count">
            {summary && summary.booked > 0 ? <span>{summary.booked}<span className="calendar-count-word"> booked</span></span> : null}
            {away > 0 ? <span className="calendar-day-away" title={`${plural(away, "doctor")} away`}><UserMinusIcon size={11} aria-hidden="true" />{away}</span> : null}
          </span>
        ) : null}
      </button>
      <div className="calendar-day-preview">
        {closed ? <span className="calendar-day-note">{closed.name}</span> : null}
        {siteClosures.length > 0 ? <span className="calendar-day-note">{siteClosures.map((closure) => shortSite(siteName(closure.locationId))).join(", ")} closed</span> : null}
        {first ? first.callId && first.callLogged ? (
          <Link to={`/calls/${encodeURIComponent(first.callId)}`} className="calendar-event-link" aria-label={`View call for ${first.patient}, ${clock(first.startMs)}`}>
            <PhoneCallIcon size={12} aria-hidden="true" />
            <span className="calendar-event-label">{clock(first.startMs)} {first.patient}</span>
          </Link>
        ) : <span className="calendar-event-link"><PhoneCallIcon size={12} aria-hidden="true" /><span className="calendar-event-label">{clock(first.startMs)} {first.patient}</span></span> : null}
        {rosario.length > 1 ? <button type="button" className="calendar-more" aria-label={`Show all ${rosario.length} Rosario bookings for ${title}`} onClick={() => onSelect(day)}>+{rosario.length - 1}<span className="calendar-count-word"> by Rosario</span></button> : null}
      </div>
    </div>
  );
}

function DayNotes({ closures, absences, providerName, siteName }: { closures: DiaryClosure[]; absences: DiaryAbsence[]; providerName: (id: string) => string; siteName: (id: string | null) => string }) {
  if (closures.length === 0 && absences.length === 0) return null;
  return (
    <ul className="calendar-notes" aria-label="Closures and doctors away">
      {closures.map((closure) => (
        <li key={`${closure.date}-${closure.locationId ?? "all"}`}>
          <CalendarSlashIcon size={16} aria-hidden="true" />
          <span>{closure.locationId ? `${siteName(closure.locationId)} closed` : "Every site closed"}<span className="calendar-note-reason">{closure.name}</span></span>
        </li>
      ))}
      {absences.map((absence) => (
        <li key={`${absence.providerId}-${absence.start}-${absence.startTime ?? ""}`}>
          <UserMinusIcon size={16} aria-hidden="true" />
          <span>{providerName(absence.providerId)} {absenceSpan(absence)}<span className="calendar-note-reason">{absence.reason}</span></span>
        </li>
      ))}
    </ul>
  );
}

const DiaryRow = memo(function DiaryRow({ record, showDoctor, expanded, onToggle, siteName }: { record: DiaryRecord; showDoctor: boolean; expanded: boolean; onToggle: (id: string) => void; siteName: (id: string | null) => string }) {
  const cancelled = record.status === "cancelled";
  const fromCall = record.source === "call";
  const site = record.locationId ? siteName(record.locationId) : record.site;
  const detailId = `diary-${record.id}`;
  return (
    <li className="diary-row" data-source={record.source} data-status={record.status}>
      <button type="button" className="diary-row-main" data-doctor={showDoctor} aria-expanded={expanded} aria-controls={expanded ? detailId : undefined} onClick={() => onToggle(record.id)}>
        <span className="diary-time mono">{clock(record.startMs)}</span>
        <span className="diary-patient">
          {fromCall ? <PhoneCallIcon size={13} className="diary-call-mark" aria-hidden="true" /> : null}
          <span className="diary-patient-name">{record.patient}</span>
          {fromCall ? <span className="sr-only">, booked by Rosario</span> : null}
          {cancelled ? <span className="sr-only">, cancelled</span> : null}
        </span>
        {showDoctor ? <span className="diary-doctor">{record.provider ?? "Doctor not recorded"}</span> : null}
        <span className="diary-site">{shortSite(site)}</span>
      </button>
      {fromCall && record.callId ? record.callLogged
        ? <Link to={`/calls/${encodeURIComponent(record.callId)}`} className="diary-call" aria-label={`View call for ${record.patient}`}>Call<ArrowUpRightIcon size={13} aria-hidden="true" /></Link>
        : <span className="diary-call diary-call-missing" title="The call log is not on this server">No log</span> : null}
      {expanded ? (
        <div id={detailId} className="diary-detail">
          <KeyValue rows={[
            ["time", `${clock(record.startMs)}${record.endMs != null ? `–${clock(record.endMs)}` : ""}${record.durationMinutes ? ` (${record.durationMinutes} min)` : ""}`],
            ["type", appointmentTypeLabel(record.appointmentType) ?? "Not recorded"],
            ["doctor", record.provider ?? "Not recorded"],
            ["site", site ?? "Not recorded"],
            ["status", record.status],
            ["source", fromCall ? `Rosario call${record.recordedAt ? `, saved ${dayLabel(record.recordedAt)} ${wallClock(record.recordedAt)}` : ""}` : "Clinic diary"],
            ["patient_id", record.patientId ?? "Not recorded"],
            ["appointment_id", record.appointmentId ?? record.id],
          ]} />
        </div>
      ) : null}
    </li>
  );
});
