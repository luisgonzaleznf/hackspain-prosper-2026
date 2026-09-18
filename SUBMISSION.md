<!--
  SUBMISSION.md — the deliverable. Fill every section before you submit.
  Judges decide in minutes: lead with the demo and the wow, keep it tight.
  Delete these HTML comments as you go.
-->

# <Project name>

> One-line pitch — what it is and who it's for, in a single sentence.

## The problem

<!-- 2–3 sentences. What's broken / annoying / impossible today? Make it concrete. -->

## The demo

<!-- THE most important section. Drop the recorded GIF/video here.
     The artifact lives in demo/ (e.g. demo/final.gif or demo/final.mp4). -->

![demo](./demo/final.gif)

<!-- Or, if it's a video file:  https://github.com/<you>/<repo>/raw/main/demo/final.mp4 -->

**Golden path shown:** <one line — the exact flow the video walks, start to finish.>

## How AI is load-bearing

<!-- Be specific. NOT "we use AI to help users" — say exactly what the model does
     that nothing else could, where in the flow, and why it's the core of the product.
     Name the model(s) used (claude-opus-4-8 / claude-sonnet-4-6 / claude-haiku-4-5)
     and what each does. -->

- **What the model does:**
- **Where it sits in the flow:**
- **Why it's essential (not a bolt-on):**

## What's next

<!-- 2–4 bullets. What you'd build with another day / week. Shows ambition + that you
     know what's a stub today. -->

-
-

## Tech stack

- **Backend:** FastAPI (Python 3.12), `uv` for env/deps
- **AI:** Anthropic via `lib/ai.py` — `<model id(s) used>`
- **Frontend:** <Vite + React, or "FastAPI-served HTML", or "CLI">
- **Quality:** `ruff` + `mypy` + `pytest`, plus run-the-code verification (`/verify`)
- **Demo:** recorded locally with `ffmpeg` (no live URL — local-only)

## Run it locally

```sh
cp .env.example .env     # add ANTHROPIC_API_KEY
uv sync
make preflight           # green = ready
make dev                 # http://127.0.0.1:8000
```

## Team

<!-- Names / handles. -->
