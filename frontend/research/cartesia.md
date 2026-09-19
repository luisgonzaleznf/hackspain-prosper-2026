# Cartesia: voice agent console research

Researched 18 Sep 2026. Purpose: borrow structure, screens and capabilities for the clinic receptionist console. Pricing and marketing copy are out of scope.

Method note: cartesia.ai marketing pages and docs.cartesia.ai were read directly and screenshotted with agent-browser. The console itself (play.cartesia.ai) sits behind login; its UI is documented here from Cartesia's own doc screenshots, the changelog, and frames pulled from Cartesia's "Dialed In" YouTube demo series (Aug 2025). Anything not seen first hand is marked **unverified**. Screenshot paths are relative to `frontend/research/`.

---

## 1. What the agents product is

Cartesia sells three things: **Sonic** (TTS, now Sonic 3.6, about 90 ms time to first byte), **Ink** (streaming STT, Ink 2, native turn detection) and an agents platform. The agents platform has two generations that coexist in the docs:

- **Line** (launched 19 Aug 2025). Code first. You write a Python FastAPI agent with the Line SDK, `cartesia deploy` or push to GitHub, and Cartesia hosts it next to Sonic and Ink. Line records every call, keeps audio and transcript, reports system metrics like latency, and runs LLM-as-a-judge metrics. Hosting of Line SDK agents ends 1 Dec 2026.
- **Managed Agents** (Aug 2026). No backend. In the Playground you set instructions, welcome message, voice, LLM (hosted catalog: Claude Haiku 4.5, gpt-5.4-mini etc.), tools (webhook, client, system), noise suppression, keyterms, background sound, and publish. Every config change creates an immutable version. Connect over a WebSocket API or a phone number (Cartesia number, Twilio import, SIP trunk).

Both run in the same web console, **play.cartesia.ai** (Cartesia calls it "the Playground"). There is no separate "agents dashboard" product; agents are one section of the Playground alongside TTS, STT, voice cloning and account pages.

Positioning that matters for a receptionist console: "Configure, Test, Ship. Repeat." Built-in evaluations are sold as "live testing, system metrics, and custom call analytics". The Line launch video literally says "bring voice agents to every clinic".

Screens: `screens/cartesia/agents-page-hero.png`, `screens/cartesia/agents-page-full.png`.

## 2. IA / nav map

Two sidebar generations are visible.

**Aug 2025 console (Line era)** (`screens/cartesia/docs-playground-loggable-metrics.png`, dark mode; `screens/cartesia/video-call-logs-tab-search.png`, light):

```
Voice Tools   Text to Speech, Instant Clone, Pro Voice Clone, Localize a Voice, Voice Changer, Design a Voice
Library       Voices, Discover, Pronunciation
Agents (NEW)  Your Agents, Metrics
Studio        Narrations
Platform      Usage, Payouts, Concurrency, Subscription, API Keys
```

**2026 console** (`screens/cartesia/docs-phone-number-list.png`):

```
Dashboard
Models        Text-to-Speech
Agents        Voice Agents, Agent Metrics, Knowledge Base, Phone Numbers
Voices        Voice Library, Instant Clone, Pro Voice Clone, Localize a Voice, Voice Changer
Customize     Pronunciation
Monitor       Usage, Concurrency
```

**Agent detail page, Line era** (`screens/cartesia/docs-call-transcripts.png`): breadcrumb "All Agents", agent name, `agent_...` id in mono, source label ("Text to Agent" or git repo + branch), phone number, green **Call** button top right (with a dropdown for call type). Tabs: **Deployment | Configuration | Environment | Metrics | Calls**.

**Agent detail page, Managed Agents 2026** (`screens/cartesia/docs-playground-configure.png`): the agent gets its own left nav, grouped **Build** (Configuration, Tools, Settings) and **Monitor** (Calls, Metrics). Header: breadcrumb `voice-agent > Configuration`, **Preview** (phone icon, with dropdown) and green **Publish**. Configuration is a two column form: left = Instruction (markdown textarea, "Write with AI" button) and Welcome Message (with a "Skip" checkbox); right = Voice & Language (voice chip with waveform icon, flag, "+7" languages), LLM select with an "Advanced" disclosure showing `Temp default` as a chip, Background Sound file input, Noise Suppression select.

**Other list pages**
- Phone Numbers: search "by name, agent, or phone number", provider filter, columns Name | Phone Number | Agent (link) | Provider (mono chip) | Created (relative) | kebab menu. Header actions: Settings, **+ Add Number**.
- Metrics (org level): searchable list of metric name + prompt preview, **Export Results**, **Create**. Ships with a library of prebuilt metrics (Count number of times you speak, Ask for clarification, Appropriate time to end call, Detect AI Agent, Outbound Reached Voicemail, Malicious User, Request Human Transfer, Measure User Satisfaction, Helpful Inquiry Resolution, ...). `screens/cartesia/video-metrics-library.png`
- Deployments tab: "Production Deployment" card (Deployment ID mono, Status dot Ready, Deployed relative time, Webhook link) and "Deployment History" list with commit hash, `Production` outline chip, status dot, time, kebab, and a **Deploy** button. `screens/cartesia/docs-deployments.png`. Deployment details show a 3x3 grid of timestamps (Created, Build Started, Build Completed, Deployment Started, Deployment Completed), Namespace, Replicas `1 / 1`, then a Runtime Logs panel with download, wrap toggle, search (`⌘F`) and copy. `screens/cartesia/docs-deployment-logs.png`
- Usage dashboard (changelog, Jul 2026): daily call volume and minutes, spikes alongside spend, date range and agent filters. **Unverified visually.**
- Agents UI supports search by call ID and agent ID (changelog Mar 2026).

## 3. Playground UI (TTS / STT)

Not captured live: play.cartesia.ai requires login and my two navigation attempts timed out, and the /sonic marketing page failed to load twice (ERR_NETWORK_CHANGED). What is verifiable:

- Homepage demo (`screens/cartesia/homepage-hero.png`): a horizontal carousel of soft green gradient discs, one per voice persona (George Companion, Gemma Stories, Skylar, Corey Support, Jessica Narration). The selected disc is large with a white mic button in the centre; label "Talk to Skylar" and a one line character note "Warm and unhurried". No waveform, no latency counter on the marketing surface.
- Ink page demo (`screens/cartesia/ink-page-hero.png`): a single green mic circle, "Click or press Space to start a transcription", and a "Need a topic?" prompt card with a shuffle icon. Minimal, one action.
- TTS Playground features from the changelog (unverified visually): model picker (`sonic-3.6`, `sonic-preview`), voice picker plus a "mini voice picker" of recently used and saved voices, test any sample rate 8 to 44.8 kHz, one click "Report Issue", speed and volume controls, emotion via tags, pronunciation dictionaries, keyterms.
- STT Playground (changelog Jul 2026, unverified visually): watch transcription in real time on a sample clip or your own audio, configure keyterms, adjust turn detection sensitivity (turn-start, turn-end, eager-end thresholds).
- Voice Library: filter by locale, test with your own script, "call an agent per voice" directly from a voice card.

Emotion and speed controls on Sonic 3.x are per request fields (`speed` 0.6 to 1.5, `volume` 0.5 to 2, `emotion` such as calm, happy, sad) and inline SSML style tags; the docs do not show sliders.

## 4. Call detail

This is the best studied part and the one most worth copying.

**Calls table** (agent detail > Calls tab) `screens/cartesia/video-agent-calls-table.png`, `screens/cartesia/docs-call-transcripts.png`:
Status | Date | Duration | To | From | Summary. Status is a pill: `Done` (blue outline, check icon), `Active` (green), `Failed` (red). Duration is written `0h 6m 53s 201ms`, so millisecond precision is shown even for minute long calls. To/From show phone numbers or "Web Call". Summary is a one to two sentence LLM summary ("A person and an AI discussed making dessert...") or "No summary available." Sortable columns. Clicking a row opens a right side **drawer**, not a new page, so the list stays visible.

**Drawer tabs: Details | Transcript | Logs | Metrics**, close X top right, audio player pinned at the bottom of the drawer on every tab.

- **Details** (`screens/cartesia/video-call-details-summary-zoom.png`, `screens/cartesia/docs-call-recordings.png`): Summary paragraph first, then a key value list: Call Status pill, Call ID (mono, copy button), Deployment ID (mono, copy), Call Type (Phone / Demo / Web Call), User Phone Number (chip), Agent Phone Number (chip), Call Direction (Inbound / Outbound). Empty values are `N/A` in grey.
- **Transcript** (`screens/cartesia/video-transcript-turns-zoom.png`, `screens/cartesia/docs-playground-loggable-metrics.png`): a header line "August 14, 6:01 PM / User calls cartesia-form-filling." then chat bubbles, agent right aligned in a filled bubble, user left aligned in an outlined bubble. A toggle (two icons top right) switches between plain turns and a **detailed view** that interleaves your custom log events as collapsible mono cards between turns: `main_concern` > `foot injury` > `timestamp: 11.9s`. Search box at top. Changelog Apr 2026: **click a transcript turn to seek the audio**. The API exposes per turn `start_timestamp`, `end_timestamp`, `was_interrupted`, `stt_ttfb`, `tts_ttfb`, `tool_calls`; the 2025 UI did not yet render these, the 2026 UI is unverified.
- **Logs** (`screens/cartesia/video-call-logs-tab-search.png`): raw runtime log lines in mono (`call_id | timestamp | LEVEL | logger: message`), with a search field (`endcall` highlighted in yellow), result count `1 of 1` with up/down, wrap toggle, download and copy. For an **Active** call the log streams in real time. Purpose stated in the video: confirm the agent actually fired `EndCall` before hangup, see interruptions, debug reasoning.
- **Metrics** (`screens/cartesia/video-call-metrics-tab.png`): "Try New Metric" button, note "Results include metrics active during the call and auto-applied system metrics (e.g. TTFB)", then one block per metric: name, value chip (`false`, `true`, `0.148 ms`), timestamp right aligned, and the judge's one paragraph reasoning. System metrics are prefixed `[System]`: `Call Success`, `Text-to-Speech TTFB`.
- **Audio player** (bottom of drawer): thin waveform bars across the full drawer width (2026 dark UI) or a plain scrub bar (2025 light UI), play button, `00:00 / 01:13`, download icon. Recording is a WAV; also fetchable via `GET /agents/calls/{id}/audio`.

**Webhooks** mirror the same data model out to your own system: `call_started`, `call_turn`, `call_completed`, `call_failed`, `post_call_analysis` (summary). `screens/cartesia/docs-webhooks.png`.

## 5. Live monitoring

Thin. What exists:
- The calls table shows an **Active** row (green pill) while a call is in progress, and opening its Logs tab streams log lines live (Aug 2025 video). The transcript for an active call is not shown streaming in the video; **unverified** whether the 2026 UI streams turns.
- Changelog Apr 2026: **Cancel call** from the Playground for active calls (guards against mistaken outbound calls).
- The real time story is pushed to developers: the Agents WebSocket API emits `turn_started`, `turn_output_text_delta`, `turn_ended`, `client_tool_call`, and the changelog frames it as "Power live transcripts and keep your systems in sync with calls in real time via turn events, word-level assistant text, interruption state, tool calls, and call IDs". In other words Cartesia expects you to build your own live view; theirs is a log tail.
- No live dashboard of concurrent calls, no live latency gauge, no supervisor barge-in found.

## 6. Evals

- **Metrics = LLM-as-a-judge prompts** that run on each completed call and output a text, boolean or number, plus a reasoning sentence. Created at org level with a name and prompt (prompt should "define one concrete question and the expected output"). Assigned per agent via an **Add Metric to Agent** modal (`screens/cartesia/docs-metric-addition.png`) with a checkbox to also run on the most recent 10 calls. Results appear in the call drawer's Metrics tab. Metric results persist even if the metric is later removed.
- **System metrics** auto applied: `system_call_success`, `system_text_to_speech_ttfb` (TTFB on the first assistant turn).
- **Export Results** to CSV, filtered by metric and date range; columns include Metric ID, Metric Name, Agent ID, Call ID, Call Summary, Call Transcript, Call Start/End Time, Deployment ID, Run ID, JSON Result (`{value, type, description}`), Value, Status, Created At. `screens/cartesia/video-metrics-export-csv.png`. The demo's punchline is "import into pandas and iterate".
- **Text-to-Agent** (deprecated Mar 2026) generated several agent candidates, ran a **simulated call by another agent** against each, and tagged candidates with a latency rating and average words per turn. This is the only place Cartesia had automated conversation simulation; it is gone from the current product.
- No test suite runner, no scenario library, no regression view over time found. Evaluation is post hoc scoring plus CSV.

## 7. Design language notes

Marketing site (`screens/cartesia/homepage-full.png`, `screens/cartesia/agents-page-full.png`, `screens/cartesia/ink-page-hero.png`):
- Off white page (`--background: #f9f9f8`, dark variant `#171715`, border `#dfdcd7`), single green accent. Green scale from the site CSS: 50 `#f4faef`, 100 `#e2f5da`, 200 `#ceecbf`, 300 `#abd49e` (growth), 400 `#5db368`, 500 `#309d4b` (verdant, the primary button), 600 `#227a38`, 700 `#1a6b2e`, 800 `#125c25`, 900 `#004e23` (forest), 950 `#00311a`. Thin 1px hairline rules everywhere: the page is a literal grid with vertical guide lines running the full height and horizontal rules between sections; dotted or hatched gutters between blocks.
- Type (read from the site CSS): display serif **PP Kyoto** (Pangram Pangram) for headlines, with mixed weight inside one sentence ("Production-ready **voice agents** built on the best voice models."); **ABC Diatype** (Dinamo) for body and UI; **IBM Plex Mono** for anything machine like (agent names `wealth-assistant`, tool names `get_portfolio`, ids). Uppercase letterspaced micro labels ("INSTRUCTION", "VOICE & LANGUAGE", "TOOLS") over hairline rules. Colour tokens are named `--color-cartesia-green-300/500/900` with aliases `growth`, `verdant`, `forest`; the console font is not confirmed but the doc screenshots look like the same grotesk plus a mono.
- The agents hero is a fake console card: mono name, `● Live` green dot, sections with small caps labels, tool rows with a green dot bullet, tool name in mono, tool type ("Webhook", "Transfer") right aligned in grey. This is exactly the density and hierarchy the console uses.
- Logos row, "Ranked #1" claim card, and a "Deploy AI anywhere" accordion. Illustrations are thin line drawings, not photos.
- Motion: almost none observed. The voice disc carousel and accordion are the only interactive elements; no shimmer or pulse.

Console (`screens/cartesia/docs-playground-loggable-metrics.png` dark, `screens/cartesia/docs-playground-configure.png` light):
- Both light and dark themes with a sun/moon toggle in the top bar. Dark mode is near black `#0B0B0B` panels with `#1A1A1A` bubbles and grey text; light mode is white with `#F5F5F5` inset panels.
- Sans UI font, mono for ids, log lines, event names and metric values. Status pills are small, rounded, tinted (`Done` blue, `Active` green, `Failed` red, `Ready` green dot).
- Left rail with small caps group headers; content area with page title in large bold, ids in mono under it; primary actions top right (green Call / Publish, black Add Metric).
- **Latency numbers**: presented as raw values, not gauges. Call duration `0h 0m 32s 1ms`, TTFB `0.148 ms` chip inside a metric row, `tts_ttfb: 0.065` seconds in the API. Marketing uses "sub-90ms", "40ms time-to-first-audio", "P90 latency". There is no per turn latency bar or waterfall in the UI (the API has the data).
- Transcript bubbles alternate side (agent right, user left), unlike most call platforms; log events sit between bubbles as mono cards with a caret.

Exact font names, hex tokens and the Sonic page were not captured; see section 11.

## 8. Demos run and screenshots

Run in headless Chromium at 1440x900 with agent-browser. No microphone in the headless session, so the voice demos could not be exercised end to end; the pre interaction states were captured.

| Screenshot | What it is |
|---|---|
| `screens/cartesia/homepage-hero.png` | cartesia.ai hero with voice persona carousel, "Talk to Skylar" |
| `screens/cartesia/homepage-full.png` | full homepage: industry tabs, Ink/Sonic cards, deploy accordion |
| `screens/cartesia/agents-page-hero.png` | /agents hero with the mock agent config card and "Listen in" |
| `screens/cartesia/agents-page-full.png` | full /agents page: four pillars incl. Built-in evaluations |
| `screens/cartesia/ink-page-hero.png`, `ink-page-full.png` | /ink with the one button transcription demo |
| `screens/cartesia/docs-playground-configure.png` | Managed Agents configuration page (Cartesia doc image) |
| `screens/cartesia/docs-playground-add-tool.png` | Add tool dialog (Webhook / Client function) |
| `screens/cartesia/docs-call-transcripts.png` | Calls tab + Transcript drawer, light |
| `screens/cartesia/docs-playground-loggable-metrics.png` | Full console in dark mode with sidebar, calls table, transcript with log events, waveform player |
| `screens/cartesia/docs-call-recordings.png` | Details tab key values + audio player |
| `screens/cartesia/docs-deployments.png` | Deployment tab: production card + history |
| `screens/cartesia/docs-deployment-logs.png` | Deployment details grid + Runtime Logs panel |
| `screens/cartesia/docs-metric-addition.png` | Add Metric to Agent modal |
| `screens/cartesia/docs-phone-number-list.png` | Phone Numbers list with 2026 sidebar |
| `screens/cartesia/docs-webhooks.png` | Webhook settings (doc image) |
| `screens/cartesia/video-agent-calls-table.png` | Calls table (Dialed In: Call Logs, 584px source) |
| `screens/cartesia/video-call-logs-tab-search.png` | Logs tab with search hit highlighted |
| `screens/cartesia/video-call-details-fields-zoom.png` | Details fields zoom |
| `screens/cartesia/video-transcript-turns-zoom.png` | Transcript turns zoom |
| `screens/cartesia/video-transcript-log-events-zoom.png` | Transcript with log event cards zoom |
| `screens/cartesia/video-metrics-library.png` | Org level Metrics page |
| `screens/cartesia/video-metric-prompt-zoom.png` | A judge prompt (Detect AI Agent) |
| `screens/cartesia/video-call-details-summary-zoom.png` | Details tab with Summary on top (1280px) |
| `screens/cartesia/video-call-metrics-tab.png`, `video-call-metrics-tab-2.png` | Metrics tab inside the call drawer |
| `screens/cartesia/video-agent-metrics-tab.png` | Agent level Metrics tab with assigned metrics |
| `screens/cartesia/video-metrics-export-csv.png` | Exported CSV opened in a spreadsheet |

Video frames are low resolution (584x360 source for two videos, 1280 for the third); use them for layout, not pixels.

## 9. What to steal for the clinic receptionist console, and what to skip

**Steal**
1. **Calls table + right hand drawer, not a detail page.** Columns: Status pill | Time | Duration (ms precision) | From | Case or caller | Outcome summary. Keep the list visible while inspecting a call; the jury will click through many calls fast.
2. **Drawer tabs Details | Transcript | Logs | Metrics with a pinned audio player.** For us: Details (caller identity match, patient record hit, action taken, reported result), Transcript, Decisions (our log of lookups, availability checks, refusals with stated reason), Score (case pass or fail from the leaderboard report).
3. **Log events interleaved in the transcript as mono cards with a timestamp.** This is the cleanest way to show "why the agent said that": `lookup_patient > 4 matches > 12.3s`, `refuse > rule: no same day cancellations > 41.0s`. Directly serves the "explain any utterance afterwards" invariant.
4. **One line LLM summary per call in the table** plus a Summary block first in Details. Cheap and it makes the list scannable.
5. **Status vocabulary**: `Active` green, `Done` blue, `Failed` red, `Ready` green dot. Small tinted pills, no big cards.
6. **Raw latency numbers as chips** (`TTFB 148 ms`) rather than gauges, and ms precision durations. Matches our dark, dense standing constraints.
7. **Mono for anything machine generated**: ids, tool names, event names, metric values. Sans for prose. Tiny uppercase letterspaced group labels over hairline rules.
8. **Config page layout**: prompt textarea left, voice/LLM/audio settings right, Preview and Publish top right. If we expose agent settings at all, use this.
9. **Metric rows with value chip + one paragraph reasoning + timestamp.** Our per case scoring (expected action vs reported action) fits this exactly.
10. **Search inside logs with match count and highlight**, wrap toggle, copy, download. Trivial to build, very useful on stage.
11. **Active call row that opens a live streaming log tail.** We can do better: stream transcript turns too, since our WebSocket gives us turn events.

**Skip**
- Voice cloning, voice library, pronunciation dictionaries, narration studio, payouts, concurrency, subscription pages. Not our product.
- Deployment history, replicas, namespaces, GitHub linking. One deployment, hardcoded.
- Text-to-Agent candidate generation and simulated calls; deprecated and heavy.
- Light theme. Standing constraint is true black.
- Chat bubbles with agent on the right. Use a single column, left aligned, speaker label in the gutter; denser and easier to scan with interleaved decision cards.
- Org level metric library and CSV export. Our eval is the 18 published cases; show a case board instead.

## 10. Sources

- https://cartesia.ai (homepage, screenshotted)
- https://cartesia.ai/agents (screenshotted)
- https://cartesia.ai/ink (screenshotted)
- https://cartesia.ai/sonic (extracted text only; page load failed in browser)
- https://cartesia.ai/blog/introducing-line-for-voice-agents (19 Aug 2025)
- https://docs.cartesia.ai/get-started/overview
- https://docs.cartesia.ai/line/introduction
- https://docs.cartesia.ai/agents/introduction (Managed Agents)
- https://docs.cartesia.ai/agents/configuration
- https://docs.cartesia.ai/agents/tools
- https://docs.cartesia.ai/agents/versions
- https://docs.cartesia.ai/line/infrastructure/observability (call logs, transcripts, loggable events and metrics, recordings, webhooks, embedded demo videos)
- https://docs.cartesia.ai/line/infrastructure/deployments
- https://docs.cartesia.ai/line/evaluations/metrics
- https://docs.cartesia.ai/line/evaluations/results
- https://docs.cartesia.ai/line/integrations/websocket-api
- https://docs.cartesia.ai/line/integrations/telephony/phone-numbers
- https://docs.cartesia.ai/line/developer-tools/release-notes
- https://docs.cartesia.ai/changelog/2026 (Playground and Agents UI changes Jan to Aug 2026)
- https://docs.cartesia.ai/llms.txt (doc index)
- YouTube, Cartesia channel "Dialed In" series: Call Logs https://www.youtube.com/watch?v=H713r_K0yaU ; Built-in Observability https://www.youtube.com/watch?v=LNQXi4C4JUk ; LLM-powered Metrics Part 1 https://www.youtube.com/watch?v=IcJYTF5kOz0 ; Text-to-Agent https://www.youtube.com/watch?v=SE0O-p1NPeQ ; Introducing Line https://www.youtube.com/watch?v=QSnH1GfqaGI (transcripts read, frames extracted from the first three)
- https://research.contrary.com/company/cartesia (secondary, for Line positioning vs ElevenLabs)

## 11. What could not be verified

- **The live 2026 console.** play.cartesia.ai requires an account and both navigations timed out before the login page rendered; no signup was attempted, so no first hand screenshots of the TTS or STT Playground, the Voice Agents list, the 2026 Calls drawer, the Usage dashboard or the Knowledge Base page. Console evidence is Cartesia's own doc images (2025 to Sep 2026) and Aug 2025 video frames.
- **Whether the 2026 call drawer renders per turn TTFB, interruption flags or tool calls inline.** The API returns them (`stt_ttfb`, `tts_ttfb`, `was_interrupted`, `tool_calls`) and the changelog adds click-to-seek, but no screenshot shows them in the UI.
- **Live transcript streaming for active calls in the console.** Only live log streaming was demonstrated.
- **TTS Playground audio visualisation** (waveform, latency indicator). Not seen; only inferred from changelog items.
- **Console typefaces and tokens.** Marketing site fonts, background, border and the green scale were read from the site CSS (section 7); the console's own font stack and dark theme hex values were not, and the console greys quoted in section 7 are eyeballed from screenshots.
- **The Sonic marketing page rendering.** Two navigation failures (ERR_NETWORK_CHANGED, then a CDP navigate timeout); text was read via an extractor.
- **Homepage and Ink voice demos end to end.** No microphone in headless Chromium; only the idle state was captured.
