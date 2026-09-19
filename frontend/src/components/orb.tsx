// orb-ui supplies the WebGL artwork, keyboard-accessible control and reduced-motion handling.
// ROSARIO supplies only real directional audio levels and its existing color tokens.
import { Orb as VoiceOrb, type OrbTheme } from "orb-ui";
import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";

export interface OrbLevels { agent: number; caller: number }
export type OrbState = "disconnected" | "connecting" | "listening" | "speaking" | "thinking";

const theme: OrbTheme = {
  name: "radial",
  preset: "calm",
  geometry: { diameterRatio: 0.92 },
  motion: { idleSpeed: 0, listeningBaseSpeed: 0, speakingBaseSpeed: 0 },
};

export function Orb({ size = 192, levels, state, className, onActivate, label, controlIcon, disabled }: {
  size?: number;
  levels?: RefObject<OrbLevels>;
  state: OrbState;
  className?: string;
  onActivate?: () => void;
  label?: string;
  controlIcon?: ReactNode;
  disabled?: boolean;
}) {
  const [meter, setMeter] = useState<OrbLevels>({ agent: 0, caller: 0 });
  useEffect(() => {
    if (!levels || state === "disconnected") {
      setMeter({ agent: 0, caller: 0 });
      return;
    }
    const timer = window.setInterval(() => {
      const agent = Math.round(levels.current.agent * 100) / 100;
      const caller = Math.round(levels.current.caller * 100) / 100;
      setMeter((previous) => previous.agent === agent && previous.caller === caller ? previous : { agent, caller });
    }, 33);
    return () => window.clearInterval(timer);
  }, [levels, state]);

  return <VoiceOrb
    className={`rosario-orb ${className ?? ""}`}
    size={size}
    theme={theme}
    signal={{ state: state === "disconnected" ? "idle" : state, inputVolume: meter.caller, outputVolume: meter.agent }}
    interactive={Boolean(onActivate)}
    disabled={disabled}
    onStart={onActivate}
    onStop={onActivate}
    aria-label={label}
    components={{ controlIcon }}
    data-levels={`${meter.agent},${meter.caller}`}
    style={{
      "--orb-ui-radial-control-surround": "var(--bg)",
      "--orb-ui-radial-appearance-deep-color": "var(--color-obsidian-burgundy)",
      "--orb-ui-radial-appearance-cobalt-color": "var(--color-nava-fire)",
      "--orb-ui-radial-appearance-aqua-color": "var(--color-ember-glow)",
      "--orb-ui-radial-appearance-pale-color": "var(--color-ash-rose)",
      "--orb-ui-radial-appearance-membrane-color": "var(--color-muted-coral)",
      "--orb-ui-radial-appearance-seam-color": "var(--color-nava-white)",
      "--orb-ui-radial-appearance-idle-control-color": "var(--primary)",
      "--orb-ui-radial-appearance-active-control-color": "var(--primary)",
      "--orb-ui-radial-appearance-connecting-control-color": "var(--primary)",
    }}
  />;
}

/** RMS microphone meter; the stream remains owned by the Talk screen. */
export function useLevelMeter(source: MediaStream | null, out: (level: number) => void): void {
  const callback = useRef(out);
  useEffect(() => { callback.current = out; }, [out]);
  useEffect(() => {
    if (!source) { callback.current(0); return; }
    const ctx = new AudioContext();
    const node = ctx.createMediaStreamSource(source);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    node.connect(analyser);
    const data = new Float32Array(analyser.fftSize);
    const timer = window.setInterval(() => {
      analyser.getFloatTimeDomainData(data);
      let sum = 0;
      for (const value of data) sum += value * value;
      callback.current(Math.min(1, Math.sqrt(sum / data.length) * 2.4));
    }, 33);
    return () => {
      window.clearInterval(timer);
      callback.current(0);
      node.disconnect();
      void ctx.close();
    };
  }, [source]);
}
