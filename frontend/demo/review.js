// Call review: the recording and the durable JSONL trace for one rehearsal.
// The server contract is unchanged from the demo branch.
const call = new URLSearchParams(location.search).get("call") || "";
const base = `/api/demo/sessions/${encodeURIComponent(call)}`;
const byId = (id) => document.getElementById(id);

byId("call-id").textContent = call ? `Call ${call}` : "No call id in the link.";
const traceLink = byId("download-trace");
traceLink.href = `${base}/trace`;
traceLink.download = `${call}.jsonl`;

// codex and watchdog rows are engine bookkeeping; they add noise without telling
// the reader anything about the call.
const HIDDEN = new Set(["codex", "watchdog.config"]);
const ERRORS = new Set(["voice_error", "recording.error", "catalogue_error", "caller_id_error"]);

try {
  const response = await fetch(`${base}/trace`, { cache: "no-store" });
  if (!response.ok) throw new Error(`The trace is unavailable (${response.status})`);
  const rows = (await response.text()).trim().split("\n").filter(Boolean).flatMap((line) => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });
  const start = rows[0]?.t || 0;
  const ended = rows.some((row) => row.kind === "call_ended");
  const tools = rows.filter((row) => row.kind === "tool").length;
  const errors = rows.filter((row) => ERRORS.has(row.kind)).length;
  byId("status").textContent = `${ended ? "Saved" : "Still running, refresh once it ends"}. ${tools} tool calls, ${errors} errors.`;

  const list = byId("trace");
  for (const row of rows.filter((r) => !HIDDEN.has(r.kind))) {
    const li = document.createElement("li");
    const at = document.createElement("span");
    at.className = "at";
    at.textContent = `${(row.t - start).toFixed(1)}s`;
    li.append(at);
    if (row.kind === "transcript") {
      const body = document.createElement("div");
      const who = document.createElement("span");
      who.className = "at";
      who.textContent = row.role === "agent" ? "ROSARIO" : "Caller";
      const text = document.createElement("p");
      text.textContent = row.text;
      body.append(who, text);
      li.append(body);
    } else {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = row.name || row.kind.replaceAll("_", " ");
      const raw = document.createElement("pre");
      raw.textContent = JSON.stringify(row, null, 2);
      details.append(summary, raw);
      li.append(details);
    }
    list.append(li);
  }

  // One-shot reveal for the rows now in view; the rest are already at rest.
  const gsap = window.gsap;
  if (gsap && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const visible = [...list.children].filter((row) => row.getBoundingClientRect().top < innerHeight);
    gsap.from(visible, { y: 14, opacity: 0, duration: 0.5, ease: "expo.out", stagger: 0.04, clearProps: "transform" });
  }

  if (rows.some((row) => row.kind === "recording.saved")) {
    const player = byId("recording");
    player.src = `${base}/audio`;
    player.hidden = false;
    const download = byId("download-audio");
    download.href = `${base}/audio`;
    download.download = `${call}.wav`;
    download.hidden = false;
  }
} catch (error) {
  byId("status").textContent = String(error.message || error);
}
