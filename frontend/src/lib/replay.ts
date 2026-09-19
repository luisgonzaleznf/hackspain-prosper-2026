// Replay: play a finished call's timeline against a clock so the Live board
// and Talk page show a call "happening" with fixture data. Named as replay in
// the UI header wherever it drives a screen; it never masquerades as live.

import { useEffect, useRef, useState } from "react";
import type { Timeline, Turn } from "./timeline.ts";

export interface ReplayState {
  /** Seconds since call start on the replay clock. */
  now: number;
  playing: boolean;
  done: boolean;
}

export interface ReplayControls extends ReplayState {
  play: () => void;
  pause: () => void;
  seek: (s: number) => void;
  restart: () => void;
}

const clocks = new Map<string, { start: number; paused: number | null; listeners: Set<() => void> }>();

function clockFor(id: string) {
  let c = clocks.get(id);
  if (!c) {
    c = { start: performance.now(), paused: null, listeners: new Set() };
    clocks.set(id, c);
  }
  return c;
}

/** Restart every replay clock (the board's Restart button). */
export function restartReplays(): void {
  const now = performance.now();
  for (const c of clocks.values()) {
    c.start = now;
    c.paused = null;
    for (const l of c.listeners) l();
  }
}

/**
 * Replay clock for one call. Shared by id: a row and the drawer opened from it
 * read the same elapsed time. Loops when the call ends plus two seconds.
 */
export function useReplayClock(id: string | null, timeline: Timeline | null, options: { autoplay: boolean; speed?: number; loop?: boolean }): ReplayControls {
  const total = timeline ? timeline.horizon + 2 : 0;
  const speed = options.speed ?? 1;
  const [, force] = useState(0);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    if (!id || !timeline) return;
    const clock = clockFor(id);
    const listener = () => force((n) => n + 1);
    clock.listeners.add(listener);
    if (!options.autoplay && clock.paused == null) clock.paused = performance.now();
    const step = () => {
      if (clock.paused == null) {
        const elapsed = ((performance.now() - clock.start) / 1000) * speed;
        if (elapsed >= total && total > 0) {
          if (options.loop) clock.start = performance.now();
          else clock.paused = performance.now();
        }
        force((n) => n + 1);
      }
      frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
    return () => {
      clock.listeners.delete(listener);
      if (frame.current != null) cancelAnimationFrame(frame.current);
    };
  }, [id, timeline, total, speed, options.loop, options.autoplay]);

  const clock = id ? clockFor(id) : null;
  const now = clock ? Math.min(total, (((clock.paused ?? performance.now()) - clock.start) / 1000) * speed) : 0;
  const playing = !!clock && clock.paused == null;
  const notify = () => {
    if (clock) for (const l of clock.listeners) l();
  };
  return {
    now,
    playing,
    done: !playing && now >= total && total > 0,
    play: () => {
      if (!clock || clock.paused == null) return;
      clock.start += performance.now() - clock.paused;
      clock.paused = null;
      notify();
    },
    pause: () => {
      if (!clock || clock.paused != null) return;
      clock.paused = performance.now();
      notify();
    },
    seek: (s) => {
      if (!clock) return;
      const at = clock.paused ?? performance.now();
      clock.start = at - (Math.max(0, Math.min(total, s)) / speed) * 1000;
      notify();
    },
    restart: () => {
      if (!clock) return;
      clock.start = performance.now();
      clock.paused = null;
      notify();
    },
  };
}

/** Turns whose replay reveal positions have been reached. */
export function turnsUntil(timeline: Timeline, now: number): Turn[] {
  const out: Turn[] = [];
  for (const turn of timeline.turns) {
    if (turn.offset > now) break;
    out.push(turn);
  }
  return out;
}

/** Who is speaking at replay time `now`: agent turns last until the next turn or 3.5s. */
export function speakerAt(timeline: Timeline, now: number): "agent" | "caller" | null {
  let current: Turn | null = null;
  let next: Turn | null = null;
  for (const turn of timeline.turns) {
    if (turn.offset <= now) current = turn;
    else {
      next = turn;
      break;
    }
  }
  if (!current || current.text.length === 0) return null;
  const words = current.text.split(/\s+/).length;
  const spoken = Math.min(next ? next.offset - current.offset : Infinity, Math.max(1.2, words * 0.36));
  return now - current.offset < spoken ? current.role : null;
}
