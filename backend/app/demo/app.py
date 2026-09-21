"""HTTP and static-file registration for Role-play Studio."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app import config
from app.demo.events import call_log_path, read_projected
from app.demo.models import DemoLedgerEntry, DemoPersona, DemoSnapshot, DemoStartRequest
from app.demo.scenarios import list_scenarios
from app.demo.settings import load_settings, save_settings
from app.demo.state import create_session, registry
from app.voice.codex.settings import SettingsCatalogue, VoiceSettings

_STATIC_DIR = Path(__file__).with_name("static")


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or parsed.path or parsed.query or parsed.fragment
    ):
        raise ValueError("Invalid origin")
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def _check_settings_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    fetch_site = request.headers.get("sec-fetch-site")
    allowed = fetch_site != "cross-site"
    if origin:
        # The same-origin development proxy forwards the browser-facing host and scheme.
        host = request.headers.get("x-forwarded-host", request.headers.get("host", "")).split(",")[0].strip()
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
        try:
            allowed = allowed and _origin(origin) == _origin(f"{scheme}://{host}")
        except ValueError:
            allowed = False
    elif fetch_site not in {None, "none", "same-origin"}:
        allowed = False
    if not allowed:
        raise HTTPException(status_code=403, detail="Save settings from the Studio's own page")


def _router() -> APIRouter:
    router = APIRouter(prefix="/api/demo", tags=["demo"])

    @router.get("/settings", response_model=SettingsCatalogue)
    def settings() -> SettingsCatalogue:
        try:
            return SettingsCatalogue(settings=load_settings())
        except (OSError, ValidationError) as error:
            raise HTTPException(
                status_code=503,
                detail="Saved voice settings could not be loaded. Check the server's settings file.",
            ) from error

    @router.put("/settings", response_model=VoiceSettings)
    def update_settings(settings: VoiceSettings, request: Request) -> VoiceSettings:
        _check_settings_origin(request)
        try:
            return save_settings(settings)
        except OSError as error:
            raise HTTPException(
                status_code=503,
                detail="Voice settings could not be saved. Check server storage and try again.",
            ) from error

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

    @app.middleware("http")
    async def no_cache_settings(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.rstrip("/") == "/api/demo/settings":
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(_router())

    @app.get("/demo", include_in_schema=False)
    def demo_index() -> RedirectResponse:
        return RedirectResponse(url="/demo/")

    # check_dir=False lets backend registration happen before a separately owned UI slice lands.
    app.mount("/demo", StaticFiles(directory=_STATIC_DIR, html=True, check_dir=False), name="demo")
    app.state.demo_routes_registered = True
