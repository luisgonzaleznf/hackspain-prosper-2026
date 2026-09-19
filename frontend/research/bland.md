# Bland AI console research

Purpose: what a best-in-class voice-agent console looks like, so the clinic receptionist console can borrow structure, screens and capabilities. Pricing and marketing copy are out of scope.

Research date: 2026-09-18. Screenshots live in `screens/bland/`. Prefixes: `docs-` = official docs image (mintcdn), `changelog-` = bland.ai changelog image, `university-` = Bland University lesson image, `homepage-` and `v2-`/`app-` = live captures I took with agent-browser, `blog-` = third-party tutorial screenshots (older UI, low trust for exact layout).

Two dashboards exist right now:

- `app.bland.ai` (the "console" most docs describe). Left icon rail, sections Build / Monitor / Deploy / Integrations.
- `v2.app.bland.ai` (new dashboard, rolled out 2026-09-10 per docs). Agent-centric: an "All agents" switcher on top, then Resources / Monitor / Validate / Dispatch. The docs for this one are thin (one getting-started page); everything else below describes the classic console unless marked v2.

I could not get into either dashboard (see section 11). Everything about in-app screens comes from official docs screenshots and text, changelogs, Bland University, and a third-party tutorial.

---

## 1. IA / nav map

### 1a. Classic console (app.bland.ai), sidebar as seen in `docs-scenarios-panel.png` and `docs-analytics-dashboard-2026.png`

```
Home
Norm (Beta)                     AI assistant chat, org-wide

Build
  Agents                        Personas: identity, voice, routing, versions
  Pathways                      Conversational Pathways list + editor
  Knowledge Bases               Sources, Knowledge Map, Query Logs
  Voices                        Voice library, cloning

Monitor
  Analytics                     Tabs: Dashboard, Citations, Reports, Presets, Outcomes
  Alerts (New)                  Threshold / custom-condition alerts
  Call Logs                     Completed / Active tabs, detail drawer
  Triage                        Issues flagged from calls, "Norm Fix"
  Compliance                    Guard rails catalog, custom guard rails

Deploy
  Send Call                     One-off outbound call form
  Batch Calls                   CSV batches
  Phone Numbers                 Inbound numbers, assignment to pathway/persona
  SIP Trunks                    Trunk wizard, porting, SIP call logs
  SMS                           SMS conversations
  Web Widget                    Embeddable voice+chat widget, threads

Integrations
  Tools                         v2 tools: integrations + custom HTTP
  Automations
  Add-ons
  Memory                        Contacts and cross-call memory

Docs
Speech                          Standalone TTS product / studio
[org switcher + credits]
```

Also reachable but not in the rail screenshot: Evals (`/dashboard/evals`), Secrets, Blocked Numbers, Billing & Credits, Settings (API keys).

### 1b. New dashboard (v2.app.bland.ai), sidebar from `docs-v2-dashboard-empty-state.png` and `docs-v2-phone-numbers.png`

```
[All agents v]                  agent scope switcher (top of sidebar)
Overview

Resources
  Knowledge
  Tools
  Voices

Monitor
  Conversations                 (replaces "Call Logs"; voice + messaging in one table)
  Issues                        (replaces "Triage")
  Alerts
  Analytics

Validate
  Evaluations                   (Evals + test cases + runs, per agent)

Dispatch
  Phone numbers                 tabs: Phone numbers | SIP
  Triggers
  Batches

Docs
TTS Studio
[org switcher]
```

Notable IA moves in v2: everything is scoped to an agent (the switcher sits above the nav), "Pathways" is no longer a top-level item (the agent builder owns it), and the four groups read as a lifecycle: Resources -> Monitor -> Validate -> Dispatch. The empty state offers "Start from scratch" or "Try a demo agent" (Marco, a restaurant reservation agent) and drops you into a guided editor tour.

---

## 2. Per-screen breakdown

### Home / Overview
Not documented beyond the v2 empty state. Unverified what the populated Overview shows.

### Norm (AI assistant)
Screenshot: `docs-norm-chat.png`, `changelog-norm-slash-menu.png`.
Chat surface. Builds and edits pathways/personas/tools in a draft fork, replays real calls on the Testbed, answers analytics questions in plain English ("transfer rate by pathway this week" returns a table or chart), and fixes Triage issues. `/` opens a skill menu; custom skills are org-scoped. Also embedded as a side panel inside the pathway editor.

### Pathways list and pathway "splash page"
Screenshot: `docs-scenarios-results.png` (the splash page).
Per pathway: Production card (ID, version, deployed timestamp, "Call activity, last 7 days" sparkline placeholder, View / Clone / Rate Limits), Staging card (version, name, created, Edit / Compare / Deploy to production), Branches table (version rows with STAGING badge, "Promote to staging"), Activity feed (Deployed v/3, View / Rollback), Policy & Compliance (Guard Rails row), Agent Testing block (progress bar "2 passed | 1/1 gates", per-scenario rows with score %, expandable to version, duration, turns, tone %, assertions, and a "Production gate" toggle, "Run All").

### Pathway editor
See section 7.

### Agents / Personas
Screenshots: `docs-personas-list.png`, `docs-persona-behavior.png`, `docs-persona-version-diff.png`.
Builder with five sections: General (identity, voice, language, background noise, modalities), Behavior (global prompt, wait for greeting, interruption threshold slider, "+ Add routing" rows that send topics to pathways), Knowledge (toggle KBs, memory), Analysis & Webhooks (summary toggle + prompt, citation schemas, outcomes, evaluations, webhook URL + events + "Test Webhook"), Version Management (Draft vs Production, visual diff of changed fields, "Promote to Production", "Reset Draft", "Version History", "Changes Ready to Promote" banner). A test modal on the right lets you web-call the current draft.

### Knowledge Bases
Screenshot: `changelog-knowledge-map.png`.
Tabs: Sources (with aggregate size/coverage stats), Knowledge Map (sources and questions as connected nodes, color-coded by coverage tier under 50 / 50-79 / 80+ and resolved vs open questions), Query Logs (full query context inline).

### Call Logs
Screenshots: `docs-call-logs-table.png`, `docs-live-call-monitor.png`, `docs-page-call-logs.png` (docs page render).
Header: title, bell with unread count (review assignments), "Export Calls" (CSV by email, timezone, up to 180 days, exclude columns). Two tabs: COMPLETED (count) and ACTIVE. Toolbar: Call ID search, Filters button, bookmark (saved filters, org-shared, URL-encoded), "Columns (18)" configurator (toggle + drag reorder).
Columns: Actions (play, download), ID (copy), Channel (Voice/Web/SMS), Direction (In/Out/Proxy with expand for warm-transfer sub-rows), To ("Web Client" chip for web calls), From, Pathway (link to editor), Duration, Issues (yellow medium, orange high, shield for guardrail), Status (Completed/failed/busy/canceled/no-answer/Unknown), Created, Tags (colored dot chips), Version (Production/Staging/Version N chips), Transferred To, Batch ID, Review Status, Memory, Recording, Error.
Filters panel: quick filters (Full Conversations, Voicemails, Assigned to Me, Warm Transfers, Unassigned), time range (1h/24h/today/7d/30d), pathway multiselect, advanced AND/OR condition rows over groups Call Details / Pathway / Data (Analysis, Variables, Citations) / Quality (Review Status, Assignee, QC Tags, Issue Severity, Notes, Guardrail Triggers) / Other (Is Simulation).

### Call detail
See section 3.

### Analytics
See section 6.

### Alerts
Screenshots: `docs-alerts-dashboard.png`, `docs-alerts-severity-config.png`.
Table of alert configs with Status (Active/Inactive), live Alert state (OK or Triggered + severity badge), last trigger time. Editor: condition (built-in metric or plain-language custom condition, or citation variable / outcome field / pathway tag), three severity rows INFO / WARNING / CRITICAL each with operator+value, percentage trigger, lookback window (10m to 24h), minimum call count; delivery by email, phone call, or custom tool.

### Triage / Issues
No screenshot available. From changelog: flag a call from the detail view, create an issue with severity, owner, assignee, description; related issues auto-surface; originating calls and pathways attach automatically; "Norm Fix" reproduces, patches a draft, and verifies with testbed simulations; you can test the fixed pathway in chat from the issue.

### Compliance / Guard Rails
Screenshots: `docs-guardrails-apply.png`, `docs-guardrails-backtest.png`.
Two types: timed (must fire within N seconds: AI disclosure, self introduction, recording disclosure) and continuous (must not fire: TCPA opt-out, content policy, custom). Actions: End call, Transfer to human, Move to node. Custom guard rails have a prompt editor and a backtest runner over multiple calls that shows the reasoning per call.

### Phone Numbers (classic and v2)
Screenshots: `docs-inbound-numbers-list.png`, `docs-v2-phone-numbers.png`.
v2 table: Number (with Free chip), Title, Source (Twilio), Status (Active), Assignment (agent), iMessage, Configure, copy. Header actions: Manage subscriptions, Blocked numbers, Connect Twilio, Buy number. Tabs: Phone numbers | SIP.

### Send Call / Batch Calls
Screenshot: `blog-fahimai-send-call.png` (older UI). Form: phone number, task prompt, voice, plus advanced settings. Batches take a CSV.

### Web Widget
Screenshot: `blog-fahimai-web-widget.png` (older UI). Create widget, pick pathway or persona, visual style editor, embed snippet, thread list with translate button, live-agent handoff via webhook.

### Evals / Evaluations
Screenshots: `docs-evals-overview.png`, `docs-evals-experiment-builder.png`, `docs-evals-verdict-drawer.png`, `docs-evals-run-analysis.png`. See section 5.

### Memory
Screenshot: `docs-call-detail-memory-tab.png`. Contacts keyed by phone/email/external ID; per contact and persona: facts, rolling summary, open items, entities (appointments, orders), recent messages.

### Outcomes (enterprise)
Screenshots: `docs-outcomes-definition.png`, `docs-outcomes-backtest-results.png`. Define fields (name, type, description), platform generates transformation code, backtest against historical calls, versioned with diffs and rollback.

### Citations (enterprise)
Screenshots: `docs-citations-variables.png`, `docs-citations-analysis.png`. Schema builder with Variables (string/number/boolean/array/category), Groupings, Conditions, Analysis tab (total extracted, extraction rate, calls processed, trend and distribution graphs).

---

## 3. Call detail anatomy

Primary source: `docs-call-detail-view.png` plus the Call Logs doc. Older layout variants: `docs-call-metrics-1.png` (2025, tabbed), `docs-call-detail-memory-tab.png` (early 2026, tabbed).

Layout (current): the table stays on the left, the detail opens as a wide drawer split in two: transcript column in the middle, "Details" context panel on the right, audio player pinned to the bottom of the transcript column.

### Header row
- Close, phone icon, pathway name (link to editor), channel chip ("Voice"), contact number (click filters the log to that contact's history), history icon, prev/next call arrows.
- Second line: direction badge ("Outbound"), status chip ("Completed", green), duration ("02:04"), cost ("$0.19").
- Actions: copy call ID, copy link, copy full transcript, translate toggle.

### Transcript column
- Toolbar: "Search transcript..." (step through matches), "Expand all logs" toggle.
- Sticky node header: a pill in the middle ("Collect Party Size") that tracks the pathway node you have scrolled past.
- Bubbles: AGENT left-aligned, blue tint; USER right-aligned, grey/white. Each has a role label and a wall-clock timestamp ("5:00:30 PM"). Hover actions per bubble: Flag (STT/TTS quality issue, amber indicator), Edit node (opens editor on that node), Testbed (opens testbed pre-loaded with this turn).
- Inline log cards between turns when "Expand all logs" is on, each color-coded:
  - PROMPT (inside the agent bubble, monospace, copy + expand)
  - VARIABLE EXTRACTION (yellow): `party_size 130`, plus AVAILABLE VARIABLES with the node each came from; "Testbed" button
  - LOOP CONDITION (green): full condition prompt and likelihood score ("Likely 7/10"); "Testbed" button
  - Node chosen / Routing: from -> to -> via edge label; chosen route check-marked, alternatives listed; "Waited" when the agent declined all routes
  - Webhook: URL, HTTP status, response time, full payload, errors inline (timeouts included)
  - Custom code: Output row, failure code (`SNIPPET_TIMEOUT`, `SNIPPET_ERROR`), runtime
  - Other events: button presses, KB tool calls, SMS, scheduling, transfers, interruptions (which node the agent returned to)

### Audio player (bottom)
- Restart, play/pause, skip; time "1:10 / 2:02"; "Sync scrolling" toggle (transcript autoscrolls with playback); speed "1x"; download.
- Two-lane waveform: Agent lane on top, User lane below.
- Colored marker dots on the waveform: green decision markers (node transitions), amber extraction markers (variables and citations), tag markers (pathway tags). Hover shows type, timestamp, name; click seeks.
- Filter chips under the waveform: "Variables 5", "Tags 2", "Decisions 3".
- "Auto-play next" toggle advances to the next call with a recording.

### Details panel (right, collapsible sections, expand/collapse all)
- Metadata, grouped: CALL DETAILS (conversation ID + copy, from, to, created at, call type, status), DURATION & COST (total duration, transfer duration, cost), PARTICIPANTS (answered by Human/Voicemail, ended by Assistant/User, caller location), CONFIGURATION (voice, interruption threshold 500.00, temperature 0.50, noise cancellation, language), PATHWAY (ID + copy, name link, version), ALERTS (errors, silence warnings), AI SUMMARY (expandable "Read more").
- Variables: all extracted variables merged.
- Citations: variable, value, expandable sources with quoted transcript text and timestamps.
- Notes & review: threaded notes with @mentions, assignee dropdown, status (Pending Review / In Progress / Completed / Not Needed), QC tag chips.
- Outcomes: disposition results with status, execution time, error, key-value results, "Open in Outcomes".
- Pathway Tags: colored chips.
- Webhook & Tools: post-call webhook status, URL, response code, time, payload, resend; tool logs per invocation with integration, status, execution time, expandable input/output.
- Guardrails: name, type, triggering content, reason.
- Memory: context going in + changes made (facts added, entities like `Appointment Inspection-2026-02-12` with date/time/service).
- Metrics: agent quality, transcription quality, response time, silence, background noise, sentiment, engagement, repetition, interruptions, speaker changes, word count; issues by severity. The 2025 Metrics tab (`docs-call-metrics-1.png`) rendered these as thin progress bars under headings Audio Quality / Conversation Flow / Agent Performance / Engagement, plus Language, Caller Profile, word counts, interruption counts, and an Utterance Types donut.
- Request Data: original API request JSON (for inbound: merged with number config).

### Under the hood: the event timeline
The docs expose the same data as an ordered event list (`GET /v1/pathway_calls/{id}?v=2`). Envelope: `conversation_id, sequence, event_type, node_id, operation_id, payload, created_at`. Sort by `sequence`, not time. Event types: `conversation.init`, `node.transition` (chosen node, label, previous node, available routes, variable changes), `node.tag`, `transcript.user`, `transcript.assistant` (with `generated_response` preserving the full intended sentence when interrupted), `interrupt.early`/`interrupt.late`, `button.press`, `llm.action`, and operation triplets `*.invoke` / `*.result` / `*.error` / `*.warning` for `webhook` (plus `webhook.mapping` per variable with outcome set/empty), `tool`, `kb`, `sms`, `scheduling`, `loop_condition`, `var_extraction`, `custom_code`, `transfer_pathway`, `transfer_call`, `unit_test`. Each assistant utterance carries an opaque `external_id` for escalation ("why did the agent say this").

---

## 4. Live monitoring

Screenshots: `docs-live-call-monitor.png`, `university-live-calls-table.png`.

- Call Logs > ACTIVE tab: rows appear and disappear as calls start and end. Columns (2025 version): ID, STATUS (`IN_PROGRESS` chip), DURATION (ticking), FROM, TO, OBJECTIVE (task text truncated), ACTIONS ("View Transcript").
- Clicking a row opens a right panel "Live Transcript": Call ID with copy, a "Call Active / Started At 11:22:55 PM" card, a small live waveform tile, and streaming bubbles labeled Assistant / User with timestamps.
- Listen-in: shipped May 2025 ("playback begins as soon as the call starts, both agent and user audio alongside transcripts"), then temporarily removed July 2025 for reliability work. The current call-logs doc still links "Live Call Monitoring" to the May 2025 changelog, and the marketing site says "Listen in to active calls". Current availability of listen-in is unverified.
- Current pathway node in the live view: not shown in any screenshot. Unverified. The completed-call view has the sticky node header, and the test panel logs the destination node per turn, so the data exists.
- Bland University also describes a "Real Time Logs" streaming view (categories Call / Queue, statuses Info / Performance / Error) filtered live. Screenshot only of the menu (`university-analytics-menu.png`). Likely an older surface.
- Marketing mock of the ideal (product page): "Observability / Live" panel with "Active calls, last 60s: 4,127" and a table Number / Duration / Latency per active call.

---

## 5. Testing

Bland has five distinct testing surfaces. Worth knowing all of them because they map to different console screens.

### 5a. Pathway editor Test panel
Screenshots: `docs-pathway-testing-hero.png`, `docs-pathway-testing-branch.png`, `university-pathway-test-chat.png`, `university-pathway-test-decision-box.png`.
"Test" button in the toolbar opens a left panel "Testing" with tabs CHAT / CALL / UNIT.
- Shared config: load/save named configuration, start node, version (draft or published), request data key-values, "Use Candidate Model".
- CHAT: text chat; each message timestamped to the tenth of a second ("13:46:09.3"); small badges on bubbles indicate a variable extraction `{}` or a route decision; "Expand all logs" shows the same per-turn cards as call logs (variable extraction, loop condition with likelihood, route with alternatives, interruption, webhook). Any user message has an edit icon; editing forks a branch and arrows "1/2" swap between branches. Bottom: channel picker + "Your message" input.
- Voice tab inside chat: voice, language, block interruptions, pronunciation guide.
- CALL: "Send call" to a real number; logs stream into the panel.
- UNIT: pick node, pick historical call ID, pick a user message from it, optional replacement message, optional LLM grading goal, "Simulated variations" (default 5 rephrasings). Result: Pass/Fail per variant with rationale, summary badge like "1/1 failed".
- The 2024 university version showed a "Pathways Decision Info" box with a "Fine-Tune Decisions" button (correct a wrong route) and "Edit Prompt and Generate Response" (rerun the same turn with a new node prompt). This is the origin of the "fine-tuning examples" feature; today the equivalent is the Decision Guide on a node plus the Testbed.

### 5b. Testbed
Screenshots: `docs-testbed-main.png`, `docs-testbed-existing-call.png`, `docs-testbed-review.png`.
Modal with two columns. Left "Agent prompts": Global prompt (collapsed), Node prompt (editable, `{{var}}` highlighted), Variables (name, type, description), Conversation history (real transcript that seeds the run), "Prompt outputs" with a run-count selector ("x20") and "Run outputs" producing e.g. `PARTY_SIZE 20/20 | ORIGINAL 130`. Right "Standard": Configuration (evaluation method: variable + Exact/regex/prompt + expected value; Threshold presets Rigorous 10/10, Flexible 9/10, Relaxed 8/10; Max conversation turns slider), Simulations list with per-run check/cross rows and a "PASS 9/10 passing, 8/10 REQUIRED" badge; selecting a run shows ACTUAL vs EXPECTED and the simulated dialogue. Footer: `node: Collect Party Size  type: Variable Extraction`, "Review standard" leads to a diff + batch results view before "Publish" (which saves the prompt and creates a Standard).

### 5c. Standards
Screenshot: `docs-standards-panel-simulation.png`.
Node-level regression tests. Types: dialogue (simulated caller persona, success-definition prompt), loop condition and variable extraction (nine wording permutations of a real transcript plus the original = ten runs). Each run scored, tallied against the threshold. Listed on a STANDARDS tab inside the node drawer. Must pass before publishing prompt changes from the Testbed.

### 5d. Scenarios (agent-to-agent testing)
Screenshots: `docs-scenarios-panel.png`, `docs-scenarios-create.png`, `docs-scenarios-results.png`, `changelog-agent-testing-edit-scenario.png`.
Right panel in the editor: "Scenarios" with "+ New", a "2 passed" summary, GATES group (required for promotion, shows 100%), TESTS group (score %), RECENT runs list (name, timestamp, "1/2" pass count), "Run All". A scenario = tester persona prompt + assertions (LLM_JUDGE, BLAND_TONE, VARIABLE_EXTRACTED, node reached, regex, etc., each with weight and Required toggle) + max turns + start node + request data. Nine templates (voicemail, gatekeeper, escalating anger, abusive, rambling, happy path, edge cases...). Generate a scenario from a call log in one modal. Results on the pathway splash page: pass/fail, score %, assertion breakdown, tone score, AI reasoning, full transcript. Simulation sets run the same scenario N times for flakiness (pass rate, mean/median/stddev, confidence). "Tornado mode" loops run -> analyze -> fix draft -> rerun. Analytics: health score, reliability, trend, node failure heatmap, weakest link.

### 5e. Evals (LLM judges over real calls)
Screenshots listed in section 2. Eval agents (rubric prompt, text or audio modality, pass/fail or 2 to 5 graded levels with colors, target levels, weight 0-100, versioned draft/published). Experiments: pick up to 5,000 calls, attach up to 50 agents, set pass threshold; results grid with per-call aggregate score and per-agent verdicts; verdict drawer shows selected level, reasoning, quoted evidence next to the transcript; analysis view shows per-agent success rate and a histogram of weighted scores. Workbench setups are saved bundles that can attach to a persona to auto-grade every call. In v2 this lives under Validate > Evaluations with tabs Test cases / Runs, and test cases can be generated from production calls.

---

## 6. Analytics and charts

### 2025 layout (`docs-analytics-filtering-2025.png`)
Tabs Calls / Pathways / Presets / Reports. Time presets Today / Last week / Last 2 months + date picker; filters All, Filter by Pathway, Filter by Tag (and to/from number). KPI strip: TOTAL CALLS 808 (+0.1% green), TOTAL COST $16.98 (-5.8% red), AVG DURATION 0:40, TOTAL TRANSFERS 2. Big area chart of daily volume with a grey comparison line for the previous period. Three donuts: PATHWAY TAGS, UTTERANCE TYPES (pause filler, statement, question, acknowledgement, answer, clarification request), CALL OBJECTIVES (Verify identity, Confirm identity, Identify caller...). Below, the filtered call table with play/download.

### 2026 layout (`docs-analytics-dashboard-2026.png`, `docs-analytics-panel-builder-2026.png`)
Tabs DASHBOARD / CITATIONS / REPORTS / PRESETS / OUTCOMES. Dashboards are named boards ("Call Overview", "+" for more) on a dotted grid with "Date range", "+ Add Panel", View / Edit mode toggle. Panel types: KPI tile (value + delta vs previous period + per-panel range "7d"), line/area (Call volume, dashed projection line), donut (Breakdown of calls per pathway), bar (Avg duration over time), table, scatter. AI panel generation: type "Daily call volume per pathway for the last 30 days" and the panel form fills itself with a live preview. Panel titles can be full sentences ("Over the last 2 months, you had 6 calls total that went to v...").

### Per-pathway heatmap
Changelog mentions "pathway heatmaps" (node traffic overlay on the canvas). No screenshot found. Unverified appearance.

### Metric vocabulary worth copying
calls, cost, avg duration, transfers, issues (severity), completion rate, p50 latency, off-script %, pass rate, transfer rate by pathway, disconnect reasons, sentiment, silence count, interruptions, engagement ratio, transcription score.

---

## 7. Conversational Pathways builder in detail

Screenshots: `docs-pathway-testing-hero.png` (whole editor), `docs-pathway-node-tools-before-after.png`, `docs-pathway-node-tools-tab.png`, `docs-pathway-node-response-pathways.png`, `docs-pathway-final-canvas.png`, `docs-pathway-new-edge.png`, `docs-pathway-edge-label.png`, `docs-pathway-condition-example.png`, `docs-pathway-global-node-example.png`, `docs-pathway-global-node-config.png`, `docs-pathway-default-node.png`, `docs-pathway-webhook-node.png`, `docs-pathway-transfer-node.png`, `docs-pathway-end-node.png`, `docs-pathway-kb-node.png`, `docs-pathway-global-prompt.png`, `docs-flex-mode-pathway.png`, `docs-flex-groups.png`, `changelog-multiplayer-pathways.png`.

### Frame
- Top bar: back chevron, breadcrumb "Pathway / Tech Support", environment + version chip ("Staging  Version 2" dropdown, or "Console  Bland Console Mar 25 #2"), "Saved" indicator, overflow menu, duplicate, `{}` (JSON view), "Test", "Norm (AI Assistant)", "Global Prompt", orange "Deploy". A "Flex" mode selector lives in the header too.
- Canvas: dotted grid, top-left "Add new node", minimap bottom-right, left-edge vertical toolbar (zoom in/out, fit, lock, auto-layout, search, delete, duplicate, save, undo, redo).
- Left drawer for the selected node with tabs PROMPT / TOOLS / STANDARDS / SETTINGS and a persistent unsaved-changes banner.
- Multiplayer: collaborator avatars on nodes and edges, live cursors, a diff banner when someone else changed the pathway.

### Nodes
- Card: type icon (phone for Default, play for Start, webhook glyph, scissors-phone for End Call, arrow-phone for Transfer), title, type label on the right ("Default", "Webhook", "End Call", "Transfer Call"), two-line prompt preview, optional tag chips with a colored square ("Old Way", "New Way", "Troubleshooting", "Escalation", "Callback"), optional attached-tool chip ("WH Look Up Order" in purple). Selected node gets an orange outline and a small side toolbar (delete, duplicate, ...). Purple connector circles at top and bottom.
- Types: Default, Webhook, Knowledge Base, End Call, Transfer Call, Wait for Response, plus enterprise Scheduling and Custom Code, plus Transfer Pathway. Any node can be marked Global.
- Default node fields: Prompt or Static Text toggle; Condition (loop condition, "You must get the date, time and number of guests"); Extract Variables from Call Info (name, type string/integer/boolean, description); Optional Decision Guide (example user input -> which pathway; this is the "fine-tuning examples" mechanism); Global toggle with Global Pathway Label and Enable Forwarding; per-node interruptibility, background track, tags.
- Tools tab (2026): attach webhook / code / custom tool / tool chain inline; each with name, config, speech-during-execution, timeout, retries, variable extraction from response, and "Response pathways" that route on returned values.
- End Call and Cold Transfer tools: "Before the call ends / Before the transfer" agent speech, verbatim or AI-composed with fallback line.

### Edges ("pathways")
Dotted lines; a rounded label box in the middle ("Customer describes their issue", "Issue resolved", "Wants to see the old way"). Drag from bottom circle to top circle to create; the new edge shows a "New Pathway" button with an edit icon; the label is the routing condition the LLM reads. Edges can carry structured conditions (`open == true`) that are pre-evaluated against variables.

### Global nodes and global prompt
Global node = implicit edge from every node with the global label as condition; agent runs it and returns to the previous node (or forwards). Built-ins `{{lastUserMessage}}` and `{{prevNodePrompt}}` steer back. "Global Prompt" button opens a modal for instructions applied to every node.

### Versions, staging, gates
Draft -> publish creates a version and promotes to production; staging promotion for testing; per-call version override; branches; GitHub sync of `source/nodes` and `source/edges`; scenario gates block promotion; canary rollout on enterprise.

### Flex Mode and Flex Groups
Header "Flex" selector switches the whole pathway from strict edge-following to LLM-chosen next node. Flex Groups are named, color-coded sets of nodes (tag on each node) that can flex internally while the rest stays strict; exits from a group need explicit edges.

### Right-side panels
Scenarios panel (section 5d) and Norm assistant panel open on the right; the Testing panel opens on the left.

---

## 8. Demo / call widget

Screenshots: `homepage-hero.png`, `homepage-demo-after-click.png`, `homepage-demo-mic-blocked-ended.png`.

- Hero right side: a 3-card carousel. Center card has a large glossy orb with a play glyph, small label "BLAND", title "Ask anything"; side cards are the Healthcare (Patient services) and Financial services (Customer service) agents. Under it: cursor icon + "Click to speak with an agent". Prev/next arrows.
- Clicking the orb turns the card into a call panel in place: header "BLAND / Ask anything", right side status text ("Allow mic" while requesting permission, "Ended" after), close X; the orb shrinks to a small avatar at the top; the middle is empty (transcript area, presumably fills during the call); bottom has a red round hang-up button and a "Type instead" link (button "Switch to typing" in the a11y tree). Buttons exposed: Close, End call, Switch to typing.
- With the mic blocked the panel shows red text "Microphone access is blocked. Turn it on in your browser, then try again." and the status flips to "Ended".
- It is a browser voice session (WebRTC via the Web Agent SDK), not a phone call. Privacy policy confirms they store transcript and summary of these demo conversations but not audio.
- Product page mocks worth noting: "Build" section shows Norm building "Bright Smile Dental, Scheduling agent, Maya" with a checklist (Pathway, Cal.com calendar, SMS confirmation, Voice, HubSpot CRM, Warm transfer) and a "Building agent 0/6" progress; "Test" section shows "1,003 scenarios, 0 failing, 0 fixed, 0 reruns passing, Rollout staging".
- No public sandbox of the console exists. The homepage widget is the only thing you can run without an account.

---

## 9. What to steal for the clinic receptionist console, and what to skip

### Steal

1. **Two-tab call list: Completed / Active, same table.** Active rows tick their duration and open a live transcript drawer. This is the single most demo-friendly screen for the jury ("watch a call happen").
2. **Call detail as a three-part drawer**: transcript center, context panel right, audio player bottom. Keep the table visible on the left so reviewers can step through calls with prev/next arrows and auto-play-next.
3. **Sticky node header in the transcript** plus **inline decision cards** between turns (Node chosen, Routing with the alternatives it did not take, Variable extraction, Tool call with status/latency/payload, Refusal reason). This is exactly the "explain any utterance afterwards" invariant. Color-code by kind (blue agent, yellow extraction, green condition/route, red tool error).
4. **Waveform markers with filter chips** (Decisions / Variables / Tags). Cheap to build if you already have per-turn timestamps, and it reads as pro.
5. **Event timeline as the source of truth**: mirror Bland's envelope (`sequence, event_type, node_id, operation_id, payload, created_at`) in your backend log. It makes the transcript view, the live view, the post-call report and the leaderboard report all projections of one list.
6. **Context panel sections**: Metadata grouped (Call details / Duration / Participants / Configuration / Pathway version), AI summary, Variables, Outcome (what the agent reported: booked / moved / cancelled / declined + reason), Tool logs, Guardrails triggered, Memory (who the caller is, what we knew).
7. **Contact history by number**: clicking the caller number filters the log to that contact. For the clinic this becomes "patient record + past calls" in one click.
8. **Reported outcome as a first-class column and chip** (Bland's Outcomes / Review Status). The leaderboard is binary on the reported action, so the console should show "Reported: BOOK ok" or "Reported: DECLINE (rule X)" per call, in the table.
9. **Issues column with severity dots and a shield for guardrail triggers**, and a flag-for-triage action on any call.
10. **Test panel next to the flow**: CHAT / CALL tabs, timestamped bubbles, "Expand all logs", branching a conversation from any user message ("what if they said Tuesday instead"). For rehearsing the 18 practice cases this is gold: one saved config per case (start node, request data = the persona).
11. **Scenario gates on the pathway splash page**: list the 18 cases as scenarios with pass/fail, score, last run, and a "Run All". Judges love a green board.
12. **KPI tiles with delta + one area chart + one donut** for the analytics screen. Do not build more than that.
13. **v2 IA grouping** (Monitor / Validate / Dispatch) as the sidebar skeleton: Conversations, Live, Cases (tests), Analytics, Numbers, Settings.
14. **Version chip in the header** ("Production v3" / "Staging v4") and a version column in the call table so you can prove which prompt handled which call.

### Skip

- Norm-style AI copilot, Tornado auto-fix, Evals workbenches, Standards permutations: heavy, and the judges score the calls, not the tooling.
- Full visual pathway editor with drag-to-connect edges. Read-only flow visualisation with the live node highlighted is enough for the demo; editing stays in code.
- Multiplayer cursors, GitHub sync, canary rollout, SIP wizard, SMS/iMessage, web widget builder, knowledge map, voice cloning.
- Configurable column sets and saved filter groups. Fixed columns and three quick filters (Booked / Declined / Escalated) cover the 18 cases.
- CSV export by email. A single "Download JSON of this call" link is enough for proof.
- Utterance-type and call-objective donuts. Replace with one chart: outcome per case category.

---

## 10. Sources

Official docs (Mintlify, markdown at `.md` suffix):
- https://docs.bland.ai/tutorials/call-logs (table, filters, detail view, audio player, context panel)
- https://docs.bland.ai/tutorials/pathway-call-events (event envelope and catalog)
- https://docs.bland.ai/tutorials/pathways (nodes, edges, globals, testing panel, unit tests, variables)
- https://docs.bland.ai/tutorials/testbed
- https://docs.bland.ai/tutorials/standards
- https://docs.bland.ai/tutorials/scenarios
- https://docs.bland.ai/tutorials/evals
- https://docs.bland.ai/tutorials/flex-mode
- https://docs.bland.ai/tutorials/personas
- https://docs.bland.ai/tutorials/alerts
- https://docs.bland.ai/tutorials/guard-rails
- https://docs.bland.ai/tutorials/outcomes
- https://docs.bland.ai/tutorials/memories
- https://docs.bland.ai/tutorials/norm
- https://docs.bland.ai/tutorials/chat-widget
- https://docs.bland.ai/enterprise-features/citations
- https://docs.bland.ai/build-your-first-agent (v2 dashboard)
- https://docs.bland.ai/llms.txt (full index)
- https://docs.bland.ai/changelog/05_12_2025 (live call monitoring, analytics filtering)
- https://docs.bland.ai/changelog/07_21_2025 (call reviewing, call metrics)
- https://docs.bland.ai/changelog/03_23_2026 (tools on nodes, standards custom conversation)
- https://docs.bland.ai/changelog/04_30_2026 (triage, alerts, analytics overhaul, GitHub sync)

Marketing / changelog:
- https://www.bland.ai (homepage, demo widget)
- https://www.bland.ai/product/conversational-pathways (product page with observability / testing / guardrails mocks)
- https://www.bland.ai/changelog (full list back to March 2026)
- https://www.bland.ai/blog/bland-evals-evaluate-real-calls-for-quality-at-scale
- https://www.bland.ai/legal/privacy (demo widget data handling)

Bland University:
- https://university.bland.ai/modules/5/lesson-1, /lesson-2 (analytics menu, real time logs, live calls table), /lesson-3 (2024 pathway testing, fine-tune decisions)

Third party:
- https://www.fahimai.com/how-to-use-bland-ai/ (2026 tutorial, older UI screenshots)
- https://www.youtube.com/watch?v=qbYv7FqxRYs (Mark Kashef, 2024, pathways walkthrough; not watched, transcript snippets only)

Live captures: `homepage-hero.png`, `homepage-demo-after-click.png`, `homepage-demo-mic-blocked-ended.png`, `app-login.png`, `v2-signup.png`, `docs-page-call-logs.png`.

---

## 11. What I could not verify

- **No dashboard access.** `app.bland.ai` rendered a blank page in headless Chromium (no interactive elements; `app-login.png` is near-empty). `v2.app.bland.ai/signup` loads a form (first name, last name, phone, email, ToS checkbox, Google sign-up) behind a Cloudflare Turnstile "Verify you are human" widget; I did not attempt to pass it or complete email verification. All in-app screens above are from official screenshots and text, not my own session.
- **Live listen-in availability today.** Shipped May 2025, pulled July 2025 "temporarily", still referenced by the current docs and marketing. Unknown whether it is back.
- **Current pathway node in the live transcript view.** Not visible in any screenshot.
- **Pathway heatmap** appearance (only mentioned in a changelog fix).
- **Triage / Issues screen** layout (text only, no screenshot).
- **v2 dashboard**: only two screenshots exist (empty Overview, Phone numbers). Conversations, Issues, Evaluations, Triggers, Batches and the agent builder in v2 are unseen; descriptions are inferred from names and from the classic console equivalents.
- **Home / Overview** contents in either dashboard.
- **YouTube walkthroughs** were not watched (video search tool unavailable, and transcripts only surfaced via search snippets). The 2024 Mark Kashef video is from a much older UI.
- **Third-party blog screenshots** (`blog-fahimai-*.png`) are 2024 captures and may not match the current UI.
- Exact chart libraries, fonts and design tokens: not inspected (no DOM access to the console).
