// One-shot entrances. Only visible rows animate, so long call histories never
// hide rows behind a multi-second stagger. Reduced motion is immediate.

import gsap from "gsap";
import { useLayoutEffect, type RefObject } from "react";

const EASE_OUT = "expo.out";

/** Production CSS may minify 500ms to .5s; Web Animations always expects ms. */
export function motionDurationMs(value: string): number {
  return parseFloat(value) * (value.trim().endsWith("ms") ? 1 : 1000);
}

/** Brief entrance for visible children, without delaying off-screen rows. */
export function useRiseIn(ref: RefObject<HTMLElement | null>, selector: string, deps: unknown[] = []): void {
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const bounds = root.getBoundingClientRect();
    const targets = Array.from(root.querySelectorAll<HTMLElement>(selector)).filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.bottom > bounds.top && rect.top < bounds.bottom;
    });
    if (targets.length === 0) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.from(targets, { y: 6, opacity: 0, duration: 0.2, ease: EASE_OUT, stagger: { amount: 0.1 }, clearProps: "transform,opacity" });
    });
    return () => mm.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/** Slide a drawer in from the right (or up on narrow screens) on mount. */
export function useSlideIn(ref: RefObject<HTMLElement | null>, axis: "x" | "y" = "x"): void {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.from(el, { [axis]: axis === "x" ? 16 : 12, opacity: 0, duration: 0.25, ease: EASE_OUT, clearProps: "transform,opacity" });
    });
    return () => mm.revert();
  }, [ref, axis]);
}

/** Count a numeral up from zero once, snapping to integers (stats rule from the brand page). */
export function useCountUp(ref: RefObject<HTMLElement | null>, value: number, decimals = 0): void {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    const format = (n: number) => (decimals > 0 ? n.toFixed(decimals) : Math.round(n).toLocaleString("en-GB"));
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      const obj = { n: 0 };
      gsap.to(obj, { n: value, duration: 0.9, ease: "power3.out", onUpdate: () => (el.textContent = format(obj.n)) });
    });
    mm.add("(prefers-reduced-motion: reduce)", () => {
      el.textContent = format(value);
    });
    return () => mm.revert();
  }, [ref, value, decimals]);
}
