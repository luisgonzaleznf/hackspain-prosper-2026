// Calls: table left, detail drawer right; the drawer takes the screen on a
// phone. Each row is a small picture of the call: outcome icon, caller, a
// speaker strip with decision ticks, duration, median response gap.

import { clsx } from "clsx";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ScreenHeader } from "@/app";
import { CallInProgress } from "@/components/call-status";
import { CallStrip } from "@/components/call-strip";
import { LoadingCall, LoadingRows } from "@/components/loading";
import { Empty, Label, Mono, Outcome } from "@/components/primitives";
import { SelectionIndicator } from "@/components/selection-indicator";
import { dayLabel, duration, latency, maskPhone, wallClock } from "@/lib/format";
import { isActive, loadDetail, refreshNow, useCallDetail, useCallRecord, useCallsIndex } from "@/lib/store";
import { outcomeOf } from "@/lib/timeline";
import type { CallSummary } from "@/lib/types";
import { CallDrawer, CallDuration, callerLabel } from "./detail";

type Filter = "all" | "booked" | "refused" | "escalated" | "registered" | "failed";
const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "booked", label: "Booked" },
  { id: "registered", label: "Registered" },
  { id: "refused", label: "Declined" },
  { id: "escalated", label: "Escalated" },
  { id: "failed", label: "Failed submit" },
];

function matchesFilter(summary: CallSummary, filter: Filter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "booked":
      return summary.action === "BOOK";
    case "registered":
      return summary.action === "REGISTER";
    case "refused":
      return summary.action === "NO_ACTION";
    case "escalated":
      return summary.action === "ESCALATE";
    case "failed":
      return /^submitted [45]\d{2}$/.test(summary.status);
  }
}

export function CallsScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { calls, loading, error, loadedAt } = useCallsIndex();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const list = useRef<HTMLDivElement>(null);

  const { active, history } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const active: CallSummary[] = [];
    const history: CallSummary[] = [];
    for (const call of calls) {
      if (q && !call.call_id.toLowerCase().includes(q)) continue;
      if (isActive(call)) active.push(call);
      else if (matchesFilter(call, filter)) history.push(call);
    }
    return { active, history };
  }, [calls, loadedAt, filter, query]);
  const displayed = useMemo(() => [...active, ...history], [active, history]);


  useEffect(() => {
    const root = list.current;
    if (!root) return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const id = (entry.target as HTMLElement).dataset.callId;
        if (id) void loadDetail(id);
        observer.unobserve(entry.target);
      }
    }, { root, rootMargin: "160px 0px" });
    for (const row of root.querySelectorAll("[data-call-id]")) observer.observe(row);
    return () => observer.disconnect();
  }, [displayed, id]);

  const index = id ? displayed.findIndex((c) => c.call_id === id) : -1;
  const prev = index > 0 ? (displayed[index - 1]?.call_id ?? null) : null;
  const next = index >= 0 && index < displayed.length - 1 ? (displayed[index + 1]?.call_id ?? null) : null;
  const selected = useCallDetail(id ?? null);

  const groups = useMemo(() => {
    const out: { key: string; day: string; items: CallSummary[] }[] = [];
    for (const c of history) {
      const day = dayLabel(c.started_at);
      const last = out[out.length - 1];
      if (last && last.day === day) last.items.push(c);
      else out.push({ key: `${day}-${c.call_id}`, day, items: [c] });
    }
    return out;
  }, [history]);

  const compact = !!id;

  return (
    <div className={clsx("flex min-h-0 flex-1 flex-col overflow-hidden", id && "lg:grid lg:grid-cols-[minmax(400px,4fr)_minmax(560px,8fr)]")}>
      <div className={clsx("flex min-h-0 flex-1 flex-col", id && "hidden lg:flex")}>
        <ScreenHeader title="Calls" search={{ placeholder: "Search call ID", value: query, onChange: setQuery }} />

        <div ref={list} className="scroll-y flex-1 px-2 pb-24 pt-2 md:px-8 md:pb-8">
          <div className="measure">
            {error ? <div role="alert" className="py-4 text-[14px] text-fg-2"><p>{loadedAt == null ? "Calls could not be loaded." : "Updates paused. Showing the last loaded calls."} {error}</p><button type="button" className="pill pill-quiet pill-sm mt-2" disabled={refreshing} onClick={async () => { setRefreshing(true); try { await refreshNow(); } finally { setRefreshing(false); } }}>{refreshing ? "Retrying…" : "Try again"}</button></div> : null}
            {loading && !error ? <LoadingRows label="Loading calls" compact={compact} /> : null}
            {loadedAt != null ? (
              <section className="mb-6" aria-labelledby="live-calls-heading">
                <h2 id="live-calls-heading" className="px-3 py-3 text-[18px] font-light text-fg">Live calls <Mono dim className="ml-2 text-[13px]">{active.length}</Mono></h2>
                {active.length === 0 ? <p className="px-3 py-2 text-[14px] text-fg-3">{query.trim() ? "No live calls match this search." : "No calls in progress."}</p> : (
                  <ul className="m-0 grid list-none gap-0.5 p-0">
                    {active.map((c) => <CallRow key={c.call_id} summary={c} live selected={c.call_id === id} compact={compact} onOpen={() => navigate(`/calls/${c.call_id}`)} />)}
                  </ul>
                )}
              </section>
            ) : null}
            <h2 className="px-3 pt-3 text-[18px] font-light text-fg">Call history</h2>
            <div role="group" aria-label="Call history filters" className="relative isolate my-3 flex gap-2 overflow-x-auto pb-1">
              <SelectionIndicator activeKey={filter} />
              {FILTERS.map((f) => (
                <button key={f.id} type="button" aria-pressed={filter === f.id} className={clsx("tab sliding-tab shrink-0", filter === f.id && "text-fg")} onClick={() => setFilter(f.id)}>
                  {f.label}
                </button>
              ))}
            </div>
            {loadedAt != null && history.length === 0 ? <Empty>No completed calls match.</Empty> : null}
            <div className={clsx("gap-3 px-3 pb-2", history.length > 0 ? "hidden md:grid" : "hidden", compact ? "grid-cols-[56px_minmax(0,1.2fr)_minmax(0,1fr)_64px]" : "grid-cols-[56px_minmax(0,1.3fr)_minmax(0,1.6fr)_minmax(0,1.1fr)_72px_64px]")} aria-hidden="true">
              <Label>time</Label>
              <Label>caller</Label>
              <Label>call</Label>
              {!compact ? <Label>outcome</Label> : null}
              {!compact ? <Label>length</Label> : null}
              <Label className="text-right">p50 gap</Label>
            </div>
            {groups.map((g) => (
              <section key={g.key} className="mb-3">
                <h3 className="mono px-3 py-2 text-[11px] uppercase tracking-[0.04em] text-fg-3">{g.day}</h3>
                <ul className="m-0 grid list-none gap-0.5 p-0">
                  {g.items.map((c) => (
                    <CallRow key={c.call_id} summary={c} selected={c.call_id === id} compact={compact} onOpen={() => navigate(`/calls/${c.call_id}`)} />
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      </div>

      {id ? (
        <div className="fixed inset-0 z-30 min-h-0 bg-bg lg:static lg:sticky lg:top-0 lg:z-auto lg:h-[100dvh]">
          {selected ? <CallDrawer key={id} record={selected} onClose={() => navigate("/calls")} prev={prev} next={next} basePath="/calls" /> : <LoadingCall onClose={() => navigate("/calls")} />}
        </div>
      ) : null}
    </div>
  );
}

const CallRow = memo(function CallRow({ summary, live = false, selected, compact, onOpen }: { summary: CallSummary; live?: boolean; selected: boolean; compact: boolean; onOpen: () => void }) {
  const record = useCallRecord(summary.call_id);
  const timeline = record?.timeline ?? null;
  const detail = record?.detail ?? null;
  const outcome = outcomeOf(detail, summary);
  return (
    <li data-row data-call-id={summary.call_id}>
      <button type="button" className="row w-full px-3 py-2.5 text-left" aria-selected={selected} onClick={onOpen}>
        <div className={clsx("grid items-center gap-x-3 gap-y-1.5", "grid-cols-[56px_1fr_auto]", compact ? "md:grid-cols-[56px_minmax(0,1.2fr)_minmax(0,1fr)_64px]" : "md:grid-cols-[56px_minmax(0,1.3fr)_minmax(0,1.6fr)_minmax(0,1.1fr)_72px_64px]")}>
          <Mono className="text-[13px]">{live ? <><span className="sr-only">Elapsed: </span><CallDuration summary={summary} endedAt={timeline?.endedAt} /></> : wallClock(summary.started_at)}</Mono>
          <span className="min-w-0">
            <span className="flex h-[21px] items-center truncate text-[14px] text-fg">{timeline ? <span className="loading-reveal truncate">{callerLabel(timeline)}</span> : record?.detailError ? "Caller unavailable" : <><span className="sr-only">Loading caller</span><span className="loading-skeleton loading-row-title" aria-hidden="true" /></>}</span>
            <span className="mono flex h-[16.5px] items-center truncate text-[11px] text-fg-3 tabular">
              {timeline ? <span className="loading-reveal">{maskPhone(timeline.fromNumber)}</span> : !record?.detailError ? <span className="loading-skeleton h-2.5 w-20" aria-hidden="true" /> : null}
            </span>
          </span>
          <span className="min-w-0 justify-self-end md:hidden">
            {live ? <CallInProgress endedAt={timeline?.endedAt} /> : <Outcome verb={outcome.verb} status={outcome.status} size="sm" />}
          </span>
          <span className="col-span-3 min-w-0 md:col-span-1">
            {live && compact ? <span className="mb-1 hidden md:flex"><CallInProgress endedAt={timeline?.endedAt} /></span> : null}
            <CallStrip timeline={timeline} />
          </span>
          {!compact ? (
            <span className="hidden min-w-0 items-center gap-3 md:flex">
              {live ? <CallInProgress endedAt={timeline?.endedAt} /> : <Outcome verb={outcome.verb} reason={outcome.reason} status={outcome.status} size="sm" />}
            </span>
          ) : null}
          {!compact ? (
            <Mono className="hidden text-[13px] md:block">{live ? <span className="text-fg-3">Ongoing</span> : duration(summary.duration_seconds)}</Mono>
          ) : null}
          <Mono className="hidden text-right text-[13px] md:block"><span className="sr-only">Median response gap: </span>{latency(timeline?.medianResponseGapMs)}</Mono>
        </div>
      </button>
    </li>
  );
});
