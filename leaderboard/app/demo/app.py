"""HTTP and static-file registration for Role-play Studio."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.demo.events import call_log_path, read_projected
from app.demo.models import DemoLedgerEntry, DemoPersona, DemoSnapshot, DemoStartRequest
from app.demo.scenarios import list_scenarios
from app.demo.state import create_session, registry

_STATIC_DIR = Path(__file__).with_name("static")


def _router() -> APIRouter:
    router = APIRouter(prefix="/api/demo", tags=["demo"])

    @router.get("/scenarios", response_model=list[DemoPersona])
    def scenarios() -> list[DemoPersona]:
        return list_scenarios()

    @router.get("/ledger", response_model=list[DemoLedgerEntry])
    def ledger() -> list[DemoLedgerEntry]:
        return registry.ledger()

    @router.put("/sessions/{session_id}", response_model=DemoSnapshot)
    def initialize_session(session_id: str, request: DemoStartRequest) -> DemoSnapshot:
        try:
            return create_session(session_id, request.scenario_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.get("/sessions/{session_id}", response_model=DemoSnapshot)
    def session(session_id: str) -> DemoSnapshot:
        try:
            return registry.get(session_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Demo session not found") from error

    @router.post("/sessions/{session_id}/end", response_model=DemoSnapshot)
    def end_session(session_id: str) -> DemoSnapshot:
        try:
            snapshot = registry.get(session_id)
            # Final evidence is written by the bot after the browser disconnects.
            return snapshot
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Demo session not found") from error

    @router.get("/sessions/{session_id}/trace")
    def trace(session_id: str):
        try:
            path = call_log_path(session_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid session ID") from error
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Call trace not found")
        return FileResponse(path, media_type="application/x-ndjson")

    @router.get("/sessions/{session_id}/audio")
    def audio(session_id: str):
        try:
            call_log_path(session_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid session ID") from error
        path = config.AUDIO_DIR / f"{session_id}.wav"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Recording is not available yet")
        return FileResponse(path, media_type="audio/wav")

    @router.get("/sessions/{session_id}/events")
    async def session_events(
        session_id: str,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        try:
            after = max(0, int(last_event_id or 0))
        except ValueError:
            after = 0

        async def stream():
            cursor, idle = after, 0
            while True:
                events, cursor = read_projected(session_id, cursor)
                for event in events:
                    yield f"id: {event['id']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                if events:
                    idle = 0
                else:
                    idle += 1
                    if idle % 15 == 0:
                        yield ": keepalive\n\n"
                await asyncio.sleep(0.35)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router


def register_demo_routes(app: FastAPI) -> None:
    """Mount demo APIs and UI on an existing Pipecat runner FastAPI application."""
    if getattr(app.state, "demo_routes_registered", False):
        return

    app.include_router(_router())

    @app.get("/demo", include_in_schema=False)
    def demo_index() -> RedirectResponse:
        return RedirectResponse(url="/demo/")

    # check_dir=False lets backend registration happen before a separately owned UI slice lands.
    app.mount("/demo", StaticFiles(directory=_STATIC_DIR, html=True, check_dir=False), name="demo")
    app.state.demo_routes_registered = True
