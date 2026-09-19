# ROSARIO console spec

What the dashboard shows and how it behaves: navigation, call review, scheduling reports and component mapping. The visual contract is `DESIGN.md`; the design linter (`pnpm lint:design`) enforces token use. Historical component sketches below are superseded by the implementation notes here.

Current implementation overrides the older component sketches below:

- No chips, tags, decorative dots or left-side selection stripes. IDs and reason codes are plain mono text; outcomes and stages use icons and text.
- Dropdowns use Base UI Select with token-styled popups, keyboard selection and viewport collision handling.
- Calls use a stereo audiogram, transcript-span track and individually clickable tool/action icons. Peaks come from the actual recording. Selecting an icon seeks and opens its decision; late submissions remain accessible after the audio ends.
- Talk uses the `orb-ui` radial component in controlled mode. Its button plays/pauses recordings or mutes/unmutes the local microphone. Directional levels come from Web Audio, never simulated caller activity. Live calls without an audio feed do not receive amplitude values.
- Browser calling is not connected. Talk offers recorded calls and a local microphone preview, not a telephone session. The old language selector is omitted because it could not change either mode.
- `/` is the landing page. `/metrics` is the dashboard entry; `/dashboard` redirects there. Primary navigation is Overview, Calls, Calendar and Live. `/cases` and `/talk` have a separate tools header with a return to the dashboard.
- The console shell is one viewport tall. Screen headers stay outside their content scroller; split-view lists and drawers scroll independently. Scrollable flex children may shrink below content height. Nested transcript scrolling chains to the outer panel at its edges. Mobile content has bottom clearance for navigation.
- Live transcripts follow new turns only while the reader is within 48px of the bottom. Scrolling up preserves the reading position; returning to the bottom resumes following.
- Light and dark themes share semantic tokens and persist across dashboard/tool routes. The theme switch adapts Magic UI's circular View Transition reveal; reduced motion skips the transition. Navigation and tabs share one moving selection background, measured again when individual controls resize after font or label changes.
- Call review shows the full chat immediately. Playback reveals bubbles at detected speech endings and follows the current turn. Unmatched fragments retain logged timing. Scrolling disables following; pausing restores the full conversation. Clicking a message seeks; clicking a decision opens and scrolls to that exact card, including repeated selections. Only the actual playhead determines the current turn. Tooltips are portaled, kept within the viewport and hidden when their anchor scrolls away.
- Caller-number lookups, canonical tools, legacy proxy steps and complete Codex tool wrappers contribute timeline markers. Matching wrapper echoes are deduplicated one-to-one; truncated payloads are not reconstructed.
- Calendar shows accepted scheduling reports, including practice calls. The clinic API is read-only: acceptance does not reserve or change an appointment. Staged/rejected actions are excluded; changes reconcile by appointment ID within one call. Separate calls remain separate reports.
- Unknown data uses content-shaped skeletons, not zero counts or empty-state claims. Placeholders fade in after 150ms and remain still; cached content does not return to placeholders. Already-loaded records remain usable if an update fails. JSON requests time out after 15 seconds, freeing pending requests for retry.
- Calls load details as rows approach the viewport, including older history. A loading drawer always has a Close button. Rows do not replay entrance animations as data arrives; newly available fields use a short opacity reveal. Reduced motion is immediate.
- The recording frame reserves its waveform and a two-row, internally scrolling decision lane (one row in compact mode). The lane snaps to whole rows, has a contrasting scrollbar and supports keyboard access to every marker. Loading, buffering and cancellation do not move the transcript below it. Audio can be cancelled before playback starts. Audio and waveform retries remain separate, so waveform failure does not block playback or transcript review.
- The call library uses a pinned private GitHub snapshot. From `frontend/`, run `pnpm recordings:import` with authenticated `gh`, `ffprobe` and `ffmpeg` installed. The importer stores logs and Opus files in ignored `.recordings/`; rerunning rebuilds derived data from cached sources. Reload the console after importing. Recordings and credentials are not included in the public repository.
- Caller bubbles use a distinct burgundy fill in dark mode and rose fill in light mode. Both speakers have visible borders; text contrast is above 11:1 in both themes.

Sources, all under `research/`: `nava-brand.md` (palette and type), `refero-style.md` (structure: hairlines, flat depth, one accent, tracked eyebrows), `vapi.md`, `bland.md`, `elevenlabs.md`, `cartesia.md` (console anatomy), `components.md` (parts to use), `quiver.md` (logo generation).

## 1. Brand

**Name.** ROSARIO. Spanish for both the rose garden and the rosary: a loop of beads you move through one at a time. That is a phone call at a front desk: one turn after another, around a fixed loop (greet, identify, look up, offer, confirm, write). The mark should read as a rose from across the room and as a loop of turns when you look closer.

**Voice.** A receptionist who knows you. Short sentences, concrete nouns, no exclamation marks, no marketing adjectives. Spanish domain words stay Spanish (Centro, Norte, Sur, DNI, cita). No em dashes anywhere **[lint]**.

**Where the look comes from.** Copied, not invented. The palette, type treatment and page anatomy are the Nava Labs identity by Wednesday Studio (the red-on-black entry on rebrand.gallery; the gold nava.com site is a different company). Nava's four published colors are Red #FE0600, Fire #BC0400, Black #000000, White #FEFEFE. What makes Nava read red rather than black is that every section sits on a large red radial glow or the red dome texture; copy that. From navalabs.ai: sticky black nav at 86% with blur, centered bold headlines at 80/56px with negative tracking, grey body at 65% white, red gradient pill CTA with an inner highlight, glass cards (#0D0D0D at 80%, 14px blur, white 15% hairline, 24px radius), mono uppercase comparison tables with red check marks, numbered red squares with outlined labels for the timeline, mono chips joined by red dotted connectors. From the Refero Galileo-ft entry: the split hero and the "at a glance" stat block with oversized gradient numerals, pill buttons, generous radii. Reference captures live in `research/screens/refs/` (navalabs.ai sections, the rebrand video montage, the Galileo scroll montage). No eyebrow labels above headings and no status pills or chip rows in UI: those were the parts of the first draft that read as a spec sheet rather than as this brand.

**Logo.** The current mark is `dial-rose-ten` (Marcos has asked for riskier candidates; see the gallery on the brand page): a rotary telephone dial with its ten finger holes (the digits 0 to 9) around a single rose-bud spiral. Phone and rose in one flat silhouette, one color, perfectly circular, legible at 16px. Generated with QuiverAI Arrow 2 Telos, normalized to color from CSS (`brand/logos/marks/dial-rose-ten.svg`). Final assets in `brand/logos/final/`: `mark.svg`, `wordmark.svg` (lowercase Plain Light outlines, no font dependency), `lockup-horizontal.svg`, `lockup-stacked.svg`, favicons 16/32/180/512. Lockups are two-tone: mark in `--accent-ink`, word in `--fg` (set `--logo-word` to change). The other candidates stay on the brand site as alternatives; regenerate with `brand/scripts/quiver-logos.sh` (always `MODEL=arrow-2-telos`) and rebuild assets with `brand/scripts/build-lockups.py <mark.svg>`.

## 2. Color

Black ground, red glow, glass surfaces, a white-to-grey text ladder, one chroma in two tones. Raw values live only in `tokens/tokens.css` **[lint]**.

| Token | Value | Role | Contrast |
|---|---|---|---|
| `--bg` | #000000 | page and table ground | |
| `--surface-1` | #0D0D0D | drawer, panel, hover row | 1.08 vs bg |
| `--surface-2` | #191919 | chip fill, code block, active tab track | 1.19 vs bg |
| `--surface-accent` | #2A0200 | selected row, live call row | 1.11 vs bg |
| `--line-1` | #1A1A1A | structural hairline | |
| `--line-2` | #2A2A2A | emphasized hairline, input border | |
| `--line-accent` | #5C0200 | keyline on the active item | |
| `--fg` | #FEFEFE | primary text | 19.8:1 |
| `--fg-2` | #A6A6A6 | secondary text, column headers | 8.6:1 |
| `--fg-3` | #8A8A8A | meta, timestamps | 6.1:1 |
| `--fg-4` | #6B6B6B | disabled, placeholder only | 3.9:1 |
| `--accent-fill` | #BC0400 | the one filled control per view, active tab, live dot ring | white on it 6.7:1 |
| `--accent-fill-hover` | #D20500 | hover of the above | |
| `--accent-ink` | #FE0600 | accent text, icons, 1px focus ring, link underline, fail | 5.2:1 on bg |
| `--accent-ink-hover` | #FF5141 | hover of the above | 6.5:1 |

Surface and effect tokens (values copied from navalabs.ai CSS):

| Token | Value | Use |
|---|---|---|
| `--card-fill` + `--card-blur` | #0D0D0D at 80%, blur 14px | glass panels and cards |
| `--line-glass` / `--line-glass-soft` | white 15% / 5% | card hairlines, dividers |
| `--glow-card` | 0 0 0 1px white 15% | the card border, drawn as a ring |
| `--glow-cta` | inset 0 2px 2px #FF5141, 0 0 8px red | the primary pill |
| `--glow-ghost` | inset 0 1px 1px #DB8989 at 46% | ghost pills and inputs |
| `--glow-hero` | 0 65px 135px 18px red | hero and section bleed |
| `--gradient-cta` / `--gradient-cta-hover` | #E60300 to #AA0400 / #FF0300 to #DA0500 | primary pill fill |
| `--gradient-section` | red radial to transparent | the "how it works" band |
| `--gradient-hero-fade`, `--gradient-hero-mask`, `--gradient-card`, `--gradient-orb`, `--gradient-numeral` | see tokens.css | hero, cards, icon discs, stat numerals |
| `--fill-chip`, `--fill-input`, `--fill-step`, `--fill-note`, `--fill-nav`, `--dome-dark` | translucent blacks and reds | chips, inputs, timeline, nav, dome texture |

Rules:
- Red is used the way Nava uses it: as the ground's glow (hero texture, section radial), as the one gradient pill per view, as check marks, timeline squares and mark. Text stays white and grey.
- Fill and ink are a pair. Red text never sits on the red fill.
- Status is neutral by default. Red means attention (live, failed, blocked). Pass is a red check glyph on white text like Nava's table; no is a grey cross. There is no green.
- Effects come from the tokens above, never ad hoc **[lint]**: no hand-typed shadows, blurs or gradients in components.
- Tailwind palette classes (`bg-zinc-800`, `text-red-500`), literal `bg-white`/`text-black`, hex, `rgb()`, `hsl()` and arbitrary color values are errors in TSX **[lint]**. Use the token utilities the app theme maps from these variables.

## 3. Typography

| Token | Family | Stands in for | Use |
|---|---|---|---|
| `--font-sans` | Plain (Optimo), Hairline 100 to Medium 500, fetched per the design brief; commercial, license before public use | the face DESIGN.md names | everything that is prose or UI |
| `--font-mono` | Iosevka Fixed 400 / 500 / 600 (OFL) | Muoto Mono | ids, tool names, reason codes, slots, latencies, costs, eyebrow labels |
| `--font-display` | alias of sans | | hero and stat numerals |

Self-hosted from `fonts/` (downloaded with `moji`). No runtime font requests. Raw `font-family` values outside `tokens.css` are errors **[lint]**.

Scale (px / line-height / weight / tracking):

| Role | Size | Leading | Weight | Tracking |
|---|---|---|---|---|
| display (brand site only) | 80 | 1.0 | 700 | -0.03em |
| h1 console | 28 | 1.2 | 700 | -0.02em |
| h2 | 20 | 1.2 | 700 | -0.02em |
| h3 / stat label | 16 | 1.4 | 500 | 0 |
| body | 14 | 1.5 | 400 | 0 |
| ui default, table body | 13 | 1.4 | 400 | 0 |
| meta | 12 | 1.4 | 400 | 0 |
| mono chip, eyebrow | 11 or 12 | 1.2 | 500 | +0.12em, uppercase |
| stat numeral | 40 or 56 | 1.0 | 700 | -0.03em, tabular |

Rules:
- Headings are 700 with negative tracking (Nava's treatment). Body is 400. Medium 500 for buttons and key table cells. Never 800 or 900 **[lint]**.
- Numbers that line up (times, durations, ms, costs, counts) use `font-variant-numeric: tabular-nums`.
- No eyebrow labels above headings. A section is a headline plus a grey lede, centered, like Nava's.
- Mono uppercase with +0.08em tracking is for machine text and Nava-style comparison tables: ids, tool names, reason codes, slots, latencies, table cells. Reason codes render verbatim plus a short gloss in sans.

## 4. Space, radius, borders

- 4px grid: 4, 8, 12, 16, 20, 24, 32, 48, 64, 96.
- Row height 36px in tables; cell padding 8px 12px; panel padding 16px; page gutter 24px.
- Radius, copied from Nava: `--radius-control` 8px (chips, timeline squares, code tags), `--radius-panel` 16px (swatches, drawers), `--radius-card` 24px (glass cards, hero panel, tiles), `--radius-pill` (buttons, inputs). `rounded-4xl` is an error **[lint]**.
- Borders are white at 5% or 15% (`--line-glass-soft`, `--line-glass`), drawn as a 1px ring (`--glow-card`) on glass fills. Table rows have no rules; spacing separates them (Nava's comparison table).
- Selection uses a neutral surface fill without an inset left rule. Live rows use `--fill-row-live`.
- Links: plain white, grey on hover (Nava nav). No underline.
- Focus: 1px `--accent-ink` outline, 3px offset. Never remove it.

## 5. Motion

- Motion explains a state change: navigation selection, theme, chart series, incoming message or drawer.
- Tokens cover 150ms feedback, 200ms popovers, 300ms overlays, 350ms selection/reveals and a 500ms theme reveal. Reduced motion collapses these. JavaScript reading CSS durations handles both `ms` and minified `s` units.
- No decorative looping animation. Liveness comes from elapsed time and new transcript turns; status is an icon and text.
- The one continuously moving element is the voice orb, and it moves only with real audio levels (section 7.5). When no audio flows it is still. Nava's 15s marquee and 50s ambient spin are not copied.
- The hero dome texture is drawn once on a canvas (`brand/brand.js`) from the tokens and redrawn only on resize.

## 6. Components

Copied from navalabs.ai; shadcn/ui (Base UI) primitives restyled through the tokens. Brand page previews in `brand/index.html` are the reference implementation.

| Part | Spec |
|---|---|
| Primary pill | `--gradient-cta` fill, `--glow-cta`, white 700 at 15px with +0.3px tracking, 44px tall, 22px x padding, trailing chevron. One per view. |
| Ghost pill | `--fill-input`, `--glow-ghost` plus a 1px `--line-input` ring, white label, same geometry. |
| Glass card | `--card-fill`, `--card-blur`, `--glow-card` ring, 24px radius, 32 to 36px padding; title 20px 700, body 16px `--fg-2`. Cards in a row share edges and paddings. |
| Hero panel | glass card with a header row (mark + mono label), a flow row of mono chips joined by red double-line connectors on `--gradient-card`, and a footer with a ghost pill input and the primary pill. |
| Mono chip | `--fill-chip`, 10px radius, 12px mono, +0.06em tracking, white or `--fg-2`. Used for ids, tool names, reason codes, slots. Never as a status badge. |
| Comparison table | mono uppercase 12px +0.08em, grey headers with no fill, group label column, red check for yes (white text), grey cross for no (`--fg-4`), no row rules. |
| Timeline step | red 36px square with the step number, outlined red 8px-radius label beside it, dotted red connector before it, mono code chip below on `--fill-step`, note on `--fill-note`. |
| Stat block | 120px gradient numerals (`--gradient-numeral`, background-clip text), 18px grey label, cells divided by `--line-glass-soft`. |
| Nav | 82px, `--fill-nav` with blur, lockup left (mark 30px + lowercase word 26px 700), links 16px, primary pill right. |
| Data table (console) | 13px sans body, 36px rows, no rules, hover `--surface-1`, selection inset left rule, numeric columns tabular. Column headers in mono uppercase grey like the comparison table. |
| Transcript turn | single column, speaker in mono uppercase grey in a 72px gutter, 14px body, timestamps right in 12px mono. Interrupted turns end with a grey "cut off" in mono. |
| Decision card | glass card at 16px radius between turns: mono header (kind, tool, latency), key-value grid in mono. Red left rule when it is a refusal, guard block or error. |
| Waveform | two lanes, ROSARIO above in `--accent-ink`, caller below in `--fg-2`, inside a glass card. Markers as in Bland: decisions white, submit red, interruption red tick. |
| Orb (Talk) | disc `--accent-fill` on `--gradient-orb` with `--glow-orb`; ring `--line-accent`. Ring scales with ROSARIO's level, disc with the caller's. |
| Toast | glass card 16px radius, bottom right, 300ms. |
| Empty state | one grey sentence. No illustrations. |

Not used anywhere: eyebrow labels, status pills, chip rows as decoration, light-grey subtitle lines.

## 7. Screens

### 7.1 Information architecture

Primary navigation uses a collapsible desktop rail and a four-item mobile bar:

| Screen | Route | Purpose |
|---|---|---|
| Overview | `/metrics` | Reception activity, reported bookings, duration and response gap |
| Calls | `/calls` | Search/filter recordings and review each conversation |
| Calendar | `/calendar` | Accepted scheduling reports by appointment date |
| Live | `/live` | Current calls, with explicitly labeled recording replays |

Rehearsal (`/cases`) and the voice demo (`/talk`) live outside the dashboard in a separate tools shell. The landing-page footer links to both.

### 7.2 Live board

Reception staff can inspect current calls and their decisions. Recorded replays are labeled as replay.

```
LIVE                                              3 active · 10 queued
──────────────────────────────────────────────────────────────────────
● 00:42  +34 612 ··· 678  Marta Ruiz Sáez  P00042   OFFERING   book ×1   1.2s
● 01:17  withheld          identifying…    —        IDENTIFY   —          0.9s
● 00:08  +34 699 ··· 120  (4 matches)      —        IDENTIFY   —          —
──────────────────────────────────────────────────────────────────────
[row click] → drawer: live transcript + decision cards streaming, pending
actions list, patient brief, engine seconds and spend, "Report" preview of
what would be submitted right now.
```

Rows show elapsed time, caller, conversation strip, stage and recorded per-call median response gap. Replay withholds the completed-call metric until the timeline ends. Unknown identity stays unknown until a lookup supplies it. Selecting a call opens its conversation and recorded context.

Data comes from the calls index and per-call details. The index polls every four seconds; active details refresh every 1.5 seconds. Overlapping index requests share one response, and unchanged polls do not restart detail loading. The backend does not expose an event stream.

### 7.3 Calls

The call list shows time, caller, conversation strip, outcome, duration and recorded per-call median response gap (p50 gap). Quick filters and call-ID search narrow the list. Challenge attribution stays out of the primary review surface.

The drawer places decision icons above the stereo audiogram and caller/ROSARIO chat below it. Its tabs are Transcript, Report, Patient and Raw. Report retains submitted actions, replies and recorded metadata; Patient is read-only lookup data. Full chat is available before playback. During playback, turns appear at detected speech endings, with frame updates at message boundaries rather than waiting for the next media timeupdate. Unmatched fragments retain logged timing; Raw keeps original timestamps. Scrolling or pausing restores full review; a message seeks the player. A marker switches to Transcript, clears search and opens its exact decision card, scrolling the transcript pane on desktop or the drawer on mobile.

### 7.4 Cases

```
CASES                                          Run All ▸   last run 21:14 · 31/49
──────────────────────────────────────────────────────────────────────────────
#   PROBLEM               W   OPEN   PUBLIC              LAST RUN
1   simple_booking        1   yes    ✓ ✓ ✓ ✓             4/4
3   doctor_and_site       2   yes    ✓ ✓ ✗ ✓ ·           3/4  record_mismatch
6   the_rules             3   no     · · · · ·           —
…
```

One row per problem (weight, open state), one glyph per public case (pass, fail, not run), last Run All fraction and failure signal. Click a case glyph: its persona prompt, expected actions, last transcript link, "Call" button (practice, 30s cooldown shown as a countdown in mono). Run All status line with the 15 minute cooldown. This screen is the eval story for the jury.

### 7.5 Talk

The separate voice-demo page uses the `orb-ui` radial orb with actual recording or local-microphone levels. Recordings have the same audiogram and chat as call review. The orb button plays/pauses a recording or mutes/unmutes microphone preview. Browser telephone calling is not connected, and the page says so.

### 7.6 Patients

Drawer opened from any patient chip: name, `patient_id`, DNI masked, date of birth, plans (policy chips), the record `note` verbatim (this is the "clinic knows who is calling" material), past visits and upcoming appointments as a hairline list, past calls to ROSARIO. Read only.

### 7.7 Overview

Four metrics show handled calls, accepted booking reports, average call duration and median response gap. Ranges are 24 hours, seven days and all recorded calls. The activity chart switches between calls, booking reports and average duration; reported outcomes and recent conversations provide context.

Completed-call counts and durations come from the index. Booking reports and response gaps use up to 60 recent completed-call details, with coverage shown. Response gap is the median of the available `audio.timeline.turns.latency_p50_s` values: recorded per-call medians, not pooled individual responses. Missing measurements stay unknown and are excluded, not counted as zero. Only accepted BOOK actions count as booking reports; moves, cancellations and registrations are separate. Accepted reports do not prove a clinic diary mutation.

Details load in batches of four. Sample-based statistics appear progressively with an explicit partial-sample count and progress bar. Changing range cancels future batches; cached values remain visible. Failed details can be retried without losing the usable sample. A concise sample/read-only note remains; the methodology dropdown is removed.

### 7.8 Calendar

Month navigation and Today select appointment dates in Europe/Madrid. A selected-day agenda shows patient/caller, time, provider/site where recorded, and the source call. Undated reports remain separate. Initial selection chooses a date as soon as recorded activity arrives, without overriding a date the reader selected. Details load in batches of four, prioritizing calls whose summary reports scheduling activity while still reading the full history. Counts remain explicitly partial until loading finishes. Leaving the screen cancels future batches.

Only successful scheduling submissions appear. Identical retries within one call are deduplicated; appointment IDs link same-call changes and cancellations. Practice scenarios do not mutate the clinic, so separate calls are not merged into a fictional current diary. A short read-only notice stays above the calendar without a second provenance disclosure.

## 8. Copy rules

- Labels are nouns, buttons are verbs, both short: "Run All", "Call", "Start call", "End", "Copy id".
- Times in Europe/Madrid, 24h, `HH:MM` for wall clock, `+ss.s` for offsets, `1m 42s` for durations under an hour, `312 ms` for latencies.
- Reason codes verbatim in mono (`provider_on_leave`) with the gloss beside them ("provider on leave"). Never rephrase the code.
- Numbers of people: "4 matches", not "multiple".
- Errors say what happened and what to do next: "Clinic API timed out. Retrying in 2s."

## 9. What the linter checks

| Rule | Where | Catches |
|---|---|---|
| `design/no-raw-color` | TS/TSX | hex, rgb/hsl/oklch, Tailwind palette classes, bg-white/black, arbitrary color values |
| `design/no-infinite-motion` | TS/TSX | animate-spin/pulse/ping/bounce, `infinite`, `repeat: Infinity` |
| `design/no-decorative-chrome` | TS/TSX | ad-hoc shadow-*, drop-shadow, blur-*, gradient utilities, rounded-4xl (use the glow, gradient and radius tokens) |
| `design/no-raw-font` | TS/TSX | `font-[…]`, font-serif, inline font-family |
| `design/no-em-dash` | TS/TSX | U+2014 in strings and JSX text |
| `design/no-inline-style-tokens` | TS/TSX | inline `style` color/font/shadow/animation values that are not `var(--…)` |
| Stylelint | CSS | hex and named colors outside tokens.css, non-variable color/font-family/background, `infinite`, drop-shadow, box-shadow and backdrop-filter other than none/inset/var(), weights 800+, em dash in `content`, underline |

The linter does not check density, hierarchy or copy. Those are reviewed by eye against sections 6 to 8 before a screen is called done.

## 10. Decisions taken

1. Mark: `dial-rose-ten` (section 1). Alternatives remain on the brand site; swapping is one `build-lockups.py` run.
2. Accent: Nava's exact pair, #BC0400 fill and #FE0600 ink, as the brief specified. A truer wine is a one-token edit in `tokens.css`; recheck contrast if changed.
3. Status color: monochrome plus red. No green token until the cases board proves unreadable to judges.
