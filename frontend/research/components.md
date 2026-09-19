# Component library research: clinic voice-agent console

Date: 2026-09-18. Target stack: React 19 + Tailwind v4 + TypeScript. Design: true black (#000), dense, editorial, burgundy accent. Motion budget: minimal, no continuously repainting CSS animations (no infinite pulse, shimmer, spinners, marquees); the only allowed live animation is a voice orb driven by real audio levels.

Screens to cover: live call board (many concurrent calls), call detail (transcript + audio waveform + tool-call timeline), evals/results table, analytics (charts), "talk to the agent" web-call widget with an orb.

Versions below were read from the npm registry on 2026-09-18 unless stated otherwise.

---

## 1. Beautiful UI (beautifului.dev)

- Real URL: https://www.beautifului.dev/ (the name is also used by an unrelated agent-skill repo, github.com/Kainiko943/beautiful-ui, and by Tailwind Plus marketing copy; neither is this).
- What it is: a copy-paste catalogue of 21 "AI-native interface" primitives by Shane Levine / Turbo (turbodesign.co). Single-page site; each component has a live demo and a copy button. No package, no official registry.
- Stack: React ("use client"), Tailwind v4 token layer (OKLCH surfaces, ink ramp, hairlines, radii chip 6 / control 8 / card 10 / window 14, easing `cubic-bezier(0.23, 1, 0.32, 1)`), CSS transitions. Two components pull extra deps: `liveline` (Insight Cards, live charts, npm 0.0.7 MIT) and `glimm` (Prompt Bar WebGL sweep, npm 0.3.1 MIT).
- License and price: MIT, free (footer: "Copyright 2026 Shane Levine, MIT License").
- Install: copy-paste from the site. Unofficial shadcn registry with 10 of the 21 items (reconstructions, not the original source): `npx shadcn@latest add https://beautiful-ui.chorus.host/r/thinking-state.json` (github.com/ansh/beautiful-ui-registry). Unofficial full mirror of the 19 earlier components extracted from the RSC payload: github.com/grxtory/beautifului-mirror.
- Dark mode: yes, light and dark tokens, dark under `.dark`; the site itself has a theme toggle.
- Fit for this product (component name, URL is the anchor on the home page):
  - Thinking (steps / reasoning / search / coding traces): tool-call timeline in call detail. https://www.beautifului.dev/#thinking (mirror file ThinkingState.tsx)
  - Tool Chips ("code edits and tool calls as compact chips"): tool calls inline in the transcript. ToolChips.tsx
  - Task Rows ("live agent task status: running, failed, completed"): live call board rows or per-call action list. TaskRows.tsx
  - Streaming Text (streamed answer with inline sources, actions, follow-ups): live transcript rendering. StreamingText.tsx
  - Approval Card (human-in-the-loop questions): confirm-before-write moments (book / move / cancel). ApprovalCard.tsx
  - Diff Table ("AI-proposed edits sweeping through tabular data"): appointment before/after view. DiffTable.tsx
  - Records Table (CRM-style dense grid with tags, sorting, relationship status): evals/results table pattern. RecordsTable.tsx
  - Filter Table (status chips that reorganize live data): call board filters. FilterTable.tsx
  - Code Block (line numbers + unified diff): raw tool payloads and diff view. CodeBlock.tsx
  - Search (command search with live filtering and empty state): command palette pattern. SearchList.tsx
  - Insight Cards (paged insights with live charts via liveline): analytics tiles.
- Motion: CSS transitions only, no Framer Motion. Infinite loops present in Loading State (shimmer + elapsed time), Thinking header shimmer, and the Prompt Bar WebGL sweep. Avoid those; the rest is state-driven.
- Accessibility: not documented on the site; the unofficial registry scopes its `prefers-reduced-motion` rule to its own keyframes. Treat as unverified.
- Registry JSON: not published by the author. Only the unofficial chorus.host registry above.
- Caveat: the mirror notes `SelectionActions.tsx` imports two atoms (`Shimmer`, `StreamText`) not present in the public copy.

## 2. beUI (beui.dev)

- Real URL: https://beui.dev (GitHub: github.com/starc007/ui-components, 1.4k stars). Author Saurabh Chauhan (@saurra3h). Pro: https://pro.beui.dev.
- What it is: an animated component library plus shadcn-compatible registry. Home page states "117 components, Tailwind 4 + React 19". Sections: Components (motion), AI Agents (17), Blocks, Charts, Playground.
- Stack: React 19, TypeScript, Tailwind v4, Motion for React (`motion/react`, npm `motion` 13.4.0). Every component I read imports `useReducedMotion` and shortens or removes motion when it is set. Shared `lib/ease.ts` tokens.
- License and price: MIT for the public library. beUI Pro: $129 per seat per year or $179 lifetime; private registry `@beui-pro/...`; includes a "Voice Conversation" block (audio-reactive waveform + transcript + session controls), four virtualized Data Table blocks, Conversion Funnel (Recharts), Usage Budget, Questionnaire, Agent Chat Input. Templates $39 to $69 each.
- Install: `npx shadcn@latest add @beui/<slug>` (namespace is in the shadcn registry directory) or `npx shadcn@latest add https://beui.dev/r/<slug>.json`. Raw TSX at `https://beui.dev/r/<slug>/raw`. MCP server at https://mcp.beui.dev/mcp. Agent skill: `npx skills add starc007/ui-components-skill beui`. Requires shadcn semantic tokens (`bg-primary`, `text-muted-foreground`); non-shadcn projects add the beUI theme CSS below the Tailwind import.
- Dark mode: yes, shadcn tokens; ships a View Transition theme toggle.
- Registry JSON verified (2026-09-18):
  - `animated-badge`: deps clsx, lucide-react, motion, tailwind-merge; files `components/motion/animated-badge.tsx`, `lib/ease.ts`, `lib/utils.ts`.
  - `table`: deps @tanstack/react-virtual, clsx, lucide-react, motion, tailwind-merge; 16 files (hooks for sort, resize, reorder, selection).
  - `drawer`, `animated-toast-stack`, `loader`: deps clsx, motion, tailwind-merge (+ lucide for toast).
  - `number.json` returned empty; the number primitives install as `@beui/digit-swap` (shown on the page).
- Fit for this product:
  - Number Animation (DigitSwap, count-up, rolling tickers): KPI tiles, call counters. https://beui.dev/components/motion/number, `npx shadcn@latest add @beui/digit-swap`. One-shot on value change, reduced-motion aware.
  - Table (virtualized 10k+ rows, sortable, row selection, column resize/reorder, sticky header, "minimal, reduced-motion-safe motion"): evals table and live call board. https://beui.dev/components/motion/table, `npx shadcn@latest add @beui/table`.
  - Animated Badge (neutral / info / loading / success / warning / danger): call status chips. https://beui.dev/components/motion/animated-badge. Flag: `pulse` defaults to true when `status="loading"`; pass `pulse={false}`.
  - Animated Toast Stack (status morphs, swipe dismissal, actions): toasts. https://beui.dev/components/motion/animated-toast-stack.
  - Drawer (side panel, spring, esc-to-close, scroll lock): call detail sheet. https://beui.dev/components/motion/drawer.
  - Tabs (spring layoutId indicator), Tooltip, Combobox, Animated Context Menu, Animated Sidebar, File Tree (keyboard navigable; usable as a JSON tree shell).
  - AI Agents set (https://beui.dev/components/agents): Message, Message Bubble, Message Scroller, Prompt Input, Todo List, Code Block, Approval Card, File Diff (streaming added/removed/context lines), Tool Result (terminal output that collapses to a completed summary; request result with retry/copy), Streaming Response, Tool Approval, Citations, Agent Activity (one adaptive stream for reasoning, searches, tool calls, "chronological mix"), Agent Loading States, AI Sidebar, Chat App. Agent Activity plus Tool Result map directly to the tool-call timeline; File Diff covers the diff view.
  - Charts (https://beui.dev/charts): Heat Calendar, Returns Calendar, Price Target Fan. Composable SVG, keyboard scrub. Niche; the analytics page is better served by shadcn charts.
- Motion flags (avoid): Marquee (infinite scroll), Loader (17 variants, all continuous; reduced-motion swaps to an opacity pulse, still a loop), Text Animation shimmer variant, Shader Background (canvas loop; reduced-motion freezes it), Agent Loading States, the loading pulse on Animated Badge, Cylinder Carousel glide. Everything else animates only on state change.
- Accessibility: reduced motion honored everywhere I read; keyboard navigation documented for Combobox, File Tree, Context Menu (typeahead), Table, Range Slider, Wheel Picker; Animated Badge demo uses `aria-live="polite"`. No published audit.

## 3. Rare UI (two unrelated projects share the name)

### 3a. Rare UI, rareui.com (recommended one)

- Real URL: https://www.rareui.com/components (GitHub: github.com/swamimalode07/rare-ui, MIT, Swami Malode 2026).
- What it is: a small shadcn registry (about 22 items: New releases 3, Display 6, AI kit 3, Navigation 5, Inputs 3, Feedback 2) of "rare" animated components.
- Stack: Next.js, Tailwind CSS, TypeScript, Motion. README: "Every component is animated with Motion, honors prefers-reduced-motion, and installs straight into your codebase."
- License and price: MIT, free, sponsor tiers at rareui.com/sponsors.
- Install (GitHub registry form): `npx shadcn@latest add swamimalode07/rare-ui/<name>`. Registry source: registry.json in the repo; built items under `public/r/<name>.json`.
- Dark mode: yes (site is dark by default).
- Fit for this product:
  - Matrix Orb: "A dot-matrix orb that animates through idle, listening and thinking states." Props: `state` (idle | listening | thinking), `level` (number 0..1, "how far the orb blooms, falls back to a built-in envelope"), `size`, `color`, `dots`, `labels`, `className` (root has `data-slot="matrix-orb"`). Registry JSON: no npm deps, only `utils`. This is the voice orb: feed `level` from an AnalyserNode and it stops being decorative. https://www.rareui.com/components/matrixorb, `npx shadcn@latest add swamimalode07/rare-ui/matrix-orb`.
  - Fluid Orb: WebGL orb with drifting fluid shading, `size` and `color` props. Continuous shader loop; only acceptable if you gate rendering on audio level. https://www.rareui.com/components/fluidorb.
  - Animated Counter (odometer wheel, dep: motion): KPI tiles. https://www.rareui.com/components/animatedcounter.
  - Code Block (theme from one accent color; deps motion, prism-react-renderer, lucide-react): raw payload view in burgundy.
  - Step Player (stepped progress track with play/pause/replay): could double as a call-phase indicator.
  - Delete Button (inline confirmation, no dialog): destructive actions in the console.
  - Notification Bell, Family Drawer (Vaul), Bounce Sidebar, Duration Picker, OTP Input, Task list.
- Motion flags: Fluid Orb (WebGL loop), Gooey Nav and Gravity Letters (decorative), GitHub Activity heatmap footer. Matrix Orb idle state animates on its own envelope; set `level` explicitly and keep it near 0 when silent.
- Accessibility: prefers-reduced-motion stated in README; no other a11y claims.

### 3b. RareUI, rareui.in (not recommended)

- Real URL: https://rareui.in (GitHub: github.com/Codewithswappy/RareUI, MIT, Swapnil Kalambe 2025). Product Hunt listing "RareUI - free premium components".
- What it is: "50+" (docs say 100+) animated landing-page components: liquid buttons, glass shimmer button, neumorphic buttons, particle cards, liquid metal (WebGL2 GLSL), Three.js liquid wave background, sound text, magnetic scatter text, 3D book.
- Stack: React 19, Next.js 16, Tailwind CSS 4, Framer Motion 12. Own CLI: `npx rareui init` / `npx rareui add <name>` (npm `rareui` 0.1.6). Not a shadcn registry.
- License and price: MIT, free.
- Dark mode: "first-class" per README.
- Fit: none of the components match a dense console; most are continuous effects (shimmer sweeps, gradient shifts, WebGL). Avoid.

## 4. Transitions (transitions.dev)

- Real URL: https://transitions.dev/ (GitHub: github.com/Jakubantalik/transitions.dev, 4.2k stars). Author Jakub Antalik.
- What it is: a catalogue of portable CSS transitions for product UI, plus an agent skill and a "Refine" tool. Not a component library: each card ships a self-contained CSS snippet (custom properties on `:root`, rules namespaced under `t-*` classes, `@media (prefers-reduced-motion: reduce)` guard). Pro cards also ship React.
- Stack: CSS first; some Pro items React. No Framer Motion.
- License and price: free tier plus Pro. CLI package `transitions-dev` 0.3.0 is MIT on npm. The repo LICENSE file returned 404 and the snippet license is not stated on the site; Pro pricing is behind "Get Pro" and was not captured. Both unverified.
- Install: copy button per card; `npx transitions-dev add card-resize` (free, no account), `npx transitions-dev add --free`, `npx transitions-dev list`; Pro after `npx transitions-dev login` (device flow). Agent skill: `npx skills add Jakubantalik/transitions.dev` (already installed locally at ~/.claude/skills/transitions-dev with 32 reference files and `_root.css`). Refine tool: `npx transitions-refine live`.
- Dark mode: snippets are colorless (custom properties only); the site has light and dark.
- Fit for this product (skill file numbers in parentheses):
  - Number pop-in (02) and Spinning counter (26): one-shot digit change for KPIs.
  - Text states swap (04): status text changing in place ("Ringing" to "Identified" to "Booking").
  - Panel reveal (07), Page side-by-side (08): list to call-detail navigation.
  - Tabs sliding (16), Tooltip open/close (17), Menu dropdown (05), Modal (06), Toast (22), Accordion (21), Notification badge (03).
  - Success check (10), Spinner-to-check morph, Error state shake (12): write confirmations and refusals.
  - Skeleton loader and reveal (14): only the reveal half; the placeholder pulse is a loop.
  - Streaming text (30, Pro): words resolving through a cross-blur for the live transcript.
  - Motion tokens: the skill defines a duration and easing scale (for example `--duration-quick` 150ms) and `transitions refine` can rewrite ad-hoc durations to tokens.
- Motion flags (avoid): Shimmer text (15), Organic shimmer, Thinking states (28), Reasoning stream (29), Matrix dot loader (31), Skeleton pulse, Pro gradient text, Image generation placeholder. All loop.
- Accessibility: every snippet ships a reduced-motion guard; nothing else claimed.
- Registry JSON: none. Own CLI only.

## 5. shadcn/ui and its registry ecosystem

- Real URL: https://ui.shadcn.com. CLI `shadcn` 4.21.0 on npm (shadcn/cli v4 shipped March 2026). Docs: changelog https://ui.shadcn.com/docs/changelog.
- What it is: copy-into-your-repo components plus a code distribution system (registries). Since July 2026 new projects default to Base UI primitives (`@base-ui/react` 1.8.0); Radix remains supported (`npx shadcn init -b radix`). Eight styles; presets (`init --preset <code>`); `shadcn/create` for previewing presets.
- Tailwind v4 support: yes since February 2025; React 19; `data-slot` attributes on every primitive; OKLCH colors; `tw-animate-css` replaced `tailwindcss-animate`; `toast` moved to Sonner then back to a Base UI Toast in July 2026. September 2026: `cn` now comes from the `cn` package (`npx shadcn migrate cn`).
- Registry system (https://ui.shadcn.com/docs/registry): `registry.json` + `registry-item.json` schema; namespaces in `components.json` (`"@acme": "https://.../{name}.json"`), install with `npx shadcn@latest add @acme/item`; GitHub repos as registries without config (`npx shadcn add owner/repo/item`, private repos via `gh` credentials since August 2026); `registry:base` for whole design systems, `registry:font`; `--dry-run`, `--diff`, `--view` flags; dynamic server-side search (July 2026); public directory at https://ui.shadcn.com/docs/directory. MCP server since August 2025; agent skill `npx skills add shadcn/ui`.
- Charts (https://ui.shadcn.com/docs/components/chart): `npx shadcn@latest add chart`. Thin layer over Recharts v3 (npm `recharts` 3.10.1): `ChartContainer`, `ChartTooltip` + `ChartTooltipContent`, `ChartLegend` + `ChartLegendContent`, `ChartConfig` with `var(--chart-1)` tokens (light/dark theme object supported). Recharts `accessibilityLayer` prop adds keyboard and screen-reader support. `ChartContainer` needs a `min-h-*`. Gallery at https://ui.shadcn.com/charts. Sparklines are just a `LineChart`/`AreaChart` with axes hidden inside a small container.
- Core components that fit this product (all `npx shadcn@latest add <name>`): `data-table` (TanStack Table 9.2.4, dense rows via `className` on rows), `table`, `badge`, `command` (cmdk 1.1.1, command palette), `resizable` (react-resizable-panels 4.12.4, split view), `sheet`, `drawer`, `toast` (Base UI), `kbd`, `spinner` (loop, avoid), `empty`, `item`, `sidebar`, `scroll-area`, `tabs`, `tooltip`, `hover-card`, `progress`, `separator`, `skeleton` (pulse loop, avoid).
- Chat components (June 2026, https://ui.shadcn.com/docs/changelog/2026-06-chat-components): `npx shadcn@latest add message-scroller message bubble attachment marker`. `MessageScroller` handles anchored turns, streamed replies, prepended history, jump-to-message, visibility tracking (headless version in `@shadcn/react/message-scroller`). `Message` (row with avatar, header, footer, grouped messages), `Bubble` (variants, alignment, collapsible), `Marker` (status updates, system notes, labeled separators "for things like streaming state, tool activity, and date breaks"). This is the live transcript plus tool-call markers. New CSS utilities `scroll-fade` (fine) and `shimmer` (loop, avoid).
- Questionnaire (August 2026) for multi-step flows; `@shadcn/helpers` mocks AI SDK conversations with human-in-the-loop pauses (useful for demo fixtures).
- Third-party registries worth using for this product:
  - LiveKit Agents UI (`npx shadcn@latest registry add @agents-ui` then `npx shadcn@latest add @agents-ui/agent-audio-visualizer-bar`): `AgentAudioVisualizerBar | Grid | Radial | Wave | Aura`, `AgentChatTranscript`, `AgentControlBar`, `agent-session-view-01`. Same props on all visualizers (`audioTrack`, `state`, `size`). Built on `@livekit/components-react` 2.9.24 (Apache-2.0) and driven by track volume plus agent state (listening / thinking / speaking). Only a fit if the web-call widget runs on LiveKit; otherwise copy the bar renderer and feed your own levels. Docs: https://docs.livekit.io/frontends/agents-ui/audio-visualizer/prebuilt.
  - Magic UI `number-ticker` (`npx shadcn@latest add @magicui/number-ticker`): one-shot count up/down, props value, direction, delay, decimalPlaces, startValue. https://magicui.design/docs/components/number-ticker. Prefer NumberFlow below.
  - NumberFlow (`@number-flow/react` 0.6.2, MIT, not a registry): dependency-free custom element, transitions on value change, `respectMotionPreference` default true, `Intl.NumberFormat` formatting, `NumberFlowGroup`, `trend` control. https://number-flow.barvian.me/. Best number ticker for KPI tiles.
  - Motion Primitives `animated-number` (`npx motion-primitives@latest add animated-number`, spring via motion). https://motion-primitives.com/docs/animated-number. Their `text-shimmer` and `text-loop` are infinite; skip.
  - Kibo UI (https://www.kibo-ui.com, MIT, `@kibo-ui` namespace): tables, dropzones, AI chat primitives, code block, kanban, gantt. Specific component names not verified in this pass.
  - Origin UI has become "coss ui" (https://originui.com/ui), a Base UI library: Kbd, Meter, Segmented Control, Table, Toast, Sheet, Command, Number Field. The old originui.com/timeline page now redirects there; a timeline component was not found.
  - Vercel AI Elements (https://ai-sdk.dev/elements): conversation, message, tool and reasoning components for AI SDK apps. shadcn states its chat components do not replace them. Not verified in depth.
  - Aceternity, Animate UI, cult/ui, Magic UI (beyond number-ticker): landing-page motion catalogues; mostly infinite effects, not useful here.
- Motion: core shadcn animates with `tw-animate-css` enter/exit classes only; no Framer Motion. Loops exist only in `spinner`, `skeleton`, and the `shimmer` utility.
- Accessibility: Base UI follows ARIA APG patterns and WCAG 2.2 for component behavior (their FAQ); charts expose `accessibilityLayer`; RTL supported since January 2026.

## 6. Cuvii Labs (labs.cuvii.dev)

- Real URL: https://labs.cuvii.dev/ (author Cuvii, x.com/thecuvii, github.com/thecuvii, part of zolplay-labs). Personal site https://cuvii.dev is a placeholder. No "Cuvii Labs" company.
- What it is: a personal lab, "a gallery of signal-inspired interface effects", "lab work I made with AI". Volume 001 "motion" (18 text effects: BLINKY, GLITCH, TRAIL, STROKE_N_FILL, SHUFFLE, CRASH_N_BLINK, SLIDE_N_BLINK, COLOR_FLASH, BUILD_ON, SCALE_N_BLINK, STROKE_N_FADE, SCANNER, TOTAL_RECALL, SLICE_IN, VOLTRON, PORTAL, CHROMA_WIPE, BLIPPITY_ON) and volume 002 "phosphor". Recreations of Jerry Liu's FUI field guide series (Beep Boop, Blip Blip); the site credits him.
- Stack: Next.js site; header says "STACK GSAP · CSS · SVG"; canvas present; hashed keyframes (StyleX-style) on the page. Each card has REPLAY and COPY.
- License and price: free; on-page text "COPY THE CODE. MODIFY IT. USE IT FREELY." No LICENSE file or repository found. Unverified license.
- Install: copy button per effect. No npm, no registry.
- Dark mode: dark only, true black, monospace, teenage-engineering aesthetic. Visually the closest reference for the "editorial dark console" brief.
- Fit for this product: a one-shot text reveal on a heading or status change (BUILD_ON, SLICE_IN, STROKE_N_FILL, SHUFFLE) can carry the editorial feel. Nothing here is a component.
- Motion flags: most effects are by nature blink / glitch / scanner loops. Use only the one-shot reveals and only on state change.
- Accessibility: none stated. Registry JSON: none.

## 7. Radius Browser (radiusbrowser.com)

- Real URL: https://www.radiusbrowser.com/ (YC Fall 2025, founders Quentin Romero Lauro and Michael Klikushin, formerly "Inspector"). Not radix-ui.com, not a border-radius tool.
- What it is: a macOS Chromium-based browser where coding agents (Claude Code, Codex, Cursor Agent) run in tabs next to PRs, diffs, terminals and localhost; spaces per project, tab groups per worktree, `radius tab open ...` CLI. Free; uses your existing agent subscriptions; local-first.
- Stack, install, components: not applicable. It is a developer tool, not a UI library.
- Relevance: none for the frontend. Possible use as a dev workflow tool during the hackathon, macOS only.

---

## Pick list

| Product need | Recommended component | Source | Install |
|---|---|---|---|
| Audio waveform player (call detail) | wavesurfer.js 7.12.12 + `@wavesurfer/react` 1.0.12 (regions + timeline plugins) | npm, BSD-3 | `npm i wavesurfer.js @wavesurfer/react` |
| Voice orb driven by real audio | Matrix Orb (`state`, `level` 0..1) | Rare UI (rareui.com) | `npx shadcn@latest add swamimalode07/rare-ui/matrix-orb` |
| Voice bars if the widget runs on LiveKit | AgentAudioVisualizerBar / Wave | LiveKit Agents UI | `npx shadcn@latest registry add @agents-ui && npx shadcn@latest add @agents-ui/agent-audio-visualizer-bar` |
| Live transcript container | MessageScroller + Message + Bubble + Marker | shadcn/ui | `npx shadcn@latest add message-scroller message bubble marker` |
| Streaming utterance text | Streaming Response, or transitions.dev Streaming text (Pro) | beUI / transitions.dev | `npx shadcn@latest add @beui/streaming-response` |
| Tool-call timeline | Agent Activity + Tool Result; alternative Beautiful UI Thinking + Tool Chips | beUI / Beautiful UI | `npx shadcn@latest add @beui/agent-activity @beui/tool-result` |
| Approval before write | Approval Card / Tool Approval | beUI (or Beautiful UI Approval Card) | `npx shadcn@latest add @beui/tool-approval` |
| Dense data table (evals, results) | Data Table (TanStack Table 9.2.4) | shadcn/ui | `npx shadcn@latest add data-table` |
| Live call board with many rows | beUI Table (virtualized, sortable, sticky header) or shadcn table + `@tanstack/react-virtual` 3.14.13 | beUI / npm | `npx shadcn@latest add @beui/table` |
| Status badges | shadcn `badge`; beUI Animated Badge with `pulse={false}` | shadcn/ui / beUI | `npx shadcn@latest add badge` |
| Charts and sparklines | `chart` (Recharts 3.10.1) | shadcn/ui | `npx shadcn@latest add chart` |
| Number tickers (one-shot) | NumberFlow (`@number-flow/react` 0.6.2); alt beUI DigitSwap | npm / beUI | `npm i @number-flow/react` |
| Command palette | `command` (cmdk 1.1.1) | shadcn/ui | `npx shadcn@latest add command` |
| Resizable panels, split view | `resizable` (react-resizable-panels 4.12.4) | shadcn/ui | `npx shadcn@latest add resizable` |
| Sheet / drawer | `sheet`, `drawer` | shadcn/ui | `npx shadcn@latest add sheet drawer` |
| Toast | `toast` (Base UI) or Sonner 2.0.8 | shadcn/ui | `npx shadcn@latest add toast` |
| Kbd hints | `kbd` | shadcn/ui | `npx shadcn@latest add kbd` |
| Diff view (proposed appointment change) | beUI File Diff; Beautiful UI Diff Table for tabular diffs; `react-diff-viewer-continued` 4.4.0 for text | beUI / Beautiful UI / npm | `npx shadcn@latest add @beui/file-diff` |
| JSON / tree viewer (tool payloads) | `@textea/json-viewer` 4.0.1 or `react18-json-view` 0.2.10; beUI File Tree as a styled shell | npm / beUI | `npm i @textea/json-viewer` |
| Log viewer | beUI Tool Result (terminal output, bounded viewport, collapses) or shadcn `scroll-area` + `scroll-fade` utility | beUI / shadcn | `npx shadcn@latest add @beui/tool-result` |
| Micro transitions (tabs, panels, text swap, number pop-in) | transitions.dev snippets and motion tokens | transitions.dev | `npx transitions-dev add text-states-swap` (skill already installed locally) |
| Editorial one-shot text reveal | BUILD_ON / SLICE_IN | Cuvii Labs | copy from https://labs.cuvii.dev/volume/motion |

---

## Libraries and pieces to avoid, and why

- RareUI at rareui.in: landing-page effects (liquid, glass shimmer, WebGL liquid metal), Framer Motion 12 loops everywhere, own CLI instead of shadcn. Wrong register for a dense console.
- Rare UI Fluid Orb: WebGL loop that runs regardless of audio. Use Matrix Orb with `level` instead.
- beUI Loader, Marquee, Shader Background, Text Animation shimmer, Agent Loading States, Cylinder Carousel, Animated Badge default `pulse` on loading: all continuous.
- shadcn `spinner`, `skeleton`, and the `shimmer` utility: continuous. Use static placeholders and the transitions.dev "skeleton reveal" half only.
- transitions.dev Shimmer text, Organic shimmer, Thinking states, Reasoning stream, Matrix dot loader, Pro gradient text: loops.
- Beautiful UI Loading State, Thinking shimmer header, Prompt Bar `glimm` sweep: loops; also `SelectionActions` has missing private atoms.
- Cuvii Labs blink / glitch / scanner effects: loops by design; and its license is only an on-page sentence.
- Magic UI, Aceternity, Animate UI, cult/ui as wholesale sources: marketing-page motion, infinite by default; take `number-ticker` at most.
- Motion Primitives `text-shimmer`, `text-loop`: infinite.
- LiveKit Agents UI outside a LiveKit session: components require `audioTrack` and `state` from `useAgent`; do not import them for a non-LiveKit widget.
- Radius Browser: not a UI library at all.

---

## Recommended base stack

- shadcn/ui via `shadcn` CLI 4.21.0, Base UI primitives (default since July 2026, `@base-ui/react` 1.8.0), `new-york` style or a preset from shadcn/create with true black `--background: #000` and a burgundy `--primary`; `cn` from the `cn` package. Init: `npx shadcn@latest init -t vite`.
- Tailwind CSS 4.3.3 with `@theme inline` tokens, OKLCH colors, `tw-animate-css` for enter/exit only.
- React 19, TypeScript, Vite.
- Charts: shadcn `chart` over Recharts 3.10.1 with `accessibilityLayer`.
- Tables: shadcn `data-table` (TanStack Table 9.2.4) for evals; `@tanstack/react-virtual` 3.14.13 (or beUI Table which bundles it) for the live board.
- Motion: none as a base. CSS transitions with the transitions.dev token scale (150ms state changes, 200ms popovers, 300ms overlays; easing `cubic-bezier(0.175, 0.885, 0.32, 1.1)` per project standing constraints). `motion` 13.4.0 arrives only as a dependency of the beUI components you install; keep it out of app code.
- Audio: wavesurfer.js 7.12.12 + `@wavesurfer/react` 1.0.12 for recorded calls; Web Audio `AnalyserNode` RMS to drive Matrix Orb `level` for the live widget.
- Numbers: `@number-flow/react` 0.6.2.
- Icons: `lucide-react` 1.47.0 (shadcn default, also used by beUI and Rare UI).
- Palette, drawer, toast, kbd, resizable: shadcn items listed above (cmdk 1.1.1, react-resizable-panels 4.12.4, Sonner 2.0.8 if you prefer it over the Base UI toast).
- Transcript: shadcn `message-scroller` + `marker` for tool activity; beUI Agent Activity / Tool Result for the timeline.

---

## Screenshot index

All files under `frontend/research/screens/components/`, 1440x900, dark color scheme.

- beautiful-ui-home-thinking-streaming.png: Beautiful UI home, Loading State + Thinking (steps trace) demos.
- beautiful-ui-approval-tool-chips-task-rows.png: Approval Card, Tool Chips, Task Rows.
- beautiful-ui-diff-records-table.png: Diff Table and Records Table.
- beui-number-animation.png: beUI Number Animation (DigitSwap) with install command and AI Agents nav.
- beui-virtualized-table.png: beUI Table, 10k virtualized rows.
- beui-animated-badge.png: beUI Animated Badge states.
- rare-ui-components-index.png: rareui.com components index.
- rare-ui-matrix-orb.png: Matrix Orb in "Listening" state with idle / listening / thinking toggle.
- rare-ui-fluid-orb.png: Fluid Orb (WebGL).
- rare-ui-animated-counter.png: Animated Counter.
- transitions-dev-catalogue.png: transitions.dev catalogue top (Card resize, Number pop-in, Notification badge).
- transitions-dev-pro-thinking-states.png: catalogue scrolled to Pro items.
- shadcn-chart-recharts.png: shadcn Chart docs.
- shadcn-message-scroller.png: shadcn MessageScroller docs.
- shadcn-resizable-panels.png: shadcn Resizable docs.
- livekit-agents-ui-audio-visualizer.png: LiveKit Agents UI visualizer docs (bar / grid / radial / wave / aura).
- number-flow-react.png: NumberFlow for React.
- cuvii-labs-signal-effects.png: labs.cuvii.dev index after boot.
- cuvii-labs-volume-motion.png: labs.cuvii.dev volume 001 motion grid (BLINKY, GLITCH, TRAIL, STROKE_N_FILL, SHUFFLE, CRASH_N_BLINK) with COPY buttons.
- radius-browser-home.png: radiusbrowser.com home.

---

## Sources

- https://www.beautifului.dev/ ; https://github.com/ansh/beautiful-ui-registry ; https://github.com/grxtory/beautifului-mirror
- https://beui.dev ; https://beui.dev/components ; https://beui.dev/components/agents ; https://beui.dev/charts ; https://beui.dev/components/motion/number ; https://beui.dev/components/motion/table ; https://beui.dev/components/motion/animated-badge ; https://beui.dev/r/animated-badge.json ; https://beui.dev/r/table.json ; https://pro.beui.dev/ ; https://github.com/starc007/ui-components
- https://www.rareui.com/components ; https://www.rareui.com/components/matrixorb ; https://github.com/swamimalode07/rare-ui (registry.json, LICENSE, public/r/*.json)
- https://rareui.in ; https://github.com/Codewithswappy/RareUI ; https://mintlify.com/Codewithswappy/RareUI/llms.txt ; https://www.npmjs.com/~rareui
- https://transitions.dev/ ; https://github.com/Jakubantalik/transitions.dev ; local skill ~/.claude/skills/transitions-dev/SKILL.md ; npm transitions-dev
- https://ui.shadcn.com/docs/changelog ; /docs/changelog/2026-07-base-ui-default ; /docs/changelog/2026-03-cli-v4 ; /docs/changelog/2026-06-chat-components ; /docs/changelog/2026-07-toast ; /docs/registry ; /docs/registry/namespace ; /docs/directory ; /docs/components/chart ; /docs/tailwind-v4
- https://docs.livekit.io/frontends/agents-ui ; https://docs.livekit.io/frontends/agents-ui/audio-visualizer/prebuilt ; https://github.com/livekit/components-js/blob/main/packages/shadcn/README.md
- https://magicui.design/docs/components/number-ticker ; https://number-flow.barvian.me/ ; https://motion-primitives.com/docs/animated-number ; https://www.kibo-ui.com/docs ; https://originui.com/ui ; https://base-ui.com/
- https://labs.cuvii.dev/ ; https://labs.cuvii.dev/volume/motion ; https://github.com/thecuvii ; https://cuvii.dev
- https://www.radiusbrowser.com/ ; https://www.ycombinator.com/companies/radiusbrowser
- npm registry (versions): shadcn, tailwindcss, @base-ui/react, recharts, motion, wavesurfer.js, @wavesurfer/react, @number-flow/react, @tanstack/react-table, @tanstack/react-virtual, react-resizable-panels, cmdk, sonner, lucide-react, react-diff-viewer-continued, @textea/json-viewer, react18-json-view, @livekit/components-react, liveline, glimm, transitions-dev

---

## Unverified

- transitions.dev: Pro price and the license of the CSS snippets (repo LICENSE returns 404; only the CLI package is confirmed MIT).
- Cuvii Labs: license beyond the on-page "use it freely" sentence; no repository located.
- Beautiful UI: accessibility posture; whether the 21st component (Agent Screen) is copyable; the unofficial registry is a reconstruction, not the author's source.
- beUI: the "117 components" count and exact slugs of the 17 AI Agents items (names read from the site nav; slugs assumed to follow `beui.dev/components/agents/<kebab-name>` as confirmed for tool-result, file-diff, agent-activity). Registry index at `https://beui.dev/r` returned an empty list to curl.
- Rare UI (rareui.com): whether Matrix Orb's idle envelope can be fully disabled; not read from source.
- Kibo UI: specific component names and infinite-animation status.
- coss ui / Origin UI: whether a timeline component still exists anywhere on the site.
- Vercel AI Elements: component list and motion behavior not checked in this pass.
- LiveKit Agents UI: behavior when `audioTrack` is undefined (whether the bars fall back to a loop).
- Magic UI number-ticker: underlying dependency (likely motion `useSpring`) not confirmed.
