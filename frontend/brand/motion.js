// ROSARIO motion layer. GSAP 3.15 (vendored), ScrollTrigger, SplitText.
//
// Rules this file keeps:
// - The page reads fully at rest without JS: every animation is a gsap.from(),
//   so the resting styles in CSS are the final state.
// - Nothing loops. Motion is one-shot on load, scrub-bound to scroll, or bound
//   to pointer movement. There is no timer-driven repaint.
// - transform and opacity only, plus clip-path for the headline mask.
// - prefers-reduced-motion: every tween collapses to opacity only via matchMedia.
// - Tokens: durations and eases live here in one place; keep them few.

(() => {
  if (!window.gsap) return;
  const { gsap } = window;
  gsap.registerPlugin(window.ScrollTrigger, window.SplitText);
  window.ScrollTrigger.config({ ignoreMobileResize: true });
  gsap.defaults({ ease: "power3.out", duration: 0.9 });

  // One strong ease for entrances; scrubbed motion is linear.
  const EASE_OUT = "expo.out";
  const D = { fast: 0.45, base: 0.8, slow: 1.1 };

  const mm = gsap.matchMedia();

  // ---------------------------------------------------------------- reduced motion
  // Opacity only, short. The page still "arrives", nothing travels.
  mm.add("(prefers-reduced-motion: reduce)", () => {
    gsap.utils.toArray("[data-reveal], .hero-copy > *, .hero-art, .top .lockup, .top-nav > a").forEach((el) => {
      gsap.from(el, { opacity: 0, duration: 0.4, ease: "none", scrollTrigger: { trigger: el, start: "top 92%", once: true } });
    });
  });

  // ---------------------------------------------------------------- full motion
  mm.add("(prefers-reduced-motion: no-preference)", (context) => {
    const cleanups = [];
    // Async work (fonts, marks:ready) may resolve after the preference flips and this
    // context is reverted; `live` stops those callbacks from starting motion late.
    let live = true;
    cleanups.push(() => { live = false; });
    const hero = document.querySelector(".hero");
    // ----- 1. Load sequence: lockup, nav, headline, copy, art.
    if (hero) {
      const tl = gsap.timeline({ defaults: { ease: EASE_OUT } });
      const lockup = document.querySelector(".top .lockup");
      const navItems = gsap.utils.toArray(".top .top-nav > a");
      const h1 = hero.querySelector("h1");
      const copy = hero.querySelectorAll(".hero-copy > p, .hero-copy > .btn");
      const art = hero.querySelector(".hero-art img");

      if (lockup) tl.from(lockup, { y: 12, opacity: 0, duration: D.fast }, 0.15);
      if (navItems.length) tl.from(navItems, { y: -10, opacity: 0, duration: D.fast, stagger: 0.05 }, 0.25);

      // Headline: each line rises out of its own mask. Weight-100 type wants
      // a clean edge, so the mask is a clip-path, not a fade. Plain loads with
      // font-display: swap, so the split waits for the real metrics (otherwise a
      // cold visit would freeze fallback-font line breaks); the headline is hidden
      // meanwhile so it cannot paint and then replay. The wrappers are reverted
      // once the entrance ends, so later resizes reflow the headline normally.
      if (h1) {
        gsap.set(h1, { autoAlpha: 0 });
        document.fonts.ready.then(context.add(() => {
          if (!live) { gsap.set(h1, { clearProps: "all" }); return; }
          // Each line rises inside a stationary mask wrapper (SplitText mask: "lines").
          // Line-height is 1.0, so descenders hang below the line box: the mask gets
          // that much padding, pulled back with a negative margin so layout is unchanged
          // and the descenders of "judgement" are never clipped, at any point of the ease.
          const split = new window.SplitText(h1, { type: "lines", linesClass: "split-line", mask: "lines" });
          gsap.set(split.masks, { paddingBottom: "0.3em", marginBottom: "-0.3em" });
          gsap.set(h1, { autoAlpha: 1 });
          gsap.from(split.lines, { yPercent: 130, duration: D.slow, ease: EASE_OUT, stagger: 0.09, onComplete: () => split.revert() });
          window.ScrollTrigger.refresh();
        }));
      }
      if (copy.length) tl.from(copy, { y: 24, opacity: 0, duration: D.base, stagger: 0.1 }, 0.9);

      // The handset is picked up: it rises into place and tilts level, once.
      if (art) {
        gsap.set(art, { transformOrigin: "50% 50%" });
        tl.from(art, { y: 90, opacity: 0, duration: D.slow, ease: EASE_OUT }, 0.5);
        tl.from(art, { rotation: 7, duration: 1.2, ease: "back.out(1.4)" }, 0.6);
      }
    }

    // ----- 2. Pointer parallax on the hero art: decorative, marketing page,
    // moves only while the pointer moves. quickTo keeps it cheap.
    // Parallax writes to the wrapper; the entrance owns the image's transform.
    const artWrap = document.querySelector(".hero-art");
    if (hero && artWrap && matchMedia("(hover: hover) and (pointer: fine)").matches) {
      const toX = gsap.quickTo(artWrap, "x", { duration: 0.6, ease: "power3.out" });
      const toY = gsap.quickTo(artWrap, "y", { duration: 0.6, ease: "power3.out" });
      const toR = gsap.quickTo(artWrap, "rotation", { duration: 0.8, ease: "power3.out" });
      const onMove = (e) => {
        const r = hero.getBoundingClientRect();
        const nx = (e.clientX - r.left) / r.width - 0.5;
        const ny = (e.clientY - r.top) / r.height - 0.5;
        toX(nx * 18); toY(ny * 12); toR(nx * 3);
      };
      const onLeave = () => { toX(0); toY(0); toR(0); };
      hero.addEventListener("pointermove", onMove);
      hero.addEventListener("pointerleave", onLeave);
      // matchMedia cleanup: if the reduced-motion preference flips on, stop the parallax and rest the wrapper.
      cleanups.push(() => {
        hero.removeEventListener("pointermove", onMove);
        hero.removeEventListener("pointerleave", onLeave);
        gsap.set(artWrap, { clearProps: "transform" });
      });
    }

    // ----- 3. Section reveals: heading, copy, actions rise in order.
    gsap.utils.toArray("[data-reveal]").forEach((block) => {
      const items = block.querySelectorAll(":scope > *");
      gsap.from(items.length ? items : block, {
        y: 28, opacity: 0, duration: D.base, ease: EASE_OUT, stagger: 0.08,
        scrollTrigger: { trigger: block, start: "top 82%", once: true },
      });
    });

    // Cards slide in from their side of the grid while the feature sections are
    // two columns (1200px and up, see brand.css); once they stack, cards rise
    // instead, so a pre-trigger x offset never pushes a full-width card past the edge.
    const twoColumnFeatures = matchMedia("(min-width: 1200px)").matches;
    gsap.utils.toArray(".feature .card, .glance .card").forEach((card) => {
      const fromRight = card.parentElement.classList.contains("reverse") ? -1 : 1;
      gsap.from(card, {
        ...(twoColumnFeatures ? { x: 48 * fromRight } : { y: 32 }), opacity: 0, duration: D.slow, ease: EASE_OUT,
        scrollTrigger: { trigger: card, start: "top 80%", once: true },
      });
      // Rows land one by one after the card.
      gsap.from(card.querySelectorAll(".mock-row"), {
        y: 12, opacity: 0, duration: D.fast, ease: EASE_OUT, stagger: 0.06, delay: 0.35,
        scrollTrigger: { trigger: card, start: "top 80%", once: true },
      });
    });

    // ----- 4. The dial turns as you scroll past it: a rotary dial being dialled.
    const dial = document.querySelector(".plate img");
    if (dial) {
      gsap.fromTo(dial, { rotation: -70 }, {
        rotation: 0, ease: "none",
        scrollTrigger: { trigger: ".plate-wrap", start: "top bottom", end: "center center", scrub: 0.6 },
      });
      gsap.from(".plate", { scale: 0.92, opacity: 0, duration: D.slow, ease: EASE_OUT,
        scrollTrigger: { trigger: ".plate-wrap", start: "top 75%", once: true } });
    }

    // ----- 5. Stats count up once, from zero, snapping to integers.
    gsap.utils.toArray(".stats strong").forEach((el) => {
      const end = parseInt(el.textContent, 10);
      if (Number.isNaN(end)) return;
      const obj = { v: 0 };
      gsap.to(obj, {
        v: end, duration: 1.1, ease: "power2.out", snap: { v: 1 },
        onUpdate: () => { el.textContent = String(obj.v); },
        scrollTrigger: { trigger: ".stats", start: "top 80%", once: true },
      });
    });
    gsap.from(".stats > div", { y: 24, opacity: 0, duration: D.base, ease: EASE_OUT, stagger: 0.08,
      scrollTrigger: { trigger: ".stats", start: "top 80%", once: true } });

    // ----- 6. Light band: the six steps rise in a staggered wave.
    gsap.from(".grid > div", { y: 32, opacity: 0, duration: D.base, ease: EASE_OUT, stagger: { each: 0.08, from: "start" },
      scrollTrigger: { trigger: ".grid", start: "top 80%", once: true } });

    // ----- 7. The rosary hangs into the closing band and swings once about its top.
    const hang = document.querySelector(".cta-art img");
    if (hang) {
      gsap.set(hang, { transformOrigin: "50% 0%" });
      gsap.from(hang, { y: -120, opacity: 0, duration: D.slow, ease: EASE_OUT,
        scrollTrigger: { trigger: ".cta-band", start: "top 75%", once: true } });
      gsap.from(hang, { rotation: -7, duration: 1.3, ease: "back.out(1.4)",
        scrollTrigger: { trigger: ".cta-band", start: "top 75%", once: true } });
      gsap.fromTo(".cta-art", { y: 24 }, { y: -24, ease: "none",
        scrollTrigger: { trigger: ".cta-band", start: "top bottom", end: "bottom top", scrub: 0.8 } });
    }

    // ----- 7b. Call bars grow from the left as their table enters, one row after another.
    gsap.utils.toArray(".mock-table").forEach((table) => {
      const bars = table.querySelectorAll(".callbar svg");
      if (!bars.length) return;
      gsap.set(bars, { transformOrigin: "0% 50%" });
      gsap.from(bars, { scaleX: 0, duration: D.base, ease: EASE_OUT, stagger: 0.08,
        scrollTrigger: { trigger: table, start: "top 80%", once: true } });
    });

    // ----- 7c. Audiogram: bars rise from the midline, then the playhead sweeps the
    // call once, lighting each turn as it passes. Afterwards the pointer scrubs it.
    gsap.utils.toArray("[data-audiogram]").forEach((ag) => {
      const svg = ag.querySelector(".ag-wave");
      const head = svg.querySelector(".ag-head-line");
      const timeEl = ag.querySelector("[data-ag-time]");
      const turns = [...ag.querySelectorAll("li")];
      const length = Number(ag.dataset.length);
      const bars = svg.querySelectorAll("rect");
      const range = ag.querySelector(".ag-range");
      const pos = { t: 0 };
      const show = () => {
        range.value = String(Math.round(pos.t));
        const x = (pos.t / length) * 600;
        gsap.set(head, { attr: { x1: x, x2: x } });
        timeEl.textContent = `${Math.floor(pos.t / 60)}:${String(Math.floor(pos.t % 60)).padStart(2, "0")}`;
        turns.forEach((li) => {
          li.classList.toggle("on", pos.t >= Number(li.dataset.from) && pos.t < Number(li.dataset.to));
        });
        bars.forEach((r) => r.classList.toggle("dim", Number(r.getAttribute("x")) > x));
      };
      show();
      gsap.set(bars, { transformOrigin: "50% 50%" });
      const intro = gsap.timeline({ scrollTrigger: { trigger: ag, start: "top 80%", once: true } });
      intro.from(bars, { scaleY: 0, duration: D.base, ease: EASE_OUT, stagger: { each: 0.006, from: "start" } }, 0);
      intro.to(pos, { t: length - 0.01, duration: 2.6, ease: "none", onUpdate: show }, 0.3);
      // The range input lies over the wave and is the only position state: the sweep
      // writes to it, and the pointer and the keyboard both move it, so the value it
      // reports is always the time on screen.
      const onInput = () => { intro.kill(); pos.t = Number(range.value); show(); };
      range.addEventListener("input", onInput);
      cleanups.push(() => range.removeEventListener("input", onInput));
    });


    // ----- 8. Identity page: marks arrive from the center of the grid. The
    // gallery is filled asynchronously by brand.js, so wait for marks:ready
    // (all SVGs inlined, heights final) before measuring the trigger.
    const marks = document.getElementById("marks");
    if (marks) {
      document.addEventListener("marks:ready", context.add(() => {
        const figs = marks.querySelectorAll("figure");
        if (!live || !figs.length) return;
        gsap.from(figs, { scale: 0.85, opacity: 0, duration: D.base, ease: EASE_OUT,
          stagger: { amount: 0.6, from: "center", grid: "auto" },
          scrollTrigger: { trigger: marks, start: "top 85%", once: true } });
        window.ScrollTrigger.refresh();
      }), { once: true });
    }
    gsap.utils.toArray(".id-row, .swatches, .imagery-row, .specimen").forEach((row) => {
      gsap.from(row.children, { y: 24, opacity: 0, duration: D.base, ease: EASE_OUT, stagger: 0.06,
        scrollTrigger: { trigger: row, start: "top 82%", once: true } });
    });
    return () => cleanups.forEach((fn) => fn());
  });

  // Recalculate positions once images and inline SVGs are in (they change layout height).
  window.addEventListener("load", () => window.ScrollTrigger.refresh());
  document.addEventListener("marks:ready", () => window.ScrollTrigger.refresh(), { once: true });
})();
