import { CaretLeftIcon } from "@phosphor-icons/react/dist/csr/CaretLeft";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { ArrowUpRightIcon } from "@phosphor-icons/react/dist/csr/ArrowUpRight";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/csr/CalendarDots";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react/dist/csr/ArrowsClockwise";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { api } from "@/lib/api";
import { ScreenHeader } from "@/app";
import { ProgressStrip } from "@/components/loading";
import { SelectionIndicator } from "@/components/selection-indicator";
import { calendarDay, schedulingRecords, type SchedulingRecord } from "@/lib/calendar";
import { maskPhone, slotLabel, wallClock } from "@/lib/format";
import { loadDetail, refreshNow, useCallsIndex } from "@/lib/store";
import type { CallDetail } from "@/lib/types";
import "./calendar.css";

const monthFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", month: "long", year: "numeric" });
const dayFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric" });
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const actionLabels = { BOOK: "Booking reported", RESCHEDULE: "Reschedule reported", CANCEL: "Cancellation reported" };

function monthDays(month: string): string[] {
  const first = new Date(`${month}-01T12:00:00Z`);
  const offset = (first.getUTCDay() + 6) % 7;
  const last = new Date(first);
  last.setUTCMonth(last.getUTCMonth() + 1, 0);
  const count = Math.ceil((offset + last.getUTCDate()) / 7) * 7;
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(first);
    date.setUTCDate(index - offset + 1);
    return date.toISOString().slice(0, 10);
  });
}

export function CalendarScreen() {
  const { calls, byId, loading, error } = useCallsIndex();
  const [source, setSource] = useState<"local" | "reports">("local");
  const [localRecords, setLocalRecords] = useState<SchedulingRecord[]>([]);
  const [localLoading, setLocalLoading] = useState(true);
  const [localError, setLocalError] = useState(false);
  const loadLocal = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await api.calendar(signal);
      if (signal?.aborted) return;
      setLocalRecords(data.records);
      setLocalError(false);
    } catch {
      if (!signal?.aborted) setLocalError(true);
    } finally {
      if (!signal?.aborted) setLocalLoading(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      await loadLocal(controller.signal);
      if (!controller.signal.aborted) timer = setTimeout(poll, 5000);
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [loadLocal]);
  const today = calendarDay(new Date());
  const [month, setMonth] = useState(today.slice(0, 7));
  const [selectedDay, setSelectedDay] = useState(today);
  const initialized = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const refreshInFlight = useRef(false);
  const mounted = useRef(false);
  const latest = useRef({ calls, byId });
  latest.current = { calls, byId };
  const detailQueue = useRef(Promise.resolve());
  const callIdsKey = useMemo(() => JSON.stringify(calls.map((call) => call.call_id)), [calls]);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const loadRecords = useCallback((retryFailed: boolean, cancelled: () => boolean) => {
    const task = detailQueue.current.then(async () => {
      if (cancelled()) return;
      const ids = latest.current.calls.filter((call) => {
        const record = latest.current.byId[call.call_id];
        return (!record?.detail && !record?.detailError) || (retryFailed && Boolean(record?.detailError));
      }).sort((a, b) => Number(Object.hasOwn(actionLabels, b.action)) - Number(Object.hasOwn(actionLabels, a.action))).map((call) => call.call_id);
      for (let offset = 0; offset < ids.length; offset += 4) {
        if (cancelled()) return;
        await Promise.all(ids.slice(offset, offset + 4).map((id) => loadDetail(id, retryFailed)));
      }
    });
    detailQueue.current = task;
    return task;
  }, []);

  useEffect(() => {
    let cancelled = false;
    void loadRecords(false, () => cancelled);
    return () => { cancelled = true; };
  }, [callIdsKey, loadRecords]);

  const { records: reportRecords, failed, pending, loaded } = useMemo(() => {
    let loaded = 0;
    const details: CallDetail[] = [];
    let failed = 0;
    let pending = 0;
    for (const call of calls) {
      const record = byId[call.call_id];
      if (record?.detail) details.push(record.detail);
      if (record?.detailError) failed += 1;
      else if (record?.detail) loaded += 1;
      else pending += 1;
    }
    return { records: schedulingRecords(details), failed, pending, loaded };
  }, [calls, byId]);

  const records = source === "local" ? localRecords : reportRecords;

  const { byDay, undated } = useMemo(() => {
    const byDay: Record<string, SchedulingRecord[]> = {};
    const undated: SchedulingRecord[] = [];
    for (const record of records) {
      if (record.day) (byDay[record.day] ??= []).push(record);
      else undated.push(record);
    }
    return { byDay, undated };
  }, [records]);

  useEffect(() => {
    if (initialized.current) return;
    const dates = Object.keys(byDay).sort();
    const current = dates.find((day) => day.startsWith(today.slice(0, 7)));
    const chosen = byDay[today] ? today : current ?? dates.find((day) => day >= today) ?? dates.at(-1);
    if (!chosen) return;
    initialized.current = true;
    setMonth(chosen.slice(0, 7));
    setSelectedDay(chosen);
  }, [byDay, calls.length, loading, today]);

  const days = useMemo(() => monthDays(month), [month]);
  const monthRecords = records.filter((record) => record.day?.startsWith(month));
  const agenda = byDay[selectedDay] ?? [];
  const monthTitle = monthFormat.format(new Date(`${month}-01T12:00:00Z`));
  const selectedTitle = dayFormat.format(new Date(`${selectedDay}T12:00:00Z`));
  const loadingRecords = refreshing || (source === "local" ? localLoading : loading || pending > 0);
  const incomplete = loadingRecords || (source === "local" ? localError : failed > 0 || Boolean(error));

  function reportCount(count: number) {
    if (source === "local") return incomplete && count === 0 ? "Appointments unavailable" : `${count} ${count === 1 ? "appointment" : "appointments"}`;
    if (incomplete && count === 0) return loadingRecords ? "Reports loading" : "Reports incomplete";
    return `${count} ${count === 1 ? "report" : "reports"}${incomplete ? "+" : ""}`;
  }

  function changeMonth(direction: number) {
    initialized.current = true;
    const date = new Date(`${month}-01T12:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() + direction);
    const next = date.toISOString().slice(0, 7);
    setMonth(next);
    setSelectedDay(Object.keys(byDay).sort().find((day) => day.startsWith(next)) ?? `${next}-01`);
  }

  function selectDay(day: string) {
    initialized.current = true;
    setSelectedDay(day);
    setMonth(day.slice(0, 7));
  }

  async function refresh() {
    if (refreshInFlight.current) return;
    refreshInFlight.current = true;
    setRefreshing(true);
    try {
      if (source === "local") { await loadLocal(); return; }
      await refreshNow();
      if (!mounted.current) return;
      await loadRecords(true, () => !mounted.current);
    } finally {
      refreshInFlight.current = false;
      if (mounted.current) setRefreshing(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ScreenHeader title="Calendar" action={
        <button type="button" className="pill pill-ghost calendar-refresh" onClick={refresh} disabled={refreshing} aria-busy={refreshing}><ArrowsClockwiseIcon size={14} aria-hidden="true" />{refreshing ? "Refreshing…" : "Refresh"}</button>
      } />
      <div className="scroll-y calendar-scroll flex-1 px-4 pb-24 pt-5 md:px-8 md:pb-8">
        <div className="measure">
          <div className="relative isolate mb-4 flex gap-2" role="group" aria-label="Calendar source">
            <SelectionIndicator activeKey={source} />
            <button type="button" className="tab sliding-tab min-h-11" aria-pressed={source === "local"} onClick={() => { setSource("local"); initialized.current = false; }}>Appointments</button>
            <button type="button" className="tab sliding-tab min-h-11" aria-pressed={source === "reports"} onClick={() => { setSource("reports"); initialized.current = false; }}>Call reports</button>
          </div>
          <section className="calendar-source" aria-labelledby="calendar-source-title">
            <CalendarDotsIcon size={20} aria-hidden="true" />
            <div>
              <h2 id="calendar-source-title">{source === "local" ? "Local appointments" : "Call reports · Read-only clinic"}</h2>
              <p>{source === "local" ? "Confirmed bookings saved here. Open the source call to review the conversation." : "Reports include practice calls and do not change the clinic diary."}</p>
            </div>
          </section>

          <div className="calendar-loading">
            {source === "local" ? <p className="calendar-status" role="status">{localLoading ? "Loading appointments…" : localError ? "Appointments unavailable. Start the local console server and refresh." : `${records.length} saved ${records.length === 1 ? "appointment" : "appointments"}`}</p> : loadingRecords && calls.length > 0 ? <ProgressStrip label={refreshing ? "Refreshing reports" : "Reading calls"} value={loaded + failed} max={calls.length} /> : <p className="calendar-status" role="status">{loadingRecords ? "Loading calls…" : `${records.length} accepted ${records.length === 1 ? "report" : "reports"}${incomplete ? " · Incomplete" : ""}`}</p>}
            <p className="calendar-status-note" role="status">{source === "local" ? "" : error ? "Updates unavailable" : failed > 0 ? `${failed} unavailable` : ""}</p>
          </div>

          <div className="calendar-layout">
            <section className="calendar-month card" aria-labelledby="calendar-month-title">
              <div className="calendar-toolbar">
                <div>
                  <h2 className="t-title" id="calendar-month-title" aria-live="polite">{monthTitle}</h2>
                  <p>{reportCount(monthRecords.length)} · Madrid</p>
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
                  <tr key={week}>{days.slice(week * 7, week * 7 + 7).map((day) => {
                    const events = byDay[day] ?? [];
                    const outside = !day.startsWith(month);
                    return (
                      <td key={day}>
                        <div className="calendar-day" data-outside={outside} data-selected={day === selectedDay}>
                          <button type="button" className="calendar-day-select" aria-pressed={day === selectedDay} aria-current={day === today ? "date" : undefined} aria-label={`${dayFormat.format(new Date(`${day}T12:00:00Z`))}, ${reportCount(events.length)}`} onClick={() => selectDay(day)}>
                            <span className="calendar-date">{Number(day.slice(-2))}{day === today ? <span className="calendar-today-word">Today</span> : null}</span>
                            {events.length > 0 ? <span className="calendar-day-count">{events.length}{incomplete ? "+" : ""}<span className="calendar-count-word"> {source === "local" ? "saved" : events.length === 1 ? "report" : "reports"}</span></span> : null}
                          </button>
                          {events.length > 0 ? <div className="calendar-day-preview">
                            {events.slice(0, 1).map((event) => <Link key={event.id} to={`/calls/${encodeURIComponent(event.callId)}`} className="calendar-event-link" aria-label={`View call for ${event.patient}${event.slot ? `, ${slotLabel(event.slot)}` : ""}`}>
                              <span className="calendar-event-label">{event.kind === "CANCEL" ? (event.persisted ? "Cancelled" : "Cancel report") : event.supersededBy ? "Changed" : event.slot ? wallClock(Date.parse(event.slot) / 1000) : "Time unknown"} {event.patient}</span>
                              <span className="calendar-event-call"><span><span className="calendar-call-view-word">View </span>call</span><ArrowUpRightIcon size={12} aria-hidden="true" /></span>
                            </Link>)}
                            {events.length > 1 ? <button type="button" className="calendar-more" aria-label={`Show all ${events.length} ${source === "local" ? "appointments" : "reports"} for ${dayFormat.format(new Date(`${day}T12:00:00Z`))}`} onClick={() => selectDay(day)}>+{events.length - 1} more</button> : null}
                          </div> : null}
                        </div>
                      </td>
                    );
                  })}</tr>
                ))}</tbody>
              </table>
            </section>

            <section className="calendar-agenda card" aria-labelledby="calendar-agenda-title">
              <div className="calendar-agenda-heading">
                <h2 id="calendar-agenda-title">{selectedTitle}</h2>
                <p>{reportCount(agenda.length)}</p>
              </div>
              <div className="calendar-agenda-content" aria-busy={loadingRecords}>
                {agenda.length > 0 ? <ol className="calendar-agenda-list">{agenda.map((record) => <AgendaRecord key={record.id} record={record} />)}</ol> : loadingRecords ? <div className="calendar-record calendar-agenda-placeholder" role="status" aria-label="Loading reports for this date">
                  <div aria-hidden="true">
                    <div className="calendar-record-top"><span className="loading-skeleton calendar-placeholder-time" /><span className="loading-skeleton calendar-placeholder-action" /></div>
                    <h3><span className="loading-skeleton calendar-placeholder-title" /></h3>
                    <p><span className="loading-skeleton calendar-placeholder-detail" /></p>
                    <p className="calendar-caller"><span className="loading-skeleton calendar-placeholder-caller" /></p>
                    <div className="calendar-record-footer"><span className="loading-skeleton calendar-placeholder-kind" /><span className="calendar-call-link"><span className="loading-skeleton calendar-placeholder-link" /></span></div>
                  </div>
                </div> : <div className="calendar-empty"><CalendarDotsIcon size={28} aria-hidden="true" /><h3>{incomplete ? "Records incomplete" : source === "local" ? "No local appointments for this date" : "No reports for this date"}</h3><p>{incomplete ? "Refresh to retry unavailable records." : "This does not mean the clinic is free."}</p></div>}
              </div>
            </section>
          </div>

          {undated.length > 0 ? <section className="calendar-undated card" aria-labelledby="calendar-undated-title"><h2 className="t-title" id="calendar-undated-title">Reports without a date</h2><ol className="calendar-agenda-list">{undated.map((record) => <AgendaRecord key={record.id} record={record} />)}</ol></section> : null}
        </div>
      </div>
    </div>
  );
}

function AgendaRecord({ record }: { record: SchedulingRecord }) {
  return <li className="calendar-record loading-reveal">
    <div className="calendar-record-top"><span className="mono">{record.slot ? wallClock(Date.parse(record.slot) / 1000) : "Time unavailable"}</span><span className="calendar-action">{record.persisted ? (record.kind === "CANCEL" ? "Cancelled" : "Booked") : actionLabels[record.kind]}</span></div>
    <h3>{record.patient}</h3>
    <p>{record.provider ?? "Provider not recorded"}{record.site ? ` · ${record.site}` : " · Site not recorded"}</p>
    {record.caller ? <p className="calendar-caller">Caller <span className="mono">{maskPhone(record.caller)}</span></p> : null}
    {record.previousSlot && record.kind === "RESCHEDULE" ? <p className="calendar-change">Moved from {slotLabel(record.previousSlot)}</p> : null}
    {record.kind === "CANCEL" ? <p className="calendar-change">{record.persisted ? "This appointment is cancelled." : "Cancellation reported for this appointment, not an active booking."}</p> : null}
    {record.supersededBy ? <p className="calendar-change">{record.supersededBy === "CANCEL" ? "Cancellation" : "A later change"} was reported for this appointment in the same call.</p> : null}
    {record.persisted && record.appointmentId ? <p className="mono break-all">{record.appointmentId}</p> : null}
    <div className="calendar-record-footer"><span>{record.persisted ? "Saved locally" : record.practice ? "Practice call" : "Recorded call"}</span><Link to={`/calls/${encodeURIComponent(record.callId)}`} className="calendar-call-link">View call<ArrowUpRightIcon size={14} aria-hidden="true" /></Link></div>
  </li>;
}
