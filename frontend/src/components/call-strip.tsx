// A one-line picture of a call for table rows: caller blocks above the axis,
// ROSARIO blocks below, a tick per decision, red for writes and refusals. Pure
// CSS, no audio decode, so twenty rows cost nothing.

import { clsx } from "clsx";
import type { Timeline } from "@/lib/timeline";
import { decisionGlyph } from "./call-timeline";

export function CallStrip({ timeline, progress, className }: { timeline: Timeline | null; progress?: number; className?: string }) {
  if (!timeline) return <span className={clsx("loading-skeleton h-4", className)} aria-hidden="true" />;
  const total = Math.max(1, timeline.horizon);
  const turns = timeline.turns.filter((t) => t.text.length > 0);
  return (
    <span className={clsx("relative block h-4 overflow-hidden rounded-band bg-canvas-deep", className)} aria-hidden="true">
      <span className="absolute inset-x-0 top-1/2 h-px bg-line-1" />
      {turns.map((t, i) => {
        const next = turns[i + 1];
        const end = Math.min(total, next ? next.offset : t.offset + Math.max(1.2, t.text.split(/\s+/).length * 0.36));
        const left = (t.offset / total) * 100;
        const width = Math.max(0.6, ((end - t.offset) / total) * 100);
        return <span key={t.key} className={clsx("absolute h-[6px] rounded-[1px]", t.role === "agent" ? "top-1/2 bg-lane-agent" : "bottom-1/2 bg-lane-caller/70")} style={{ left: `${left}%`, width: `${width}%` }} />;
      })}
      {timeline.decisions.map((d) => {
        const { tone } = decisionGlyph(d);
        return <span key={d.key} className={clsx("absolute top-0 h-full w-px", tone === "write" || tone === "refusal" || tone === "submit" ? "bg-accent-ink" : "bg-fg/70")} style={{ left: `${Math.min(99.5, (d.offset / total) * 100)}%` }} />;
      })}
      {progress != null ? <span className="absolute top-0 h-full w-px bg-fg" style={{ left: `${Math.min(100, (progress / total) * 100)}%` }} /> : null}
    </span>
  );
}
