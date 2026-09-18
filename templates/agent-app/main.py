"""FastAPI app: a static chat UI + a /chat endpoint backed by the agent loop.

Run it:
    uv run uvicorn main:app --reload

Then open http://127.0.0.1:8000 and chat. Needs ANTHROPIC_API_KEY set in the
environment for live calls; the tests mock the model so they pass with no key.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agent import DEFAULT_MODEL, run_agent
from seed import DEMO_PROMPT

app = FastAPI(title="hack-kit agent-app")

_INDEX_HTML = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    steps: list[dict]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the single-page chat UI."""
    return _INDEX_HTML


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by the demo / verify harness."""
    return {"status": "ok", "model": DEFAULT_MODEL, "demo_prompt": DEMO_PROMPT}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> JSONResponse:
    """Run one turn of the tool-calling agent and return the reply + tool trace."""
    result = run_agent(req.message)
    return JSONResponse(result)
