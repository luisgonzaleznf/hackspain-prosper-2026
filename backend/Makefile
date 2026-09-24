# Run every target from this directory. `--project .` uses THIS package's venv and pins;
# `--env-file ../.env` loads the repo-root secrets (voice, Twilio and email keys).
# PYTHONPATH=. is needed for targets that run a script BY PATH: python puts the script's own
# directory on sys.path, not the package root, so `import app` would fail without it.
UV := uv run --project . --env-file ../.env
UVS := PYTHONPATH=. $(UV)

VOICE ?= codex
PORT  ?= 7860
CONSOLE_PORT ?= 8000

.DEFAULT_GOAL := help
.PHONY: help serve roleplay-demo console seed tunnel verify

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

serve:  ## Voice server (Twilio webhook + media stream) on :$(PORT) (VOICE=codex|gptlive|none)
	VOICE=$(VOICE) PORT=$(PORT) $(UV) python -m app.server

roleplay-demo:  ## Browser GPT-Live with local bookings; pair with the frontend demo proxy
	$(UV) python -m app.demo.bot --host 127.0.0.1 --port $(PORT) --transport webrtc

console:  ## ROSARIO console (call log API + built frontend) on http://127.0.0.1:$(CONSOLE_PORT)
	$(UV) uvicorn app.dashboard:app --port $(CONSOLE_PORT) --reload

seed:  ## (Re)build the clinic DB: ~3000 patients, 4 dense weeks + tail. ANCHOR=YYYY-MM-DD PATIENTS=N; wipes local bookings
	PYTHONPATH=. uv run --project . python scripts/seed_clinic.py --force $(if $(ANCHOR),--anchor $(ANCHOR)) $(if $(PATIENTS),--patients $(PATIENTS))

tunnel:  ## Public tunnel to the local voice server (Twilio webhook)
	scripts/tunnel.sh

verify:  ## ruff + mypy + pytest against THIS package's copy
	$(UV) ruff check app integrations tests scripts
	$(UV) mypy app integrations
	$(UVS) python -m pytest
