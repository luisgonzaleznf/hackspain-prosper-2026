import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

const OUTCOME_LABELS = Object.freeze({
  BOOK: "Booking prepared",
  CANCEL: "Cancellation prepared",
  RESCHEDULE: "Change prepared",
  ESCALATE: "Escalated safely",
  NO_ACTION: "No action required",
});
const ROLE_ICONS = Object.freeze(["◷", "↻", "+"]);
const POLL_INTERVAL_MS = 900;

const state = {
  scenarios: [],
  selected: null,
  client: null,
  sessionId: null,
  snapshotReady: false,
  snapshot: null,
  eventSource: null,
  executionEvents: [],
  pollTimer: null,
  phase: "idle",
  stopping: false,
  audio: null,
};

const elements = {
  alert: document.querySelector("#global-alert"),
  grid: document.querySelector("#scenario-grid"),
  studio: document.querySelector("#studio"),
  briefEmpty: document.querySelector("#brief-empty"),
  briefContent: document.querySelector("#brief-content"),
  monogram: document.querySelector("#persona-monogram"),
  personaTitle: document.querySelector("#persona-title"),
  personaName: document.querySelector("#persona-name"),
  personaPhone: document.querySelector("#persona-phone"),
  facts: document.querySelector("#persona-facts"),
  objective: document.querySelector("#persona-objective"),
  hint: document.querySelector("#persona-hint"),
  connection: document.querySelector("#connection-pill"),
  connectionText: document.querySelector("#connection-pill span"),
  studioHeading: document.querySelector("#studio-heading"),
  micButton: document.querySelector("#mic-button"),
  micTitle: document.querySelector("#mic-title"),
  micSubtitle: document.querySelector("#mic-subtitle"),
  engineeringView: document.querySelector("#engineering-view"),
  executionGraph: document.querySelector("#execution-graph"),
  eventCount: document.querySelector("#event-count"),
  fullTraceLink: document.querySelector("#full-trace-link"),
  milestones: document.querySelector("#milestone-list"),
  milestoneCount: document.querySelector("#milestone-count"),
  transcript: document.querySelector("#transcript"),
  toolCount: document.querySelector("#tool-count"),
  toolEvents: document.querySelector("#tool-events"),
  receiptEmpty: document.querySelector("#receipt-empty"),
  receiptContent: document.querySelector("#receipt-content"),
  receiptLabel: document.querySelector("#receipt-label"),
  receiptFields: document.querySelector("#receipt-fields"),
  receiptChecks: document.querySelector("#receipt-checks"),
  botAudio: document.querySelector("#bot-audio"),
  ledger: document.querySelector("#ledger"),
  resetButton: document.querySelector("#reset-button"),
};

function showAlert(message) {
  elements.alert.textContent = message;
  elements.alert.hidden = !message;
}

function setPhase(phase, detail) {
  state.phase = phase;
  const presentations = {
    idle: ["idle", "Not connected", "Ready when you are", "Start voice rehearsal", "Your microphone stays off until you start."],
    connecting: ["busy", "Connecting", "Opening the studio…", "Connecting securely…", "Allow microphone access if your browser asks."],
    live: ["live", "Live", "Rehearsal in progress", "End rehearsal", "Speak naturally. Rosario is listening."],
    ending: ["busy", "Wrapping up", "Preparing your receipt…", "Ending safely…", "Saving the outcome…"],
    complete: ["idle", "Complete", "Rehearsal complete", "Rehearsal complete", "Review your staged outcome."],
    error: ["error", "Attention needed", "The studio paused", "Try voice rehearsal again", detail || "Check your connection and try again."],
  };
  const view = presentations[phase] || presentations.idle;
  elements.connection.dataset.state = view[0];
  elements.connectionText.textContent = view[1];
  elements.studioHeading.textContent = view[2];
  elements.micTitle.textContent = view[3];
  elements.micSubtitle.textContent = view[4];
  elements.studio.classList.toggle("is-live", phase === "live");
  elements.micButton.disabled = !state.selected || ["connecting", "ending", "complete"].includes(phase);
  elements.micButton.setAttribute("aria-label", phase === "live" ? "End voice rehearsal" : "Start voice rehearsal");
}

function scenarioSubtitle(scenario) {
  const subject = scenario.objective.replace(/[.!]$/, "");
  return subject.length > 82 ? `${subject.slice(0, 79)}…` : subject;
}

function renderScenarios() {
  elements.grid.replaceChildren();
  if (!state.scenarios.length) {
    const empty = document.createElement("p");
    empty.className = "empty-row";
    empty.textContent = "No rehearsal roles are available right now.";
    elements.grid.append(empty);
    return;
  }

  state.scenarios.forEach((scenario, index) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "scenario-card";
    card.dataset.scenarioId = scenario.id;
    card.setAttribute("aria-pressed", String(state.selected?.id === scenario.id));

    const icon = document.createElement("span");
    icon.className = "card-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = ROLE_ICONS[index] || "•";
    const title = document.createElement("h3");
    title.textContent = scenario.title;
    const description = document.createElement("p");
    description.textContent = scenarioSubtitle(scenario);
    card.append(icon, title, description);
    card.addEventListener("click", () => selectScenario(scenario));
    elements.grid.append(card);
  });
}

function appendDefinition(parent, term, description) {
  const row = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = description;
  row.append(dt, dd);
  parent.append(row);
}

function selectScenario(scenario) {
  if (["connecting", "live", "ending"].includes(state.phase)) return;
  showAlert("");
  state.selected = scenario;
  state.snapshot = null;
  state.snapshotReady = false;
  state.sessionId = null;
  renderScenarios();
  elements.briefEmpty.hidden = true;
  elements.briefContent.hidden = false;
  elements.monogram.textContent = scenario.name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  elements.personaTitle.textContent = scenario.title;
  elements.personaName.textContent = scenario.name;
  elements.personaPhone.textContent = scenario.phone;
  elements.objective.textContent = scenario.objective;
  elements.hint.textContent = scenario.opening_hint;
  elements.facts.replaceChildren();
  scenario.facts.forEach(([label, value]) => appendDefinition(elements.facts, label, value));
  clearActivity();
  hideReceipt();
  setPhase("idle");
}

function clearActivity() {
  elements.milestones.innerHTML = '<li class="empty-row">Progress appears during your call.</li>';
  elements.milestoneCount.textContent = "0 / 0";
  elements.transcript.innerHTML = '<p class="empty-row">The compact transcript appears here.</p>';
  elements.toolEvents.innerHTML = '<p class="empty-row">No tools used yet. Sensitive arguments are never shown.</p>';
  elements.toolCount.textContent = "0 events";
  state.executionEvents = [];
  renderExecutionGraph();
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  elements.milestones.replaceChildren();
  if (snapshot.milestones?.length) {
    snapshot.milestones.forEach((milestone) => {
      const item = document.createElement("li");
      item.dataset.state = milestone.state;
      item.textContent = milestone.label;
      elements.milestones.append(item);
    });
    const complete = snapshot.milestones.filter((item) => item.state === "complete").length;
    elements.milestoneCount.textContent = `${complete} / ${snapshot.milestones.length}`;
  } else {
    elements.milestones.innerHTML = '<li class="empty-row">Waiting for the first milestone…</li>';
    elements.milestoneCount.textContent = "0 / 0";
  }

  elements.transcript.replaceChildren();
  if (snapshot.transcript?.length) {
    snapshot.transcript.slice(-8).forEach((turn) => {
      const row = document.createElement("div");
      row.className = `turn${turn.interrupted ? " interrupted" : ""}`;
      row.dataset.role = turn.role;
      const role = document.createElement("span");
      role.textContent = turn.role === "agent" ? "AI" : "You";
      const text = document.createElement("p");
      text.textContent = turn.text;
      row.append(role, text);
      elements.transcript.append(row);
    });
    elements.transcript.scrollTop = elements.transcript.scrollHeight;
  } else {
    elements.transcript.innerHTML = '<p class="empty-row">Listening for the conversation…</p>';
  }

  elements.toolEvents.replaceChildren();
  if (snapshot.tools?.length) {
    snapshot.tools.forEach((event) => {
      const row = document.createElement("div");
      row.className = "tool-event";
      row.dataset.status = event.status;
      const dot = document.createElement("i");
      const name = document.createElement("b");
      name.textContent = event.name;
      const summary = document.createElement("span");
      summary.textContent = event.summary;
      row.append(dot, name, summary);
      elements.toolEvents.append(row);
    });
  } else {
    elements.toolEvents.innerHTML = '<p class="empty-row">No tools used yet. Sensitive arguments are never shown.</p>';
  }
  const toolTotal = snapshot.tools?.length || 0;
  elements.toolCount.textContent = `${toolTotal} ${toolTotal === 1 ? "event" : "events"}`;

  if (snapshot.error) showAlert(snapshot.error);
  if (snapshot.status === "complete") finishComplete();
  else if (snapshot.status === "error") failCall(snapshot.error || "The rehearsal ended unexpectedly.");
}

function getSessionId(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) return null;
  seen.add(value);
  if (typeof value.session_id === "string") return value.session_id;
  if (typeof value.sessionId === "string") return value.sessionId;
  for (const nested of Object.values(value)) {
    const found = getSessionId(nested, seen);
    if (found) return found;
  }
  return null;
}

function describeError(error) {
  const name = error?.name || "";
  const message = String(error?.message || error || "");
  if (name === "NotAllowedError" || /permission|denied|notallowed/i.test(message)) {
    return "Microphone access was denied. Allow it in your browser settings, then try again.";
  }
  if (name === "NotFoundError" || /no.*microphone|device.*not found/i.test(message)) {
    return "No microphone was found. Connect one and try the rehearsal again.";
  }
  return message ? `Could not start the rehearsal: ${message}` : "Could not start the rehearsal. Check the server and try again.";
}

function setupBotAudio(client) {
  const audio = elements.botAudio;
  state.audio = audio;
  client.on(RTVIEvent.TrackStarted, (track, participant) => {
    if (participant?.local || track.kind !== "audio") return;
    audio.srcObject = new MediaStream([track]);
    audio.muted = false;
    audio.volume = 1;
    audio.play().catch(() => {
      showAlert("Your browser blocked speaker playback. Click the microphone button once more to enable sound.");
    });
  });
}

function renderExecutionGraph() {
  elements.executionGraph.replaceChildren();
  if (!state.executionEvents.length) {
    elements.executionGraph.innerHTML = '<p class="empty-row">Start a rehearsal to inspect the durable JSONL trace.</p>';
  } else {
    state.executionEvents.slice(-80).forEach((event, index) => {
      const participant = event.participant || "brain";
      const row = document.createElement("article");
      row.className = "execution-event";
      row.dataset.status = event.status || "complete";
      row.dataset.participant = participant;
      const number = document.createElement("span");
      number.className = "event-number";
      number.textContent = String(index + 1).padStart(2, "0");
      const body = document.createElement("div");
      body.className = "event-body";
      const meta = document.createElement("span");
      meta.className = "execution-kind";
      meta.textContent = `${participant} · ${event.type.replaceAll(".", " ")}`;
      const title = document.createElement("strong");
      title.textContent = event.label;
      const summary = document.createElement("p");
      summary.textContent = event.summary;
      body.append(meta, title, summary);
      row.append(number, body);
      elements.executionGraph.append(row);
    });
    elements.executionGraph.scrollTop = elements.executionGraph.scrollHeight;
  }
  elements.eventCount.textContent = `${state.executionEvents.length} events`;
}

function startEngineeringStream() {
  if (!state.sessionId) return;
  if (state.eventSource) state.eventSource.close();
  state.executionEvents = [];
  renderExecutionGraph();
  const source = new EventSource(`/api/demo/sessions/${encodeURIComponent(state.sessionId)}/events`);
  state.eventSource = source;
  source.onmessage = ({ data }) => {
    try {
      state.executionEvents.push(JSON.parse(data));
      renderExecutionGraph();
    } catch { /* Ignore malformed transport fragments; JSONL remains authoritative. */ }
  };
  elements.fullTraceLink.href = `/demo/review.html?call=${encodeURIComponent(state.sessionId)}`;
  elements.fullTraceLink.hidden = false;
}

function stopEngineeringStream() {
  if (state.eventSource) state.eventSource.close();
  state.eventSource = null;
}

async function startCall() {
  if (!state.selected || ["connecting", "live", "ending"].includes(state.phase)) return;
  showAlert("");
  hideReceipt();
  clearActivity();
  state.sessionId = null;
  state.snapshotReady = false;
  state.snapshot = null;
  stopEngineeringStream();
  setPhase("connecting");

  try {
    const transport = new SmallWebRTCTransport();
    state.client = new PipecatClient({
      transport,
      enableCam: false,
      enableMic: true,
      disconnectOnBotDisconnect: false,
      callbacks: {
        onBotStarted: (response) => {
          state.sessionId = getSessionId(response) || state.sessionId;
          if (state.sessionId && state.snapshotReady) beginPolling();
        },
        onConnected: () => setPhase("live"),
        onBotReady: (data) => {
          state.sessionId = getSessionId(data) || state.sessionId;
          setPhase("live");
          if (state.sessionId && state.snapshotReady) beginPolling();
        },
        onDisconnected: () => {
          if (!state.stopping && state.phase !== "complete") failCall("The voice connection closed. You can safely try again.");
        },
        onTransportStateChanged: (transportState) => {
          if (transportState === "error") failCall("The voice connection failed. Check your network and try again.");
        },
        onDeviceError: (error) => failCall(describeError(error)),
        onError: (message) => failCall(describeError(message?.data || message)),
      },
    });
    setupBotAudio(state.client);

    await state.client.initDevices();
    const ready = await state.client.startBotAndConnect({
      endpoint: "/start",
      requestData: {
        transport: "webrtc",
        enableDefaultIceServers: true,
        body: { scenario_id: state.selected.id },
      },
    });
    state.sessionId = getSessionId(ready) || state.sessionId;
    if (!state.sessionId) throw new Error("The server did not return a demo session identifier.");
    const initialized = await fetch(`/api/demo/sessions/${encodeURIComponent(state.sessionId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: state.selected.id }),
    });
    if (!initialized.ok) throw new Error(`Session initialization failed (${initialized.status})`);
    state.snapshotReady = true;
    renderSnapshot(await initialized.json());
    setPhase("live");
    beginPolling();
    startEngineeringStream();
  } catch (error) {
    await safelyDisconnect();
    failCall(describeError(error));
  }
}

async function pollSnapshot() {
  if (!state.sessionId || !["connecting", "live", "ending"].includes(state.phase)) return;
  try {
    const response = await fetch(`/api/demo/sessions/${encodeURIComponent(state.sessionId)}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Snapshot request failed (${response.status})`);
    renderSnapshot(await response.json());
  } catch (error) {
    if (state.phase !== "ending") showAlert(`Live activity is temporarily unavailable. ${error.message}`);
  }
}

function beginPolling() {
  window.clearInterval(state.pollTimer);
  pollSnapshot();
  state.pollTimer = window.setInterval(pollSnapshot, POLL_INTERVAL_MS);
}

async function stopCall() {
  if (state.phase !== "live" || state.stopping) return;
  state.stopping = true;
  setPhase("ending");
  window.clearInterval(state.pollTimer);
  try {
    await safelyDisconnect();
    if (state.sessionId) {
      for (let attempt = 0; attempt < 40; attempt += 1) {
        const response = await fetch(`/api/demo/sessions/${encodeURIComponent(state.sessionId)}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Review request failed (${response.status})`);
        const snapshot = await response.json();
        if (["complete", "error"].includes(snapshot.status)) {
          renderSnapshot(snapshot);
          await loadLedger();
          return;
        }
        await new Promise(resolve => window.setTimeout(resolve, 500));
      }
      throw new Error("Recording is still being finalized. Open the call trace to review it.");
    }
    if (state.phase !== "complete") finishComplete();
  } catch (error) {
    await safelyDisconnect();
    failCall(`The call ended, but the receipt could not be loaded: ${error.message}`);
  } finally {
    state.stopping = false;
  }
}

async function safelyDisconnect() {
  if (state.audio) {
    state.audio.pause();
    state.audio.srcObject = null;
  }
  const client = state.client;
  state.client = null;
  if (!client) return;
  try { await client.disconnect(); } catch { /* The media connection may already be closed. */ }
}

function finishComplete() {
  window.clearInterval(state.pollTimer);
  setPhase("complete");
  loadLedger();
  const evidence = state.snapshot?.evidence?.[0];
  if (!evidence) {
    hideReceipt();
    elements.receiptEmpty.textContent = "Call saved with no staged action. Open the call trace to inspect what happened, or choose a role to try again.";
    return;
  }
  elements.receiptLabel.textContent = evidence.label || OUTCOME_LABELS[evidence.action] || "Action prepared";
  elements.receiptFields.replaceChildren();
  evidence.fields.forEach(([label, value]) => appendDefinition(elements.receiptFields, label, value));
  elements.receiptChecks.replaceChildren();
  evidence.checks.forEach((check) => {
    const item = document.createElement("li");
    item.textContent = check;
    elements.receiptChecks.append(item);
  });
  elements.receiptEmpty.hidden = true;
  elements.receiptContent.hidden = false;
}

function hideReceipt() {
  elements.receiptEmpty.hidden = false;
  elements.receiptContent.hidden = true;
}

function failCall(message) {
  window.clearInterval(state.pollTimer);
  state.stopping = false;
  showAlert(message);
  setPhase("error", message);
}

async function resetStudio() {
  await safelyDisconnect();
  window.clearInterval(state.pollTimer);
  state.sessionId = null;
  state.snapshot = null;
  state.snapshotReady = false;
  stopEngineeringStream();
  state.executionEvents = [];
  renderExecutionGraph();
  elements.fullTraceLink.hidden = true;
  state.stopping = false;
  showAlert("");
  clearActivity();
  hideReceipt();
  setPhase(state.selected ? "idle" : "idle");
  elements.grid.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function loadLedger() {
  try {
    const response = await fetch("/api/demo/ledger", { cache: "no-store" });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    const entries = await response.json();
    elements.ledger.replaceChildren();
    if (!entries.length) {
      elements.ledger.innerHTML = '<p class="empty-row">No saved rehearsals yet.</p>';
      return;
    }
    entries.forEach((entry) => {
      const evidence = entry.evidence?.[0];
      const row = document.createElement("article");
      row.className = "ledger-entry";
      const time = document.createElement("time");
      time.className = "ledger-time";
      time.dateTime = entry.completed_at;
      time.textContent = new Date(entry.completed_at).toLocaleString();
      const action = document.createElement("strong");
      action.className = "ledger-action";
      action.textContent = entry.status === "error" ? "Call failed" : evidence?.label || "No action staged";
      const detail = document.createElement("span");
      detail.className = "ledger-detail";
      detail.textContent = evidence ? evidence.fields.map(([key, value]) => `${key}: ${value}`).join(" · ") : entry.error || "Review the recording and tools to diagnose this call.";
      const review = document.createElement("a");
      review.className = "trace-link";
      review.textContent = `Review call ${entry.session_id.slice(0, 8)} ↗`;
      review.href = `/demo/review.html?call=${encodeURIComponent(entry.session_id)}`;
      review.target = "_blank";
      review.rel = "noreferrer";
      row.append(time, action, detail, review);
      elements.ledger.append(row);
    });
  } catch (error) {
    elements.ledger.innerHTML = `<p class="empty-row">Ledger unavailable: ${String(error.message || error)}</p>`;
  }
}

async function loadScenarios() {
  try {
    const response = await fetch("/api/demo/scenarios", { cache: "no-store" });
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    const payload = await response.json();
    state.scenarios = Array.isArray(payload) ? payload : payload.scenarios || [];
    renderScenarios();
    if (!state.scenarios.length) showAlert("No rehearsal roles are available. Try refreshing in a moment.");
  } catch (error) {
    state.scenarios = [];
    renderScenarios();
    showAlert(`The role library could not be loaded: ${error.message}`);
  }
}

elements.micButton.addEventListener("click", () => state.phase === "live" ? stopCall() : startCall());
elements.resetButton.addEventListener("click", resetStudio);
window.addEventListener("pagehide", () => {
  window.clearInterval(state.pollTimer);
  stopEngineeringStream();
  if (state.client) state.client.disconnect().catch(() => {});
});

setPhase("idle");
loadScenarios();
loadLedger();
