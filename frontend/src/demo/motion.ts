// Motion for the roleplay studio.
//
// Brand motion, not console motion: DESIGN.md gives the brand pages 450 to
// 1200ms one-shot entrances, where the console uses 200ms state changes. Every
// tween here is a gsap.from, so the resting styles in CSS are the final state
// and the page reads correctly if JavaScript never runs.
//
// Nothing loops. Each effect fires once, on mount or when its data first
// arrives, and every one collapses to a short fade under prefers-reduced-motion.

import gsap from "gsap";
import { SplitText } from "gsap/SplitText";
import { useLayoutEffect, type RefObject } from "react";

gsap.registerPlugin(SplitText);

const EASE = "expo.out";
export const D = { fast: 0.45, base: 0.8, slow: 1.1 };

/** Runs `build` inside a context scoped to `scope`, once `when` turns true. */
function useMotion(scope: RefObject<HTMLElement | null>, when: boolean, build: (ctx: { still: boolean }) => void, deps: unknown[]) {
  useLayoutEffect(() => {
    const root = scope.current;
    if (!root || !when) return;
    const mm = gsap.matchMedia();
    mm.add({ still: "(prefers-reduced-motion: reduce)", full: "(prefers-reduced-motion: no-preference)" }, (context) => {
      build({ still: Boolean(context.conditions?.still) });
    });
    return () => mm.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/** The headline rises line by line out of its own mask. */
export function useHeadline(ref: RefObject<HTMLElement | null>) {
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      // Wait for Plain: weight-100 headlines reflow badly if split against a fallback.
      void document.fonts.ready.then(() => {
        if (!ref.current) return;
        const split = new SplitText(element, { type: "lines", mask: "lines" });
        gsap.set(element, { autoAlpha: 1 });
        gsap.from(split.lines, { yPercent: 120, duration: D.slow, ease: EASE, stagger: 0.08, onComplete: () => split.revert() });
      });
    });
    mm.add("(prefers-reduced-motion: reduce)", () => { gsap.set(element, { autoAlpha: 1 }); });
    return () => mm.revert();
  }, [ref]);
}

/** The caller cards deal in, one after another. */
export function useRoleCards(scope: RefObject<HTMLElement | null>, count: number) {
  useMotion(scope, count > 0, ({ still }) => {
    const cards = scope.current?.querySelectorAll(".role");
    if (!cards?.length) return;
    if (still) { gsap.from(cards, { opacity: 0, duration: 0.3, ease: "none" }); return; }
    gsap.from(cards, { y: 34, opacity: 0, scale: 0.97, duration: D.base, ease: EASE, stagger: 0.07, clearProps: "transform" });
  }, [count]);
}

/** The stage arrives: the orb blooms, the brief slides in, its facts follow. */
export function useStageIn(scope: RefObject<HTMLElement | null>, roleId: string | null) {
  useMotion(scope, Boolean(roleId), ({ still }) => {
    const root = scope.current;
    if (!root) return;
    const orb = root.querySelector(".control");
    const brief = root.querySelector(".brief");
    const facts = root.querySelectorAll(".brief > *");
    if (still) {
      gsap.from([orb, brief].filter(Boolean), { opacity: 0, duration: 0.3, ease: "none" });
      return;
    }
    const timeline = gsap.timeline({ defaults: { ease: EASE } });
    if (orb) timeline.from(orb, { scale: 0.86, opacity: 0, duration: D.slow, ease: "back.out(1.5)", clearProps: "transform" }, 0);
    if (brief) timeline.from(brief, { x: 40, opacity: 0, duration: D.base, clearProps: "transform" }, 0.08);
    if (facts.length) timeline.from(facts, { y: 14, opacity: 0, duration: D.fast, stagger: 0.05, clearProps: "transform" }, 0.2);
  }, [roleId]);
}

/** The orb blooms once when the call connects, and once when it closes. */
export function useCallMoment(scope: RefObject<HTMLElement | null>, phase: string) {
  useLayoutEffect(() => {
    if (phase !== "live" && phase !== "complete") return;
    const orb = scope.current?.querySelector(".rosario-orb") ?? scope.current;
    if (!orb) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.fromTo(orb,
        { scale: phase === "live" ? 0.94 : 1.03 },
        { scale: 1, duration: D.slow, ease: "elastic.out(1, 0.55)", clearProps: "transform" });
    });
    return () => mm.revert();
  }, [scope, phase]);
}

/** Each new turn or lookup slides in as it arrives, and the list follows it. */
export function useFeed(ref: RefObject<HTMLElement | null>, length: number) {
  useLayoutEffect(() => {
    const list = ref.current;
    if (!list || !length) return;
    const row = list.lastElementChild;
    if (!row) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.from(row, { x: -18, opacity: 0, duration: D.fast, ease: EASE, clearProps: "transform" });
    });
    list.scrollTo({ top: list.scrollHeight, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    return () => mm.revert();
  }, [ref, length]);
}

/** The status line crossfades rather than snapping between states. */
export function useStatus(ref: RefObject<HTMLElement | null>, text: string) {
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.from(element, { y: 8, opacity: 0, duration: 0.35, ease: EASE, clearProps: "transform" });
    });
    return () => mm.revert();
  }, [ref, text]);
}

/** The receipt lands, then its checks tick in one by one. */
export function useReceipt(scope: RefObject<HTMLElement | null>, shown: boolean) {
  useMotion(scope, shown, ({ still }) => {
    const root = scope.current;
    if (!root) return;
    const card = root.querySelector(".receipt");
    const parts = root.querySelectorAll(".receipt > *");
    const checks = root.querySelectorAll(".checks li");
    if (still) { gsap.from(card, { opacity: 0, duration: 0.3, ease: "none" }); return; }
    const timeline = gsap.timeline({ defaults: { ease: EASE } });
    if (card) timeline.from(card, { y: 26, opacity: 0, scale: 0.98, duration: D.base, clearProps: "transform" }, 0);
    if (parts.length) timeline.from(parts, { y: 12, opacity: 0, duration: D.fast, stagger: 0.06, clearProps: "transform" }, 0.15);
    if (checks.length) timeline.from(checks, { x: -12, opacity: 0, duration: D.fast, stagger: 0.07, clearProps: "transform" }, 0.35);
  }, [shown]);
}

/** Saved rehearsals rise as a group when the list first fills. */
export function useLedger(scope: RefObject<HTMLElement | null>, count: number) {
  useMotion(scope, count > 0, ({ still }) => {
    const rows = scope.current?.querySelectorAll(".ledger-row");
    if (!rows?.length) return;
    if (still) { gsap.from(rows, { opacity: 0, duration: 0.3, ease: "none" }); return; }
    gsap.from(rows, { y: 16, opacity: 0, duration: D.fast, ease: EASE, stagger: 0.05, clearProps: "transform" });
  }, [count]);
}
