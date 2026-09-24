import { MicrophoneIcon } from "@phosphor-icons/react/dist/csr/Microphone";
import { MicrophoneSlashIcon } from "@phosphor-icons/react/dist/csr/MicrophoneSlash";
import { PauseIcon } from "@phosphor-icons/react/dist/csr/Pause";
import { PlayIcon } from "@phosphor-icons/react/dist/csr/Play";
import { StopIcon } from "@phosphor-icons/react/dist/csr/Stop";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ScreenHeader } from "@/app";
import { CallTimeline, type TimelineHandle } from "@/components/call-timeline";
import { Orb, useLevelMeter, type OrbLevels, type OrbState } from "@/components/orb";
import { Empty, Label, OUTCOME_LABEL, PillSelect, SwapText } from "@/components/primitives";
import { Transcript } from "@/components/transcript";
import { api } from "@/lib/api";
import { duration } from "@/lib/format";
import { isActive, useCallDetail, useCallsIndex } from "@/lib/store";
import { actionVerbs } from "@/lib/timeline";

export function TalkScreen() {
  const { calls } = useCallsIndex();
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [muted, setMuted] = useState(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [revealDecision, setRevealDecision] = useState<{ key: string; request: number } | null>(null);
  const onPlaying = useCallback((value: boolean) => {
    setPlaying(value);
    if (value) setRevealDecision(null);
  }, []);
  const [speaker, setSpeaker] = useState<"agent" | "caller" | null>(null);
  const levels = useRef<OrbLevels>({ agent: 0, caller: 0 });
  const controller = useRef<TimelineHandle | null>(null);
  const holdUntil = useRef(0);
  const candidates = useMemo(() => calls.filter((c) => !isActive(c) && c.has_audio && (c.duration_seconds ?? 0) > 60).slice(0, 12), [calls]);
  const [pickedId, setPickedId] = useState<string | null>(null);
  const recordingId = pickedId ?? candidates[0]?.call_id ?? null;
  const record = useCallDetail(recordingId);
  const timeline = record?.timeline ?? null;

  const onLevels = useCallback((caller: number, agent: number) => {
    levels.current = { caller, agent };
    const next = agent > 0.08 ? "agent" : caller > 0.08 ? "caller" : null;
    const now = performance.now();
    if (next) {
      holdUntil.current = now + 500;
      setSpeaker(next);
    } else if (now > holdUntil.current) setSpeaker(null);
  }, []);
  const setCaller = useCallback((caller: number) => { levels.current = { caller, agent: 0 }; }, []);
  useLevelMeter(stream, setCaller);
  useEffect(() => () => stream?.getTracks().forEach((track) => track.stop()), [stream]);
  useEffect(() => {
    stream?.getAudioTracks().forEach((track) => { track.enabled = !muted; });
  }, [stream, muted]);

  const startMic = async () => {
    setMicError(null);
    if (playing) controller.current?.toggle();
    try {
      if (!navigator.mediaDevices) throw new Error("Open this page on localhost or HTTPS to enable microphone access.");
      const next = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMuted(false);
      setStream(next);
    } catch (error) {
      setMicError(error instanceof Error ? error.message : String(error));
    }
  };
  const stopMic = () => {
    stream?.getTracks().forEach((track) => track.stop());
    setStream(null);
    levels.current = { caller: 0, agent: 0 };
  };
  const orbAction = () => {
    if (stream) setMuted((value) => !value);
    else controller.current?.toggle();
  };
  const orbState: OrbState = stream ? (muted ? "disconnected" : "listening") : !playing ? "disconnected" : speaker === "agent" ? "speaking" : "listening";
  const status = stream ? (muted ? "Microphone muted" : "Listening to your microphone") : !playing ? "Ready when you are" : speaker === "agent" ? "ROSARIO speaking" : speaker === "caller" ? "Caller speaking" : "Listening to the call";
  const orbLabel = stream ? (muted ? "Unmute microphone" : "Mute microphone") : playing ? "Pause recording" : "Play recording";
  const activeKey = timeline?.turns.filter((turn) => turn.offset <= playhead).at(-1)?.key ?? null;

  return <div className="flex min-h-0 flex-1 flex-col">
    <ScreenHeader title="Talk to ROSARIO" />
    <div className="scroll-y flex-1 px-4 pb-24 pt-6 md:px-8 md:pb-10">
      <div className="measure grid items-start gap-8 lg:grid-cols-[minmax(300px,4fr)_minmax(420px,8fr)]">
        <section className="grid justify-items-center gap-5 text-center lg:sticky lg:top-0" aria-label="Call controls">
          <Orb size={300} levels={levels} state={orbState} onActivate={orbAction} label={orbLabel} disabled={!stream && !timeline}
            controlIcon={stream ? (muted ? <MicrophoneSlashIcon size={24} /> : <MicrophoneIcon size={24} />) : playing ? <PauseIcon size={24} /> : <PlayIcon size={24} />} />
          <p className="min-h-6 text-[16px] text-fg" aria-live="polite"><SwapText text={status} /></p>
          <div className="grid w-full max-w-[360px] gap-4 text-left">
            {!stream && candidates.length > 0 ? <div className="grid gap-2">
              <Label>Recorded call</Label>
              <PillSelect value={recordingId ?? ""} onChange={(id) => { setPickedId(id); setPlayhead(0); setPlaying(false); setRevealDecision(null); }} label="Recorded call to listen to"
                options={candidates.map((call) => ({ value: call.call_id, label: `${OUTCOME_LABEL[actionVerbs(call.action).at(-1) ?? ""] ?? "Recorded"} call · ${duration(call.duration_seconds)}`, hint: call.call_id.slice(0, 8) }))} />
            </div> : null}
            <button type="button" className="pill pill-ghost" onClick={stream ? stopMic : () => void startMic()}>
              {stream ? <StopIcon size={16} /> : <MicrophoneIcon size={16} />}{stream ? "Stop microphone" : "Try your microphone"}
            </button>
            {micError ? <p role="alert" className="text-[13px] text-fg-2">{micError}</p> : null}
            <p className="text-center text-[12px] leading-[1.6] text-fg-3">{stream ? "Local microphone preview. Audio is not sent to the agent." : "Recorded calls only. Browser calling is not connected."}</p>
          </div>
        </section>
        <section className="min-w-0" aria-label="Call recording and transcript">
          {record?.detail && timeline && recordingId ? <div className="card overflow-hidden">
            <div className="border-b border-line-1 px-4 py-5 md:px-6">
              <h2 className="mb-5 text-[22px] font-extralight text-fg">Inside the call</h2>
              {!stream ? <CallTimeline key={recordingId} controller={controller} audioUrl={api.audioUrl(recordingId)} durationSeconds={record.detail.audio?.duration_seconds ?? 0} turns={timeline.turns} decisions={timeline.decisions} onTime={setPlayhead} onLevels={onLevels} onPlaying={onPlaying} onDecision={(decision) => {
                setRevealDecision((previous) => ({ key: decision.key, request: (previous?.request ?? 0) + 1 }));
              }} /> : <p className="text-[14px] text-fg-2">Stop the microphone to return to the recording.</p>}
            </div>
            <div className="scroll-y max-h-[420px] px-4 py-2 md:px-6"><Transcript turns={timeline.turns} follow={playing} activeKey={activeKey} revealDecision={revealDecision} /></div>
          </div> : <div className="card px-5"><Empty>{record?.detailError ?? "Loading a recorded call…"}</Empty></div>}
        </section>
      </div>
    </div>
  </div>;
}
