import { clsx } from "clsx";
import { CaretDownIcon } from "@phosphor-icons/react/dist/csr/CaretDown";
import { memo, useEffect, useLayoutEffect, useRef, useState } from "react";
import { decisionGlyph } from "./call-timeline";
import { KeyValue, ReasonCode, ToolName } from "./primitives";
import { offset } from "@/lib/format";
import type { Decision, Turn } from "@/lib/timeline";
import "./call-review.css";

export const DecisionCard = memo(function DecisionCard({ decision, compact }: { decision: Decision; compact?: boolean }) {
  const { Icon, tone, title } = decisionGlyph(decision);
  const reason = decision.fields.find(([k]) => k === "reason" || k === "recorded.reason")?.[1];
  const fields = decision.fields.filter(([k]) => k !== "gloss" && !(reason && (k === "reason" || k === "recorded.reason")));
  return (
    <article className="review-decision" data-decision={decision.key} aria-label={`${title} ${decision.label}`}>
      <header className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Icon size={14} className={clsx("shrink-0", tone === "refusal" ? "text-accent-ink" : "text-fg-2")} aria-hidden="true" />
        <span className="text-[13px] text-fg">{title}</span>
        <span className="mono ml-auto text-[11px] text-fg-3 tabular">{offset(decision.offset)}</span>
      </header>
      {decision.kind === "tool" ? <div className="mt-1"><ToolName name={decision.label} /></div> : null}
      {reason ? <ReasonCode code={reason} className="mt-2" /> : null}
      {fields.length > 0 ? <KeyValue rows={compact ? fields.slice(0, 6) : fields} className="mt-3" /> : null}
      {compact && fields.length > 6 ? <p className="mono mt-2 text-[11px] text-fg-3">{fields.length - 6} more fields in the call detail</p> : null}
    </article>
  );
});

export const TranscriptTurn = memo(function TranscriptTurn({
  turn,
  open,
  onToggle,
  expandAll,
  highlight,
  active = false,
  onSeek,
}: {
  turn: Turn;
  open: boolean;
  onToggle: (key: string) => void;
  expandAll: boolean;
  highlight?: string;
  active?: boolean;
  onSeek?: (seconds: number) => void;
}) {
  const hasDecisions = turn.decisions.length > 0;
  const expanded = expandAll || open;
  const isClose = turn.text.length === 0 && turn.key === "turn-close";
  const isOpen = turn.text.length === 0 && turn.key === "turn-open";
  const speaker = turn.role === "agent" ? "ROSARIO" : "Caller";
  const message = isClose ? "After the call" : isOpen ? "Working on the request" : turn.text;
  const interactive = !!onSeek || hasDecisions;
  return (
    <li data-turn={turn.key} aria-current={active ? "true" : undefined} className={clsx("chat-turn", turn.role === "agent" ? "chat-turn-agent" : "chat-turn-caller", !turn.text && "chat-turn-event")}>
      <div className="chat-identity">
        <span>{speaker}</span>
        <span className="mono tabular">{offset(turn.offset)}</span>
        {active ? <span className="chat-current">Current</span> : null}
      </div>
      {interactive ? (
        <button type="button" className="chat-bubble chat-bubble-action" onClick={() => onSeek ? onSeek(turn.offset) : onToggle(turn.key)} aria-label={onSeek ? `Seek to ${speaker} at ${offset(turn.offset)}: ${message}` : `${expanded ? "Hide" : "Show"} decisions for ${speaker}: ${message}`} aria-expanded={!onSeek && hasDecisions ? expanded : undefined}>
          <Highlight text={message} query={highlight} />
        </button>
      ) : <div className="chat-bubble"><Highlight text={message} query={highlight} /></div>}
      {hasDecisions ? (
        <button type="button" className="chat-decisions-toggle" aria-expanded={expanded} onClick={() => onToggle(turn.key)}>
          <CaretDownIcon size={14} className={clsx("chat-chevron", expanded && "chat-chevron-open")} aria-hidden="true" />
          <span>{turn.decisions.length === 1 ? decisionGlyph(turn.decisions[0]!).title : `${turn.decisions.length} decisions`}</span>
        </button>
      ) : null}
      {hasDecisions && expanded ? <div className="chat-decisions">{turn.decisions.map((decision) => <DecisionCard key={decision.key} decision={decision} />)}</div> : null}
    </li>
  );
});

function Highlight({ text, query }: { text: string; query?: string }) {
  if (!query) return <>{text}</>;
  const index = text.toLowerCase().indexOf(query.toLowerCase());
  if (index < 0) return <>{text}</>;
  return <>{text.slice(0, index)}<mark className="chat-match">{text.slice(index, index + query.length)}</mark>{text.slice(index + query.length)}</>;
}

export function Transcript({
  turns,
  expandAll = false,
  query,
  follow = false,
  className,
  emptyText = "No transcript yet.",
  activeKey,
  revealDecision,
  onSeek,
  followPlayback = true,
  playbackTime,
}: {
  turns: Turn[];
  expandAll?: boolean;
  query?: string;
  follow?: boolean;
  activeKey?: string | null;
  revealDecision?: { key: string; request: number } | null;
  onSeek?: (seconds: number) => void;
  followPlayback?: boolean;
  playbackTime?: number;
  className?: string;
  emptyText?: string;
}) {
  const [open, setOpen] = useState<Record<string, true>>({});
  const list = useRef<HTMLOListElement>(null);
  const scroller = useRef<HTMLElement | null>(null);
  const pinnedToBottom = useRef(true);
  const count = turns.length;
  const autoFollow = follow && activeKey === undefined;
  const hasTurns = count > 0;
  const revealedTurnKey = revealDecision
    ? turns.find((turn) => turn.decisions.some((decision) => decision.key === revealDecision.key))?.key
    : undefined;
  useLayoutEffect(() => {
    if (!list.current) return;
    let parent = list.current.parentElement;
    while (parent && !/^(auto|scroll)$/.test(getComputedStyle(parent).overflowY)) parent = parent.parentElement;
    if (!parent) return;
    const container = parent;
    scroller.current = container;
    pinnedToBottom.current = true;
    const onScroll = () => {
      pinnedToBottom.current = container.scrollHeight - container.clientHeight - container.scrollTop <= 48;
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      container.removeEventListener("scroll", onScroll);
      scroller.current = null;
    };
  }, [autoFollow, hasTurns, query]);
  useLayoutEffect(() => {
    const container = scroller.current;
    // New turns follow only readers already at the bottom; returning there resumes it.
    if (autoFollow && pinnedToBottom.current && container) container.scrollTop = container.scrollHeight;
  }, [count, autoFollow]);
  useLayoutEffect(() => {
    if (revealedTurnKey) setOpen((previous) => previous[revealedTurnKey] ? previous : { ...previous, [revealedTurnKey]: true });
  }, [revealedTurnKey, revealDecision]);
  const focusKey = followPlayback ? activeKey : null;
  const decisionReady = !revealedTurnKey || expandAll || !!open[revealedTurnKey];
  useEffect(() => {
    const targetKey = revealDecision?.key ?? focusKey;
    if (!targetKey || !decisionReady || !list.current || query) return;
    const selector = revealDecision ? "data-decision" : "data-turn";
    const target = list.current.querySelector<HTMLElement>(`[${selector}="${CSS.escape(targetKey)}"]`);
    if (!target) return;
    // Resolve at navigation time: resizing switches between pane and drawer scrolling.
    let container = target.parentElement;
    while (container && (container.scrollHeight <= container.clientHeight || !/^(auto|scroll)$/.test(getComputedStyle(container).overflowY))) container = container.parentElement;
    if (!container) return;
    const bounds = container.getBoundingClientRect();
    const targetBounds = target.getBoundingClientRect();
    const inset = revealDecision ? 16 : Math.max(16, (container.clientHeight - targetBounds.height) / 2);
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
    container.scrollTo({ top: container.scrollTop + targetBounds.top - bounds.top - inset, behavior });
  }, [focusKey, revealDecision, decisionReady, query]);
  const needle = query?.toLowerCase();
  const visible = playbackTime === undefined || revealDecision ? turns : turns.filter((turn) => turn.offset <= playbackTime);
  const filtered = needle ? visible.filter((turn) => turn.text.toLowerCase().includes(needle) || turn.decisions.some((decision) => decision.label.toLowerCase().includes(needle) || decision.fields.some(([key, value]) => `${key} ${value}`.toLowerCase().includes(needle)))) : visible;
  if (filtered.length === 0) return <p className="py-6 text-[14px] text-fg-2">{query ? "Nothing in the transcript matches." : emptyText}</p>;
  return (
    <ol ref={list} className={clsx("chat-conversation", className)}>
      {filtered.map((turn) => (
        <TranscriptTurn key={turn.key} turn={turn} open={turn.key in open} expandAll={expandAll} onToggle={(key) => setOpen((previous) => {
          const next = { ...previous };
          if (key in next) delete next[key];
          else next[key] = true;
          return next;
        })} highlight={query} active={turn.key === activeKey} onSeek={onSeek} />
      ))}
    </ol>
  );
}
