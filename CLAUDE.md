# hack-kit — the brain

You are building inside **hack-kit**: a private template repo cloned fresh for a hackathon. The domain is unknown until the event starts. Your job is to help a solo dev or small team ship a REAL, working, AI-first app FAST, IN PARALLEL, and KEEP IT CORRECT with no CI and no external review safety net.

Internalize the posture below. It overrides generic habits.

## Posture (non-negotiable)

- **Build real, but ruthlessly scope to the demo.** The only thing that has to work flawlessly is the golden path the judges will see. Everything off that path is a stub. A feature that isn't in the recorded demo does not exist.
- **Freeze the shared rules BEFORE parallelizing.** Types, API shapes, data schema, and file ownership get nailed down in `/brainstorm` and written into `CONTRACTS.md`. Parallel builders who don't share frozen contracts collide and produce garbage. No contract = no parallel work.
- **Parallelize only past ~4 independent slices.** Below that, go serial — coordination overhead and merge conflicts cost more than they save. At 4+ genuinely independent slices, fan out into worktrees/sessions.
- **Verify by RUNNING, never by re-reading a diff.** A change is "done" when the code has been executed and observed doing the right thing — endpoint called, UI driven, output checked against the claim. Re-reading your own diff proves nothing.
- **Demo from a CLEAN checkout.** No uncommitted state. If it only works because of a file you forgot to commit or an env var only in your shell, it doesn't work. The recorded demo runs from what's pushed.
- **Commit often.** Small, frequent commits. A lost hour is fatal at a hackathon; uncommitted work is a lost hour waiting to happen.
- **The recorded demo is the deliverable.** There is no live URL (local-only). What you submit is a GIF/video walking the golden path plus `SUBMISSION.md`. Optimize everything toward producing that artifact.
- **Front-load the wow.** Judges decide in minutes. The first 15 seconds of the demo must show the most impressive, most AI-load-bearing moment. Don't bury the magic behind setup.

## Locked technical decisions

- **Local only.** No Vercel, no Expo, no paid hosting. Apps run on `localhost` and are demoed from the laptop.
- **Cloud LLM APIs are fine.** Anthropic is primary. OpenAI/Gemini are optional fallbacks behind a stub in `lib/ai.py`.
- **Python-first.** `uv` for env/deps, `ruff` + `mypy` + `pytest` for checks, **FastAPI** for backends. A Vite + React UI is a *recipe* you reach for only when the demo is polish-critical — not the default.
- **All model calls go through `lib/ai.py`.** Never `import anthropic` and call the SDK directly from feature code. The wrapper is the one chokepoint for the model id, system prompt, retries, and provider swap.

## Model IDs (do NOT invent ids)

Use only these. They are real even if they look unfamiliar.

| Role | Model ID | Use for |
|---|---|---|
| Heavy reasoning | `claude-opus-4-8` | Planning, hard agentic work, the load-bearing AI feature |
| Default workhorse | `claude-sonnet-4-6` | Most feature calls — good speed/quality balance |
| Cheap & fast | `claude-haiku-4-5` | Classification, extraction, high-volume simple calls |

Thinking: on Opus/Sonnet 4.6+, use `thinking={"type": "adaptive"}` — never `budget_tokens` (it 400s on these models). Control depth with `output_config={"effort": "low|medium|high"}`. Default `max_tokens` to ~16000 non-streaming, ~64000 streaming. Stream anything large.

## Repo layout

```
CLAUDE.md          # this file — the posture/brain
CONTRACTS.md       # written during /brainstorm: frozen types, API shapes, schema, file ownership
README.md          # what the kit is + per-hackathon quickstart
SUBMISSION.md      # fill-in pitch template (the deliverable, with the demo)
pyproject.toml     # uv-managed deps + ruff/mypy/pytest config
Makefile           # preflight / dev / verify / demo / new
.env.example       # ANTHROPIC_API_KEY + optional fallbacks
.mcp.json          # context7 (live docs) + claude-in-chrome (drive/screenshot the app)
.claude/
  settings.json    # pre-allowed safe commands
  skills/<name>/SKILL.md   # the 8-skill harness
lib/
  ai.py            # the ONE Anthropic wrapper — chat/stream/structured/tools + provider swap
scripts/
  preflight.py     # checks keys + tooling, does a tiny real model call, prints GREEN/RED
app/               # your FastAPI app (created per hackathon)
tests/             # pytest
demo/              # recorded GIF/video artifacts (gitignored except the final cut)
```

## The 8-skill harness + flow

Skills live at `.claude/skills/<name>/SKILL.md`. The flow:

1. **`/brainstorm <topic>`** — pick the idea, plan it, and SPLIT it into non-overlapping build slices. FREEZE the shared rules/contracts (types, API shapes, data schema, file ownership) into `CONTRACTS.md` up front so parallel builders never collide.
2. **`/orchestrate`** — hand slices to parallel workers (background subagents in their own git worktrees, and/or separate terminal sessions); keep the main session lean so it never compacts. **Mandatory first move: confirm `CONTRACTS.md` is frozen before dispatching anything.**
3. **`/ship` (a.k.a. quick-pr)** — per slice: branch, implement, commit, push, open PR. The review/CI tail is REPLACED by `/verify`. (No Linear, no Greptile.)
4. **`/verify`** — the CI replacement, local: (1) `ruff` + `mypy` + `pytest`; (2) adversarial checker-agents that ACTUALLY RUN the code and confirm/refute each load-bearing claim with file:line evidence; (3) walk the golden demo path end-to-end on a CLEAN checkout.
5. **`/solve-merge-conflicts`** — only when parallel branches clash; combine both sides' intent, never blindly pick a side.
6. **`/debug-issue`** — when something fails, falsify the load-bearing premise first, build a timeline, write a repro — then fix the root cause, not the symptom.
7. **`/demo`** — record the demo: boot the local app with deterministic seed data, drive the golden path, capture a GIF/video.
8. **`/pitch`** — write `SUBMISSION.md` (problem → demo → how AI is load-bearing → what's next → stack) + a frontend-design polish pass on the demo screens.

## Working rules

- One teammate/worktree per slice. Never two agents editing the same files concurrently.
- Pass context forward: branch names, ports, the contract a slice owns.
- When unsure about a library's current API, fetch live docs via context7 — don't guess.
- When you need to see the app actually work, drive it with claude-in-chrome — don't assert it works from the code.
- If a slice's contract needs to change mid-build, change it in `CONTRACTS.md` first and tell the affected slices. The contract is the source of truth, not any one branch.
