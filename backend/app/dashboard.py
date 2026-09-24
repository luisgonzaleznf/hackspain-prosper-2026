"""The console's own server: call log API, and the built frontend when there is one.

    uv run --project . uvicorn app.dashboard:app --port 8000 --reload

Deliberately NOT the voice server (`app/server.py`). That one goes under a public tunnel;
this serves every transcript we hold and stays on localhost.

With `frontend/dist` built, it also serves the pages. Vite rewrites console routes to
`console.html` through a dev-only plugin (`vite.config.ts`), so any other host has to do
the same rewrite — that is what `_page_for` below is.
"""

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from integrations.clinic_api import router as clinic_router

from app.calls_api import router as calls_router
from app.ratelimit import RateLimitMiddleware
from app.waitlist import router as waitlist_router

# Console lockdown: every console route serves the waitlist page until this
# flips back. The waitlist API itself stays open.
CONSOLE_LOCKED = os.getenv("CONSOLE_LOCKED", "1") == "1"

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
CONSOLE_ROUTES = re.compile(r"^/(dashboard|live|calls|calendar|metrics|talk)(/|$)")
DEMO_ROUTE = re.compile(r"^/demo/?$")

app = FastAPI(title="ROSARIO console")
app.add_middleware(RateLimitMiddleware)

# `pnpm dev` serves the pages from 5173 and proxies /api here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(waitlist_router)
app.include_router(calls_router)
app.include_router(clinic_router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "frontend_built": DIST.is_dir()}


def _page_for(path: str) -> Path:
    if DEMO_ROUTE.match(path):
        return DIST / "demo.html"
    if path == "/":
        return DIST / "index.html"
    if CONSOLE_LOCKED:
        # The dashboard is closed: console routes and unknown paths serve the
        # static lockdown page. Real files (assets, fonts) still resolve in the
        # caller below.
        return DIST / "waitlist.html"
    # Known console routes and everything unknown: the console renders its own
    # 404 for a mistyped address (frontend/src/screens/not-found.tsx). Only
    # real files and the landing page stay static.
    return DIST / "console.html"


if DIST.is_dir():
    for name in ("assets", "brand", "tokens", "fonts", "licenses"):
        if (DIST / name).is_dir():
            app.mount(f"/{name}", StaticFiles(directory=DIST / name), name=name)

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        direct = (DIST / path).resolve()
        if not direct.is_relative_to(DIST.resolve()):
            raise HTTPException(status_code=404, detail="Not found")
        if path and direct.is_file():
            return FileResponse(direct)
        return FileResponse(_page_for(f"/{path}"))
