import { CaretDownIcon } from "@phosphor-icons/react/dist/csr/CaretDown";
import { CheckIcon } from "@phosphor-icons/react/dist/csr/Check";
import { SpeakerHighIcon } from "@phosphor-icons/react/dist/csr/SpeakerHigh";
import { StopIcon } from "@phosphor-icons/react/dist/csr/Stop";
import { WarningIcon } from "@phosphor-icons/react/dist/csr/Warning";
import gsap from "gsap";
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { ScreenHeader } from "@/app";
import { Orb } from "@/components/orb";
import { PillSelect } from "@/components/primitives";
import { demo } from "@/demo/api";
import { motionDurationMs, useRiseIn } from "@/lib/motion";
import { VOICE_SAMPLES } from "@/lib/voice-samples";
import { sameVoiceSettings, type VoiceId, type VoiceSettings, type VoiceSettingsDocument } from "@/lib/voice-settings";
import "./settings.css";

type ReadySettings = {
  status: "ready";
  document: VoiceSettingsDocument;
  draft: VoiceSettings;
  save: "idle" | "saving" | "saved" | "discarded" | "error";
};
type SettingsState = { status: "loading" } | { status: "error" } | ReadySettings;

// Memory-only drafts survive dashboard navigation without storing guidance on disk.
let state: SettingsState = { status: "loading" };
let loading = false;
const listeners = new Set<() => void>();
const snapshot = () => state;
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};
const isDirty = (value: ReadySettings) => !sameVoiceSettings(value.draft, value.document.settings);
const protectDraft = (event: BeforeUnloadEvent) => {
  event.preventDefault();
  event.returnValue = "";
};

function publish(next: SettingsState) {
  state = next;
  // Keep the warning active even after the Settings screen unmounts.
  window.removeEventListener("beforeunload", protectDraft);
  if (next.status === "ready" && isDirty(next)) window.addEventListener("beforeunload", protectDraft);
  listeners.forEach((listener) => listener());
}

async function loadSettings() {
  if (loading || state.status === "ready") return;
  loading = true;
  publish({ status: "loading" });
  try {
    const document = await demo.settings();
    publish({ status: "ready", document, draft: document.settings, save: "idle" });
  } catch {
    publish({ status: "error" });
  } finally {
    loading = false;
  }
}

function updateDraft(change: Partial<VoiceSettings>) {
  if (state.status !== "ready" || state.save === "saving") return;
  publish({ ...state, draft: { ...state.draft, ...change }, save: "idle" });
}

function validationError(value: ReadySettings): string | null {
  if (!value.document.presets.some((preset) => preset.id === value.draft.preset)) return "Choose an available receptionist preset.";
  if (!value.document.voices.some((voice) => voice.id === value.draft.voice)) return "Choose an available voice.";
  if (value.draft.opening_language !== "en" && value.draft.opening_language !== "es") return "Choose English or Spanish for the opening language.";
  if (value.draft.guidance.length > 1200) return "Keep additional instructions to 1,200 characters or fewer.";
  return null;
}

async function saveSettings() {
  if (state.status !== "ready" || state.save === "saving" || !isDirty(state) || validationError(state)) return;
  const current = state;
  publish({ ...current, save: "saving" });
  try {
    const saved = await demo.saveSettings(current.draft);
    publish({ ...current, document: { ...current.document, settings: saved }, draft: saved, save: "saved" });
  } catch {
    publish({ ...current, save: "error" });
  }
}

/** Save on a public demo: the write lands on the demo backend, but the page is a showcase. */
function SaveNotice({ onClose }: { onClose: () => void }) {
  return <div className="settings-notice-backdrop" onClick={onClose}>
    <div role="alertdialog" aria-label="Public demo notice" className="settings-notice" onClick={(event) => event.stopPropagation()}>
      <h2>This is a public demo</h2>
      <p>
        ROSARIO is shown here as a showcase. Your change is applied to the demo receptionist right
        away, but nothing is kept: the saved settings reset, and this page exists to demonstrate how
        the console works, not to store real preferences.
      </p>
      <button type="button" className="pill pill-primary" onClick={onClose}>Got it</button>
    </div>
  </div>;
}

function discardSettings() {
  if (state.status !== "ready" || state.save === "saving") return;
  publish({ ...state, draft: state.document.settings, save: "discarded" });
}

function VoiceSample({ voice, name }: { voice: VoiceId; name: string }) {
  const audio = useRef<HTMLAudioElement>(null);
  const request = useRef(0);
  const [playback, setPlayback] = useState<"idle" | "loading" | "playing" | "error">("idle");
  const active = playback === "loading" || playback === "playing";
  const label = active ? `Stop ${name} sample` : playback === "error" ? `Retry ${name} sample` : `Play ${name} sample`;

  useEffect(() => {
    const player = audio.current;
    return () => {
      request.current++;
      player?.pause();
    };
  }, []);

  const toggle = async () => {
    const player = audio.current;
    if (!player) return;
    const attempt = ++request.current;
    if (active) {
      player.pause();
      player.currentTime = 0;
      setPlayback("idle");
      return;
    }
    if (playback === "error") player.load();
    setPlayback("loading");
    try {
      await player.play();
    } catch {
      if (request.current === attempt) setPlayback("error");
    }
  };

  return <>
    <audio ref={audio} src={VOICE_SAMPLES[voice]} preload="none"
      onPlaying={() => setPlayback("playing")}
      onEnded={() => setPlayback("idle")}
      onError={() => setPlayback("error")} />
    <button type="button" className="pill pill-quiet settings-sample" aria-label={label} title={label}
      aria-pressed={active} aria-busy={playback === "loading"} onClick={() => void toggle()}>
      {active ? <StopIcon size={19} aria-hidden="true" /> : <SpeakerHighIcon size={19} aria-hidden="true" />}
    </button>
    {playback === "error" ? <p className="settings-sample-error" role="alert">The voice sample could not be played. Try again.</p> : null}
  </>;
}

function SettingsForm({ value }: { value: ReadySettings }) {
  const [notice, setNotice] = useState(false);
  const { document, draft, save } = value;
  const root = useRef<HTMLFormElement>(null);
  const portrait = useRef<HTMLDivElement>(null);
  const pointerChoice = useRef(false);
  const tween = useRef<gsap.core.Tween | null>(null);
  const previousPreset = useRef(draft.preset);
  const [instructionsOpen, setInstructionsOpen] = useState(draft.guidance.length > 0);
  const preset = document.presets.find((item) => item.id === draft.preset);
  const voice = document.voices.find((item) => item.id === draft.voice);
  const defaultVoice = document.voices.find((item) => item.id === preset?.voice);
  const dirty = isDirty(value);
  const pending = save === "saving";
  const error = validationError(value);
  const customVoice = preset != null && draft.voice !== preset.voice;
  useRiseIn(root, ".settings-enter");

  // Retarget from an interrupted transition; never queue portrait animations.
  useLayoutEffect(() => {
    const target = portrait.current;
    if (!target || previousPreset.current === draft.preset) return;
    previousPreset.current = draft.preset;
    const interrupted = tween.current?.isActive();
    tween.current?.kill();
    if (!pointerChoice.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      gsap.set(target, { clearProps: "transform,opacity" });
      return;
    }
    if (!interrupted) gsap.set(target, { opacity: 0.6, y: 6 });
    tween.current = gsap.to(target, {
      opacity: 1, y: 0, duration: motionDurationMs(getComputedStyle(target).getPropertyValue("--dur-popover")) / 1000,
      ease: "expo.out", overwrite: true, clearProps: "transform,opacity",
    });
    pointerChoice.current = false;
  }, [draft.preset]);
  useEffect(() => () => { tween.current?.kill(); }, []);

  const status = pending ? "Saving changes…"
    : save === "saved" ? "Settings saved. New Roleplay Studio calls will use these settings."
    : save === "discarded" ? "Changes discarded. The saved settings are shown."
    : dirty ? "Unsaved changes. Your draft stays here while you browse the dashboard."
    : null;

  return <form ref={root} className="settings-form" onSubmit={(event) => { event.preventDefault(); void saveSettings().then(() => { if (state.status === "ready" && state.save === "saved") setNotice(true); }); }} aria-busy={pending}>
    {notice ? <SaveNotice onClose={() => setNotice(false)} /> : null}
    <fieldset className="settings-presets settings-enter" disabled={pending}>
      <legend>Choose a receptionist</legend>
      <div className="settings-preset-grid" onPointerDown={() => { pointerChoice.current = true; }} onKeyDown={() => { pointerChoice.current = false; }}>
        {document.presets.map((item) => <label key={item.id} className="settings-preset">
          <input type="radio" name="receptionist-preset" value={item.id} checked={draft.preset === item.id}
            aria-labelledby={`preset-${item.id}-name`} aria-describedby={`preset-${item.id}-description`}
            onChange={() => updateDraft({ preset: item.id, voice: item.voice })} />
          <span className="settings-preset-art" aria-hidden="true"><Orb size={112} state="disconnected" palette={item.id} /></span>
          <span className="settings-preset-copy">
            <span className="settings-preset-name" id={`preset-${item.id}-name`}>{item.name}<CheckIcon size={18} className="settings-preset-check" aria-hidden="true" /></span>
            <span className="settings-preset-description" id={`preset-${item.id}-description`}>{item.description}</span>
          </span>
        </label>)}
      </div>
    </fieldset>

    <div className="settings-editor settings-enter">
      <section className="settings-profile" aria-label="Selected receptionist">
        <div ref={portrait} className="settings-profile-content">
          <div className="settings-profile-art" aria-hidden="true"><Orb size={200} state="disconnected" palette={draft.preset} /></div>
          <div className="settings-profile-copy">
            <h2>{preset?.name ?? "Choose a preset"}</h2>
            <p>{preset?.description}</p>
            <p className="settings-profile-voice">{voice?.name ?? draft.voice} voice{customVoice ? `, customized from ${defaultVoice?.name ?? preset?.voice}` : ", preset default"}</p>
          </div>
        </div>
      </section>

      <fieldset className="settings-controls" disabled={pending}>
        <legend className="sr-only">Voice and conversation</legend>
        <div className="settings-voice-field">
          <label className="settings-field">
            <span className="settings-field-label">Voice</span>
            <PillSelect value={draft.voice} onChange={(next) => updateDraft({ voice: next })} label="Voice"
              options={document.voices.map((item) => ({ value: item.id, label: item.name }))} />
          </label>
          <VoiceSample key={draft.voice} voice={draft.voice} name={voice?.name ?? draft.voice} />
        </div>
        <div className="settings-voice-note">
          <p>{voice?.description}</p>
        </div>
        <label className="settings-field settings-language">
          <span className="settings-field-label">Opening language</span>
          <PillSelect value={draft.opening_language} onChange={(next) => updateDraft({ opening_language: next })} label="Opening language"
            options={[{ value: "en", label: "English" }, { value: "es", label: "Spanish" }]} />
        </label>
        <p className="settings-help">The receptionist greets the caller in this language, then follows the caller's language.</p>

        <details className="settings-instructions" open={instructionsOpen} onToggle={(event) => setInstructionsOpen(event.currentTarget.open)}>
          <summary>Additional instructions <span className="settings-optional">Optional</span><CaretDownIcon size={16} aria-hidden="true" /></summary>
          <div className="settings-instructions-body">
            <label className="settings-field" htmlFor="settings-guidance"><span className="settings-field-label">Conversation guidance</span></label>
            <p className="settings-help" id="settings-guidance-help">Add preferences for wording or tone. Clinic safety and delegation rules still apply.</p>
            <textarea id="settings-guidance" name="guidance" className="settings-textarea" rows={5} maxLength={1200} value={draft.guidance}
              aria-describedby={`settings-guidance-help settings-guidance-count${error ? " settings-validation" : ""}`} aria-invalid={draft.guidance.length > 1200}
              onChange={(event) => updateDraft({ guidance: event.target.value })} />
            <p id="settings-guidance-count" className="settings-character-count">{draft.guidance.length.toLocaleString("en-GB")} / 1,200 characters</p>
          </div>
        </details>
      </fieldset>
    </div>

    <footer className="settings-footer settings-enter">
      <div className="settings-save-area">
        {error ? <p className="settings-error" id="settings-validation" role="alert"><WarningIcon size={18} aria-hidden="true" />{error}</p> : null}
        {save === "error" ? <p className="settings-error" role="alert"><WarningIcon size={18} aria-hidden="true" />We could not confirm the save. Your draft is unchanged. Check the connection and retry.</p> : null}
        {status ? <p className="settings-save-status" role="status" aria-atomic="true">{status}</p> : null}
        <div className="settings-actions">
          <button type="button" className="pill pill-quiet" disabled={!dirty || pending} onClick={discardSettings}>Discard</button>
          <button type="submit" className="pill pill-primary" disabled={!dirty || pending || error != null}>{pending ? "Saving…" : save === "error" ? "Retry save" : "Save changes"}</button>
        </div>
      </div>
    </footer>
  </form>;
}

export function SettingsScreen() {
  const value = useSyncExternalStore(subscribe, snapshot);
  useEffect(() => { void loadSettings(); }, []);
  return <div className="settings-screen">
    <ScreenHeader title="Settings" />
    <div className="scroll-y settings-scroll">
      <div className="measure">
        {value.status === "ready" ? <SettingsForm value={value} /> : value.status === "error" ? <section className="settings-load-error" aria-labelledby="settings-load-title">
          <WarningIcon size={24} aria-hidden="true" />
          <h2 id="settings-load-title">Settings could not be loaded</h2>
          <p role="alert">We could not read the saved settings. Check the connection and try again. Nothing has changed.</p>
          <button type="button" className="pill pill-ghost" onClick={() => { void loadSettings(); }}>Retry loading</button>
        </section> : <div className="settings-loading" aria-busy="true">
          <p role="status">Loading saved settings…</p>
          <div className="settings-loading-presets" aria-hidden="true"><span className="loading-skeleton" /><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
          <div className="settings-loading-fields" aria-hidden="true"><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
        </div>}
      </div>
    </div>
  </div>;
}
