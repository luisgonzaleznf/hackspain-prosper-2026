import { ArrowsClockwiseIcon } from "@phosphor-icons/react/dist/csr/ArrowsClockwise";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/csr/CalendarDots";
import { CaretLeftIcon } from "@phosphor-icons/react/dist/csr/CaretLeft";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ScreenHeader } from "@/app";
import { api } from "@/lib/api";
import { calendarDay } from "@/lib/calendar";
import { wallClock } from "@/lib/format";
import type { CalendarAppointment } from "@/lib/types";
import "./calendar.css";

const monthFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", month: "long", year: "numeric" });
const dayFormat = new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric" });
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function monthDays(month: string): string[] {
  const first = new Date(`${month}-01T12:00:00Z`);
  const offset = (first.getUTCDay() + 6) % 7;
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(first);
    date.setUTCDate(index - offset + 1);
    return date.toISOString().slice(0, 10);
  });
}

export function CalendarScreen() {
  const today = calendarDay(new Date());
  const [appointments, setAppointments] = useState<CalendarAppointment[]>([]);
  const [month, setMonth] = useState(today.slice(0, 7));
  const [selectedDay, setSelectedDay] = useState(today);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setAppointments((await api.calendar()).appointments);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "hidden") void refresh();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const byDay = useMemo(() => {
    const grouped: Record<string, CalendarAppointment[]> = {};
    for (const appointment of appointments) {
      (grouped[calendarDay(new Date(appointment.start_time))] ??= []).push(appointment);
    }
    return grouped;
  }, [appointments]);
  const days = useMemo(() => monthDays(month), [month]);
  const agenda = byDay[selectedDay] ?? [];
  const monthCount = appointments.filter((appointment) => calendarDay(new Date(appointment.start_time)).startsWith(month)).length;

  function changeMonth(direction: number) {
    const date = new Date(`${month}-01T12:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() + direction);
    const next = date.toISOString().slice(0, 7);
    setMonth(next);
    setSelectedDay(`${next}-01`);
  }

  return <div className="flex min-h-0 flex-1 flex-col">
    <ScreenHeader title="Calendar" action={<button type="button" className="pill pill-ghost calendar-refresh" onClick={() => void refresh()} disabled={loading} aria-busy={loading}><ArrowsClockwiseIcon size={14} />{loading ? "Refreshing…" : "Refresh"}</button>} />
    <div className="scroll-y calendar-scroll flex-1 px-4 pb-24 pt-5 md:px-8 md:pb-8">
      <div className="measure">
        <section className="calendar-source" aria-labelledby="calendar-source-title"><CalendarDotsIcon size={20} /><div><h2 id="calendar-source-title">Clinic diary</h2><p>Confirmed bookings, reschedules and cancellations update this schedule immediately.</p></div></section>
        <div className="calendar-loading"><p className="calendar-status" role="status">{loading ? "Loading clinic diary…" : `${appointments.length} active appointments`}</p><p className="calendar-status-note">{error ? `Updates unavailable: ${error}` : "SQLite clinic state"}</p></div>
        <div className="calendar-layout">
          <section className="calendar-month card" aria-labelledby="calendar-month-title">
            <div className="calendar-toolbar"><div><h2 className="t-title" id="calendar-month-title">{monthFormat.format(new Date(`${month}-01T12:00:00Z`))}</h2><p>{monthCount} appointments · Madrid</p></div><div className="calendar-controls"><button type="button" className="pill pill-ghost" onClick={() => { setSelectedDay(today); setMonth(today.slice(0, 7)); }}>Today</button><button type="button" className="calendar-arrow" aria-label="Previous month" onClick={() => changeMonth(-1)}><CaretLeftIcon size={18} /></button><button type="button" className="calendar-arrow" aria-label="Next month" onClick={() => changeMonth(1)}><CaretRightIcon size={18} /></button></div></div>
            <table className="calendar-table" aria-label={month}><thead><tr>{weekdays.map((day) => <th key={day}>{day}</th>)}</tr></thead><tbody>{Array.from({ length: 6 }, (_, week) => <tr key={week}>{days.slice(week * 7, week * 7 + 7).map((day) => { const events = byDay[day] ?? []; return <td key={day}><button type="button" className="calendar-day" data-outside={!day.startsWith(month)} data-selected={day === selectedDay} aria-pressed={day === selectedDay} aria-current={day === today ? "date" : undefined} onClick={() => { setSelectedDay(day); setMonth(day.slice(0, 7)); }}><span className="calendar-date">{Number(day.slice(-2))}{day === today ? <span className="calendar-today-word">Today</span> : null}</span>{events.length ? <><span className="calendar-day-count">{events.length} {events.length === 1 ? "appointment" : "appointments"}</span><span className="calendar-day-preview">{events.slice(0, 2).map((event) => <span key={event.appointment_id}>{wallClock(Date.parse(event.start_time) / 1000)} {event.patient_name}</span>)}</span></> : null}</button></td>; })}</tr>)}</tbody></table>
          </section>
          <section className="calendar-agenda card" aria-labelledby="calendar-agenda-title"><div className="calendar-agenda-heading"><h2 id="calendar-agenda-title">{dayFormat.format(new Date(`${selectedDay}T12:00:00Z`))}</h2><p>{agenda.length} {agenda.length === 1 ? "appointment" : "appointments"}</p></div><div className="calendar-agenda-content">{agenda.length ? <ol className="calendar-agenda-list">{agenda.map((appointment) => <li key={appointment.appointment_id} className="calendar-record loading-reveal"><div className="calendar-record-top"><span className="mono">{wallClock(Date.parse(appointment.start_time) / 1000)}</span><span className="calendar-action">Confirmed</span></div><h3>{appointment.patient_name}</h3><p>{appointment.provider_name} · {appointment.location_name}</p><p className="calendar-caller mono">{appointment.appointment_type_id ?? "appointment"} · {appointment.duration_minutes} min</p><div className="calendar-record-footer"><span>{appointment.patient_id}</span><span className="mono">{appointment.appointment_id}</span></div></li>)}</ol> : <div className="calendar-empty"><CalendarDotsIcon size={28} /><h3>No appointments for this date</h3><p>The live clinic diary has no active booking here.</p></div>}</div></section>
        </div>
      </div>
    </div>
  </div>;
}
