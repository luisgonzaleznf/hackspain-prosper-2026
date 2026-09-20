import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import { MicrophoneIcon } from "@phosphor-icons/react/dist/csr/Microphone";
import { StopIcon } from "@phosphor-icons/react/dist/csr/Stop";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Orb, useLevelMeter, type OrbLevels, type OrbState } from "@/components/orb";
import { demo, describeError, sessionIdOf, type LedgerEntry, type Persona, type Snapshot, type StreamEvent } from "./api";
import { useCallMoment, useFeed, useHeadline, useLedger, useReceipt, useRoleCards, useStageIn, useStatus } from "./motion";

type Phase = "idle" | "connecting" | "live" | "ending" | "complete" | "error";
const POLL_MS = 900;

/** The whole studio: pick a caller, talk, read what was staged. */
export function Studio() {
  const [roles, setRoles] = useState<Persona[]>([]);
  const [picked, setPicked] = useState<Persona | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [alert, setAlert] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [speaker, setSpeaker] = useState<"agent" | "caller" | null>(null);
  // The live feed comes from the event stream, which is ordered, so a lookup shows
  // up between the turns it happened between instead of after all of them.
  const [feed, setFeed] = useState<StreamEvent[]>([]);
  const stream = useRef<EventSource | null>(null);

  const client = useRef<PipecatClient | null>(null);
  const sessionId = useRef<string | null>(null);
  const ready = useRef(false);
  const poll = useRef(0);
  const stopping = useRef(false);
  const holdUntil = useRef(0);
  const levels = useRef<OrbLevels>({ agent: 0, caller: 0 });
  const [micStream, setMicStream] = useState<MediaStream | null>(null);

  // Motion scopes. Every effect is one-shot; see motion.ts.
  const headline = useRef<HTMLHeadingElement | null>(null);
  const rolesScope = useRef<HTMLDivElement | null>(null);
  const stageScope = useRef<HTMLElement | null>(null);
  const feedRef = useRef<HTMLOListElement | null>(null);
  const statusRef = useRef<HTMLParagraphElement | null>(null);
  const outcomeScope = useRef<HTMLElement | null>(null);
  const ledgerScope = useRef<HTMLDivElement | null>(null);

  // The caller side of the meter comes from the local microphone track, exactly
  // as the Talk screen does it.
  const setCaller = useCallback((caller: number) => {
    levels.current = { ...levels.current, caller };
    const now = performance.now();
    if (caller > 0.08) { holdUntil.current = now + 500; setSpeaker("caller"); }
    else if (now > holdUntil.current) setSpeaker((value) => (value === "caller" ? null : value));
  }, []);
  useLevelMeter(micStream, setCaller);

  // brand.js inlines [data-mark] before React mounts, so the lockup loads its own mark.
  const mark = useRef<HTMLElement | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch("/brand/logos/marks/dial-rose-ten.svg")
      .then((response) => (response.ok ? response.text() : ""))
      .then((svg) => {
        if (cancelled || !mark.current || !svg) return;
        mark.current.innerHTML = svg.replace(/\s+id="[^"]*"/g, "").replace(/<svg (?![^>]*aria-hidden)/, '<svg aria-hidden="true" focusable="false" ');
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const refreshLedger = useCallback(() => { demo.ledger().then(setLedger).catch(() => setLedger([])); }, []);
  useEffect(() => {
    demo.scenarios().then(setRoles).catch((error: unknown) => setAlert(`The roles could not be loaded: ${String((error as Error).message)}`));
    refreshLedger();
  }, [refreshLedger]);

  const stopPolling = () => { window.clearInterval(poll.current); poll.current = 0; };
  const stopStream = () => { stream.current?.close(); stream.current = null; };
  const openStream = (id: string) => {
    stopStream();
    setFeed([]);
    const source = new EventSource(demo.eventsUrl(id));
    source.onmessage = ({ data }) => {
      try { setFeed((rows) => [...rows, JSON.parse(data) as StreamEvent]); }
      catch { /* the JSONL on disk stays authoritative */ }
    };
    stream.current = source;
  };
  const disconnect = useCallback(async () => {
    const active = client.current;
    client.current = null;
    stopStream();
    setMicStream(null);
    levels.current = { agent: 0, caller: 0 };
    setSpeaker(null);
    const audio = document.getElementById("bot-audio") as HTMLAudioElement | null;
    if (audio) { audio.pause(); audio.srcObject = null; }
    if (active) { try { await active.disconnect(); } catch { /* already closed */ } }
  }, []);

  const fail = useCallback((message: string) => {
    stopPolling();
    stopping.current = false;
    setAlert(message);
    setPhase("error");
  }, []);

  const finish = useCallback((final: Snapshot | null) => {
    stopPolling();
    setPhase("complete");
    setSnapshot(final);
    refreshLedger();
  }, [refreshLedger]);

  const apply = useCallback((next: Snapshot) => {
    setSnapshot(next);
    if (next.error) setAlert(next.error);
    if (next.status === "complete") finish(next);
    else if (next.status === "error") fail(next.error ?? "The rehearsal ended unexpectedly.");
  }, [fail, finish]);

  const pollOnce = useCallback(async () => {
    if (!sessionId.current) return;
    try { apply(await demo.snapshot(sessionId.current)); }
    catch (error) { setAlert(`Live activity is temporarily unavailable. ${String((error as Error).message)}`); }
  }, [apply]);

  const start = async () => {
    if (!picked) return;
    setAlert(""); setSnapshot(null);
    sessionId.current = null; ready.current = false;
    setPhase("connecting");
    try {
      const pipecat = new PipecatClient({
        transport: new SmallWebRTCTransport(),
        enableCam: false, enableMic: true, disconnectOnBotDisconnect: false,
        callbacks: {
          onBotStarted: (response: unknown) => { sessionId.current = sessionIdOf(response) ?? sessionId.current; },
          onConnected: () => setPhase("live"),
          onBotReady: (data: unknown) => { sessionId.current = sessionIdOf(data) ?? sessionId.current; setPhase("live"); },
          onDisconnected: () => { if (!stopping.current) setPhase((value) => (value === "complete" ? value : value === "live" ? "error" : value)); },
          onTransportStateChanged: (value: string) => { if (value === "error") fail("The voice connection failed. Check your network and try again."); },
          onDeviceError: (error: unknown) => fail(describeError(error)),
          onError: (message: unknown) => fail(describeError((message as { data?: unknown })?.data ?? message)),
        },
      });
      client.current = pipecat;
      pipecat.on(RTVIEvent.TrackStarted, (track: MediaStreamTrack, participant?: { local?: boolean }) => {
        if (track.kind !== "audio") return;
        const stream = new MediaStream([track]);
        if (participant?.local) { setMicStream(stream); return; }
        const audio = document.getElementById("bot-audio") as HTMLAudioElement | null;
        if (!audio) return;
        audio.srcObject = stream;
        audio.muted = false;
        audio.volume = 1;
        meterAgent(stream, (agent) => {
          levels.current = { ...levels.current, agent };
          const now = performance.now();
          if (agent > 0.08) { holdUntil.current = now + 500; setSpeaker("agent"); }
          else if (now > holdUntil.current) setSpeaker((value) => (value === "agent" ? null : value));
        });
        void audio.play().catch(() => setAlert("Your browser blocked playback. Press the orb once more to enable sound."));
      });

      await pipecat.initDevices();
      const started = await pipecat.startBotAndConnect({
        endpoint: "/start",
        requestData: { transport: "webrtc", enableDefaultIceServers: true, body: { scenario_id: picked.id } },
      });
      sessionId.current = sessionIdOf(started) ?? sessionId.current;
      if (!sessionId.current) throw new Error("The server did not return a session id.");
      apply(await demo.open(sessionId.current, picked.id));
      openStream(sessionId.current);
      ready.current = true;
      setPhase("live");
      stopPolling();
      poll.current = window.setInterval(() => void pollOnce(), POLL_MS);
    } catch (error) {
      await disconnect();
      fail(describeError(error));
    }
  };

  const stop = async () => {
    if (phase !== "live" || stopping.current) return;
    stopping.current = true;
    setPhase("ending");
    stopPolling();
    try {
      await disconnect();
      const id = sessionId.current;
      if (!id) { finish(null); return; }
      // The recording and the receipt are written after the media closes.
      for (let attempt = 0; attempt < 40; attempt += 1) {
        const next = await demo.snapshot(id);
        if (next.status === "complete" || next.status === "error") { apply(next); return; }
        await new Promise((resolve) => window.setTimeout(resolve, 500));
      }
      throw new Error("The recording is still being written. Open the trace to review it.");
    } catch (error) {
      await disconnect();
      fail(`The call ended, but the receipt could not be loaded: ${String((error as Error).message)}`);
    } finally {
      stopping.current = false;
    }
  };

  useEffect(() => () => { stopPolling(); stopStream(); void client.current?.disconnect().catch(() => {}); }, []);

  const orbState: OrbState = phase === "live" ? (speaker === "agent" ? "speaking" : "listening")
    : phase === "connecting" || phase === "ending" ? "connecting" : "disconnected";
  const status = phase === "live" ? (speaker === "agent" ? "ROSARIO speaking" : speaker === "caller" ? "Listening to you" : "Listening")
    : phase === "connecting" ? "Connecting" : phase === "ending" ? "Saving the call"
    : phase === "complete" ? "Call saved" : phase === "error" ? (alert || "Something went wrong") : "Ready when you are";

  const rows = useMemo(() => feed.flatMap((event) => {
    if (event.type.startsWith("conversation.")) {
      return [{ key: String(event.id), kind: event.type.endsWith("agent") ? "agent" : "caller", text: event.summary }];
    }
    if (event.type.startsWith("tool.") || event.type === "action.staged") {
      return [{ key: String(event.id), kind: "tool", text: `${event.label} · ${event.summary}` }];
    }
    return [];
  }).slice(-14), [feed]);
  const evidence = snapshot?.evidence?.[0];
  const milestones = snapshot?.milestones ?? [];
  const done = milestones.filter((item) => item.state === "complete").length;

  useHeadline(headline);
  useRoleCards(rolesScope, roles.length);
  useStageIn(stageScope, picked?.id ?? null);
  useCallMoment(stageScope, phase);
  useFeed(feedRef, rows.length);
  useStatus(statusRef, status);
  useReceipt(outcomeScope, phase === "complete");
  useLedger(ledgerScope, ledger.length);

  return <>
    <header className="top">
      <a className="lockup" href="/" aria-label="ROSARIO home"><i ref={mark} data-mark="dial-rose-ten" /><span>rosario</span></a>
    </header>

    <main id="main" tabIndex={-1}>
      <h1 className="lead" ref={headline}>Rehearse the call.</h1>
      {alert && phase !== "error" ? <p className="alert" role="alert">{alert}</p> : null}

      <section className="roles-wrap" aria-labelledby="who">
        <h2 id="who">Who are you calling as?</h2>
        <div className="roles" ref={rolesScope}>
          {roles.map((role) => <button key={role.id} type="button" className="role" aria-pressed={picked?.id === role.id}
            onClick={() => { if (phase === "live" || phase === "connecting" || phase === "ending") return; setPicked(role); setSnapshot(null); setAlert(""); setPhase("idle"); }}>
            <h3>{role.title}</h3>
            <p>{role.objective.replace(/[.!]$/, "")}</p>
          </button>)}
        </div>
      </section>

      {picked ? <section className="stage" aria-label="The call" ref={stageScope}>
        <div className="control">
          <Orb size={300} levels={levels} state={orbState} onActivate={() => void (phase === "live" ? stop() : start())}
            label={phase === "live" ? "End the call" : "Start the call"}
            disabled={phase === "connecting" || phase === "ending"}
            controlIcon={phase === "live" ? <StopIcon size={22} /> : <MicrophoneIcon size={22} />} />
          <p className="status" aria-live="polite" ref={statusRef}>{status}</p>
          {milestones.length ? <p className="progress">{done} of {milestones.length} steps done</p> : null}
        </div>

        <div className="side">
          <div className="card dark brief">
            <p className="who-name">{picked.name}</p>
            <p className="who-phone mono">{picked.phone}</p>
            <dl className="facts">{picked.facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
            <p className="objective">{picked.objective}</p>
            <p className="hint">Open with <q>{picked.opening_hint}</q></p>
          </div>
          {rows.length ? <ol className="turns" ref={feedRef}>
            {rows.map((row) => <li key={row.key} className={row.kind}>
              <span className="who">{row.kind === "agent" ? "ROSARIO" : row.kind === "tool" ? "Lookup" : "You"}</span>
              <span>{row.text}</span>
            </li>)}
          </ol> : null}
        </div>
      </section> : null}

      {phase === "complete" ? <section className="block" aria-labelledby="outcome-heading" ref={outcomeScope}>
        <h2 id="outcome-heading">What it staged</h2>
        <div className="card dark receipt">
          <p className="receipt-label">{evidence?.label ?? "No action staged"}</p>
          {evidence ? <>
            <dl className="facts">{evidence.fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
            <ul className="checks">{evidence.checks.map((check) => <li key={check}>{check}</li>)}</ul>
          </> : null}
          <p className="row">
            {sessionId.current ? <a className="link" href={demo.reviewUrl(sessionId.current)} target="_blank" rel="noreferrer">Full trace</a> : null}
            <button className="link" type="button" onClick={() => { setSnapshot(null); setAlert(""); setPhase("idle"); }}>Another call</button>
          </p>
        </div>
      </section> : null}

      <section className="block" aria-labelledby="saved">
        <h2 id="saved">Saved rehearsals</h2>
        <div className="ledger" ref={ledgerScope}>
          {ledger.length ? ledger.map((entry) => <div key={entry.session_id} className="ledger-row">
            <time dateTime={entry.completed_at}>{new Date(entry.completed_at).toLocaleString()}</time>
            <span>{entry.status === "error" ? "Call failed" : entry.evidence?.[0]?.label ?? "No action staged"}</span>
            <span className="detail">{entry.evidence?.[0] ? entry.evidence[0].fields.map(([k, v]) => `${k}: ${v}`).join(" · ") : entry.error ?? "Open the trace to see what happened."}</span>
            <a href={demo.reviewUrl(entry.session_id)}>Review</a>
          </div>) : <p className="quiet">Nothing saved yet.</p>}
        </div>
      </section>
    </main>
  </>;
}

/** RMS meter for the bot track; mirrors useLevelMeter for a stream we do not own. */
function meterAgent(stream: MediaStream, out: (level: number) => void) {
  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const data = new Float32Array(analyser.fftSize);
  const timer = window.setInterval(() => {
    if (stream.getAudioTracks().every((track) => track.readyState === "ended")) {
      window.clearInterval(timer);
      out(0);
      void ctx.close();
      return;
    }
    analyser.getFloatTimeDomainData(data);
    let sum = 0;
    for (const value of data) sum += value * value;
    out(Math.min(1, Math.sqrt(sum / data.length) * 2.4));
  }, 33);
}
