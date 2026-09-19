# Vapi console research (dashboard.vapi.ai)

Researched 2026-09-18 for the HackSpain clinic receptionist console. Focus: information architecture, call detail anatomy, live monitoring, evals, analytics, flow builder, web call widget. Pricing and marketing ignored.

Evidence grades used throughout:

- VERIFIED: seen in a screenshot saved under `screens/vapi/` or stated verbatim in docs.vapi.ai.
- DOCS ONLY: described in docs text, no screenshot obtained.
- UNVERIFIED: inferred from blog posts, changelogs, or third party videos; not confirmed against the live product.

Access note: I could not log into dashboard.vapi.ai. The register page requires Google, GitHub, SSO, or work email plus password (`screens/vapi/dashboard-login-page.png`), and I did not create an account. Everything below about logged-in screens comes from Vapi's own docs screenshots, the Dashboard 2.0 launch GIF, the Evals launch blog, and the changelog.

## 1. IA / nav map

Left sidebar, icon rail collapsed by default, expands to labels on hover (VERIFIED in `docs-assistant-editor-configure.png` and the Dashboard 2.0 GIF frames). Dark theme, near black background, teal accent for primary actions (Create, Publish, Talk).

Section grouping as of the Dashboard 2.0 redesign (VERIFIED in `blog-dashboard-2-0-sidebar-build-section.png`):

```
Overview                          (home: KPI tiles + charts)
BUILD
  Assistants
  Workflows                       (retiring 2026-08-18, replaced by Squads)
  Phone Numbers
  Tools
  Files                           (knowledge base uploads)
  Squads
  Integrations
  Vapi API Keys
TEST                              (collapsed group in the GIF; docs name: Simulations, Evals, Test Suites)
DEPLOY                            (collapsed group; docs mention Outbound Campaigns here)
```

Docs consistently reference an `Observe` group too: `Observe > Call Logs`, `Observe > API Logs`, `Observe > Webhook Logs` (DOCS ONLY, docs.vapi.ai/debugging). The current docs sidebar lists an `Observability` product family with `Evals`, `Simulations`, `Boards`, `Scorecard`, `Monitoring` (VERIFIED in the docs nav). Additional items named as sidebar entries in the docs: `Structured Outputs`, `Monitors`, `Issues`, `Notifiers`, `Boards`, `Chat` and `Session` logs (DOCS ONLY).

The 2026 icon rail in the assistant editor screenshot shows roughly 18 icons top to bottom: home, search, assistants, workflows, phone, tools, files, squads, integrations, keys, then a test group (flask icon), campaigns, evals, monitors, analytics, and a billing `$` at the very bottom (VERIFIED as icons, labels inferred: UNVERIFIED).

Routes seen in the wild: `dashboard.vapi.ai/calls` (call logs), `/logs`, `/v2`, `/register`, `/login`. Every screen has a global search (magnifier icon in the rail) and a `Composer` button in the top bar (an in-dashboard AI chat that drafts assistants and squads; VERIFIED label in screenshots).

## 2. Per screen breakdown

### Overview (home)

VERIFIED from the Dashboard 2.0 GIF (`blog-dashboard-2-0-overview-charts-last-frame.png`, March 2025 data):

- Grid of card tiles, each = title, one big monospaced KPI number, one chart below it.
- `Total Call Minutes` 54,437.39 with an orange line chart over ~30 days.
- `Number of Calls` 37,437 with a violet line chart.
- `Average Cost per Call` $0.15 with a cyan line chart; hover tooltip shows date and `avgCallCost 0.167`.
- `Average Call Duration by Assistant`: stacked bar chart by day, one colour per assistant, legend of assistant names underneath (`AirGarage - MIKE PROD`, `Vapi LP - PRODUCTION`, etc).
- Chart style: thin smoothed lines, no fill, sparse y axis labels, dates on x axis, dark card with 1px border, no decorative chrome.

### Assistants

VERIFIED (`docs-assistant-editor-configure.png`, `docs-assistant-version-*.png`):

- Two pane layout: left list panel (`Assistants 3` header, `Create Assistant` primary button with a template dropdown chevron, folder icon, search box, list rows with name and three small tags) and right editor.
- Top bar of the editor: `Composer`, `Talk` (starts a web call from the browser, with a dropdown chevron), `Published` state pill, kebab menu.
- Editor tabs: `Assistant`, `Logs`, `Tools`, `Analysis`, `Advanced`, plus a search icon. Version pills `v2`, `v1` down the left edge.
- Above the fold: a `Cost` bar and a `Latency` bar (`~1,570 ms`) rendered as segmented horizontal bars (orange = transcriber, blue = model, magenta = voice), plus model preset chips `Balanced`, `High Intelligence`, `Ultra Fast`, `Cost Saver`.
- Three provider cards side by side: `TRANSCRIBER` (latency, cost, accuracy as `1.8% WER`), `MODEL` (`GPT-4.1`, OpenAI, `Latency 690ms`, `Cost $0.02/min`, `Intelligence 19`), `VOICE` (`Elliot v2`, Vapi, `Latency 440ms`, `Cost $0.02/min`, `Humanness 93`). Each card has a pencil edit icon. This is the "Model Intelligence" feature from the changelog.
- `First Message` textarea with a `Assistant speaks first` dropdown to its right.
- `System Prompt` editor with search, keyboard shortcut hint, `Generate` (AI drafting) and expand buttons.
- Versioning: `Version History` side panel lists versions grouped by day (`v2 Clarify opening message  Current`, `v1 First draft`, `Legacy Versions 2`), and a diff modal `Changes in v2 vs v1` showing a red/green JSON line diff of the assistant config, with search, sort, copy (VERIFIED). Publishing flows through a `Publish` review modal (`docs-assistant-publish-review.png`, `docs-assistant-publish-details.png`).
- Assistant chat menu (`docs-assistant-chat-menu.png`): small popover to test by chat instead of voice.

### Phone Numbers

VERIFIED (`docs-phone-number-create.png`, `docs-phone-number-outbound-call.png`):

- Same two pane pattern: left list with `Create Phone Number` and search, right detail.
- Create modal has a left option list: `Free Vapi Number`, `Free Vapi SIP`, `Import Twilio`, `Import Vonage`, `Import Telnyx`, `BYO SIP Trunk Number`; right side form (`Area Code`), info callout, payment gate card, `Cancel` / `Create`.
- Number detail has an inbound assignment (assistant or squad), headers config (`Add Header`, `No Headers Configured`), and an outbound test panel (`docs-phone-number-outbound-call.png`: phone number field, assistant picker, call button).

### Call Logs (Observe > Call Logs)

List view (DOCS ONLY plus changelog): table of calls with an `Ended Reason` column (docs.vapi.ai/calls/call-ended-reason), filters, row selection with a bulk actions bar, CSV export (added in Dashboard 2.0), and thumbs up / thumbs down per call. The same table pattern was later reused for Chat logs and Session logs (changelog: "export selected rows from chat and session logs and use a bulk-actions bar, matching the call logs experience"). Column set beyond Ended Reason is UNVERIFIED; the Call object suggests: started at, type (`inboundPhoneCall`, `outboundPhoneCall`, `webCall`), assistant, phone number, customer number, duration, cost, status, ended reason.

Detail view: see section 3.

### Tools, Files, Squads, Integrations

DOCS ONLY:

- Tools: visual Tools section with types `Query`, `End Call`, `Transfer Call`, `Handoff`, `Send Text`, `API Request`, `Function`, `DTMF`, `Voicemail`, `MCP`. Each tool page has a `Test` button that sends sample payloads and shows the response (docs.vapi.ai/debugging). API Request tool config exposes URL, method, model generated body, headers, static body fields, Liquid templating, timeouts, retries.
- Files: upload documents that become knowledge bases; attached to assistants through the `Query` tool.
- Squads: list of squads, each a set of assistants with handoff tools; a `Clinic triage and scheduling squad` example exists in docs (triage, emergency, scheduling assistants). Handoff config includes destinations, context passing, spoken messages per phase, and rejection rules.
- Integrations: Google Calendar (create event, check availability), Google Sheets, Slack, GoHighLevel.

### Outbound Campaigns

VERIFIED (`docs-campaign-create-details.png`, `docs-campaign-contacts-preview.png`): a setup form (name, phone number, assistant or squad, schedule window) and a contacts table preview parsed from CSV with dynamic variable columns. Campaign dashboard shows status, completed calls, pick up rate, voicemail count, and per contact call rows with transcript links (DOCS ONLY).

### Structured Outputs

DOCS ONLY: sidebar item `Structured Outputs`, `Create New Structured Output` button, form with Name, Type (Object, Boolean, String, Number), Description, visual JSON schema builder, attach-to-assistant dropdown, `Compliance Settings` expander with a HIPAA storage toggle. Results appear in the call detail under a `Structured Outputs` tab as formatted JSON keyed by output id with `name` and `result`.

## 3. Call detail anatomy

Best evidence is the Evals launch blog screenshot of a real call detail (`blog-evals-call-log-thumbs-down-to-eval.png`, Nov 2025, VERIFIED), plus docs text.

Header row:

- Left: `11/15/2025 13:06  webCall  [Assistant]` chip, second line `Ended: Customer Ended Call`, third line the call id (truncated, copy icon).
- Right: `Cost: $0.03`, `Duration: 16s`, up/down arrows to step to the previous/next call without leaving the panel, close X. The detail opens as a panel over the list, not a separate page.

Recording block:

- Title `Recording` with running time `00:16` right aligned.
- Dual channel waveform: orange band above the centre line for the assistant, teal band below for the caller. This makes talk-over and interruptions visible at a glance.
- Play button bottom left, `Audio` download button bottom right. Stereo recording is the default artifact; mono and video variants also exist in the Call object.

Tab strip under the recording (VERIFIED labels, horizontally scrollable): `Transcripts`, `Logs`, `Analysis`, `Structured Outputs`, `Messages`, `Call Cost`, `Latency`, `Summary` (last two cut off in the screenshot, read as `Lat...` and `Sum...`).

Transcripts tab:

- Chat bubble layout. Assistant bubbles left aligned with a teal `Assistant` label; user bubbles right aligned in a lighter grey with an amber `User` label.
- Each bubble has a timestamp below it in wall clock plus offset form: `1:06:39 PM (+00:00.23)`, so both absolute time and seconds since call start are visible.
- A thumbs down icon sits next to each assistant turn. Clicking it opens "use this as an eval": you state what the assistant should have done and it becomes a regression test (blog, VERIFIED text).
- System events render as centred pills in the timeline: `Customer ended the call  01:06 PM`.

Logs tab (DOCS ONLY plus changelog): raw pipeline log lines for the call, including tool execution results and errors, and since 2026 "voice-activity-detection transitions with a per-phase latency breakdown" (changelog, UNVERIFIED layout).

Analysis tab (DOCS ONLY): summary, success evaluation, and structured data from the assistant's analysis plan. Success evaluation rubric types: `NumericScale` (1 to 10), `DescriptiveScale` (Excellent, Good, Fair, Poor), `Checklist`, `Matrix`, `PercentageScale`, `LikertScale`, `AutomaticRubric`, `PassFail`. `{{endedReason}}` is available inside analysis prompts.

Structured Outputs tab (DOCS ONLY): formatted JSON per output with id, name, result. Conditional outputs that were skipped are surfaced as skipped rather than omitted (changelog).

Messages tab (UNVERIFIED layout): the raw `messages` array of the Call object, i.e. role, message, time, secondsFromStart, tool call and tool result entries.

Call Cost tab (UNVERIFIED layout, VERIFIED data model): `costBreakdown` has `transport`, `stt`, `llm`, `tts`, `vapi`, `total`, plus per provider `costs[]` entries with minutes and type. Expect a small table or stacked bar per component.

Latency tab (UNVERIFIED layout): per turn latency split into transcriber, model, voice, matching the segmented Cost/Latency bars on the assistant editor. The changelog describes "per-phase latency breakdown" attached to VAD transitions.

Other Call object fields worth surfacing in a detail view (from the API reference, VERIFIED schema): `status` (`queued`, `ringing`, `in-progress`, `forwarding`, `ended`), `endedReason` (hundreds of codes, grouped as assistant actions, customer actions, timeouts, pipeline errors by provider, transport, SIP, hooks), `assistantVersion`, `customer.number`, `phoneNumberId`, `transport.provider`, `artifact.recording.stereoUrl`, `artifact.scorecards[id] = {name, score, scoreNormalized, metricPoints}`, `monitor.listenUrl`, `monitor.controlUrl`, `detectedThreats` per message.

## 4. Live monitoring

There is no documented live calls screen in the dashboard. Nothing in the docs, changelog, or screenshots shows an "in progress calls" list, a live transcript panel, or a listen-in button in the console. Treat "Vapi has a live view" as UNVERIFIED and probably false as of this date.

What exists is API level (docs.vapi.ai/calls/call-features, VERIFIED text):

- `monitor.listenUrl`: WebSocket that streams raw call audio in real time (listen in, or record).
- `monitor.controlUrl`: POST JSON to inject actions mid call: `say` a message, `add-message` to the history (optionally trigger a response), `control` the assistant (mute, pause), `end-call`, `transfer`, `handoff` to another assistant.
- Web SDK client events for a browser call: `call-start`, `call-end`, `speech-start`, `speech-end`, `volume-level`, `message` (types `transcript` with `role` and `transcript`, `speech-update`, `status-update`, `tool-calls`, `user-interrupted`, `assistant.speechStarted` with per word timing for karaoke captions).
- Server webhooks: `status-update`, `transcript`, `tool-calls`, `end-of-call-report`.

The Dashboard `Talk` button gives a live web call test with a real time transcript and immediate tool execution results (docs.vapi.ai/debugging, DOCS ONLY), which is the closest thing to a live view, but it is for the operator's own test call, not for calls in flight from the phone network.

## 5. Evals and testing

Three generations coexist. Test Suites (2024, deprecated) -> Evals (Dec 2025) plus Simulations (2026).

### Evals (turn based, chat mock conversation)

DOCS ONLY (docs.vapi.ai/observability/evals-quickstart) and blog:

- List page `Evals`: table with Name and description, Created date, Last run status, Actions (Edit, Run, Delete); search by name, sort by date or status.
- Create form: Name, Description, Type fixed to `chat.mockConversation`. Conversation builder with `Add Message` (roles User, Assistant, Tool, System). On an assistant turn: `Enable Evaluation` toggle, judge type `AI Judge` / `Exact Match` / `Regex`, provider and model pickers, judge prompt with `{{messages}}` and `{{messages[-1]}}` variables, `Add Tool Call` with function name and argument key/values, optional tool response message. Continue plan: `Exit on Failure`, `contentOverride`, `toolCallsOverride`.
- Detail page: `Run Test` section with target type (Assistant or Squad), target picker, `Run Evaluation`, live progress. Results per turn: green check or red X, `View Details` opens the full transcript with `judge.status` and `judge.failureReason` text such as "Tool call arguments mismatch. Expected time: '14:00' but got: '2:00 PM'".
- `Runs` tab: table of Run timestamp, Target, Status (pass/fail), Duration.
- Evals can be created from a bad call in Call Logs via the thumbs down icon (VERIFIED screenshot).

### Simulations (full conversation with an AI tester)

VERIFIED screenshots `docs-simulations-*.png`:

- Concepts: Suite (groups simulations, bound to assistants or squads), Simulation (Scenario + Personality), Scenario (tester intent), Personality (tester model, voice, behaviour), AI tester.
- `Create suite` dialog: suite name plus multi select `Assistants or squads`.
- Suite editor (`docs-simulations-personality-tab.png`): left column lists simulations as cards `Simulation 1: Scenario: Book an appointment -> Personality: Skeptical Sam (Default)` with the intent sentence and a trash icon, `Add simulation` button. Right column `Edit simulation 1` with tabs `Scenario` and `Personality`. Personality tab: `Personality name` dropdown (built ins marked Default), `Behavior` textarea describing the tester, warning that edits affect all simulations using it, `Who starts first?` segmented control (`AI tester` / `Assistant or squad`), `Advanced settings` expander (model, transcriber, voice, turn taking, fallbacks).
- Success criteria tab: `Create structured output` with Name, Type, Description, Comparator (`=`, `!=`, `>`, `<`, `>=`, `<=`), Expected value.
- `Run suite` dialog (`docs-simulations-run-suite-dialog.png`): target confirmation, mode `Chat` / `Voice`, `Iterations` count, `Confirm`.
- Runs list: Status, Simulation result (`Passed` or `1/1 failed`), suite, iterations, target, date; filters by time range, status, target.
- Run detail (`docs-simulations-run-results-criteria-transcript.png`): header `Simulation 1 · Iteration 1`, title `Doc Test -> Skeptical Sam`, `Run item ID` with copy icon, tabs `Results` and `Tool mocks & webhooks`. Two columns: `Success criteria` (green check, criterion name, `BOOLEAN` type chip, `Passed. Expected = true and got true.`) and `Transcript` (cards labelled `AI Tester` / `Assistant` with `0:00` offsets, full text). Voice runs also expose a recording. `Rerun`, `Cancel` (while running), `Duplicate`, delete are available.

### Voice Test Suites (legacy)

DOCS ONLY: `Test > Test Suites`, create suite bound to a phone number, add up to 50 test cases each with a Script (what the tester says) and a Rubric (LLM grading text), run all, results per case with transcript and pass/fail.

### Scorecard and Monitoring

DOCS ONLY:

- Scorecard: metrics = structured output + conditions with points, sums to 100, stored per call as `score` and `scoreNormalized`. API only today.
- Monitoring: `Monitors` (name, category Technical / Infrastructure / Effectiveness / Compliance, target all or specific assistants, severity, comparator, threshold, check frequency, notifiers), `Issues` (summary cards for total / open / recently resolved, table by monitor, severity, status, filters New / In Progress / Resolved; issue detail with affected calls, `Analyze` AI root cause, `Acknowledge`, `Resolve`), `Notifiers` (Email, Slack, Webhook).

## 6. Analytics and charts

Overview page (VERIFIED, section 2): KPI tile with a line chart underneath, and one stacked bar by assistant. Colours: orange, violet, cyan, teal, one hue per series; dark cards; tooltips show date plus metric name and value.

Boards (DOCS ONLY, docs.vapi.ai/observability/boards-quickstart): custom dashboards on a 6 column responsive grid.

- Widget types: `Text` (single KPI), `Bar Chart`, `Line Chart`, `Pie Chart`.
- Widget config: Name, Data Source (`Calls`), Metric (`Count`, `Average`, etc), Field (`Call ID`, `Duration`, `Cost`), Time Range (`Last 24 hours`, `Last 7 days`, `Last 30 days`), `Group By` (Assistant, Status, Ended Reason), `Group By Time` (Day), `Add Another Metric` for multi line, optional X and Y axis labels and colour scheme, `Preview`, `Add to Board`.
- Filters per widget: gear icon, Field / Operator (`=`, `>`) / Value, `Add Another Filter`, `Save`.
- Global time range and granularity controls, calculated metrics with formulas (for example booking conversion rate), drag and resize.
- Pie charts have no time grouping.

Analytics API (DOCS ONLY, docs.vapi.ai/calls/call-concurrency): `POST /analytics` with `queries[]` of `{table: "call", groupBy, operations: [{operation: "sum|avg|count|max|min", column}], timeRange: {start, end, step}}`. Columns include `cost`, `duration`, `costBreakdown.*`, `concurrency`.

Campaign analytics (DOCS ONLY): status, completed calls, pick up rate, voicemail rate, per contact outcome.

## 7. Workflow / flow builder

Workflows is a node and edge canvas (DOCS ONLY; being retired 2026-08-18 in favour of Squads, so no fresh screenshots exist in the docs):

- Node types: `Start`, `Conversation` (prompt, model, voice, transcriber, extract variables), `API Request`, `Transfer Call`, `End Call`, `Tool`, `Global` node (reachable from anywhere when its condition matches).
- Edges carry conditions: AI evaluated natural language, or `Logic` edges with LiquidJS expressions (up to 1000 chars) over extracted variables.
- Variables extracted in one node flow into later prompts with `{{variable}}`.

Replacement model (Squads, DOCS ONLY): a list of member assistants, each with `handoff` tools whose descriptions act as edge conditions, variable extraction on handoff, and spoken messages per handoff phase. The dashboard does not render squads as a graph in any docs screenshot; they appear as a members list with per member handoff destinations (UNVERIFIED).

## 8. Web call widget

Homepage demo (VERIFIED, `site-homepage-hero.png`, `site-homepage-demo-scenario-menu.png`): a single control bar under the hero. Left: a scenario select (`Customer Support`, `Lead Qualification`, `Appointment Scheduling`). Right: a `Start call` button with a play glyph. Below: `Mic permissions needed` helper text. Clicking Start in a headless browser without a mic did not produce a connected state, so the in call visuals of the homepage demo are UNVERIFIED. There is also a phone number `1-844-HEY-VAPI` to call the demo from a real phone.

Dashboard `Talk` button (VERIFIED label): starts a web call against the assistant being edited; the docs say it shows a real time transcript and tool results. Layout UNVERIFIED.

Official Voice Widget (`@vapi-ai/client-sdk-react`, docs.vapi.ai/chat/web-widget, DOCS ONLY): a floating launcher button that opens a panel.

- Modes: `voice`, `chat`, `hybrid`.
- Props: `theme` light or dark, `position` (four corners), `size` `tiny` / `compact` / `full`, `radius` none to large, `base-color`, `accent-color` (default `#14B8A6`), `button-base-color` (default `#000000`), `button-accent-color`, `main-label` (default `Talk with AI`), `start-button-text` (`Start`), `end-button-text` (`End Call`), `empty-voice-message`, `empty-chat-message`, `require-consent` with `terms-content`, `show-transcript` (default true).
- Events: `call-start`, `call-end`, `message`, `error`.
- Legacy script tag widget exposes CSS state classes on the button: `vapi-btn-is-idle`, `vapi-btn-is-loading` (connecting), `vapi-btn-is-active`, `vapi-btn-is-speaking`, plus `vapi-btn-pill` / `vapi-btn-round` variants. That is the state machine: idle -> loading -> active, with speaking as an overlay state.
- Web SDK signals available for a custom UI: `volume-level` (0 to 1, for a meter or orb), `speech-start` / `speech-end` (assistant talking), `user-interrupted`, `transcript` partial and final with role, `assistant.speechStarted` with word timing for live captions, `setMuted`, `say`, `send add-message`, `stop`.

No official orb or waveform component is documented; community widgets (for example cameronking4/vapi-ai-configurable-web-component) add Start / Stop / Mute buttons, a status line, a transcript list, and a volume callback.

## 9. What to steal for the clinic receptionist console, and what to skip

Steal:

1. Call detail as a slide over panel with prev/next arrows, not a page. Header with time, channel, assistant, ended reason, cost, duration, call id copy.
2. Dual channel waveform (assistant above, caller below the centre line) with play and download. Interruptions and long silences become visible without reading.
3. Transcript bubbles with two timestamps per turn (wall clock plus `+ss.ms` offset), system events as centred pills (`Customer ended the call`), and per turn feedback (thumbs down -> becomes a regression test). For the hackathon the thumbs down can write a practice case fixture.
4. Tab strip on the call: `Transcript`, `Logs`, `Analysis`, `Structured Outputs`, `Messages`, `Cost`, `Latency`. Rename for the clinic: `Transcript`, `Decisions` (tool calls, lookups, availability, checks, refusals with reason), `Report` (what was sent to the leaderboard), `Latency`, `Raw`.
5. `Ended Reason` as a first class column and header value, with a fixed enum. Map to the clinic domain: booked, moved, cancelled, refused (rule), refused (identity), escalated to doctor, caller hung up, error.
6. Assistant header showing the pipeline as three cards (STT, LLM, TTS) with latency and cost, and a segmented latency bar. Cheap to build, reads as "we know our stack".
7. Version history with a JSON diff modal for the prompt and config. Judges ask "what changed between checkpoints"; this answers it.
8. Simulations structure: Scenario (intent) + Personality (tester behaviour) + Success criteria (typed structured output with comparator). This maps one to one onto the 18 hackathon personas. Run detail with `Success criteria` beside `Transcript` is exactly the rehearsal screen needed.
9. Overview KPI tiles with a small line chart each, one stacked bar by category. Use: calls today, bookings, refusals, escalations, median latency, and outcome by case.
10. Structured outputs shown as formatted JSON keyed by name in the call detail; the leaderboard report payload should render the same way.
11. Segmented state classes for the web call button: idle, connecting, active, speaking, plus a volume driven meter. Add `listening` and `interrupted` since the jury scores interruption handling.

Skip:

- Boards / custom dashboard builder, Monitors / Issues / Notifiers, Scorecards. Too much surface for a weekend and the jury will not build dashboards live.
- Workflows canvas. Vapi itself is retiring it. A linear "decision log" per call explains orchestration better than a graph.
- Outbound campaigns, phone number import options, billing, API keys, integrations marketplace.
- Composer (AI drafting of assistants), template galleries, model preset marketplace.
- Chat and hybrid widget modes; the clinic agent is voice only.

Gap Vapi leaves open that the clinic console should fill: a real live view. Vapi exposes `listenUrl`, `controlUrl`, `transcript`, `speech-start`, `user-interrupted` and `tool-calls` events but has no in-progress calls screen. A live panel with active calls, streaming transcript, current state (identifying, looking up, offering slots, confirming, writing), pending tool call, and interruption markers would be a visible differentiator for the jury.

## 10. Sources

Docs (VERIFIED text, fetched 2026-09-18):

- https://docs.vapi.ai/quickstart/phone
- https://docs.vapi.ai/assistants/quickstart (screenshots: assistant editor, phone number create, outbound test)
- https://docs.vapi.ai/assistants/versioning/versioning-assistants (screenshots: version history, diff, publish)
- https://docs.vapi.ai/assistants/call-analysis
- https://docs.vapi.ai/assistants/structured-outputs-quickstart
- https://docs.vapi.ai/assistants/call-recording
- https://docs.vapi.ai/calls/call-ended-reason
- https://docs.vapi.ai/calls/call-features (live call control and listen)
- https://docs.vapi.ai/calls/call-concurrency (analytics API)
- https://docs.vapi.ai/debugging (Observe > Call Logs, API Logs, Webhook Logs, Tool test)
- https://docs.vapi.ai/observability/evals-quickstart
- https://docs.vapi.ai/observability/simulations-overview
- https://docs.vapi.ai/observability/simulations-quickstart (screenshots: create suite, scenario, personality, run suite, run results)
- https://docs.vapi.ai/observability/simulations-manage
- https://docs.vapi.ai/observability/boards-quickstart
- https://docs.vapi.ai/observability/scorecard-quickstart
- https://docs.vapi.ai/observability/monitoring-quickstart
- https://docs.vapi.ai/test/voice-testing and https://docs.vapi.ai/test/test-suites
- https://docs.vapi.ai/workflows/overview and https://docs.vapi.ai/workflows/legacy-migration
- https://docs.vapi.ai/squads and https://docs.vapi.ai/squads/examples/clinic-triage-scheduling
- https://docs.vapi.ai/quickstart/web and https://docs.vapi.ai/sdk/web
- https://docs.vapi.ai/chat/web-widget and https://docs.vapi.ai/assistants/examples/voice-widget
- https://docs.vapi.ai/outbound-campaigns/quickstart (screenshots: campaign form, contacts preview)
- https://docs.vapi.ai/whats-new (changelog: VAD transitions and latency breakdown in call logs, bulk actions bar, conditional structured outputs, Model Intelligence)
- https://docs.vapi.ai/api-reference/calls/list (Call object schema)

Blog:

- https://vapi.ai/blog/vapi-dashboard-2-0 (Mar 2025, GIF of sidebar and Overview charts)
- https://www.vapi.ai/blog/evals (Dec 2025, call detail screenshot)
- https://vapi.ai/blog/call-analysis (Jun 2024)
- https://vapi.ai/blog/debug-with-ease (2024, call logs under the Calls tab)

Live pages visited with agent-browser:

- https://vapi.ai (homepage demo control)
- https://dashboard.vapi.ai (redirects to /register)

Saved screenshots (all under `screens/vapi/`):

- `site-homepage-hero.png`, `site-homepage-demo-scenario-menu.png`, `dashboard-login-page.png`
- `blog-dashboard-2-0-sidebar-build-section.png`, `blog-dashboard-2-0-overview-charts.png`, `blog-dashboard-2-0-overview-charts-last-frame.png`
- `blog-evals-call-log-thumbs-down-to-eval.png`
- `docs-assistant-editor-configure.png`, `docs-assistant-version-history.png`, `docs-assistant-version-diff.png`, `docs-assistant-version-menu.png`, `docs-assistant-publish-review.png`, `docs-assistant-publish-details.png`, `docs-assistant-chat-menu.png`
- `docs-phone-number-create.png`, `docs-phone-number-outbound-call.png`
- `docs-simulations-create-suite-dialog.png`, `docs-simulations-scenario-tab.png`, `docs-simulations-personality-tab.png`, `docs-simulations-run-suite-dialog.png`, `docs-simulations-run-results-criteria-transcript.png`
- `docs-campaign-create-details.png`, `docs-campaign-contacts-preview.png`

## 11. What I could not verify

- Anything behind login: the call logs table columns and filters, the Logs / Messages / Call Cost / Latency tab layouts, the Overview page as it looks in 2026 (the GIF is from March 2025), the Boards UI, Monitors / Issues / Notifiers screens, Squads list and detail, Tools and Files screens. Signup needs a Google, GitHub, SSO, or email plus password account; I did not create one.
- Whether any live or in-progress calls view exists in the dashboard. No docs, changelog entry, or screenshot mentions one; I treat it as absent.
- The homepage demo's in call visuals (orb, waveform, mute). The headless browser had no microphone, so the call never connected.
- The `Talk` web call panel inside the dashboard: only the button label and the docs description of a live transcript are confirmed.
- Exact icon to label mapping of the 2026 sidebar rail below the BUILD group.
- Whether Squads are rendered as a graph anywhere in the console.
- YouTube walkthroughs were found (for example "How to Analyze Vapi Call Transcripts", Dec 2024, and several agency tutorials) but not watched; none was used as evidence.
