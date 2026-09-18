---
name: pitch
description: Write SUBMISSION.md FROM the actual repo state — problem → the demo (embed the GIF) → how AI is load-bearing → what's next → stack — tight enough that a judge reads it in 60 seconds. Then offer a frontend-design polish pass on the 2–3 demo screens. Use when asked to "write the submission", "pitch it", or "prep the judges' README".
argument-hint: "[one-line-problem-or-hook]"
---

## What this does

Judges decide in **minutes**, often reading the submission in **~60 seconds** before they even watch the demo. So `SUBMISSION.md` must be short, scannable, and **front-load the wow**. This skill generates it **from the real repo state** (not aspirations), embeds the recorded demo GIF, makes crystal-clear **how the AI is load-bearing**, and ends with an optional design-polish pass on the demo screens.

## Inputs

- `$ARGUMENTS` may carry a one-line hook / problem statement. If empty, derive it from the README, `CLAUDE.md`, or the brainstorm notes.
- Requires the demo artifact from `/demo` (`docs/demo.gif`). If it's missing, **run `/demo` first** — the embedded GIF is the centerpiece.

## Steps

### 1. Read the actual repo state — don't invent

Ground every claim in what's really there:
- `git log --oneline` and the README for what got built.
- `lib/ai.py` (and callers) to see **which model is wired and where the AI decision lives** — this is what makes the "load-bearing AI" section honest.
- The FastAPI routes / Vite pages for the real feature surface.
- `pyproject.toml` / `package.json` for the **actual stack** (versions, deps) — list what's used, not what's fashionable.
- `docs/demo.gif` (and `docs/demo.mp4` if present) for the demo embed.

If a claim isn't backed by the repo, **cut it**. Don't describe features that aren't wired.

### 2. Write SUBMISSION.md (this exact spine, kept tight)

Write `/Users/luis/Desktop/GitHub/hack-kit/SUBMISSION.md` with these sections, in order. Total length: skimmable in ~60s — short paragraphs, tight bullets, no filler.

1. **Title + one-line hook** — the project name and a single sentence a judge remembers. Lead with the wow.
2. **Problem** — 2–3 sentences. Who hurts, why it matters now. No preamble.
3. **The demo** — embed the GIF immediately so it renders inline:
   ```markdown
   ![demo](docs/demo.gif)
   ```
   Add one line on what the GIF shows + how to run it locally (`make demo`, the localhost URL). Link `docs/demo.mp4` if it exists. Remember: **there's no live URL** — the recording is the proof.
4. **How AI is load-bearing** — the most important section. Name the **model id** (from `lib/ai.py`: `claude-opus-4-8` / `claude-sonnet-4-6` / `claude-haiku-4-5` — never invent ids), point to the exact place the AI makes the decision, and state plainly **why the app doesn't work without it** (i.e. the AI isn't a garnish on a CRUD app). One tight paragraph or 3–4 bullets.
5. **What's next** — 3 bullets. Honest near-term roadmap; signals you know the gaps.
6. **Stack** — a compact list pulled from the real manifests: language/runtime, FastAPI (+ Vite/React if used), uv, ruff/mypy/pytest, the AI provider/model. One line each.

Style: confident, concrete, zero marketing fluff. Prefer verbs and specifics over adjectives. If you can't demo it, don't claim it.

### 3. Offer the frontend-design polish pass

After writing the submission, **offer** (don't force) a visual polish pass on the **2–3 screens that actually appear in the demo GIF** — the only screens judges see. Invoke the global **`/frontend-design`** skill for this, scoped to those screens, so the polish lands where the wow is:

- Identify the 2–3 demo screens (the pages the golden path touches).
- Run `/frontend-design` to lift them out of generic-AI aesthetic — typography, spacing, hierarchy, a distinctive but legible look that reads at thumbnail scale.
- **Re-record after polishing**: any visual change means the GIF is stale — re-run `/demo` so the embedded artifact matches, then the submission is consistent.

Keep this scoped to demo screens only — don't redesign surfaces no judge will see.

## Output

- `/Users/luis/Desktop/GitHub/hack-kit/SUBMISSION.md` — judge-ready, GIF embedded, ~60s read.
- The absolute path, printed.
- If the design pass ran: the polished screens + a re-recorded `docs/demo.gif`.

## Don'ts

- Don't write claims the repo doesn't back — judges (and `/verify`) will catch it.
- Don't bury the demo or the AI section below the fold; front-load both.
- Don't invent model ids — read them from `lib/ai.py`.
- Don't polish (or describe) screens that aren't in the demo.
- Don't leave a stale GIF after a design change — re-record.
