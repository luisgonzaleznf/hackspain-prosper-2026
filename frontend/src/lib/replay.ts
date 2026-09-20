import type { Timeline, Turn } from "./timeline.ts";

/** Turns whose replay reveal positions have been reached. */
export function turnsUntil(timeline: Timeline, now: number): Turn[] {
  const out: Turn[] = [];
  for (const turn of timeline.turns) {
    if (turn.offset > now) break;
    out.push(turn);
  }
  return out;
}
