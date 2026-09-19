// The call as a video-editor timeline: an audiogram of both lanes across the
// full width (caller above the axis, ROSARIO below), a speaker track of turn
// blocks, a marker lane with one icon per tool call / staged action / refusal /
// submission, a time ruler, and a scrubbable playhead. Peaks are decoded once
// from the stereo recording with Web Audio and drawn on canvas in token colors.
// Playback goes through a plain <audio>; the orb's stereo meter taps it once.

import { Tooltip } from "@base-ui/react/tooltip";
import { clsx } from "clsx";
import { AlertTriangle, CalendarSearch, Check, ClipboardCheck, Pause, Play, Search, Send, ShieldOff, UserPlus, UserSearch, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type CSSProperties, type RefObject } from "react";
import { offset as fmtOffset, playerClock } from "@/lib/format";
import type { Decision, Turn } from "@/lib/timeline";
import { useTheme } from "@/lib/theme";
import "./call-review.css";

export interface TimelineHandle {
  seek: (seconds: number) => void;
  toggle: () => void;
}

interface Peaks {
  caller: Float32Array;
  agent: Float32Array;
  duration: number;
}

const BUCKETS = 1200;
const MARKER_SIZE = 44;
const MARKER_GAP = 4;
const MARKER_INSET = 6;
const finiteSeconds = (value: number) => Number.isFinite(value) ? Math.max(0, value) : 0;
const clampSeconds = (value: number, total: number) => Math.min(total, finiteSeconds(value));

// A media element can only be bound once, including React's effect replay.
let meterContext: AudioContext | null = null;
const meters = new WeakMap<HTMLAudioElement, {
  source: MediaElementAudioSourceNode;
  split: ChannelSplitterNode;
  left: AnalyserNode;
  right: AnalyserNode;
  buffer: Uint8Array<ArrayBuffer>;
  connected: boolean;
}>();

function meterFor(element: HTMLAudioElement) {
  meterContext ??= new AudioContext();
  let meter = meters.get(element);
  if (!meter) {
    const left = meterContext.createAnalyser();
    const right = meterContext.createAnalyser();
    left.fftSize = right.fftSize = 256;
    meter = { source: meterContext.createMediaElementSource(element), split: meterContext.createChannelSplitter(2), left, right, buffer: new Uint8Array(256), connected: false };
    meters.set(element, meter);
  }
  if (!meter.connected) {
    meter.source.connect(meter.split);
    meter.split.connect(meter.left, 0);
    meter.split.connect(meter.right, 1);
    meter.source.connect(meterContext.destination);
    meter.connected = true;
  }
  return meter;
}

async function decodePeaks(url: string, signal: AbortSignal): Promise<Peaks> {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`audio ${res.status}`);
  const buf = await res.arrayBuffer();
  signal.throwIfAborted();
  const AudioContextCtor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioContextCtor();
  let decoded: AudioBuffer;
  try {
    decoded = await ctx.decodeAudioData(buf);
  } finally {
    void ctx.close();
  }
  signal.throwIfAborted();
  const lane = (ch: number) => {
    const data = decoded.getChannelData(Math.min(ch, decoded.numberOfChannels - 1));
    const out = new Float32Array(BUCKETS);
    const step = data.length / BUCKETS;
    for (let i = 0; i < BUCKETS; i++) {
      const start = Math.floor(i * step);
      const end = Math.min(data.length, Math.floor((i + 1) * step));
      let sum = 0;
      for (let j = start; j < end; j++) {
        const v = data[j] ?? 0;
        sum += v * v;
      }
      out[i] = Math.sqrt(sum / Math.max(1, end - start));
    }
    // Normalize each lane to its own peak so a quiet phone line still reads.
    let max = 0;
    for (const v of out) if (v > max) max = v;
    if (max > 0) for (let i = 0; i < out.length; i++) out[i] = Math.min(1, (out[i] ?? 0) / max);
    return out;
  };
  return { caller: lane(0), agent: lane(1), duration: decoded.duration };
}

/** Icon and lane color per decision, so a glance says what happened. */
export function decisionGlyph(d: Decision): { Icon: LucideIcon; tone: "lookup" | "availability" | "write" | "refusal" | "submit"; title: string } {
  if (d.kind === "submit") return { Icon: Send, tone: d.attention ? "refusal" : "submit", title: `Submitted ${d.label.replace("submit ", "")}` };
  if (d.kind === "fallback" || d.kind === "guard" || d.kind === "error") return { Icon: d.kind === "error" ? AlertTriangle : ShieldOff, tone: "refusal", title: d.label };
  if (d.kind === "staged") return { Icon: ClipboardCheck, tone: "write", title: d.label };
  if (d.label === "caller_id_lookup") return { Icon: UserSearch, tone: "lookup", title: "Looked up the caller number" };
  if (d.label === "list_appointments") return { Icon: CalendarSearch, tone: "availability", title: "Looked up existing appointments" };
  if (d.label === "find_patient") return { Icon: UserSearch, tone: "lookup", title: "Looked up the patient" };
  if (d.label === "search_availability") return { Icon: CalendarSearch, tone: "availability", title: "Queried availability" };
  if (d.label === "validate_registration_details") return { Icon: Check, tone: "lookup", title: "Validated registration details" };
  if (d.label.startsWith("record_registration")) return { Icon: UserPlus, tone: "write", title: "Recorded a new patient" };
  if (d.label.startsWith("record_")) return { Icon: ClipboardCheck, tone: "write", title: `Recorded ${d.label.replace("record_", "")}` };
  return { Icon: Search, tone: "lookup", title: d.label };
}

const TONE_VAR: Record<string, string> = { lookup: "--event-lookup", availability: "--event-availability", write: "--event-write", refusal: "--event-refusal", submit: "--event-submit" };

export function CallTimeline({
  audioUrl,
  durationSeconds,
  turns,
  decisions,
  onTime,
  onLevels,
  onPlaying,
  onDecision,
  seekTo,
  controller,
  compact = false,
}: {
  audioUrl: string | null;
  durationSeconds: number;
  turns: Turn[];
  decisions: Decision[];
  onTime?: (seconds: number) => void;
  onLevels?: (caller: number, agent: number) => void;
  onPlaying?: (playing: boolean) => void;
  onDecision?: (d: Decision) => void;
  seekTo?: number | null;
  controller?: RefObject<TimelineHandle | null>;
  compact?: boolean;
}) {
  const theme = useTheme();
  const wrap = useRef<HTMLDivElement>(null);
  const markerLane = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const audio = useRef<HTMLAudioElement>(null);
  const callbacks = useRef({ onTime, onLevels, onPlaying, turns });
  callbacks.current = { onTime, onLevels, onPlaying, turns };
  const virtualTime = useRef<number | null>(null);
  const playbackRequest = useRef(0);
  const pendingPlay = useRef(false);
  const deferredSeek = useRef<number | null>(null);
  const waveformRequest = useRef<AbortController | null>(null);
  const [peaks, setPeaks] = useState<Peaks | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playError, setPlayError] = useState<string | null>(null);
  const [playbackWait, setPlaybackWait] = useState<"starting" | "buffering" | null>(null);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaDuration, setMediaDuration] = useState(0);
  const [width, setWidth] = useState(0);
  const [markerWidth, setMarkerWidth] = useState(0);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [hover, setHover] = useState<number | null>(null);
  const [tooltipKey, setTooltipKey] = useState<string | null>(null);
  const hasDecisions = decisions.length > 0;
  const total = useMemo(() => {
    let end = Math.max(1, finiteSeconds(durationSeconds), mediaDuration, peaks?.duration ?? 0);
    for (const turn of turns) end = Math.max(end, finiteSeconds(turn.offset));
    for (const decision of decisions) end = Math.max(end, finiteSeconds(decision.offset));
    return end;
  }, [durationSeconds, mediaDuration, peaks, turns, decisions]);

  const loadWaveform = useCallback(() => {
    if (!audioUrl || waveformRequest.current) return;
    const ac = new AbortController();
    waveformRequest.current = ac;
    setError(null);
    void decodePeaks(audioUrl, ac.signal)
      .then((decoded) => { if (!ac.signal.aborted) setPeaks(decoded); })
      .catch((e: unknown) => {
        if (!ac.signal.aborted) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (waveformRequest.current === ac) waveformRequest.current = null;
      });
  }, [audioUrl]);

  // Reset only when the source changes, not when retrying its waveform.
  useEffect(() => {
    setPeaks(null);
    setError(null);
    setPlayError(null);
    setMediaDuration(0);
    setTime(0);
    setPlaying(false);
    setPlaybackWait(null);
    setMediaLoading(!!audioUrl);
    pendingPlay.current = false;
    deferredSeek.current = null;
    virtualTime.current = null;
    callbacks.current.onTime?.(0);
    callbacks.current.onPlaying?.(false);
    loadWaveform();
    return () => {
      waveformRequest.current?.abort();
      waveformRequest.current = null;
    };
  }, [audioUrl, loadWaveform]);

  // Draw: audiogram (two lanes mirrored around the axis) + speaker blocks.
  const draw = useCallback(() => {
    const c = canvas.current;
    const w = wrap.current;
    if (!c || !w) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const width = w.clientWidth;
    const height = compact ? 72 : 112;
    c.width = width * dpr;
    c.height = height * dpr;
    c.style.height = `${height}px`;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    const styles = getComputedStyle(w);
    const callerColor = styles.getPropertyValue("--lane-caller").trim();
    const agentColor = styles.getPropertyValue("--lane-agent").trim();
    const axis = styles.getPropertyValue("--line-1").trim();
    const played = styles.getPropertyValue("--fg").trim();
    const mid = height / 2;
    const half = mid - 4;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = axis;
    ctx.fillRect(0, mid - 0.5, width, 1);
    if (peaks) {
      const recordedWidth = width * peaks.duration / total;
      const barW = Math.max(0.5, recordedWidth / BUCKETS);
      const gap = barW * 0.35;
      for (let i = 0; i < BUCKETS; i++) {
        const x = (i / BUCKETS) * recordedWidth;
        const isPlayed = i / BUCKETS * peaks.duration <= time;
        const up = (peaks.caller[i] ?? 0) * half;
        const down = (peaks.agent[i] ?? 0) * half;
        ctx.globalAlpha = isPlayed ? 1 : 0.55;
        ctx.fillStyle = callerColor;
        ctx.fillRect(x, mid - Math.max(1, up), barW - gap, Math.max(1, up));
        ctx.fillStyle = agentColor;
        ctx.fillRect(x, mid, barW - gap, Math.max(1, down));
      }
      ctx.globalAlpha = 1;
    }
    // Playhead
    const px = (time / total) * width;
    ctx.fillStyle = played;
    ctx.fillRect(px - 0.5, 0, 1, height);
    if (hover != null) {
      ctx.globalAlpha = 0.5;
      ctx.fillRect((hover / total) * width - 0.5, 0, 1, height);
      ctx.globalAlpha = 1;
    }
  }, [peaks, time, total, hover, compact]);

  const latestDraw = useRef(draw);
  latestDraw.current = draw;
  useEffect(() => { draw(); }, [draw, theme]);

  useEffect(() => {
    const ro = new ResizeObserver(() => {
      setWidth(wrap.current?.clientWidth ?? 0);
      setMarkerWidth(markerLane.current?.clientWidth ?? wrap.current?.clientWidth ?? 0);
      latestDraw.current();
    });
    if (wrap.current) ro.observe(wrap.current);
    if (markerLane.current) ro.observe(markerLane.current);
    return () => ro.disconnect();
  }, [hasDecisions]);

  // Callbacks can change without rebinding the media element or its audio graph.
  useEffect(() => {
    const a = audio.current;
    if (!a || !audioUrl) return;
    let frame = 0;
    let nextTurnAt = Infinity;
    const stopMeter = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      callbacks.current.onLevels?.(0, 0);
    };
    const onT = () => {
      if (virtualTime.current != null) return;
      const now = a.currentTime;
      setTime(now);
      callbacks.current.onTime?.(now);
      nextTurnAt = callbacks.current.turns.find((turn) => turn.offset > now)?.offset ?? Infinity;
    };
    const onStart = () => {
      if (!a.paused) {
        pendingPlay.current = true;
        setPlaybackWait("starting");
      }
    };
    const onP = () => {
      if (a.paused) return;
      pendingPlay.current = false;
      setPlaybackWait(null);
      setMediaLoading(false);
      virtualTime.current = null;
      setPlayError(null);
      setPlaying(true);
      callbacks.current.onPlaying?.(true);
      stopMeter();
      onT();
      const meter = callbacks.current.onLevels ? meterFor(a) : null;
      const rms = (analyser: AnalyserNode, buffer: Uint8Array<ArrayBuffer>) => {
        analyser.getByteTimeDomainData(buffer);
        let sum = 0;
        for (const sample of buffer) {
          const value = (sample - 128) / 128;
          sum += value * value;
        }
        return Math.min(1, Math.sqrt(sum / buffer.length) * 3);
      };
      const tick = () => {
        if (a.paused || a.ended) return;
        // timeupdate can lag by hundreds of milliseconds; publish speech endings on the next frame.
        if (a.currentTime >= nextTurnAt) onT();
        if (meter) callbacks.current.onLevels?.(rms(meter.left, meter.buffer), rms(meter.right, meter.buffer));
        frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    };
    const onS = () => {
      if (!a.paused && !a.ended) return;
      playbackRequest.current++;
      pendingPlay.current = false;
      setPlaybackWait(null);
      stopMeter();
      setPlaying(false);
      callbacks.current.onPlaying?.(false);
    };
    const onWaiting = () => {
      if (a.paused && !pendingPlay.current) return;
      setPlaybackWait("buffering");
      setPlaying(false);
      callbacks.current.onPlaying?.(false);
      stopMeter();
    };
    const onLoading = () => setMediaLoading(true);
    const onReady = () => setMediaLoading(false);
    const onMetadata = () => {
      if (a.readyState >= 1) setMediaLoading(false);
      setMediaDuration(finiteSeconds(a.duration));
      if (deferredSeek.current != null) {
        a.currentTime = clampSeconds(deferredSeek.current, finiteSeconds(a.duration));
        deferredSeek.current = null;
      }
    };
    const onError = () => {
      playbackRequest.current++;
      pendingPlay.current = false;
      setPlaybackWait(null);
      setMediaLoading(false);
      a.pause();
      stopMeter();
      setPlaying(false);
      callbacks.current.onPlaying?.(false);
      setPlayError("The recording could not be loaded. Retry audio, or continue reviewing the transcript and decisions.");
    };
    a.addEventListener("timeupdate", onT);
    a.addEventListener("play", onStart);
    a.addEventListener("playing", onP);
    a.addEventListener("waiting", onWaiting);
    a.addEventListener("stalled", onWaiting);
    a.addEventListener("loadstart", onLoading);
    a.addEventListener("canplay", onReady);
    a.addEventListener("pause", onS);
    a.addEventListener("ended", onS);
    a.addEventListener("loadedmetadata", onMetadata);
    a.addEventListener("durationchange", onMetadata);
    a.addEventListener("error", onError);
    if (a.readyState >= 1) onMetadata();
    if (a.readyState >= 3) onReady();
    if (a.error) onError();
    return () => {
      playbackRequest.current++;
      pendingPlay.current = false;
      a.removeEventListener("timeupdate", onT);
      a.removeEventListener("play", onStart);
      a.removeEventListener("playing", onP);
      a.removeEventListener("waiting", onWaiting);
      a.removeEventListener("stalled", onWaiting);
      a.removeEventListener("loadstart", onLoading);
      a.removeEventListener("canplay", onReady);
      a.removeEventListener("pause", onS);
      a.removeEventListener("ended", onS);
      a.removeEventListener("loadedmetadata", onMetadata);
      a.removeEventListener("durationchange", onMetadata);
      a.removeEventListener("error", onError);
      a.pause();
      stopMeter();
      callbacks.current.onPlaying?.(false);
      const meter = meters.get(a);
      if (meter) {
        meter.source.disconnect();
        meter.split.disconnect();
        meter.connected = false;
      }
    };
  }, [audioUrl]);

  useEffect(() => {
    if (audio.current) audio.current.playbackRate = speed;
  }, [speed, audioUrl]);

  const pause = useCallback(() => {
    playbackRequest.current++;
    pendingPlay.current = false;
    setPlaybackWait(null);
    setPlaying(false);
    audio.current?.pause();
    callbacks.current.onPlaying?.(false);
    callbacks.current.onLevels?.(0, 0);
  }, []);

  const seek = useCallback((seconds: number) => {
    const next = clampSeconds(seconds, total);
    const a = audio.current;
    const recorded = a && Number.isFinite(a.duration) ? a.duration : peaks?.duration ?? durationSeconds;
    const afterRecording = !!a && recorded > 0 && next >= recorded;
    virtualTime.current = afterRecording ? next : null;
    if (a) {
      if (afterRecording) pause();
      const position = clampSeconds(next, recorded > 0 ? recorded : total);
      if (a.readyState === 0) deferredSeek.current = position;
      else a.currentTime = position;
    }
    setTime(next);
    callbacks.current.onTime?.(next);
  }, [total, peaks, durationSeconds, pause]);

  useEffect(() => {
    if (seekTo != null) seek(seekTo);
  }, [seekTo, seek]);

  const seekAt = (clientX: number) => {
    const bounds = wrap.current?.getBoundingClientRect();
    if (bounds?.width) seek(((clientX - bounds.left) / bounds.width) * total);
  };

  const toggle = useCallback(() => {
    const a = audio.current;
    if (!a) return;
    if (pendingPlay.current || !a.paused) {
      pause();
      return;
    }
    if (a.ended || virtualTime.current != null) seek(0);
    const request = ++playbackRequest.current;
    if (playError || a.error) {
      deferredSeek.current = deferredSeek.current ?? virtualTime.current ?? a.currentTime;
      a.load();
      a.playbackRate = speed;
      setMediaLoading(true);
      if (error) loadWaveform();
    }
    setPlayError(null);
    pendingPlay.current = true;
    setPlaybackWait("starting");
    const play = async () => {
      if (callbacks.current.onLevels) {
        meterFor(a);
        void meterContext?.resume().catch(() => {
          // Playback remains usable if the optional level meter cannot resume.
        });
      }
      if (request !== playbackRequest.current) return;
      await a.play();
      if (request === playbackRequest.current) pendingPlay.current = false;
    };
    void play().catch(() => {
      if (request !== playbackRequest.current) return;
      pendingPlay.current = false;
      a.pause();
      setPlaybackWait(null);
      setMediaLoading(false);
      setPlaying(false);
      callbacks.current.onPlaying?.(false);
      callbacks.current.onLevels?.(0, 0);
      setPlayError("The recording could not be played. Retry audio, or continue reviewing the transcript and decisions.");
    });
  }, [seek, pause, playError, speed, error, loadWaveform]);

  useImperativeHandle(controller, () => ({ seek, toggle }), [seek, toggle]);

  const ticks = useMemo(() => {
    const intervals = Math.max(1, Math.floor(width / 72));
    const rawStep = total / intervals;
    const magnitude = 10 ** Math.floor(Math.log10(rawStep));
    const step = [1, 2, 5, 10].map((value) => value * magnitude).find((value) => value >= rawStep) ?? rawStep;
    const out: number[] = [];
    for (let t = 0; t < total; t += step) out.push(t);
    return out;
  }, [total, width]);

  // Nearby events occupy separate rows, never a summary that hides a decision.
  const { markers, markerRows } = useMemo(() => {
    const rowEnds: number[] = [];
    const size = Math.min(MARKER_SIZE, Math.max(0, markerWidth - MARKER_INSET * 2));
    const markers = [...decisions].sort((a, b) => a.offset - b.offset).map((decision) => {
      const center = Math.max(MARKER_INSET + size / 2, Math.min(markerWidth - MARKER_INSET - size / 2, clampSeconds(decision.offset, total) / total * width));
      const left = center - size / 2;
      let row = rowEnds.findIndex((end) => left >= end + MARKER_GAP);
      if (row < 0) row = rowEnds.length;
      rowEnds[row] = left + size;
      return { decision, left, size, row };
    });
    return { markers, markerRows: rowEnds.length };
  }, [decisions, total, markerWidth, width]);

  return (
    <div className="review-player relative grid min-w-0 gap-2 select-none" data-compact={compact}>
      {audioUrl ? <audio key={audioUrl} ref={audio} src={audioUrl} preload="metadata" crossOrigin="anonymous" /> : null}
      <span className="review-playback-status" role="status">
        {playbackWait === "starting" ? "Starting audio…" : playbackWait === "buffering" ? "Buffering audio…" : null}
      </span>

      {/* Marker lane */}
      {markers.length > 0 ? (
        <div className="review-marker-frame" data-compact={compact}>
          <div className="review-marker-scroll" role="region" tabIndex={0} aria-label={`Call decisions: ${markers.length} decisions in ${markerRows} rows. Scroll vertically for more.`}>
          <div ref={markerLane} className="review-marker-track" style={{ height: markerRows * (MARKER_SIZE + MARKER_GAP) }}>
            {Array.from({ length: markerRows }, (_, row) => <span key={row} aria-hidden="true" className="review-marker-row" style={{ top: row * (MARKER_SIZE + MARKER_GAP), height: MARKER_SIZE + MARKER_GAP }} />)}
            <Tooltip.Provider>
              {markers.map(({ decision, left, size, row }) => {
                const { Icon, tone, title } = decisionGlyph(decision);
                const style: CSSProperties = { left, top: row * (MARKER_SIZE + MARKER_GAP), width: size, height: MARKER_SIZE, ["--tone" as string]: `var(${TONE_VAR[tone]})` };
                return (
                  <Tooltip.Root key={decision.key} open={tooltipKey === decision.key} onOpenChange={(open) => setTooltipKey((previous) => open ? decision.key : previous === decision.key ? null : previous)}>
                    <Tooltip.Trigger
                      type="button"
                      className="review-marker"
                      style={style}
                      delay={200}
                      closeOnClick={false}
                      aria-label={`${title} at ${fmtOffset(decision.offset)}. Show decision`}
                      onClick={() => {
                        pause();
                        seek(decision.offset);
                        setTooltipKey(decision.key);
                        onDecision?.(decision);
                      }}
                    >
                      <Icon size={17} strokeWidth={1.75} aria-hidden="true" />
                    </Tooltip.Trigger>
                    <Tooltip.Portal>
                      <Tooltip.Positioner side="top" sideOffset={8} collisionPadding={12} sticky className="review-tooltip-positioner">
                        <Tooltip.Popup className="review-tooltip">
                          {title}
                          <span className="review-tooltip-time">{fmtOffset(decision.offset)}</span>
                        </Tooltip.Popup>
                      </Tooltip.Positioner>
                    </Tooltip.Portal>
                  </Tooltip.Root>
                );
              })}
            </Tooltip.Provider>
          </div>
          </div>
        </div>
      ) : <div className="review-marker-frame review-marker-empty" data-compact={compact}>No recorded decisions</div>}

      {/* Audiogram */}
      <div
        ref={wrap}
        className="relative touch-pan-y cursor-crosshair rounded-tags overflow-hidden"
        role="slider"
        aria-label="Call timeline; click or drag to seek"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={clampSeconds(time, total)}
        aria-valuetext={playerClock(time)}
        tabIndex={0}
        onPointerDown={(e) => {
          (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
          seekAt(e.clientX);
        }}
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHover(Math.max(0, Math.min(total, ((e.clientX - r.left) / r.width) * total)));
          if (e.currentTarget.hasPointerCapture(e.pointerId)) seekAt(e.clientX);
        }}
        onPointerUp={(e) => { if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId); }}
        onPointerCancel={(e) => { if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId); }}
        onPointerLeave={() => setHover(null)}
        onKeyDown={(e) => {
          if (e.key === " ") {
            e.preventDefault();
            toggle();
          }
          if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
            e.preventDefault();
            seek(e.key === "Home" ? 0 : e.key === "End" ? total : time + (e.key === "ArrowLeft" ? -5 : 5));
          }
        }}
      >
        <canvas ref={canvas} className="block w-full" style={{ height: compact ? 72 : 112 }} />
        {!peaks && audioUrl && !error ? <span className="review-waveform-message" role="status">Loading waveform</span> : null}
        {!audioUrl ? <span className="pointer-events-none absolute inset-0 grid place-items-center text-[12px] text-fg-3">No recording</span> : null}
        {error ? <span className="review-waveform-message">Waveform unavailable</span> : null}
        <span className="pointer-events-none absolute left-2 top-1 text-[10px] uppercase tracking-[0.06em] text-lane-caller/80">caller</span>
        <span className="pointer-events-none absolute bottom-1 left-2 text-[10px] uppercase tracking-[0.06em] text-lane-agent">rosario</span>
        {hover != null ? (
          <span className="pointer-events-none absolute top-1 mono text-[10px] text-fg-2 tabular" style={{ left: `clamp(4px, ${(hover / total) * 100}%, calc(100% - 44px))` }}>
            {playerClock(hover)}
          </span>
        ) : null}
      </div>

      {/* Speaker track */}
      <div className="relative h-2 overflow-hidden rounded-band bg-canvas-deep">
        {turns
          .filter((t) => t.text.length > 0)
          .map((t, i, all) => {
            const next = all[i + 1];
            const start = clampSeconds(t.offset, total);
            const end = Math.max(start, clampSeconds(next ? next.offset : t.offset + Math.max(1.2, t.text.split(/\s+/).length * 0.36), total));
            return <span key={t.key} className={clsx("absolute top-0 h-2 rounded-band", t.role === "agent" ? "bg-lane-agent" : "bg-lane-caller/70")} style={{ left: `${(start / total) * 100}%`, width: `${Math.min(100 - start / total * 100, Math.max(0.3, ((end - start) / total) * 100))}%` }} title={`${t.role === "agent" ? "ROSARIO" : "Caller"} ${fmtOffset(t.offset)}`} />;
          })}
      </div>

      {/* Ruler + transport */}
      <div className="relative h-4">
        {ticks.map((t) => (
          <span key={t} className="mono absolute top-0 text-[10px] text-fg-3 tabular" style={{ left: `clamp(0px, ${(t / total) * 100}%, calc(100% - 40px))` }}>
            {playerClock(t)}
          </span>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="pill pill-ghost review-playback-button" onClick={toggle} disabled={!audioUrl} aria-busy={mediaLoading || playbackWait != null} aria-label={playbackWait ? "Cancel playback" : playing ? "Pause" : playError ? "Retry audio" : "Play"}>
          {playbackWait || playing ? <Pause size={15} strokeWidth={1.75} aria-hidden="true" /> : <Play size={15} strokeWidth={1.75} aria-hidden="true" />}
          {playbackWait ? "Cancel" : playing ? "Pause" : playError ? "Retry audio" : "Play"}
        </button>
        <span className="mono text-[13px] text-fg tabular">
          {playerClock(time)} <span className="text-fg-3">/ {playerClock(total)}</span>
        </span>
        <div className="ml-auto flex items-center gap-1" role="group" aria-label="Playback speed">
          {[1, 1.5, 2].map((s) => (
            <button key={s} type="button" className={clsx("speed", s === speed && "on")} aria-pressed={s === speed} onClick={() => setSpeed(s)}>
              {s}x
            </button>
          ))}
        </div>
      </div>
      {playError ? <p role="alert" className="text-[12px] text-fg-2">{playError}</p> : null}
      {error && audioUrl ? (
        <div className="review-waveform-error">
          <p role="status">The waveform could not be loaded. You can still try audio playback or review the transcript.</p>
          <button type="button" className="pill pill-quiet pill-sm" onClick={loadWaveform}>Retry waveform</button>
        </div>
      ) : null}
    </div>
  );
}
