// Call detail: live stage or recorded audiogram with decision icons,
// followed by the conversation and Report / Patient / Raw tabs.

import { clsx } from "clsx";
import { CaretLeftIcon } from "@phosphor-icons/react/dist/csr/CaretLeft";
import { CaretRightIcon } from "@phosphor-icons/react/dist/csr/CaretRight";
import { XIcon } from "@phosphor-icons/react/dist/csr/X";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { CallInProgress } from "@/components/call-status";
import { CallTimeline, type TimelineHandle } from "@/components/call-timeline";
import { LoadingConversation, LoadingTimeline } from "@/components/loading";
import { CopyButton, Empty, KeyValue, Label, Mono, Outcome, PillSelect, ReasonCode, VerdictMark } from "@/components/primitives";
import { SelectionIndicator } from "@/components/selection-indicator";
import { StageIndicator } from "@/components/stage";
import { Transcript } from "@/components/transcript";
import { api } from "@/lib/api";
import { attribute, problemOf, verdictFor } from "@/lib/cases";
import { duration, maskNationalId, maskPhone, offset, slotLabel, wallClockSeconds } from "@/lib/format";
import { useSlideIn } from "@/lib/motion";
import { isNoise, outcomeOf, type Decision, type Timeline } from "@/lib/timeline";
import { isActive, loadDetail, type CallRecord } from "@/lib/store";
import type { CallSummary, ClinicAction, RawEvent } from "@/lib/types";

type Tab = "transcript" | "report" | "patient" | "raw";
const TABS: { id: Tab; label: string }[] = [
  { id: "transcript", label: "Transcript" },
  { id: "report", label: "Report" },
  { id: "patient", label: "Patient" },
  { id: "raw", label: "Raw" },
];

export function CallDuration({ summary, endedAt }: { summary: CallSummary; endedAt?: number | null }) {
  const active = isActive(summary);
  const ticking = active && endedAt == null;
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (!ticking) return;
    const timer = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(timer);
  }, [ticking, summary.call_id]);
  const elapsed = active ? (endedAt ?? now) - summary.started_at : summary.duration_seconds ?? (endedAt == null ? null : endedAt - summary.started_at);
  return duration(elapsed);
}

export function CallDrawer({ record, onClose, prev, next, basePath }: { record: CallRecord; onClose: () => void; prev: string | null; next: string | null; basePath: string }) {
  const panel = useRef<HTMLElement>(null);
  useSlideIn(panel, window.matchMedia("(min-width: 1024px)").matches ? "x" : "y");
  const [tab, setTab] = useState<Tab>("transcript");
  const [query, setQuery] = useState("");
  const [expandAll, setExpandAll] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [followAudio, setFollowAudio] = useState(true);
  const controller = useRef<TimelineHandle>(null);
  const [openDecision, setOpenDecision] = useState<{ key: string; request: number } | null>(null);
  const decisionRequest = useRef(0);
  const { summary, detail, timeline, detailError } = record;
  const outcome = outcomeOf(detail, summary);
  const live = isActive(summary);
  const unknown = summary.started_at === 0;

  const current = useMemo(() => {
    if (!timeline) return null;
    let key: string | null = null;
    for (const t of timeline.turns) if (t.offset <= playhead) key = t.key;
    return key;
  }, [timeline, playhead]);

  const onDecision = useCallback((d: Decision) => {
    setTab("transcript");
    setQuery("");
    setExpandAll(false);
    setOpenDecision({ key: d.key, request: ++decisionRequest.current });
  }, []);
  const onPlaying = useCallback((active: boolean) => {
    setPlaying(active);
    if (active) {
      setOpenDecision(null);
      setFollowAudio(true);
    }
  }, []);
  const onSeek = useCallback((seconds: number) => {
    setOpenDecision(null);
    controller.current?.seek(seconds);
  }, []);

  return (
    <section ref={panel} className="scroll-y flex h-full min-h-0 min-w-0 flex-col bg-bg lg:overflow-hidden lg:border-l lg:border-line-1" aria-label={`Call ${summary.call_id}`}>
      <header className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-line-1 px-4 py-3 md:px-6">
        <div className="flex items-center gap-1">
          <Link to={prev ? `${basePath}/${prev}` : "#"} aria-disabled={!prev} className={clsx("pill pill-quiet pill-sm pill-icon", !prev && "pointer-events-none opacity-40")} aria-label="Previous call">
            <CaretLeftIcon size={14} />
          </Link>
          <Link to={next ? `${basePath}/${next}` : "#"} aria-disabled={!next} className={clsx("pill pill-quiet pill-sm pill-icon", !next && "pointer-events-none opacity-40")} aria-label="Next call">
            <CaretRightIcon size={14} />
          </Link>
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[18px] font-light text-fg">{timeline ? callerLabel(timeline) : detailError ? "Call unavailable" : "Loading call"}</h2>
          {!unknown ? <p className="mt-1 text-[12px] text-fg-3">{wallClockSeconds(summary.started_at)} <span className="ml-3 mono tabular"><CallDuration summary={summary} endedAt={timeline?.endedAt} />{live ? " elapsed" : ""}</span></p> : null}
        </div>
        {!unknown ? live ? <CallInProgress endedAt={timeline?.endedAt} /> : <Outcome verb={outcome.verb} reason={outcome.reason} status={outcome.status} /> : null}
        <button type="button" className="pill pill-quiet pill-sm pill-icon" onClick={onClose} aria-label="Close call">
          <XIcon size={14} />
        </button>
      </header>


      {live && timeline ? (
        <div className="shrink-0 border-b border-line-1 px-4 py-3 md:px-6">
          <StageIndicator stage={timeline.stage} size="md" />
        </div>
      ) : detail && timeline && !unknown ? (
        <div className="shrink-0 border-y border-line-1 px-4 py-3 md:px-6">
          <CallTimeline audioUrl={detail.audio ? api.audioUrl(summary.call_id) : null} durationSeconds={detail.audio?.duration_seconds ?? summary.duration_seconds ?? 0} turns={timeline.turns} decisions={timeline.decisions} onTime={setPlayhead} onPlaying={onPlaying} onDecision={onDecision} controller={controller} />
        </div>
      ) : !detail && !detailError ? <div className="shrink-0 border-y border-line-1 px-4 py-3 md:px-6"><LoadingTimeline /></div> : null}

      <div role="tablist" aria-label="Call detail sections" className="relative isolate flex shrink-0 gap-2 overflow-x-auto px-4 py-3 md:px-6">
        <SelectionIndicator activeKey={tab} />
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} className="tab sliding-tab shrink-0" onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="shrink-0 px-4 pb-8 lg:min-h-0 lg:flex-1 lg:overflow-y-auto md:px-6" onWheel={() => { if (playing) setFollowAudio(false); }} onTouchMove={() => { if (playing) setFollowAudio(false); }}>
        {detailError ? <div role="alert" className="py-4 text-[14px] text-fg-2"><p>{detail ? "Updates paused. Showing the last loaded conversation." : "This call could not be loaded."} {detailError}</p><button type="button" className="pill pill-quiet pill-sm mt-3" disabled={retrying} onClick={async () => { setRetrying(true); try { await loadDetail(summary.call_id, true); } finally { setRetrying(false); } }}>{retrying ? "Retrying…" : "Try again"}</button></div> : null}
        {!detail && !detailError ? <LoadingConversation search /> : null}
        {detail && timeline ? (
          <>
            {tab === "transcript" ? <TranscriptTab timeline={timeline} live={live} query={query} onQuery={setQuery} expandAll={expandAll} onExpandAll={setExpandAll} current={current} openDecision={openDecision} onSeek={onSeek} playing={playing} playhead={playhead} followAudio={followAudio} onFollowAudio={setFollowAudio} /> : null}
            {tab === "report" ? <ReportTab record={record} /> : null}
            {tab === "patient" ? <PatientTab timeline={timeline} /> : null}
            {tab === "raw" ? <RawTab events={detail.events} startedAt={timeline.startedAt} /> : null}
          </>
        ) : null}
      </div>
    </section>
  );
}


function TranscriptTab({ timeline, live, query, onQuery, expandAll, onExpandAll, current, openDecision, onSeek, playing, playhead, followAudio, onFollowAudio }: { timeline: Timeline; live: boolean; query: string; onQuery: (v: string) => void; expandAll: boolean; onExpandAll: (v: boolean) => void; current: string | null; openDecision: { key: string; request: number } | null; onSeek: (seconds: number) => void; playing: boolean; playhead: number; followAudio: boolean; onFollowAudio: (value: boolean) => void }) {
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <input className="input min-w-0 flex-1" type="search" placeholder="Search conversation or tools" value={query} onChange={(e) => onQuery(e.target.value)} aria-label="Search conversation or tools" />
        <button type="button" className="pill pill-quiet pill-sm" aria-pressed={expandAll} onClick={() => onExpandAll(!expandAll)}>
          {expandAll ? "Collapse tools" : "Show all tools"}
        </button>
        {playing ? <button type="button" className="pill pill-quiet pill-sm" aria-pressed={followAudio} onClick={() => onFollowAudio(!followAudio)}>{followAudio ? "Following audio" : "Follow audio"}</button> : null}
      </div>
      {live ? <p className="text-[12px] text-fg-3">Scroll to the bottom to follow new turns.</p> : null}
      <Transcript turns={timeline.turns} expandAll={expandAll} query={query} follow={live && !query} activeKey={live ? undefined : current} revealDecision={openDecision} onSeek={live ? undefined : onSeek} followPlayback={!live && playing && followAudio} playbackTime={!live && playing && followAudio && !query ? playhead : undefined} emptyText={live ? "Waiting for the first turn." : "No transcript yet."} />
    </div>
  );
}

function ReportTab({ record }: { record: CallRecord }) {
  const { detail, summary, timeline } = record;
  if (!detail || !timeline) return null;
  const attributed = attribute(summary, timeline);
  const verdict = attributed ? verdictFor(attributed.testCase, detail) : null;
  return (
    <div className="grid gap-6">
      <section>
        <h3 className="text-[16px] font-light text-fg">Call details</h3>
        <div className="mt-2 flex min-w-0 items-center gap-2"><Mono className="break-all">{summary.call_id}</Mono><CopyButton value={summary.call_id} label="Copy call id" /></div>
        <KeyValue className="mt-3" rows={[
          ["started", wallClockSeconds(summary.started_at)],
          ["duration", duration(summary.duration_seconds)],
          ["caller", maskPhone(timeline.fromNumber)],
          ["stage", timeline.stage],
          ["engine", timeline.engine ?? "Not recorded"],
          ["model", timeline.model ?? "Not recorded"],
          ...(timeline.agentSeconds != null ? [["speech", `${Math.round(timeline.agentSeconds)}s ROSARIO / ${timeline.callerSeconds == null ? "not recorded" : `${Math.round(timeline.callerSeconds)}s`} caller`] as [string, string]] : []),
        ]} />
      </section>
      <section>
        <h3 className="text-[16px] font-light text-fg">What was sent</h3>
        {detail.submissions.length === 0 ? <Empty>Nothing submitted yet.</Empty> : null}
        <div className="mt-3 grid gap-3">
          {detail.submissions.map((s, i) => (
            <div key={`${s._line ?? i}`} className="tile px-4 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <Outcome verb={s.action.action} status={s.status} />
                <Mono dim className="ml-auto">
                  {wallClockSeconds(s.t)}
                </Mono>
              </div>
              {s.action.reason ? <ReasonCode code={s.action.reason} className="mt-2" /> : null}
              <ActionTable action={s.action} className="mt-3" />
              <details className="mt-3">
                <summary className="cursor-pointer text-[12px] text-fg-2">Platform reply</summary>
                <pre className="mono mt-2 overflow-x-auto rounded-tags bg-fill-chip p-3 text-[11px] leading-[1.5] text-fg-2">{JSON.stringify(s.response, null, 2)}</pre>
              </details>
            </div>
          ))}
        </div>
      </section>

      {detail.provenance.length > 0 ? (
        <section>
          <h3 className="text-[16px] font-light text-fg">Provenance</h3>
          <div className="mt-3 grid gap-3">
            {detail.provenance.map((chain, i) => (
              <div key={i} className="grid gap-2 md:grid-cols-3">
                <ChainNode label="Lookup evidence" ok={!!chain.lookup}>
                  {chain.lookup ? (
                    <>
                      <span className="mono text-[12px] text-fg">{chain.lookup.name}</span>
                      <KeyValue rows={Object.entries(chain.lookup.args ?? {}).map(([k, v]) => [k, String(v)])} className="mt-2" />
                    </>
                  ) : null}
                </ChainNode>
                <ChainNode label="Recorded action" ok={!!chain.recorded}>
                  {chain.recorded ? <ActionTable action={(chain.recorded as unknown as { action: ClinicAction }).action} /> : null}
                </ChainNode>
                <ChainNode label="Final submit" ok={!!chain.submit}>
                  {chain.submit ? (
                    <>
                      <span className={clsx("mono text-[12px]", chain.submit.status >= 400 ? "text-accent-ink" : "text-fg")}>status {chain.submit.status}</span>
                      <ActionTable action={chain.submit.action} className="mt-2" />
                    </>
                  ) : null}
                </ChainNode>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {attributed && verdict ? (
        <section>
          <h3 className="text-[16px] font-light text-fg">Platform verdict</h3>
          <p className="mt-1 text-[13px] text-fg-2">
            Scored offline with the leaderboard's rules against <span className="mono text-fg">{attributed.testCase.id}</span> ({problemOf(attributed.testCase.problem_id).name}).
          </p>
          <div className="tile mt-3 px-4 py-3">
            <div className="flex items-center gap-3">
              <VerdictMark passed={verdict.passed} signal={verdict.signal} />
              {verdict.matchedAlternative ? <span className="text-[12px] text-fg-2">matched alternative {verdict.matchedAlternative}</span> : null}
            </div>
            {verdict.differences.length > 0 ? (
              <ul className="mono mt-3 grid list-none gap-1 p-0 text-[12px] text-fg-2">
                {verdict.differences.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            ) : null}
            {verdict.leaks.map((l) => (
              <p key={l} className="mono mt-2 text-[12px] text-accent-ink">
                {l}
              </p>
            ))}
            {verdict.caveats.map((c) => (
              <p key={c} className="mt-2 text-[12px] text-fg-3">
                {c}
              </p>
            ))}
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer text-[12px] text-fg-2">Accepted answers for this case</summary>
            <div className="mt-2 grid gap-2">
              {attributed.testCase.expected.acceptable.map((alt, i) => (
                <div key={i} className="tile px-4 py-3">
                  <Label>alternative {i + 1}</Label>
                  {alt.actions.map((a, j) => (
                    <ActionTable key={j} action={a} className="mt-2" />
                  ))}
                </div>
              ))}
            </div>
          </details>
        </section>
      ) : detail.submissions.length > 0 ? (
        <p className="text-[12px] text-fg-3">Not a practice case (no run reference and no unique persona number), so no verdict.</p>
      ) : null}
    </div>
  );
}

function ChainNode({ label, ok, children }: { label: string; ok: boolean; children: React.ReactNode }) {
  return (
    <div className={clsx("tile px-4 py-3", !ok && "border-dashed")}>
      <Label>{label}</Label>
      <div className="mt-2">{ok ? children : <span className="text-[12px] text-fg-3">Not recorded</span>}</div>
    </div>
  );
}

export function ActionTable({ action, className }: { action: ClinicAction; className?: string }) {
  const rows: [string, string][] = [];
  const flat: Record<string, unknown> = { ...action };
  if (action.new_patient && typeof action.new_patient === "object") Object.assign(flat, action.new_patient);
  delete flat.new_patient;
  for (const [k, v] of Object.entries(flat)) {
    if (k === "action" || v == null) continue;
    if (k === "slot") rows.push([k, `${String(v)}  (${slotLabel(String(v))})`]);
    else if (k === "national_id") rows.push([k, `${maskNationalId(String(v))}  ${String(v)}`]);
    else rows.push([k, typeof v === "string" ? v : JSON.stringify(v)]);
  }
  return <KeyValue rows={rows} className={className} />;
}

function PatientTab({ timeline }: { timeline: Timeline }) {
  const find = timeline.decisions.find((d) => d.kind === "tool" && d.label === "find_patient");
  const matches = ((find?.raw as { result?: { matches?: Record<string, unknown>[] } } | undefined)?.result?.matches ?? []) as Record<string, unknown>[];
  const validate = timeline.decisions.filter((d) => d.kind === "tool" && d.label === "validate_registration_details");
  const localRegistration = timeline.decisions.findLast((d) => d.kind === "tool" && d.label === "record_registration" && (d.raw.result as { persisted?: boolean } | undefined)?.persisted === true);
  const registered = (localRegistration?.raw.result as { recorded?: ClinicAction } | undefined)?.recorded ?? timeline.submitted.find((s) => s.action.action === "REGISTER")?.action;
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[13px]">
        <div><Label>caller id</Label><p className="mt-1 text-fg">{maskPhone(timeline.fromNumber)}</p></div>
        <div><Label>number matched</Label><p className="mt-1 text-fg">{timeline.callerIdMatches.length > 0 ? timeline.callerIdMatches.join(", ") : "no record"}</p></div>
      </div>
      {matches.length === 0 && !registered ? <Empty>{timeline.matchCount === 0 ? "The lookup found no matching patient." : "No patient lookup ran on this call."}</Empty> : null}
      {matches.length > 1 ? <p className="text-[13px] text-fg-2">{matches.length} matches. ROSARIO had to disambiguate before acting.</p> : null}
      {matches.map((m, i) => (
        <article key={i} className="card px-5 py-4 md:px-6">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="text-[20px] font-light text-fg">{String(m.name)}</h3>
            <Mono>{String(m.patient_id)}</Mono>
            {typeof m.plan_on_file === "string" ? <span className="text-[13px] text-fg-2">{m.plan_on_file}</span> : null}
          </div>
          <KeyValue
            className="mt-3"
            rows={[
              ["date_of_birth", `${String(m.date_of_birth)} (${String(m.age)})`],
              ["has_visited_before", String(m.has_visited_before)],
              ["matched_on", Array.isArray(m.matched_on) ? (m.matched_on as string[]).join(", ") : "\u2013"],
              ["referrals", Array.isArray(m.referrals) && (m.referrals as string[]).length > 0 ? (m.referrals as string[]).join(", ") : "none"],
            ]}
          />
          {typeof m.note === "string" && m.note ? (
            <blockquote className="mt-4 border-l border-line-2 pl-4 text-[14px] leading-[1.6] text-fg-2">
              <Label className="block">record note</Label>
              <span className="mt-1 block text-fg">{m.note}</span>
            </blockquote>
          ) : null}
        </article>
      ))}
      {registered ? (
        <article className="card px-5 py-4 md:px-6">
          <div className="flex items-baseline gap-3">
            <h3 className="text-[20px] font-light text-fg">
              {String(registered.given_name ?? "")} {String(registered.first_surname ?? "")} {String(registered.second_surname ?? "")}
            </h3>
            <span className="text-[13px] text-fg-2">new patient</span>
          </div>
          <ActionTable action={registered} className="mt-3" />
          {validate.length > 0 ? <p className="mono mt-3 text-[11px] text-fg-3">{validate.length} validation call(s) before registering</p> : null}
        </article>
      ) : null}
    </div>
  );
}

function RawTab({ events, startedAt }: { events: RawEvent[]; startedAt: number }) {
  const [showNoise, setShowNoise] = useState(false);
  const [kind, setKind] = useState<string>("");
  const kinds = useMemo(() => [...new Set(events.map((e) => e.kind))].sort(), [events]);
  const filtered = events.filter((e) => (showNoise || !isNoise(e)) && (!kind || e.kind === kind));
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="w-[240px]">
          <PillSelectKind value={kind} onChange={setKind} kinds={kinds} />
        </div>
        <button type="button" className="tab" aria-pressed={showNoise} onClick={() => setShowNoise((v) => !v)}>
          {showNoise ? "Hide transport events" : "Show transport events"}
        </button>
        <Mono dim className="ml-auto">
          {filtered.length} / {events.length}
        </Mono>
        <CopyButton value={events.map((e) => JSON.stringify(e)).join("\n")} label="Copy JSONL" />
      </div>
      <ol className="m-0 grid list-none gap-1.5 p-0">
        {filtered.map((e, i) => {
          const body = Object.fromEntries(Object.entries(e).filter(([k]) => !["t", "kind", "_line"].includes(k)));
          return (
            <li key={`${e._line ?? i}`} className="tile px-3 py-2">
              <div className="flex flex-wrap items-center gap-3">
                <Mono dim>{offset(e.t - startedAt)}</Mono>
                <span className="mono text-[12px] text-fg">{e.kind}</span>
                <Mono dim className="ml-auto">
                  line {e._line ?? "?"}
                </Mono>
              </div>
              {Object.keys(body).length > 0 ? <pre className="mono mt-2 max-h-[240px] overflow-auto whitespace-pre-wrap break-words text-[11px] leading-[1.5] text-fg-2">{JSON.stringify(body, null, 2)}</pre> : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function PillSelectKind({ value, onChange, kinds }: { value: string; onChange: (v: string) => void; kinds: string[] }) {
  return <PillSelect value={value} onChange={onChange} label="Filter by event kind" options={[{ value: "", label: "All kinds" }, ...kinds.map((k) => ({ value: k, label: k }))]} />;
}

export function callerLabel(timeline: Timeline | null): string {
  if (!timeline) return "connecting";
  if (timeline.identified) return timeline.identified.name;
  if (timeline.matchCount != null && timeline.matchCount > 1) return `${timeline.matchCount} matches`;
  if (timeline.matchCount === 0) return "not in records";
  const registered = timeline.submitted.find((s) => s.action.action === "REGISTER")?.action;
  if (registered) return `${String(registered.given_name ?? "")} ${String(registered.first_surname ?? "")}`.trim();
  return timeline.stage === "GREET" || timeline.stage === "IDENTIFY" ? "identifying" : "unknown caller";
}
