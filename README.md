# hack-kit

A private GitHub **template** repo you spin up fresh for any hackathon. The domain is unknown until the event starts; the point is to use Claude Code to ship a **real, working, AI-first app fast — in parallel — and keep it correct with no CI and no external review safety net.**

- **Local only.** No Vercel, no Expo, no paid hosting. The app runs on `localhost` and is demoed from your laptop. There is no live URL, so the deliverable is a **recorded GIF/video**.
- **Python-first.** `uv` for env/deps, `ruff` + `mypy` + `pytest` for checks, **FastAPI** for backends. A Vite + React UI is an optional recipe for polish-critical demos.
- **AI-first.** Cloud LLM APIs are fine. Anthropic is primary (`claude-opus-4-8` / `claude-sonnet-4-6` / `claude-haiku-4-5`); optional OpenAI/Gemini fallbacks. Every model call goes through `lib/ai.py`.

The opinionated brain lives in **[`CLAUDE.md`](./CLAUDE.md)** — read it. This README is the operating manual.

---

## The 8-skill flow

Skills live in `.claude/skills/<name>/SKILL.md`. Run them in order:

| # | Skill | What it does |
|---|---|---|
| 1 | `/brainstorm <topic>` | Pick the idea, plan it, split it into non-overlapping slices, and **freeze the shared contracts** (types, API shapes, schema, file ownership) into `CONTRACTS.md`. |
| 2 | `/orchestrate` | Fan slices out to parallel workers (background subagents in worktrees and/or separate terminals); keep the main session lean. First move: confirm contracts are frozen. |
| 3 | `/ship` | Per slice: branch → implement → commit → push → open PR. (The CI/review tail is replaced by `/verify`.) |
| 4 | `/verify` | The CI replacement, local: `ruff`+`mypy`+`pytest`, then adversarial checkers that **run the code** and confirm/refute each claim, then walk the golden path on a clean checkout. |
| 5 | `/solve-merge-conflicts` | Only when parallel branches clash — combine both sides' intent. |
| 6 | `/debug-issue` | Falsify the load-bearing premise, build a timeline, write a repro, fix the root cause. |
| 7 | `/demo` | Boot with deterministic seed data, drive the golden path, capture a GIF/video. |
| 8 | `/pitch` | Write `SUBMISSION.md` + a frontend-design polish pass on the demo screens. |

**Parallelize only past ~4 independent slices.** Below that, go serial.

---

## Per-hackathon quickstart

1. **Use this template** on GitHub → create a new private repo from it, then clone it.
2. **Set up the env and run preflight:**
   ```sh
   cp .env.example .env          # paste your ANTHROPIC_API_KEY
   uv sync                        # install deps into a local venv
   make preflight                 # or: uv run python scripts/preflight.py
   ```
   `preflight` checks your keys (and does a tiny real model call), reports optional keys, checks for `uv` / `python` / `ffmpeg` / `gh`, and prints a GREEN/RED summary. Don't start building until it's green enough.
3. **Brainstorm the topic** (once the hackathon prompt drops):
   ```
   /brainstorm <the hackathon topic>
   ```
   This produces `CONTRACTS.md` with the frozen shared rules and the slice breakdown.
4. **Orchestrate** the build:
   ```
   /orchestrate
   ```
   It confirms `CONTRACTS.md` is frozen, then dispatches slices. Each slice ships via `/ship` and is checked by `/verify`.
5. **Demo and pitch:**
   ```
   /demo
   /pitch
   ```

---

## Make targets

| Target | Does |
|---|---|
| `make preflight` | Run `scripts/preflight.py` (keys + tooling + tiny model call). |
| `make dev` | Boot the FastAPI app on `localhost` with reload. |
| `make verify` | `ruff` + `mypy` + `pytest`. (The full `/verify` skill adds run-the-code checks on top.) |
| `make demo` | Reminder/entry point for recording the demo (see `/demo`). |
| `make new name=<slug>` | Scaffold a new FastAPI app skeleton under `app/`. |

---

## MCP servers (`.mcp.json`)

Lean by design — two servers:

- **context7** — live, current library docs. Reach for this instead of guessing a library's API.
- **claude-in-chrome** — drive and screenshot the running app (used by `/verify` and `/demo`).

> ⚠️ **Launch commands are placeholders.** The `command`/`args` in `.mcp.json` are best-effort and clearly marked. Confirm the exact invocation for your installed versions (e.g. `npx -y @upstash/context7-mcp` for context7) and update `.mcp.json` before relying on these servers. If a server won't start, fix its entry there rather than working around it.

---

## Conventions

- **Model calls go through `lib/ai.py`.** Don't call the Anthropic SDK directly from feature code. Use only the model ids above — never invent ids.
- **Frozen contracts gate parallel work.** No `CONTRACTS.md` → no parallel build.
- **Verify by running, demo from a clean checkout, commit often.** See `CLAUDE.md` for the full posture.
