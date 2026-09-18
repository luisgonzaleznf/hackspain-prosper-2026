---
name: demo
description: Record the demo. There's no live URL — the recorded artifact IS the deliverable. Boot the local app with deterministic seed data, drive the golden path in Chrome capturing extra frames before/after each action, and emit a shareable GIF (and optional narrated MP4). Use when asked to "record the demo", "make the GIF/video", or "capture the golden path".
argument-hint: "[golden-path-name | url | --mp4]"
---

## What this does

There is **no live URL** for a hack-kit app — it runs on localhost and is demoed from the laptop. So the demo deliverable is a **recorded artifact**: a GIF (always) and optionally a narrated MP4. Judges watch in seconds, so the recording must boot clean, run deterministically, and front-load the wow.

This skill: (1) boots the local app on **deterministic seed data**, (2) drives the **golden demo path** in Chrome via the `claude-in-chrome` tools, capturing extra frames around each action, (3) stitches a GIF, and (4) optionally renders a narrated MP4 with a zero-dependency macOS pipeline. Output: a shareable artifact + its absolute path.

## When to run

- After `/verify` is green on the golden path. **Never record a broken or half-built path** — the recording is what judges see.
- Demo from a **clean checkout with no uncommitted state** (per CLAUDE.md posture). If `git status` is dirty, commit or stash first, then record.

## Inputs

- `$ARGUMENTS` may name a golden path (matches a target in the Makefile / `recipes/`), a URL to drive, or `--mp4` to also produce the narrated video. If empty, infer the single golden path from the repo (README "Demo" section, `make demo`, or the first FastAPI route / Vite page).

## Steps

### 1. Boot the app on deterministic seed data

The recording must be reproducible frame-for-frame, so seed data must be **fixed, not random** (pin any RNG seed, freeze timestamps, stub any live external calls; LLM calls that must run should use a low/zero temperature).

1. Look for a one-command boot, in this order:
   - `make demo` (preferred — should seed + boot in one shot)
   - `make seed && make run` / `make dev`
   - a script in `scripts/` (e.g. `scripts/demo.sh`, `scripts/seed.py`)
   - fallback: `uv run uvicorn app.main:app --port 8000` for a FastAPI backend, and `npm run dev` (or `yarn dev`) for a Vite UI.
2. **If no deterministic seed exists, create the smallest one that makes the golden path sing** and wire it into a `make demo` target so the next person gets it free. Write the seed to `scripts/seed_demo.py` (or `recipes/`), keep it tiny, and make `make demo` call it before boot. Re-run to confirm the SAME state appears twice.
3. Run the boot command in the **background** so it stays up across turns. Poll the health endpoint / page until it serves (don't foreground-`sleep`), and capture the URL + port.

### 2. Load the Chrome tools

Browser tools are deferred. Load the recording set in ONE call:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__gif_creator,mcp__claude-in-chrome__tabs_create_mcp"
```

Then `tabs_context_mcp` to attach to the live browser. Resize the window to a **clean, fixed recording size** (e.g. 1280×800) so every run frames identically and text is legible at thumbnail scale.

### 3. Drive the golden path, capturing extra frames

Walk the **single golden path** end-to-end — the one load-bearing flow that proves the app and shows the AI doing real work. Keep it short; cut anything that isn't the wow.

For each action in the path:
1. Capture a frame with `gif_creator` **before** the action (resting state).
2. Perform the action with `computer` / `navigate` (click, type, submit).
3. **Wait for the result to fully settle** — AI/LLM responses stream in, so poll `read_page` until the output is complete before grabbing the next frame.
4. Capture **1–2 extra frames after** the action so the GIF lingers on the payoff (AI output on screen) instead of flashing past it.

Rules:
- Front-load the wow: the AI's visible output should appear within the **first few seconds** of the GIF.
- Type at a human-readable pace; let streaming output land before moving on.
- If the path stalls or errors, **stop** — don't record a broken run. Hand off to `/debug-issue`, fix, re-verify, then re-record.

### 4. Stitch the GIF

Use `gif_creator` to assemble the captured frames into a single GIF.

- Target a **shareable size** — keep it small enough to drop into `SUBMISSION.md` and a chat (aim for a few MB, well under ~15s). Trim dead frames; hold longer on the AI payoff.
- Save to a stable path: `docs/demo.gif` (create `docs/` if needed). This is the path `/pitch` embeds.
- If frames are too heavy, downscale or drop the frame rate rather than truncating the golden path.

### 5. (Optional) Narrated MP4 — zero-dependency macOS pipeline

Only when asked (`--mp4`) or when a voiceover materially helps. The **no-dependency option** is macOS `say` + `ffmpeg`:

1. Write a tight ~20–30s VO script (one line per golden-path beat — problem, the action, the AI payoff).
2. TTS to audio with the built-in macOS voice:
   ```
   say -v Samantha -o /tmp/demo_vo.aiff -f scripts/vo.txt
   ```
3. Convert the GIF to a video and mux the narration with `ffmpeg`:
   ```
   ffmpeg -y -i docs/demo.gif -i /tmp/demo_vo.aiff \
     -movflags +faststart -pix_fmt yuv420p -shortest docs/demo.mp4
   ```
   (Pad/trim with `-t` so audio and video end together.)
4. If `ffmpeg` isn't installed, surface `brew install ffmpeg` as the one prereq and fall back to delivering the GIF alone — never block the deliverable on the optional MP4.

### 6. Deliver

- Tear down the background app process if you started it.
- Report the **absolute path(s)** to the artifact(s) and a one-line "what the GIF shows".
- If `/pitch` runs next, it will embed `docs/demo.gif` directly.

## Output

- `docs/demo.gif` — always.
- `docs/demo.mp4` — when `--mp4`.
- The absolute path(s), printed for the user to drop into the submission / share.

## Don'ts

- Don't record from a dirty tree or with random/un-seeded data — it won't reproduce.
- Don't record a path that `/verify` hasn't confirmed runs.
- Don't bury the AI payoff late in the GIF — judges decide in seconds.
- Don't add cloud video services or paid tools — local only (macOS `say` + `ffmpeg`).
