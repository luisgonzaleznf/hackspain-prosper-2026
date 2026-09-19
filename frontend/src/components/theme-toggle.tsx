// Circle reveal adapted from Magic UI's Animated Theme Toggler (MIT).
// https://magicui.design/docs/components/animated-theme-toggler
// Copyright (c) Magic UI. License: licenses/magic-ui.txt.
import { Moon, Sun } from "lucide-react";
import { useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { setTheme, useTheme } from "@/lib/theme";
import { motionDurationMs } from "@/lib/motion";

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const theme = useTheme();
  const button = useRef<HTMLButtonElement>(null);
  const active = useRef<ViewTransition | null>(null);
  const animation = useRef<Animation | null>(null);
  useEffect(() => () => {
    animation.current?.cancel();
    active.current?.skipTransition();
  }, []);

  const toggle = async () => {
    const root = document.documentElement;
    if (root.dataset.themeTransition === "active") return;
    const next = theme === "dark" ? "light" : "dark";
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!document.startViewTransition || reduce || !button.current) {
      setTheme(next);
      return;
    }
    const rect = button.current.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    const origin = `${x / innerWidth * 100}% ${y / innerHeight * 100}%`;
    const end = radius / (Math.hypot(innerWidth, innerHeight) / Math.SQRT2) * 100;
    const styles = getComputedStyle(root);
    const duration = motionDurationMs(styles.getPropertyValue("--dur-theme"));
    const easing = styles.getPropertyValue("--ease-smooth").trim();
    root.dataset.themeTransition = "active";
    root.style.setProperty("--theme-clip-start", `circle(0% at ${origin})`);
    const transition = document.startViewTransition(() => flushSync(() => setTheme(next)));
    active.current = transition;
    try {
      await transition.ready;
      animation.current = root.animate({ clipPath: [`circle(0% at ${origin})`, `circle(${end}% at ${origin})`] }, {
        duration, easing, fill: "forwards", pseudoElement: "::view-transition-new(root)",
      });
      await transition.finished;
    } catch {
      // The DOM update still applies when the browser skips a snapshot (e.g. hidden tab).
    } finally {
      animation.current?.cancel();
      animation.current = null;
      active.current = null;
      delete root.dataset.themeTransition;
      root.style.removeProperty("--theme-clip-start");
    }
  };

  return <button ref={button} type="button" role="switch" aria-checked={theme === "dark"} aria-label="Dark mode" title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} className={`theme-toggle ${compact ? "theme-toggle-compact" : ""}`} onClick={() => void toggle()}>
    <span className="theme-toggle-track" aria-hidden="true">
      <span className="theme-toggle-knob"><Sun className="theme-sun" size={16} /><Moon className="theme-moon" size={16} /></span>
    </span>
    {!compact ? <span>{theme === "dark" ? "Dark" : "Light"} mode</span> : null}
  </button>;
}
