"""The console's own server: call log API, and the built frontend when there is one.

    uv run --project . uvicorn app.dashboard:app --port 8000 --reload

Deliberately NOT the Prosper call server (`app/server.py`). That one goes under a public
tunnel during a run; this serves every transcript we hold and stays on localhost.

With `frontend/dist` built, it also serves the pages. Vite rewrites console routes to
`console.html` through a dev-only plugin (`vite.config.ts`), so any other host has to do
the same rewrite — that is what `_page_for` below is.
"""

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.calls_api import router as calls_router

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
CONSOLE_ROUTES = re.compile(r"^/(dashboard|live|calls|calendar|cases|metrics|talk)(/|$)")
DEMO_ROUTE = re.compile(r"^/demo/?$")

app = FastAPI(title="ROSARIO console")

# `pnpm dev` serves the pages from 5173 and proxies /api here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(calls_router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "frontend_built": DIST.is_dir()}


def _page_for(path: str) -> Path:
    if DEMO_ROUTE.match(path):
        return DIST / "demo.html"
    if CONSOLE_ROUTES.match(path):
        return DIST / "console.html"
    return DIST / "index.html"


if DIST.is_dir():
    for name in ("assets", "brand", "tokens", "fonts", "licenses"):
        if (DIST / name).is_dir():
            app.mount(f"/{name}", StaticFiles(directory=DIST / name), name=name)

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        direct = DIST / path
        if path and direct.is_file():
            return FileResponse(direct)
        return FileResponse(_page_for(f"/{path}"))
