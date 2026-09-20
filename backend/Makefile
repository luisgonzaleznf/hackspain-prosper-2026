# Run every target from this directory. `--project .` uses THIS package's venv and pins;
# `--env-file ../.env` loads the repo-root secrets (PLATFORM_API_KEY, the dashboard cookie).
# PYTHONPATH=. is needed for targets that run a script BY PATH: python puts the script's own
# directory on sys.path, not the package root, so `import app` would fail without it.
UV := uv run --project . --env-file ../.env
UVS := PYTHONPATH=. $(UV)

VOICE ?= codex
PORT  ?= 7860
CONSOLE_PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help serve roleplay-demo console session up down endpoint-status tunnel smoke fake-call replay-call dash verify collect run-audio ledger

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

serve:  ## Prosper call server on ws://0.0.0.0:$(PORT)/ws (VOICE=codex|gptlive|none)
	VOICE=$(VOICE) PORT=$(PORT) $(UV) python -m app.server

roleplay-demo:  ## Role-play Studio: serve, then open http://127.0.0.1:$(PORT)/demo/
	VOICE=$(VOICE) PORT=$(PORT) $(UV) python -m app.server

console:  ## ROSARIO console (call log API + built frontend) on http://127.0.0.1:$(CONSOLE_PORT)
	$(UV) uvicorn app.dashboard:app --port $(CONSOLE_PORT) --reload

session:  ## Connect for ONE run, auto-disconnect when idle: make session VOICE=codex
	scripts/endpoint.sh session $(or $(VOICE),$(error VOICE is required)) $(PORT)

up:  ## Connect the endpoint and wait until Prosper can reach it: make up VOICE=codex
	scripts/endpoint.sh up $(or $(VOICE),$(error VOICE is required)) $(PORT)

down:  ## Disconnect the endpoint (`scripts/endpoint.sh down --all` for everything)
	scripts/endpoint.sh down

endpoint-status:  ## Is the endpoint connected, and can Prosper reach it?
	scripts/endpoint.sh status

dash:  ## Dashboard from the shell: make dash ARGS=status|runs|wait (needs the cookie in ../.env)
	$(UVS) python scripts/prosper_dash.py $(or $(ARGS),status)

tunnel:  ## Raw tunnel (prefer `make session`: stay disconnected unless a run is in progress)
	scripts/tunnel.sh

smoke:  ## Live check: a public case through the real tools + a submit Prosper must accept
	$(UVS) python scripts/smoke_tools.py

fake-call:  ## Fake Prosper call(s) at the local server: make fake-call WAV=caller_8k.wav N=10
	$(UVS) python scripts/fake_caller.py $(WAV) --n $(or $(N),1)

replay-call:  ## Replay a recorded caller (RECORD_CALLER_AUDIO=1): make replay-call WAV=<id>.caller.wav
	$(UVS) python scripts/fake_caller.py $(WAV) --captured --n $(or $(N),1)

verify:  ## ruff + mypy + pytest against THIS package's copy
	$(UV) ruff check app integrations tests scripts
	$(UV) mypy app integrations
	$(UVS) python -m pytest

# ── after a Run All (see README, docs/private-calls/README.md) ──

collect:  ## Gather per-call JSONL from every checkout into logs/calls
	$(UVS) python scripts/collect_calls.py

run-audio:  ## Save the last Run All's Prosper recordings into logs/run_audio/
	$(UVS) python scripts/collect_run_audio.py --last

ledger:  ## Rebuild the call ledger from a fresh dashboard export: make ledger DASHBOARD=path.json
	$(UVS) python scripts/call_ledger.py --dashboard $(or $(DASHBOARD),$(error DASHBOARD=<fresh export>.json))
