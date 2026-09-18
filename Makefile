# hack-kit Makefile — thin wrappers over uv. Run targets from the repo root.
# All commands go through `uv run` so they use the project's local venv.

# App entry point: app.main:app (FastAPI). Override with: make dev APP=app.other:app
APP  ?= app.main:app
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: help preflight dev verify demo new sync

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

sync:  ## Install/update dependencies into the local venv
	uv sync

preflight:  ## Check keys + tooling and do a tiny real model call (GREEN/RED summary)
	uv run python scripts/preflight.py

dev:  ## Boot the FastAPI app on localhost with autoreload
	uv run uvicorn $(APP) --reload --host 127.0.0.1 --port $(PORT)

verify:  ## CI replacement: ruff + mypy + pytest (the /verify skill adds run-the-code checks)
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest

demo:  ## Reminder/entry point for recording the demo — see the /demo skill
	@echo "Run the /demo skill in Claude Code: boot with seed data, drive the golden path, capture a GIF/video into demo/."
	@echo "Demo artifacts live in demo/ . ffmpeg is the capture/encode tool (checked by 'make preflight')."

# Scaffold a new FastAPI app skeleton under app/.  Usage: make new name=myslug
new:  ## Scaffold a minimal FastAPI app under app/ (usage: make new name=<slug>)
	@test -n "$(name)" || { echo "ERROR: pass a name, e.g. 'make new name=triage'"; exit 1; }
	@mkdir -p app tests
	@test -f app/__init__.py || : > app/__init__.py
	@if [ -f app/main.py ]; then \
		echo "app/main.py already exists — not overwriting. Edit it directly."; \
	else \
		printf '%s\n' \
			'"""hack-kit app: $(name). Boot with: make dev"""' \
			'from fastapi import FastAPI' \
			'' \
			'app = FastAPI(title="$(name)")' \
			'' \
			'' \
			'@app.get("/health")' \
			'def health() -> dict[str, str]:' \
			'    return {"status": "ok", "app": "$(name)"}' \
			> app/main.py; \
		echo "Created app/main.py (app: $(name)). Run 'make dev' then open http://127.0.0.1:$(PORT)/health"; \
	fi
