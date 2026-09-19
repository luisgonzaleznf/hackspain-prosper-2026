// Live board: every open socket as a row, click a row for the live drawer.
// Active calls poll their detail every 1.5s. When nothing is live, the board
// replays finished calls against a shared clock and says "replay" everywhere.

import { clsx } from "clsx";
import { Activity, AudioLines, Pause, Play, RotateCcw, X } from "lucide-react";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ScreenHeader } from "@/app";
import { CallStrip } from "@/components/call-strip";
import { LoadingConversation, LoadingRows } from "@/components/loading";
import { Orb } from "@/components/orb";
import { Empty, Label, Mono, Outcome, SwapText } from "@/components/primitives";
import { StageIndicator, stageLabel } from "@/components/stage";
import { DecisionCard, Transcript } from "@/components/transcript";
import { duration, latency, maskPhone } from "@/lib/format";
import { useSlideIn } from "@/lib/motion";
import { restartReplays, speakerAt, turnsUntil, useReplayClock, type ReplayControls } from "@/lib/replay";
import { isActive, loadDetail, refreshNow, useCallRecord, useCallsIndex, type CallRecord } from "@/lib/store";
import type { Stage, Timeline, Turn } from "@/lib/timeline";
import type { ClinicAction } from "@/lib/types";
import { ActionTable, callerLabel } from "@/screens/calls/detail";

const REPLAY_ROWS = 6;

interface LiveRowModel {
  id: string;
  mode: "live" | "replay";
}

export function LiveScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { calls, loading, error, loadedAt } = useCallsIndex();
  const active = useMemo(() => calls.filter(isActive), [calls]);
  const [replayOn, setReplayOn] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const replayIds = useMemo(() => {
    if (!replayOn || active.length > 0) return [];
    return calls
      .filter((c) => !isActive(c) && c.has_audio && (c.duration_seconds ?? 0) > 40)
      .slice(0, REPLAY_ROWS)
      .map((c) => c.call_id);
  }, [calls, replayOn, active.length]);

  useEffect(() => {
    for (const rid of replayIds) void loadDetail(rid);
  }, [replayIds]);

  const rows: LiveRowModel[] = [...active.map((c) => ({ id: c.call_id, mode: "live" as const })), ...replayIds.map((rid) => ({ id: rid, mode: "replay" as const }))];
  const selectedMode = rows.find((r) => r.id === id)?.mode ?? "replay";

  return (
    <div className={clsx("flex min-h-0 flex-1 flex-col", id && "lg:grid lg:grid-cols-[minmax(400px,4fr)_minmax(560px,8fr)]")}>
      <div className={clsx("flex min-h-0 flex-1 flex-col", id && "hidden lg:flex")}>
        <ScreenHeader
          title="Live"
          action={
            loadedAt != null && active.length === 0 ? (
              <div className="flex items-center gap-2">
                <button type="button" className="pill pill-quiet pill-sm" onClick={restartReplays} aria-label="Restart replay">
                  <RotateCcw size={14} strokeWidth={1.75} /> Restart
                </button>
                <button type="button" className="pill pill-ghost pill-sm" aria-pressed={replayOn} onClick={() => setReplayOn((v) => !v)}>
                  {replayOn ? "Hide replay" : "Show replay"}
                </button>
              </div>
            ) : null
          }
        >
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[12px] text-fg-2">
            <span className="inline-flex items-center gap-2">
              <Activity size={14} strokeWidth={1.5} />
              {loadedAt == null ? <span>{error ? "Connection unavailable" : "Connecting"}</span> : <><Mono>{active.length}</Mono> live</>}
            </span>
            {replayIds.length > 0 ? (
              <span className="inline-flex items-center gap-2">
                <Play size={13} strokeWidth={1.5} />
                <Mono>{replayIds.length}</Mono> replayed from recordings
              </span>
            ) : null}
          </div>
        </ScreenHeader>

        <div className="scroll-y flex-1 px-2 pb-24 pt-2 md:px-8 md:pb-8">
          <div className="measure">
            {error ? <div role="alert" className="py-4 text-[14px] text-fg-2"><p>{loadedAt == null ? "Live calls could not be loaded." : "Updates paused. Showing the last loaded calls."} {error}</p><button type="button" className="pill pill-quiet pill-sm mt-2" disabled={refreshing} onClick={async () => { setRefreshing(true); try { await refreshNow(); } finally { setRefreshing(false); } }}>{refreshing ? "Retrying…" : "Try again"}</button></div> : null}
            {loading && !error ? <LoadingRows label="Loading live calls" rows={3} live /> : null}
            {loadedAt != null && rows.length === 0 ? <Empty>No active calls. Use Show replay to review a recording.</Empty> : null}
            <div className={clsx("grid-cols-[28px_56px_minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1.2fr)_64px] gap-3 px-3 pb-2", rows.length > 0 ? "hidden md:grid" : "hidden")} aria-hidden="true">
              <span />
              <Label>elapsed</Label>
              <Label>caller</Label>
              <Label>call</Label>
              <Label>stage</Label>
              <Label className="text-right">p50 gap</Label>
            </div>
            <ul className="m-0 grid list-none gap-0.5 p-0">
              {rows.map((row) => (
                <LiveRow key={`${row.id}-${row.mode}`} id={row.id} mode={row.mode} selected={row.id === id} onOpen={() => navigate(`/live/${row.id}`)} />
              ))}
            </ul>
          </div>
        </div>
      </div>

      {id ? (
        <div className="fixed inset-0 z-30 min-h-0 bg-bg lg:static lg:sticky lg:top-0 lg:z-auto lg:h-[100dvh]">
          <LiveDrawer key={id} id={id} mode={selectedMode} onClose={() => navigate("/live")} />
        </div>
      ) : null}
    </div>
  );
}

interface RowClock {
  elapsed: number;
  visibleTurns: Turn[];
  speaker: "agent" | "caller" | null;
  stage: Stage;
  timeline: Timeline | null;
  replay: ReplayControls;
}

/** Live: elapsed from the backend's clock. Replay: from the shared replay clock. */
function useRowClock(id: string, record: CallRecord | null, mode: "live" | "replay"): RowClock {
  const timeline = record?.timeline ?? null;
  const replay = useReplayClock(mode === "replay" ? id : null, mode === "replay" ? timeline : null, { autoplay: true, loop: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (mode !== "live") return;
    const t = window.setInterval(() => setTick((n) => n + 1), 500);
    return () => window.clearInterval(t);
  }, [mode]);
  if (!timeline) return { elapsed: 0, visibleTurns: [], speaker: null, stage: "GREET", timeline: null, replay };
  if (mode === "live") {
    void tick;
    const elapsed = (timeline.endedAt ?? Date.now() / 1000) - timeline.startedAt;
    const last = timeline.turns[timeline.turns.length - 1];
    const speaker = last && last.text && Date.now() / 1000 - last.t < 4 ? last.role : null;
    return { elapsed, visibleTurns: timeline.turns, speaker, stage: timeline.stage, timeline, replay };
  }
  const visibleTurns = turnsUntil(timeline, replay.now);
  return { elapsed: replay.now, visibleTurns, speaker: speakerAt(timeline, replay.now), stage: stageAt(timeline, visibleTurns[visibleTurns.length - 1]), timeline, replay };
}

function stageAt(timeline: Timeline, lastVisible: Turn | undefined): Stage {
  if (!lastVisible) return "GREET";
  const seen = timeline.turns.filter((t) => t.offset <= lastVisible.offset).flatMap((t) => t.decisions);
  let stage: Stage = timeline.turns.indexOf(lastVisible) > 0 ? "IDENTIFY" : "GREET";
  for (const d of seen) {
    if (d.kind === "tool" && d.label === "find_patient") stage = "LOOKUP";
    else if (d.kind === "tool" && d.label === "search_availability") stage = "OFFER";
    else if (d.kind === "staged") stage = "CONFIRM";
    else if (d.kind === "tool" && d.label.startsWith("record_")) stage = "WRITE";
    else if (d.kind === "submit") stage = d.label.includes("ESCALATE") ? "ESCALATE" : "CLOSE";
    else if (d.kind === "fallback" && d.label.includes("ESCALATE")) stage = "ESCALATE";
  }
  if (lastVisible.key === "turn-close") stage = stage === "ESCALATE" ? stage : "CLOSE";
  return stage;
}

/** Replay context, with the recorded call median withheld until the replay ends. */
function partialTimeline(timeline: Timeline | null, visible: Turn[], elapsed: number): Timeline | null {
  if (!timeline) return null;
  if (elapsed >= timeline.horizon) return timeline;
  const seen = visible.flatMap((t) => t.decisions);
  const find = seen.find((d) => d.kind === "tool" && d.label === "find_patient");
  const submitted = seen.some((d) => d.kind === "submit") ? timeline.submitted : [];
  if (!find) return { ...timeline, identified: null, matchCount: null, submitted, stage: "IDENTIFY", medianResponseGapMs: null };
  return { ...timeline, submitted, medianResponseGapMs: null };
}

const LiveRow = memo(function LiveRow({ id, mode, selected, onOpen }: { id: string; mode: "live" | "replay"; selected: boolean; onOpen: () => void }) {
  const record = useCallRecord(id);
  const { elapsed, visibleTurns, speaker, stage, timeline } = useRowClock(id, record, mode);
  const partial = mode === "live" ? timeline : partialTimeline(timeline, visibleTurns, elapsed);
  const lastCaller = [...visibleTurns].reverse().find((t) => t.role === "caller");
  return (
    <li data-row>
      <button type="button" className={clsx("row w-full px-3 py-2.5 text-left", speaker === "agent" && "row-live")} aria-selected={selected} onClick={onOpen}>
        <div className="grid grid-cols-[28px_56px_1fr] items-center gap-x-3 gap-y-1.5 md:grid-cols-[28px_56px_minmax(0,1.2fr)_minmax(0,1.4fr)_minmax(0,1.2fr)_64px]">
          <AudioLines size={19} strokeWidth={1.5} className={speaker === "agent" ? "text-lane-agent" : speaker === "caller" ? "text-lane-caller" : "text-fg-3"} aria-label={speaker === "agent" ? "ROSARIO speaking" : speaker === "caller" ? "Caller speaking" : "Listening"} />
          <Mono className="text-[13px] text-fg">{timeline ? duration(elapsed) : "…"}</Mono>
          <span className="min-w-0">
            <span className="flex h-[21px] items-center truncate text-[14px] text-fg">
              {timeline ? <SwapText text={callerLabel(partial)} className="truncate" /> : record?.detailError ? "Caller unavailable" : <><span className="sr-only">Loading caller</span><span className="loading-skeleton loading-row-title" aria-hidden="true" /></>}
            </span>
            <span className="mono flex h-[16.5px] items-center truncate text-[11px] text-fg-3 tabular">
              {timeline ? maskPhone(timeline.fromNumber) : !record?.detailError ? <span className="loading-skeleton h-2.5 w-20" aria-hidden="true" /> : null}
            </span>
          </span>
          <span className="col-span-3 min-w-0 md:col-span-1">
            <CallStrip timeline={timeline} progress={elapsed} />
          </span>
          <span className="col-span-3 flex min-w-0 items-center justify-between gap-3 md:col-span-1 md:justify-start">
            {timeline ? <StageIndicator stage={stage} /> : record?.detailError ? <span className="text-[12px] text-fg-3">Unavailable</span> : <><span className="sr-only">Loading stage</span><span className="loading-skeleton h-3 w-20" aria-hidden="true" /></>}
            {lastCaller ? <span className="hidden min-w-0 truncate text-[12px] text-fg-3 xl:inline">{lastCaller.text}</span> : null}
          </span>
          <Mono className="hidden text-right text-[13px] md:block"><span className="sr-only">Median response gap: </span>{latency(partial?.medianResponseGapMs)}</Mono>
        </div>
      </button>
    </li>
  );
});

function LiveDrawer({ id, mode, onClose }: { id: string; mode: "live" | "replay"; onClose: () => void }) {
  const record = useCallRecord(id);
  useEffect(() => {
    void loadDetail(id);
  }, [id]);
  const panel = useRef<HTMLElement>(null);
  useSlideIn(panel, window.matchMedia("(min-width: 1024px)").matches ? "x" : "y");
  const { elapsed, visibleTurns, speaker, stage, timeline, replay } = useRowClock(id, record, mode);
  const partial = mode === "live" ? timeline : partialTimeline(timeline, visibleTurns, elapsed);
  const decisions = visibleTurns.flatMap((t) => t.decisions);
  const staged = decisions.filter((d) => d.kind === "staged");
  const submitted = decisions.filter((d) => d.kind === "submit");
  const stagedNow = staged.length > 0 && submitted.length === 0 ? ((staged[staged.length - 1]?.raw as unknown as { all_staged?: ClinicAction[] } | undefined)?.all_staged ?? []) : [];
  const wouldSubmit = mode === "live" ? (timeline?.pending.length ? timeline.pending : stagedNow) : stagedNow;
  const [contextOpen, setContextOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const orbState = speaker === "agent" ? "speaking" : speaker === "caller" ? "listening" : stage === "CLOSE" || stage === "ESCALATE" ? "disconnected" : "thinking";

  return (
    <section ref={panel} className="flex h-full min-h-0 flex-col bg-bg lg:border-l lg:border-line-1" aria-label={`Live call ${id}`}>
      <header className="flex items-center gap-3 border-b border-line-1 px-4 py-3 md:px-6">
        <Orb size={44} state={orbState} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-3">
            <span className="truncate text-[18px] font-light text-fg">
              <SwapText text={timeline ? callerLabel(partial) : record?.detailError ? "Call unavailable" : "Loading call"} />
            </span>
            <Mono className="text-[14px] text-fg">{duration(elapsed)}</Mono>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-fg-3">
            <SwapText text={!timeline ? record?.detailError ? "Connection unavailable" : "Loading conversation" : mode === "live" ? (speaker === "agent" ? "ROSARIO speaking" : speaker === "caller" ? "Caller speaking" : stageLabel(stage)) : `Replay, ${speaker === "agent" ? "ROSARIO speaking" : speaker === "caller" ? "caller speaking" : stageLabel(stage).toLowerCase()}`} />
            <Mono dim className="hidden truncate lg:inline">
              {id}
            </Mono>
          </div>
        </div>
        <button type="button" className="pill pill-quiet pill-sm lg:hidden" aria-pressed={contextOpen} onClick={() => setContextOpen((v) => !v)}>
          {contextOpen ? "Transcript" : "Context"}
        </button>
        {mode === "replay" && timeline ? (
          <button type="button" className="pill pill-quiet pill-sm pill-icon" onClick={() => (replay.playing ? replay.pause() : replay.play())} aria-label={replay.playing ? "Pause replay" : "Play replay"}>
            {replay.playing ? <Pause size={14} strokeWidth={1.75} /> : <Play size={14} strokeWidth={1.75} />}
          </button>
        ) : null}
        <button type="button" className="pill pill-quiet pill-sm pill-icon" onClick={onClose} aria-label="Close">
          <X size={14} strokeWidth={1.75} />
        </button>
      </header>

      <div className="border-b border-line-1 px-4 py-2 md:px-6">
        <StageIndicator stage={stage} size="md" />
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[1fr_320px]">
        <div className={clsx("scroll-y min-h-0 px-4 pb-6 pt-2 md:px-6", contextOpen && "hidden lg:block")}>
          {record?.detailError ? <div role="alert" className="py-4 text-[14px] text-fg-2"><p>Call updates are unavailable. {record.detailError}</p><button type="button" className="pill pill-quiet pill-sm mt-2" disabled={retrying} onClick={async () => { setRetrying(true); try { await loadDetail(id, true); } finally { setRetrying(false); } }}>{retrying ? "Retrying…" : "Try again"}</button></div> : !timeline ? <LoadingConversation /> : null}
          {timeline ? <Transcript turns={visibleTurns} follow emptyText="Waiting for the first turn." /> : null}
        </div>

        <aside className={clsx("scroll-y min-h-0 px-4 py-4 lg:block lg:border-l lg:border-line-1", contextOpen ? "block" : "hidden")}>
          <Label>patient</Label>
          <p className="mt-1 text-[16px] font-light text-fg">
            <SwapText text={callerLabel(partial)} />
          </p>
          {partial?.identified ? (
            <>
              <p className="mt-1 flex flex-wrap gap-x-3 text-[12px]">
                <Mono>{partial.identified.patient_id}</Mono>
                {partial.identified.plan ? <span className="text-fg-2">{partial.identified.plan}</span> : null}
              </p>
              {partial.identified.note ? <p className="mt-3 text-[13px] leading-[1.6] text-fg-2">{partial.identified.note}</p> : null}
            </>
          ) : null}

          <div className="mt-6">
            <Label>pending actions</Label>
            {staged.length === 0 ? <p className="mt-1 text-[13px] text-fg-3">None staged yet.</p> : null}
            <div className="mt-2 grid gap-2">
              {staged.slice(-2).map((d) => (
                <DecisionCard key={d.key} decision={d} compact />
              ))}
            </div>
          </div>

          {timeline?.engine ? (
            <div className="mt-6">
              <Label>engine</Label>
              <p className="mono mt-1 text-[12px] text-fg-2">{timeline.model ?? timeline.engine}</p>
              <p className="mono mt-1 text-[12px] text-fg-3 tabular">median response gap {latency(partial?.medianResponseGapMs)}</p>
            </div>
          ) : null}

          {timeline && wouldSubmit.length > 0 ? (
            <div className="mt-6">
              <Label>report, if the call ended now</Label>
              <div className="mt-2 grid gap-2">
                {wouldSubmit.map((a, i) => (
                  <div key={i} className="tile px-3 py-2.5">
                    <Outcome verb={a.action} size="sm" />
                    <ActionTable action={a} className="mt-2" />
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {submitted.length > 0 ? (
            <div className="mt-6">
              <Label>submitted</Label>
              <div className="mt-2 grid gap-2">
                {submitted.map((d) => (
                  <DecisionCard key={d.key} decision={d} compact />
                ))}
              </div>
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
