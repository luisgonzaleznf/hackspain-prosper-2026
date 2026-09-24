# ROSARIO frontend

Working rules for anything under `frontend/`. The repo-level `AGENTS.md` still applies (hackathon mode, no secrets, one public mirror you never push to). This file adds what the frontend needs. `DESIGN.md` is the visual contract (the Galileo-ft style reference recolored to Nava, supplied by Marcos); `CONSOLE.md` holds the console screens, event contract and component mapping. Both are enforced where possible by the design linter; read them before touching a screen.

## What this is

ROSARIO is the brand and the web console for the team's voice receptionist at "Clínica Arenal". The agent reads and writes the clinic's own database (patients, the diary, doctors away, closures). The console is a jury-scored feature, not polish: judges score "what you can see while a call is happening, what you can learn from it afterwards, and whether you can show it working". Its job is to make every write to the clinic database, and every utterance behind it, visible and explainable.

Three surfaces, in priority order:

1. **Calls.** Actual active calls above completed history: caller, current stage, elapsed time and transcript updates. Click a row for the conversation and decision cards. Ten to twenty concurrent calls must stay readable. Completed recordings stay in history, never in a simulated live board.
2. **Call detail.** Table on the left, drawer on the right: transcript with inline decision cards (lookups, availability queries, refusals with the stated reason, writes), two-lane waveform with markers, context panel (patient, what was saved and its provenance), raw event log.
3. **Calendar.** The clinic diary from the database: month grid and a day list for ~100 appointments across 12 doctors and 3 sites, doctor and site filters, doctors away and closures, Rosario's bookings linked to their calls. Plus a "Talk to ROSARIO" web-call page with the orb for the jury.

Secondary: analytics strip (calls, bookings saved, p50 response gap, call duration), patient drawer (record, note, past visits, upcoming), flow view (static stage graph with live counts).

## Stack

- Vite, React 19, TypeScript strict. pnpm is the package manager here (the rest of the repo is `uv`). Never mix.
- Tailwind v4 with tokens from `tokens/tokens.css`, mapped to utilities in the app theme. Base UI for interactive primitives, Recharts for charts, native audio and Web Audio for playback. Phosphor regular icons with direct per-icon imports from `@phosphor-icons/react/dist/csr/*`.
- Routing: `react-router`. Data: `fetch` and the `useSyncExternalStore` polling store in `src/lib/store.ts`; index every 4 seconds, active details every 1.5 seconds. Keep per-row subscriptions for detail updates.
- Fonts are self-hosted from `fonts/`: Plain (Hairline 100 to Medium 500, the face `DESIGN.md` names; commercial, license before public use) and Iosevka Fixed 400/500/600 (OFL, Latin subset, no ligatures) for machine text. The Vite scaffold serves that folder as static assets. No Google Fonts requests at runtime.
- Motion: GSAP 3.15 (vendored in `brand/vendor/`, ScrollTrigger and SplitText) for orchestrated entrances, scroll-scrubbed motion and pointer parallax; CSS transitions for hover and state. Nothing loops: every tween is one-shot, scrub-bound or pointer-bound, and `gsap.from()` keeps the page fully readable with JS off. `prefers-reduced-motion` collapses everything to opacity via `gsap.matchMedia`. The voice orb in the console is the one continuously animated element and it is driven by real audio levels. `brand/motion.js` is the reference implementation.

## Layout of `frontend/`

```
frontend/
  AGENTS.md            this file
  DESIGN.md            visual contract (Galileo-ft style reference, Nava palette)
  CONSOLE.md           console screens, event contract, component mapping
  package.json         dev / build / typecheck / lint scripts
  vite.config.ts       Vite + Tailwind; proxies /api to the call backend (ROSARIO_API, default calls.udarc.com)
  index.html           the brand landing page, served at / (static HTML + brand/)
  console.html         console app entry; /dashboard, /calls, /calendar, /metrics, /settings and /talk are rewritten to it (vite.config.ts)
  demo/                roleplay studio at /demo/, unlisted (noindex, linked from nowhere). Talks to the voice backend from the
                       demo branch through the /api/demo and /start proxies (ROSARIO_DEMO_API, default http://127.0.0.1:7860)
                       To run the backend: git worktree add <dir> origin/demo/roleplay-studio-recordings, link the repo .env into
                       it, uv sync --frozen, then uv run python -m app.demo.bot --host 127.0.0.1 --port 7860 --transport webrtc
  oxlint.config.ts     design rules for TS/TSX (jsPlugins: tools/design-lint)
  .stylelintrc.json    design rules for CSS
  tools/design-lint/   the Oxlint plugin, fixtures and their test
  tokens/tokens.css    the design tokens (only place for raw values)
  fonts/               plain/ (Hairline to Medium), Iosevka Fixed 400/500/600
  brand/               brand site (static HTML + CSS), logos, imagery/ (Codex renders), generation scripts
                       landing components: call bars (data-bars) and the audiogram (data-audiogram), drawn by brand.js from data
                       attributes, with one-shot reveals in motion.js. waves.js draws the two background fields (Gradient Waves over
                       Grainient, React Bits shaders in plain WebGL2), advanced by scroll only. Nothing loops or repaints at rest.
  research/            platform, brand and component research (read-only reference)
  src/                 the console app
```

`src/`, one folder per screen, shared bits flat:

```
src/
  main.tsx            routes (react-router)
  app.tsx             Shell (rail, phone tab bar), ScreenHeader, Mark
  styles/globals.css  imports ../../tokens/tokens.css, maps tokens onto Tailwind utilities, component classes (pill, tab, chip, card, tile, row)
  lib/types.ts        backend shapes verbatim (CallSummary, CallDetail, RawEvent, ClinicAction, LocalWriteEvent)
  lib/api.ts          GET /api/calls, GET /api/calls/{id}, audio URL, GET /api/clinic/calendar?from=&to=
  lib/calendar.ts     the diary feed: tolerant parsing, month windows, filters, absences and closures per day
  lib/timeline.ts     the projection: raw JSONL events -> turns with decision cards, stage, pending, writes, markers; outcomeOf; REASON_GLOSS, TOOL_GLOSS
  lib/store.ts        polling store: index every 4s, active-call detail every 1.5s; per-row subscriptions (useCallRecord)
  lib/replay.ts       transcript bounds for recorded playback
  lib/format.ts       Europe/Madrid clocks, durations, latencies, masked phone and DNI
  lib/motion.ts       GSAP entrances (rise-in, slide-in, count-up), reduced motion via matchMedia
  components/primitives.tsx   Chip, ReasonCode, ToolName, CopyButton, Label, SwapText, KeyValue, Empty
  components/orb.tsx          the voice orb (ElevenLabs widget rule) + useLevelMeter
  components/transcript.tsx   Transcript, TranscriptTurn, DecisionCard
  components/call-timeline.tsx   stereo audiogram, stacked decision icons and recording transport
  screens/calls/      active calls above history + detail drawer (Transcript, Report, Patient, Raw)
  screens/calendar/   clinic diary: month grid, one-line day list by time or doctor, filters, absences and closures
  screens/metrics/    stat strip, hourly area chart, outcomes
  screens/talk/       orb page: listen to a recording (stereo drives the orb) or the visitor's microphone
```

Calls renders actual active records above completed history. It does not replay finished calls as live activity. Talk does not carry a browser call; it plays recordings or meters the visitor's microphone.

## Contract with the backend

The frontend renders one thing: a per-call **event timeline**. Every screen is a projection of it. Freeze this in the repo `CONTRACTS.md` before building views:

```
CallEvent {
  call_id: string            start.callSid from the wire
  seq: number                monotonic per call
  at: string                 ISO 8601 with offset
  kind: "call.started" | "call.stopped" | "turn.caller" | "turn.agent"
      | "turn.interrupted" | "stage.changed" | "tool.called" | "tool.result"
      | "action.proposed" | "action.dropped" | "write.saved" | "write.failed"
      | "guard.blocked" | "engine.usage" | "error"
  payload: object            kind-specific; ids copied from clinic API responses
}
```

Read endpoints the console uses: `GET /api/calls` (summaries; `status` is `in progress`, `ended`, `saved` or `write failed`, `action` the verbs written), `GET /api/calls/{id}` (events, `writes` = the `local_write` events, `provenance` chains lookup, recorded, write), `GET /api/calls/{id}/audio`, `GET /api/clinic/calendar?from=&to=` (the diary window) and the Studio's `/api/demo/*`. Supervisor controls (`inject note`, `end call`) are nice-to-have and stay behind a flag until the backend has them.

Anything not in the contract is mocked and named as such in the UI header ("fixture data"). Canned data never leaks into the demo path silently.

## Working rules

- **Design linter is the gate.** `pnpm lint:design` must pass before a screen is called done. It runs Oxlint with `tools/design-lint` (no raw colors or Tailwind palette classes, no looping animation, no shadows/blur/gradients/oversized radii, no raw fonts, no em dashes, no raw inline style tokens) and Stylelint on CSS (same rules; raw values allowed only in `tokens.css`). `pnpm test:design-lint` runs the fixtures. If a rule blocks something the design genuinely needs, change `DESIGN.md` first, then the rule, in the same commit.
- **Tokens, not values.** New color, font or radius: add it to `tokens.css` with a role name, then use the utility. No exceptions in components.
- **Follow DESIGN.md, copy the reference.** Weight-100 Plain headlines, weight-300 body, true black with #14090a cards and #2d1012 hairlines, 17/35/48 radii, one red for actions. `index.html` (the landing page) is the reference implementation of the Galileo layout; when unsure how something should look, find it there or in `research/screens/` before inventing.
- **Every utterance is clickable.** Any agent turn opens the decision cards that led to it. If a view shows what the agent said without why, it is not finished.
- **Mono for machine text.** Ids, tool names, event kinds, reason codes, slots, latencies, costs. Plain for everything else. No eyebrow labels anywhere (Marcos, 19 Sep); pill tabs only in a tab row; never status pills or chip rows as decoration.
- **Reason codes are the closed vocabulary from the contract.** Render them verbatim in mono plus a short human gloss from one lookup table; never rephrase them into the mono chip.
- **Live view budget.** Twenty rows, each updating several times per second, must not re-render the whole board. Per-row subscriptions to the event buffer; virtualise the transcript past 200 turns.
- **Copy.** Spanish-first UI labels are fine where the domain is Spanish (Centro, Norte, Sur, DNI); everything else in plain English. No marketing tone, no exclamation marks, no em dashes.
- **Scope.** Overview, Calls and Calendar form the dashboard; Talk is a separate tool. Landing page actions that point to console or identity pages open the waitlist dialog. Authentication is not implemented.
- **Verification.** Run `pnpm lint:design`, `pnpm typecheck` (once scaffolded) and walk the three surfaces with fixture data before claiming done. Screenshots go to `demo/`.

## Scripts

| Script | Does |
|---|---|
| `pnpm dev` | Console on http://127.0.0.1:5173 with `/api` proxied to `ROSARIO_API` (default https://calls.udarc.com) |
| `pnpm build` / `pnpm preview` | Production build to `dist/`; preview serves it with the same proxy on :4174 |
| `pnpm typecheck` | `tsc --noEmit`, strict |
| `pnpm lint:design` | Oxlint design rules on TS/TSX + Stylelint on CSS |
| `pnpm test:design-lint` | Fixture test for the linter (bad fails, good passes) |
| `pnpm serve` | Build and serve landing + console on http://0.0.0.0:4174 (landing at `/`, console at `/metrics`) |
| `pnpm brand` | Serve `frontend/` raw on http://127.0.0.1:4173 for brand QA (landing at `/`, identity at `/brand/identity.html`) |
| `brand/scripts/quiver-logos.sh <variants> [out]` | Generate logo SVGs with QuiverAI; always `MODEL=arrow-2-telos` (the top model); reads `QUIVER_API_KEY` from the repo `.env` |
| `brand/scripts/normalize-logo.py <in> <out>` | Turn a generated SVG into a CSS-colorable mark |
| `brand/scripts/build-lockups.py <mark.svg>` | Rebuild `brand/logos/final/` (mark, lowercase Plain Light wordmark outlines, lockups, favicons) |
| `brand/scripts/index-marks.py` | Rebuild `brand/logos/marks/index.json` (the gallery order on the brand page) |
| `codex exec --enable image_generation '...'` | Renders for `brand/imagery/` (red glass on the #2d1012 canvas; prompts recorded in `brand/imagery/README.md`) |
| `brand/scripts/bundle-brand.py` | Single-file `brand/dist/` bundle for publishing |

## Secrets

`QUIVER_API_KEY` lives in the repo `.env` (gitignored). The key was pasted into a chat once; rotate it at platform.quiver.ai after the hackathon. Nothing under `frontend/` reads it except the logo script.
