# ElevenLabs Agents (ElevenAgents) console research

Researched 2026-09-18 for the HackSpain clinic receptionist console. Purpose: borrow structure, screens and capabilities from a best in class voice agent console. Pricing and marketing are out of scope.

Method: official docs (`elevenlabs.io/docs/eleven-agents/...`, fetched as `.md`), the UI screenshots embedded in those docs (downloaded to `screens/elevenlabs/doc-*.png`), the open source widget package (`elevenlabs/packages`, `packages/convai-widget-core`), the ElevenLabs UI component library (`ui.elevenlabs.io`), the conversation details API schema, and a headless browser pass over `elevenlabs.io/agents`. Everything below marked **[verified]** comes from a doc screenshot, source code, or API schema. Anything marked **[unverified]** is inferred from prose or was not reachable.

Naming note: the product was renamed from "Conversational AI" to "Agents Platform" and is now branded "ElevenAgents". Old docs URLs (`/docs/agents-platform/...`) return 404; current ones live under `/docs/eleven-agents/...`. Some doc screenshots still show older sidebar labels ("Call history", "Conversational AI"); the newest ones show the current labels ("Conversations", "ElevenAgents").

---

## 1. IA and nav map

Current sidebar, from the newest doc screenshot (`screens/elevenlabs/doc-users-page.png`) **[verified]**:

```
ElevenLabs
  [Workspace switcher: ElevenAgents]
  Home
  Configure
    Agents            (+ create)
    Knowledge Base
    Tools
    Integrations      (Alpha)
    Voices            (+ create)
  Monitor
    Conversations
    Users
    Tests
```

Older screenshot of the same shell (`screens/elevenlabs/doc-phone-numbers-page.png`) shows the earlier three item nav: Agents, Call history, Phone Numbers, plus footer items Return to ElevenLabs, Notifications, account menu. Phone Numbers still exists as a page; its current position in the sidebar is **[unverified]** (probably under Configure or inside an agent's Channels section, since the widget docs say "Channels > Widget > Interface").

Workspace level screens that live under Home or Monitor **[verified from docs prose, position in nav unverified]**:

- **Analytics** (tabs: General, Evaluation, Data Collection, Audio, Tools, LLMs, Knowledge Base, Advanced, plus a Workflow tab for workflow agents).
- **Spotlight** (Alpha): recommendations, volume and success charts, topic discovery, sentiment.
- Active calls counter: shown on the dashboard in real time, also available via API.

Per agent configuration tabs. Older screenshot (`screens/elevenlabs/doc-analysis-settings.png`) shows: **Agent, Voice, Analysis, Security, Advanced, Widget** **[verified]**. Docs prose adds tabs that exist in the current build: **Workflow**, **Tests** ("Navigate to the Tests tab in your agent's interface"), **Branches / Versioning** (when versioning is enabled), **Settings**, **Channels > Widget** **[verified prose, layout unverified]**.

Per agent test button: "Test AI agent" opens a live web call to the agent from inside the dashboard, using the React SDK under the hood **[verified prose]**.

---

## 2. Per screen breakdown

### Agents list and agent editor
- Create flow: name + template (Blank template etc.), then land in the editor (`screens/elevenlabs/doc-assistant-create-flow.gif`).
- **Agent tab**: first message, system prompt, LLM, primary language, Additional Languages (per language first message auto translated by LLM, editable), tools (including system tools like `language_detection`, `transfer_to_number`, `end_call`, `skip_turn`), knowledge base attachments, dynamic variables.
- **Voice tab**: voice picker from the library, TTS model, stability/speed/similarity, language specific voices (`screens/elevenlabs/doc-voice-settings.jpg`, `doc-language-voice.png`).
- **Analysis tab**: Evaluation criteria (Add criteria: identifier + prompt, max 30), Data collection (Add item: identifier, type string/boolean/integer/number, description, max 25 to 40), toggles for Sentiment analysis and Topic discovery (`doc-analysis-settings.png`, `doc-spotlight-analysis-settings.png`).
- **Security tab**: allowlist of hosts, overrides enablement (`doc-enable-overrides.jpg`).
- **Advanced tab**: turn taking, timeouts, soft timeout filler message, interruptions on/off, Monitoring toggle (`doc-timeouts.png`, `doc-soft-timeout.png`, `doc-interruptions.png`, `doc-no-interruption.png`, `doc-realtime-monitoring-toggle.png`).
- **Widget tab**: appearance, feedback, avatar, display text, terms, language, muting, shareable page (see section 8).
- **Workflow tab**: node graph editor (section 7).
- **Tests tab**: test library, folders, Run All Tests, per test split run control (section 5).

### Conversations (history)
- Page title "Conversation history", top right "Ask AI" button (`screens/elevenlabs/doc-smart-search-conversation-history.png`) **[verified]**.
- Search bar with mode menu: **Keyword** (full text / fuzzy, all filters available) and **Smart search** (semantic over transcript chunks, most filters disabled while active). Mode stored in the URL. A query that looks like `conv_...` jumps straight to that conversation **[verified]**.
- Filters listed in docs: time range, duration, ratings, tools, languages, evaluation results, agent, branch, call type, source, plus **Node entered** (workflow node filter, scoped to an agent) **[verified prose]**.
- Conversation status enum from API: `initiated`, `in-progress`, `processing`, `done`, `failed` **[verified schema]**.
- Row content **[unverified, inferred from Users drill down and API]**: date, agent, branch, one line summary title, success badge, duration, message count, language, source (SDK/widget/phone).
- Every conversation row opens the detail view (section 3). From the detail view: "Create test from this conversation" **[verified prose]**.

### Users
- Table of end users by external `user_id`: User ID, Last contact (sortable), Agent, Conversations count (sortable). Exact match search on id; filters by date range, agent, branch **[verified]**.
- Clicking a row opens a right side drawer "User: <id>" with a **Conversation timeline**: per conversation card showing date, agent, branch chip, one sentence summary, and chips: `Successful` (green), duration `0:04`, message count, language `English`, source `SDK: React`. Right column "Customer details": Last contact, First contact, Total conversations, Last interacted agent (`screens/elevenlabs/doc-users-page.png`) **[verified]**.

### Phone Numbers
- Master detail: list on the left with "+", empty state on the right "No phone number selected / Import a phone number" (`doc-phone-numbers-page.png`, `doc-phone-numbers-new.png`). Twilio and SIP import, assign an agent to a number (`doc-twilio-assigned-agent.png`), outbound call button and modal (`doc-outbound-button.png`, `doc-outbound-modal.png`) **[verified]**.

### Knowledge Base, Tools, Voices, Integrations
- Workspace level libraries. Tools are defined once (webhook, client, code, MCP, system) and attached to agents. Knowledge base: files, URLs, text, folders, RAG toggle. Not researched in depth; not relevant to the console we build.

### Tests
Section 5.

### Analytics and Spotlight
Section 6.

---

## 3. Conversation detail anatomy

Source: `screens/elevenlabs/doc-transcript.jpg` **[verified]** plus the `GET /v1/convai/conversations/{id}` schema **[verified]**.

Layout (modal or full page card, white, single column):

1. **Header**: title "Conversation with <agent name>", date on the right (blurred in the screenshot).
2. **Audio player**: full width waveform, then a control row: play button (black round), skip back, skip forward, elapsed / total (`0:00 / 1:19`), download button. Backed by `has_audio`, `has_user_audio`, `has_response_audio`, `GET .../audio`.
3. **Tabs**: `Overview` | `Transcription` | `Client data`.
4. **Overview tab**:
   - `Summary` paragraph (`analysis.transcript_summary`; a short `call_summary_title` also exists).
   - `Call status` row with a pill: `Success` (`analysis.call_successful`: success / failure / unknown).
   - `Criteria evaluation` row with a count `4 of 4 successful`, then one block per criterion: identifier (`hallucination_kb`), result pill, and the LLM rationale paragraph (`evaluation_criteria_results[].result / rationale`; `scoring_mode` binary or numeric with `score / max_score`).
   - Data collection results appear below in the same style: name, value, rationale (`data_collection_results[]`) **[verified prose, screenshot cut off]**.
   - Sentiment trajectory chart: scored user turns plotted negative to positive over time, with the "best moment" marked (`doc-sentiment-analysis-trajectory.png`) **[verified]**.
5. **Transcription tab**: chat style list. Data available per turn from the schema **[verified]**:
   - `role` (`user` | `agent`), `time_in_call_secs` (timestamp offset), `message`, `original_message` (pre correction text), `interrupted` flag, `ignored_as_backchannel`, `source_medium` (`audio` / `dtmf` / `text`), `producing_llm`.
   - `tool_calls[]` (`tool_name`, `params_as_json`, `type` system/webhook/client/mcp/workflow) and `tool_results[]` (`result_value`, `is_error`, `is_blocked`, `tool_latency_secs`, `error_type`, `dynamic_variable_updates[]`), so tool calls render inline between agent turns with latency and error state.
   - `conversation_turn_metrics.metrics{}` per turn (elapsed times, e.g. time to first byte for ASR, LLM and TTS), `convai_asr_provider`, `convai_tts_model`.
   - `llm_usage.model_usage{}` per turn: input / cache read / cache write / output tokens and price.
   - `rag_retrieval_info` (chunks, vector distance, latency, query), `used_static_kb_document_ids`.
   - `agent_metadata` (`agent_id`, `branch_id`, `workflow_node_id`, `version_id`) so each turn can be attributed to a workflow node and version.
   - `feedback` per turn (`like` / `dislike` + time), `triggered_guardrails[]`.
   The dashboard exposes these as expandable rows under each message **[unverified detail; the `evaluation_result.gif` and `collection_result.gif` in the screens folder show the older result panels]**.
6. **Client data tab**: `conversation_initiation_client_data`: dynamic variables, overrides, `user_id`, `source_info` (SDK and version), branch, environment **[verified schema]**.
7. **Metadata** (shown in the header or a side panel **[position unverified]**): `start_time_unix_secs`, `call_duration_secs`, `queue_wait_secs`, `cost` (credits) and `cost_fiat` (USD), `charging.llm_price / llm_charge / call_charge / platform_charge`, `tts_usage` (audio seconds, characters, per voice), `asr_usage`, `analysis` cost, `phone_call` (direction, external number, call sid), `termination_reason`, `error {code, reason}`, `warnings[]`, `main_language`, `features_usage` (language detection used, transfer used, etc.), `conversation_initiation_source`, `timezone`, `tag_ids[]`.
8. **Actions**: "Create test from this conversation", tags (list/create/add), delete conversation, send feedback **[verified prose / API]**.

Older result panels (`doc-evaluation_result.gif`, `doc-collection_result.gif`) show the pre 2026 detail with an evaluation section and a data collection section listed as key/value rows with rationale.

---

## 4. Live monitoring

- **Active calls counter** on the dashboard, real time, also via API **[verified prose]**.
- **Real time monitoring** is enterprise only: `wss://api.elevenlabs.io/v1/convai/conversations/{id}/monitor`. Needs the "Monitoring" toggle in the agent's Advanced settings and a chosen event set (`doc-realtime-monitoring-toggle.png`). Streams text events only (transcripts, agent responses, corrections, tool events); no audio; roughly the last 100 events are replayed on connect; you can only connect after the call started **[verified]**.
- Control commands over the same socket: `end_call`, `transfer_to_number`, `contextual_update` (inject text the agent will use), `enable_human_takeover`, `send_human_message`, `disable_human_takeover` **[verified]**.
- There is no documented in dashboard live transcript view; the docs frame monitoring as something you build ("Build real-time monitoring dashboards", "Call center oversight") **[verified prose]**. Spotlight "Real-time insights" is near real time aggregate, not per call.
- Client side, the React SDK exposes `status` (`disconnected` / `connecting` / `connected`), `mode` (`speaking` / `listening`), `isSpeaking`, `isListening`, `canSendFeedback`, `getInputVolume()`, `getOutputVolume()`, and events `user_transcript`, `agent_response`, `agent_response_correction` (what the agent actually said after an interruption), `agent_chat_response_part` (token streaming), `client_tool_call`, `agent_tool_response`, `vad_score`, `interruption`, `guardrail_triggered`, `queue_status` (`waiting` / `admitted` / `timed_out`), `conversation_initiation_metadata` **[verified]**.

---

## 5. Tests and simulation

Three test types **[verified]** (`doc-agent-simulation-test.png`, `doc-agent-llm-eval-test.png`, `doc-agent-tool-call-test.png`):

| Type | What it checks | Editor fields |
|---|---|---|
| Simulation test (Alpha) | Full multi turn conversation with a simulated user reaches an outcome | Test name, "Describe simulated user scenario", "Describe success criteria", Maximum conversation turns (default 5, 1 to 50), Mock all tools toggle + "Choose tools to mock", Environment picker, Dynamic variables |
| Next reply (Scenario) test | The agent's next message vs criteria | Chat history editor (right pane, add/remove bubbles), success criteria, success example, failure example |
| Tool call test | Correct tool with correct params | Tool picker (`transfer_to_number`), per parameter validation: Exact / Regex / LLM with expected value, dynamic variables, chat history on the right |

Editor layout **[verified]**: two panes. Left: form. Right: chat history builder with agent and user bubbles, `+` and trash controls, and a footer note "The agent's response to the last user message will be evaluated against the success criteria using examples provided." Bottom bar: Back, Edit as JSON, Move to folder (All tests / Current), "Attach to the agent automatically" checkbox, Create, Create & Run.

Running **[verified]**:
- Tests tab per agent: run one, select several, or "Run All Tests"; folders.
- Split run control on the run button: 3x, 5x, 15x etc. (`doc-agent-test-many-run.png`).
- Results: pass rate badge `8/10` colored green (100%), amber (>= 80%), red (< 80%). Runs grouped into buckets by failure reason: "Passed 8/10", "Invented internal team name 1/10", "Incorrect internal note visibility 1/10", each expandable to rationale and the underlying run ids (`trun_...`) (`doc-agent-test-probabilistic-bucketing.png`).
- Tests can be created from a real conversation ("Create test from this conversation"), run from CLI (`elevenlabs agents test`) and API (`run-tests` with `repeat_count` 2 to 20), and wired into CI.
- Tool mocking: mock none / all / selected; fallback when no mock matches: call real tool or finish with error.

API shape for a simulated run (`simulate-conversation`): full `simulated_conversation[]` (same turn model as history, with `tool_calls`, `tool_results`) plus `analysis` (`evaluation_criteria_results`, `data_collection_results`, `transcript_summary`, `call_successful`) **[verified]**.

Video: "Introducing Tests for ElevenLabs Agents" (41 s): rerun saved conversations, generate tests from real conversations, verify tools and human handover, CI/CD **[verified transcript]**.

---

## 6. Analytics and charts

Screens: `doc-analytics-general.png`, `doc-analytics-tools.png`, `doc-analytics-llms.png`, `doc-analytics-latency.png`, `doc-workflow-analytics.png`, `doc-spotlight-overview.png`, `doc-spotlight-topic-discovery.png` **[verified]**.

Page header: workspace name, greeting ("Good afternoon, Angelo"). Tabs: **General, Evaluation, Data Collection, Audio, Tools, LLMs, Knowledge Base, Advanced** (+ Workflow when a workflow agent is selected).

Filter bar: `Views` / `Create view` (saved views), `Date Range | Last week`, `Granularity | Hourly` (auto adjusts: hourly, daily, weekly), `Agent`, `Group By | Tool Type` chip with an x. Filter dimensions: agent, branch, call type (inbound / outbound / web), language, conversation source (widget / phone / API), LLM model, TTS model, ASR model, tool type, error type, evaluation criteria, collected data values.

General tab card: a **stat strip** of selectable metric tiles (the selected one drives the chart): Number of calls `143K`, Average duration `1:58`, Total cost `1.76M credits`, Average cost `12.4 credits`, Total LLM cost `$9,718.40`, Average LLM cost `$0.068`. Below: single series **area line chart** (blue) over time, x axis start/end timestamps, y axis with 0 / 500 / 1K. Footer: `Linear scale` toggle (log scale), download CSV icon, `Filtered call history ->` link that opens Conversations with the same filters.

Tools tab: two cards side by side, **Average Error Rate** (`12.6%`) and **Average Tool Latency** (`0.72 s`), multi series line charts grouped by tool type (blue, orange, green, purple).

LLMs tab: "LLM time to first sentence" over time. Latency card: **Turn Taking Latency** `0.44 s` with p50 / p90 / p99 series (multi line).

Other documented metrics: total duration, error rate, error breakdown by type (tool failures, LLM errors, connection), success / failure / unknown rate per evaluation criterion, language breakdown (share of calls per language), active calls.

Workflow analytics tab: the workflow graph itself with metrics overlaid. Each node shows chips: entry rate `99.2%` (blue, enter icon), average time `1m 23s` (green, clock), end rate `68.9%` (amber, end icon), and a footer `616 conversations`. Edges are labelled pills with percentage and condition text (`99.2% Unconditional`, `1.3% The purchase platfo...`). Clicking a node opens a right inspector: Entry rate, End rate (with average total duration), Average time in node, Incoming edges, Outgoing edges as a **pie chart**, buttons `See conversations` (applies Node entered filter) and `Edit in workflow editor`. Canvas toolbar: zoom in, zoom out, edit pencil.

Spotlight (Alpha): header with date navigation (`< Last 7 days >`) and Granularity. Row of recommendation cards with a tag (`Recommended` / `Suggested`), title, description and actions (`Update`, `Edit`, `Inspect`, `Configure`, `Dismiss`). Below: two chart cards, **Conversations** `54K` with delta (red down arrow `11.5K`) and **Success Rate** `41.9%` with delta (green up arrow `10.7%`), both area line charts with `Linear scale` and download. Topic discovery: table of topics with conversation count, sentiment, success rate; click to drill into conversations.

Chart types used: area line, multi line, pie (edge distribution), stat tiles with deltas, pass rate badges. No bar charts seen.

---

## 7. Workflows

Screens: `doc-workflow-overview.png`, `doc-workflow-node-types.png`, `doc-workflow-edges.png`, `doc-workflow-edge-forward.png`, `doc-workflow-tool-node-result-edges.png`, `doc-workflow-subagent-extra-agent-config.png`, `doc-workflow-agent-transfer-llm-condition.png` **[verified]**.

Visual language: dotted grid canvas, white rounded node cards with an icon + title + one line description, black pill labels on edges with a small icon per condition type, colored result pills on tool edges (`Success` green, `Failure` red). Node footer shows attached tools and KB counts as chips (`+1` wrench, `+1` book).

Node types:
- **Start** (flag icon).
- **Subagent** (person icon): overrides prompt, LLM, voice, tools, knowledge base for that phase.
- **Dispatch tool** (wrench): guaranteed tool call, with `Success` / `Failure` result edges.
- **Agent transfer** (person with gear): hand off to another agent.
- **Transfer to number** (phone): shows the phone number on the card.
- **End** (call end icon).

Edges: forward and backward; condition types **LLM condition** (natural language), **Expression**, **None / Unconditional**. Each edge has a human label and the condition. Workflows are stored as `conversation_config.workflow` JSON, editable via CLI and API; `agent_metadata.workflow_node_id` on each transcript turn links turns back to nodes; analytics overlay described in section 6.

For our clinic flow the equivalent nodes would be: identify caller, look up record, disambiguate (four matches), intent triage (book / move / cancel / refuse / escalate), availability search, confirm and write, end.

---

## 8. Widget states and orb in detail

Sources: `packages/convai-widget-core/src` (Preact, shadow DOM web component `<elevenlabs-convai>`) **[verified code]**, widget docs, and doc screenshots `doc-widget.png`, `doc-widget-overview.png`, `doc-widget-language.png`, `doc-widget-feedback.png`, `doc-widget-muted.png`, `doc-widget-mute-button.png`, `doc-terms.png`, `doc-widget-shareable-page.png`, plus GIFs `doc-appearance.gif`, `doc-avatar.gif`, `doc-language.gif`, `doc-textcontents.gif`.

### Variants and placement
`variant`: `tiny` (icon only call button), `compact` (avatar + button row, `doc-widget.png`), `full` (avatar, "Need help?" label, button, language select, `doc-widget-language.png`), `expanded` (sheet always open). Placement corners. Options: `default_expanded`, `always_expanded`, `dismissible`, `disable_banner` ("Powered by ElevenLabs" footer).

### Connection and mode states (code)
- `status`: `disconnected` -> `connecting` -> `connected` -> `disconnecting` (widget adds `disconnecting`; SDK has three).
- `mode`: `listening` | `speaking`; `isSpeaking = mode === "speaking"`.
- `isWaitingForAgent` (queued while at concurrency limit).
- `error` string, `canSendFeedback`, `isMuted`, text mode toggle (`ConversationMode` voice/text), `textOnly` conversations.

### Status label copy (code, `DefaultTextContents`)
Priority order in `StatusLabel.tsx`: queued -> not connected -> text mode -> speaking -> listening.
- queued: "Waiting for an available agent"
- not connected: **"Connecting"**
- text mode: "Chatting with AI Agent"
- agent speaking: **"Talk to interrupt"** (this is the speaking state copy; it tells the user barge in works)
- agent listening: **"Listening"**
- Other strings: main label "Need help?", start call "Start a call", "Message", "Send", "New call", "End", "Mute microphone", "Switch to text mode", "Switch to voice mode", "Change language", "You ended the conversation", "The agent ended the conversation", "An error occurred", "All agents are still busy. Please try again later.", feedback "How was this conversation?" / "Tell us more" / "Thank you for your feedback!", conversation "ID" + "Copy ID".
- Label swaps animate: fade + 8px vertical slide, 200 ms ease out; non urgent changes are delayed 500 ms to avoid flicker (`updateImmediately` only when going to speaking, connecting, or queued).

There is **no explicit "thinking" state in the widget**. Thinking is covered by the "Listening" label plus the soft timeout filler message configured on the agent. The ElevenLabs UI library does model it: `Orb agentState: null | "thinking" | "listening" | "talking"` and `BarVisualizer state: connecting | initializing | listening | speaking | thinking` **[verified]**.

### Orb (code, `Orb.ts`, `OrbShader.frag`, `Avatar.tsx`)
- WebGL canvas, fragment shader over a Perlin noise texture (`eleven-public-cdn/images/perlin-noise.png`), two gradient colors `uColor1` / `uColor2` (gamma corrected), `uTime`, `uInputVolume`, `uOutputVolume`. Default colors in the UI lib `#CADCFC` / `#A0B9D1`; docs example `#6DB035` / `#F5CABB`. Avatar can instead be an image URL.
- Reactivity is done outside the shader too: the avatar is two stacked circles, a background ring (`bg-base-border`) and the orb disc. While disconnected both are at scale 1 and static. While connected, a `requestAnimationFrame` loop sets: when the agent speaks, ring scale = `1 + outputVolume * 0.4`; when the user speaks, orb scale = `1 - inputVolume * 0.4` (the orb shrinks as the mic gets louder, the ring grows as the agent gets louder). So: **idle = static orb; listening = orb pulses inward with the caller's voice; speaking = halo grows with the agent's voice.**
- Sizes: `sm` 36 px in the trigger and sheet header, `lg` 192 px in the expanded sheet. In the expanded sheet the avatar sits centered (or at 40% height when text input is enabled), and when the transcript is shown it shrinks to `scale(0.1667)` into the top left corner (200 ms), i.e. the big orb becomes the small header avatar.
- Start call button is overlaid on the bottom edge of the large avatar (phone icon, primary black) and hides once connected; the status pill appears under the avatar once connected.

### Widget anatomy
- **Trigger** (collapsed): avatar, "Need help?" label that fades to the status pill once connected, `CallButton` (phone icon + "Start a call" -> "End" red while connected), `TriggerLanguageSelect` (flag + language name dropdown, only while disconnected), `TriggerMuteButton` (only while connected), dismiss X. `doc-widget-muted.png` and `doc-widget-mute-button.png` show the mute control.
- **Sheet** (expanded): header row 64 px with back chevron, compact status pill, right side: language select, voice/text mode toggle button, maximize/minimize. Body: `Transcript` list with `TranscriptMessage` bubbles (user right aligned in accent color, agent left aligned with 20 px avatar, markdown rendering with link allowlist, file attachments, inline `ToolCallMessage` status rows, `ShimmeringText` for streaming), sticky to bottom. Footer `SheetActions`: text input ("Send a message...") when text input enabled, send, end call, feedback thumbs, "New call".
- **Transcript toggle**: `transcript_enabled` config; when on, the expanded sheet shows the transcript and the orb moves to the corner.
- **Text input fallback**: `text_input_enabled` (Voice + text) and `supports_text_only` / Chat mode (start with a text message, no mic permission requested). Mode toggle entries are written into the transcript ("Switched to text mode").
- **Terms modal**: markdown terms shown before the first call, acceptance stored under `terms_key` in localStorage (`doc-terms.png`, `doc-terms-setup.png`).
- **Feedback**: `feedback_mode` none / during / end. During: thumbs on each agent message. End: "Was the call helpful?" thumbs popover above the trigger (`doc-widget-feedback.png`), then optional follow up text.
- **Error modal**: `ErrorModal.tsx`, "An error occurred" with the disconnect reason; queue timeout has its own friendly copy.
- **Shareable page**: hosted landing page for the agent with a description (`doc-widget-shareable-page.png`).
- Attributes for runtime: `dynamic-variables`, `override-language`, `override-prompt`, `override-first-message`, `override-voice-id`, `text-contents` JSON for i18n of all labels, `avatar-orb-color-1/2`, `avatar-image-url`, `action-text`, `start-call-text`, `end-call-text`, `listening-text`, `speaking-text`.
- Client tools fire a DOM event `elevenlabs-convai:call` where the host registers handlers (used on the docs site to navigate pages).

### Live demo capture
Not achieved. The `elevenlabs.io/agents` landing page renders its demo ("Start call", Voice / Chat tabs, "Try an ElevenLabs agent") inside a client bundle that did not expose a clickable button to the headless browser, and the docs site widget did not mount in headless Chromium (blank shadow root). Only the landing hero was captured: `screens/elevenlabs/agents-landing-hero.png`. See section 12.

---

## 9. Language UI

- **Agent tab > Additional Languages**: multi select of languages; "All" enables 31 languages; each added language gets its own auto translated first message you can edit, and optionally a language specific voice (`doc-language-overview.png`, `doc-language-selection.png`, `doc-language-voice.png`, `doc-voice-library-language.png`, `doc-agent-languages.png`) **[verified]**. English uses Flash v2; any extra language switches the agent to the v2.5 Multilingual model.
- **Language detection system tool**: `language_detection` with `reason` and `language` params; switches ASR/TTS/voice mid call when the caller speaks another supported language or asks to switch; option "Only at start of conversation" limits switching to the first two user turns to avoid accidental switches from background speech (`doc-language-detection-preconfig.png`, `doc-language_detection.png`) **[verified]**.
- **Widget**: language dropdown (flag + name) on the trigger and in the sheet header, only while disconnected; "Language selection is fixed for the duration of the call" unless the detection tool is enabled. The widget's language table (`types/languages.ts`) includes `es` Español, `ca` Català (flag `es-ct`), `gl` Galego (flag `es-ga`), `pt`; **Basque (`eu`) is not in the widget's language list** **[verified code]**. Whether the agent platform can run Basque ASR/TTS is **[unverified]**; the marketing page says "70+ languages" for TTS and the language doc says 31 for agents.
- **Analytics**: Language breakdown chart (share of calls per language) and a Language filter / group by dimension. Users drill down shows a language chip per conversation. Conversation metadata has `main_language` and `features_usage.language_detection.used` **[verified]**.
- Widget text labels are per language via `language_presets[lang].text_contents` or the `text-contents` attribute **[verified code]**.

---

## 10. What to steal for the clinic console, and what to skip

### Steal
1. **Conversation detail = audio player on top, then Overview / Transcription / Client data tabs.** Overview leads with a one paragraph summary, a `Call status` pill, then one block per criterion with identifier + pill + rationale. This is exactly the shape of the HackSpain leaderboard report ("what the agent did") and the jury's "explain any utterance" demand. Add a fourth tab **Actions** for the booking / move / cancel / refuse writes.
2. **Transcript turn model.** Copy the fields: `role`, `time_in_call_secs`, `message`, `original_message`, `interrupted`, `tool_calls[]` with `params_as_json`, `tool_results[]` with `is_error` and `tool_latency_secs`, per turn latency metrics, `workflow_node_id`. Render tool calls inline as collapsible rows between turns with a latency chip and red error state. Mark interrupted agent turns (strike or "cut off" tag) since interruption handling is a jury criterion.
3. **Evaluation criteria and data collection as first class config and result objects.** For us: criteria = the 18 case rules (identity verified before write, correct refusal reason stated, escalated to doctor, no double booking). Data collection = the structured report (patient id, action, slot, doctor, site, reason). Show `success / failure / unknown` and the rationale.
4. **Users drill down layout.** Right drawer with a conversation timeline and a "Customer details" column. For the clinic: patient drawer with upcoming appointments, past calls, verified identity status.
5. **Tests screen with pass rate badges and failure buckets.** Our practice cases are literally test cases with expected reports. Show `N/M passed` colored green / amber / red, group failures by reason, expand to the transcript. The split run control (3x, 5x) is worth copying for flaky cases (noise, interruptions).
6. **Search bar with keyword vs smart mode and a `conv_` id fast path.** Cheap to build for keyword; skip semantic.
7. **Stat strip tiles that select the chart series** (General tab): calls, average duration, success rate, average latency. One area chart under it. `Filtered call history ->` link from any analytics view back to the list.
8. **Turn taking latency p50 / p90 / p99 line chart** and a per tool error rate / latency chart. Latency is a jury item; showing p90 is convincing.
9. **Workflow graph with live overlay.** Even a static graph of our call flow with per node counts (identified, looked up, booked, refused, escalated) and the current call highlighted is a strong "call orchestration" visual for the jury. Node chips: entry %, average time, end %.
10. **Widget status copy and animation rules.** Use the three labels: "Connecting", "Listening", "Talk to interrupt" (tells the judge barge in works), and a separate "Thinking" state from the UI lib since our tool lookups take time. Orb: ring grows with agent output volume (`1 + out * 0.4`), disc shrinks with caller input (`1 - in * 0.4`), static when disconnected. Shrink the big orb into the header corner when the transcript opens.
11. **Language selector on the pre call screen** (flag + name) plus mid call auto detection with a visible "switched to Català" system line in the transcript. Flags `es`, `es-ct`, `es-ga`, plus Basque which we add ourselves.
12. **Real time monitor controls**: end call, transfer, inject context ("contextual_update") and human takeover. Even mocked, a supervisor panel with "inject note" and "take over" is a jury pleaser and maps to the operator console idea.
13. **Active calls counter** top left of the home screen.
14. **Create test from this conversation** button on the detail view.

### Skip
- Branches, versioning, experiments and traffic splits. Zero value in a weekend.
- Spotlight recommendations, topic discovery, sentiment trajectories.
- Knowledge base, tools library, integrations, voices pages as separate nav items; we have a fixed tool set.
- Credits / cost accounting beyond one LLM cost number per call.
- Feedback thumbs, terms modal, shareable page, markdown link allowlists.
- Semantic search, saved analytics views, CSV export, log scale toggles.
- Twilio / SIP number management UI; a single hardcoded number is enough.

Console IA proposal derived from this: `Live` (active calls, orb per call, live transcript, supervisor controls) | `Calls` (list + detail with Overview / Transcript / Actions / Data tabs) | `Patients` (drawer) | `Cases` (18 test cases, pass rate, buckets) | `Flow` (graph with counts) | `Metrics` (stat strip + latency percentiles). Widget: "Talk to the agent" page using the orb states above.

---

## 11. Sources

Docs (current URLs):
- Overview: https://elevenlabs.io/docs/eleven-agents/overview
- Quickstart (dashboard walkthrough, transcript screenshot): https://elevenlabs.io/docs/eleven-agents/quickstart
- Analytics dashboard: https://elevenlabs.io/docs/eleven-agents/dashboard
- Spotlight: https://elevenlabs.io/docs/eleven-agents/dashboard/spotlight and /real-time-insights and /topic-discovery
- Agent testing: https://elevenlabs.io/docs/eleven-agents/customization/agent-testing
- Workflows: https://elevenlabs.io/docs/eleven-agents/customization/agent-workflows
- Real time monitoring: https://elevenlabs.io/docs/eleven-agents/guides/realtime-monitoring
- Searching conversations: https://elevenlabs.io/docs/eleven-agents/customization/agent-analysis/smart-search
- Success evaluation: https://elevenlabs.io/docs/eleven-agents/customization/agent-analysis/success-evaluation
- Data collection: https://elevenlabs.io/docs/eleven-agents/customization/agent-analysis/data-collection
- Sentiment analysis: https://elevenlabs.io/docs/eleven-agents/customization/agent-analysis/sentiment-analysis
- Users: https://elevenlabs.io/docs/eleven-agents/operate/users
- Experiments: https://elevenlabs.io/docs/eleven-agents/operate/experiments
- Versioning: https://elevenlabs.io/docs/eleven-agents/operate/versioning
- Widget: https://elevenlabs.io/docs/eleven-agents/customization/widget
- Language: https://elevenlabs.io/docs/eleven-agents/customization/voice/customization/language
- Language detection tool: https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/language-detection
- Conversation flow (timeouts, interruptions): https://elevenlabs.io/docs/eleven-agents/customization/conversation-flow
- Client events: https://elevenlabs.io/docs/eleven-agents/customization/events/client-events
- React SDK: https://elevenlabs.io/docs/eleven-agents/libraries/react
- Simulate conversations guide: https://elevenlabs.io/docs/eleven-agents/guides/simulate-conversation
- Conversation details API: https://elevenlabs.io/docs/eleven-agents/api-reference/conversations/get
- Docs index: https://elevenlabs.io/docs/llms.txt

Code:
- Widget core (Preact web component, orb shader, status label, transcript): https://github.com/elevenlabs/packages/tree/main/packages/convai-widget-core/src
- ElevenLabs UI components: https://ui.elevenlabs.io/docs/components/orb , /conversation-bar , /bar-visualizer , /voice-button , /conversation

Pages and media:
- Landing: https://elevenlabs.io/agents (screenshot `screens/elevenlabs/agents-landing-hero.png`)
- Video, Introducing Tests for ElevenLabs Agents: https://www.youtube.com/watch?v=xRupMm2NsVY

Screenshots: all files under `screens/elevenlabs/`. Files prefixed `doc-` are the official screenshots embedded in the docs, downloaded from the docs CDN. Files without the prefix were taken by the headless browser in this session.

---

## 12. What could not be verified

- **No logged in dashboard access.** Signup with `agent@micr.dev` was not attempted to completion: ElevenLabs requires email verification and this session had no access to that inbox (only a `cuatro@micr.dev` IMAP account is configured locally). All dashboard descriptions come from official doc screenshots and prose, not from a live account. The exact current sidebar (position of Phone Numbers, Analytics, Spotlight), the conversations list columns, and the exact rendering of tool calls and per turn metrics inside the Transcription tab are therefore partially inferred.
- **Live widget states (idle / connecting / listening / speaking) were not captured.** The landing page demo and the docs widget did not render an interactive widget in headless Chromium (the docs widget shadow root was empty, the landing "Start call" was not a reachable DOM button). Fake microphone flags were set but never exercised. State copy and animation rules come from the widget source code instead, which is authoritative for behavior but not for pixels. The doc GIFs (`doc-appearance.gif`, `doc-avatar.gif`, `doc-language.gif`, `doc-textcontents.gif`) show the widget config previews.
- **Basque support** in the agent platform: absent from the widget's language table; platform level ASR/TTS support not confirmed either way.
- **Real time monitoring** is documented as enterprise only and API only; whether any live transcript view exists inside the dashboard is unknown.
- **Analytics Evaluation / Data Collection / Audio / Knowledge Base / Advanced tabs** were not screenshotted in the docs; contents inferred from the metrics list.
- Docs screenshots span product versions (2025 to Feb 2026 timestamps in the charts); some labels ("Call history", "Conversational AI", "LLM evaluation" vs "Next reply test") differ between screenshots and current prose.
