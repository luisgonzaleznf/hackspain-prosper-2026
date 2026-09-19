const call = new URLSearchParams(location.search).get("call") || "";
const base = `/api/demo/sessions/${encodeURIComponent(call)}`;
document.querySelector("#call-id").textContent = `Call ID: ${call}`;
const traceLink = document.querySelector("#download-trace");
traceLink.href = `${base}/trace`;
traceLink.download = `${call}.jsonl`;

try {
  const response = await fetch(`${base}/trace`, {cache: "no-store"});
  if (!response.ok) throw new Error(`Trace unavailable (${response.status})`);
  const rows = (await response.text()).trim().split("\n").filter(Boolean).flatMap(line => {
    try { return [JSON.parse(line)]; } catch { return []; }
  });
  const start = rows[0]?.t || 0;
  const ended = rows.some(row => row.kind === "call_ended");
  const errors = rows.filter(row => ["voice_error", "recording.error", "catalogue_error", "caller_id_error"].includes(row.kind));
  document.querySelector("#status").textContent = `${ended ? "Call saved" : "Call in progress — refresh after ending it"} · ${rows.filter(row => row.kind === "tool").length} tool calls · ${errors.length} recorded errors`;
  const timeline = document.querySelector("#timeline");
  rows.filter(row => row.kind !== "codex" && row.kind !== "watchdog.config").forEach(row => {
    const article = document.createElement("article");
    article.className = "review-row";
    const meta = document.createElement("p");
    meta.className = "review-meta";
    meta.textContent = `${(row.t - start).toFixed(1)}s · ${row.kind === "transcript" ? row.role : row.kind}`;
    article.append(meta);
    if (row.kind === "transcript") {
      const speech = document.createElement("p");
      speech.textContent = row.text;
      article.append(speech);
    } else {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = row.name || row.kind.replaceAll("_", " ");
      const raw = document.createElement("pre");
      raw.textContent = JSON.stringify(row, null, 2);
      details.append(summary, raw);
      article.append(details);
    }
    timeline.append(article);
  });
  if (rows.some(row => row.kind === "recording.saved")) {
    const player = document.querySelector("#recording");
    player.src = `${base}/audio`;
    player.hidden = false;
    const download = document.querySelector("#download-audio");
    download.href = `${base}/audio`;
    download.download = `${call}.wav`;
    download.hidden = false;
  }
} catch (error) {
  document.querySelector("#status").textContent = error.message;
}
