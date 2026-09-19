// Inline the normalized logo SVGs so CSS can color them (currentColor + --logo-bg / --logo-word).
// Paths are absolute: this script runs on the landing page at / and on /brand/identity.html.
const cache = new Map();
// Inlined SVGs are decorative (their meaning is in adjacent text), and repeated
// marks would duplicate internal ids, so ids are stripped and the root is hidden
// from assistive technology.
const load = (path) => {
  if (!cache.has(path)) {
    cache.set(path, fetch(path).then((r) => (r.ok ? r.text() : "")).then((svg) =>
      svg.replace(/\s+id="[^"]*"/g, "").replace(/<svg (?![^>]*aria-hidden)/, '<svg aria-hidden="true" focusable="false" ')));
  }
  return cache.get(path);
};
// Every inline fetch is tracked so motion.js can re-measure the page once
// all marks are in (they change element heights).
const pending = [];
const inlineMarks = (root = document) => {
  for (const el of root.querySelectorAll("[data-mark]:empty")) {
    pending.push(load(`/brand/logos/marks/${el.dataset.mark}.svg`).then((svg) => { el.innerHTML = svg; }));
  }
};
inlineMarks();
for (const el of document.querySelectorAll("[data-icon]")) {
  pending.push(load(`/brand/logos/icons/${el.dataset.icon}.svg`).then((svg) => { el.innerHTML = svg; }));
}
for (const el of document.querySelectorAll("[data-file]")) {
  pending.push(load(`/brand/logos/final/${el.dataset.file}.svg`).then((svg) => { el.innerHTML = svg; }));
}
const announceReady = () => Promise.all(pending).then(() => document.dispatchEvent(new CustomEvent("marks:ready")));

// The mark gallery is built from logos/marks/index.json (written by scripts/index-marks.py)
// so new candidate rounds appear without editing the page. Only identity.html has #marks.
const gallery = document.getElementById("marks");
if (gallery) {
  fetch("/brand/logos/marks/index.json").then((r) => (r.ok ? r.json() : [])).then((names) => {
    for (const name of names) {
      const fig = document.createElement("figure");
      const el = document.createElement("i");
      el.dataset.mark = name;
      const cap = document.createElement("figcaption");
      // Captions read as words; the SVG lives at brand/logos/marks/<name>.svg.
      cap.textContent = name.replace(/^r\d+-/, "").replace(/-/g, " ");
      if (name === "dial-rose-ten") {
        fig.classList.add("current");
        const tag = document.createElement("span");
        tag.className = "current-tag";
        tag.textContent = "Current identity";
        cap.prepend(tag);
        fig.setAttribute("aria-current", "true");
      }
      fig.append(el, cap);
      gallery.appendChild(fig);
    }
    inlineMarks(gallery);
    announceReady();
  });
} else {
  announceReady();
}

// Call bars: data-bars="c3 a5 s2" is who spoke (c caller, a ROSARIO, s silence) and for
// how long, in relative units. One rounded rect per stretch, laid out across 100 units.
const SVG = "http://www.w3.org/2000/svg";
const el = (name, attrs) => { const n = document.createElementNS(SVG, name); for (const k in attrs) n.setAttribute(k, attrs[k]); return n; };
for (const bar of document.querySelectorAll(".callbar[data-bars]")) {
  const parts = bar.dataset.bars.split(" ").map((p) => [p[0], Number(p.slice(1))]);
  const total = parts.reduce((n, [, len]) => n + len, 0);
  // Caller sits above the middle, ROSARIO below, silence on the line itself, so the
  // lanes read without colour. The adjacent sr-only text carries the same facts.
  const svg = el("svg", { viewBox: "0 0 100 18", preserveAspectRatio: "none", "aria-hidden": "true", focusable: "false" });
  const lane = { c: { y: 0, h: 7 }, a: { y: 11, h: 7 }, s: { y: 8, h: 2 } };
  let x = 0;
  for (const [who, len] of parts) {
    const wdt = (len / total) * 100;
    const { y, h } = lane[who] ?? lane.s;
    svg.append(el("rect", { class: who, x: x + 0.4, y, width: Math.max(wdt - 0.8, 0.6), height: h, rx: 1 }));
    x += wdt;
  }
  bar.append(svg);
}

// Audiogram: bars every half second, caller above the midline and ROSARIO below,
// lookups as ticks. Amplitude is a fixed pseudo-random shape so the page is stable.
for (const ag of document.querySelectorAll("[data-audiogram]")) {
  const svg = ag.querySelector(".ag-wave");
  const length = Number(ag.dataset.length);
  const W = 600, H = 72, mid = H / 2, step = W / (length * 2);
  const amp = (i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 12.9898 + 4.1414) * Math.cos(i * 0.37));
  svg.append(el("line", { class: "ag-mid", x1: 0, y1: mid, x2: W, y2: mid }));
  for (const li of ag.querySelectorAll("li")) {
    const from = Number(li.dataset.from), to = Number(li.dataset.to);
    if (li.classList.contains("decision")) {
      const x = (from / length) * W + 2;
      svg.append(el("line", { class: "ag-tick", x1: x, y1: 10, x2: x, y2: H - 10 }));
      svg.append(el("circle", { class: "ag-tick-dot", cx: x, cy: 8, r: 2.5 }));
      continue;
    }
    const who = li.classList.contains("caller") ? "c" : "a";
    for (let i = from * 2; i < to * 2; i++) {
      const h = amp(i) * 26;
      svg.append(el("rect", { class: who, x: i * step + 1, width: step - 2, rx: 1, y: who === "c" ? mid - 2 - h : mid + 2, height: h }));
    }
  }
  svg.append(el("line", { class: "ag-head-line", x1: 0, y1: 0, x2: 0, y2: H }));
}

// Link each cell to its column header for assistive technology. The visible
// mobile labels come from static data-label attributes in the HTML, not from here.
for (const table of document.querySelectorAll(".mock-table")) {
  const ths = [...table.querySelectorAll("th")];
  ths.forEach((th, i) => { th.id ||= `${table.id || "t" + Math.random().toString(36).slice(2, 6)}-h${i}`; });
  for (const row of table.querySelectorAll(".mock-row")) {
    row.querySelectorAll("td").forEach((cell, i) => { if (ths[i]) cell.setAttribute("headers", ths[i].id); });
  }
}

// Hide the floating dashboard link only while another dashboard link is visible.
const floatBtn = document.getElementById("float");
const rivals = [...document.querySelectorAll(".top a, .foot a")].filter((link) => link.href === floatBtn?.href);
if (floatBtn && rivals.length && "IntersectionObserver" in window) {
  const visible = new Set();
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) { if (e.isIntersecting) visible.add(e.target); else visible.delete(e.target); }
    floatBtn.hidden = visible.size > 0;
  }, { threshold: 0 });
  rivals.forEach((el) => io.observe(el));
}
