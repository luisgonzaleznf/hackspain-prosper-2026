"""Waitlist for the console lockdown: sign up while the dashboard is offline.

Storage: `WAITLIST_DB_PATH` (default logs/demo/waitlist.sqlite3), one table,
email unique. When `RESEND_AUDIENCE_ID` is set, the address is also added to
that Resend audience so the eventual launch email is one broadcast.
"""

from __future__ import annotations

import asyncio
import os
import re
import sqlite3
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


def _db_path() -> Path:
    return Path(os.getenv("WAITLIST_DB_PATH", str(config.CALLS_DIR.parent / "demo" / "waitlist.sqlite3")))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS waitlist ("
        "email TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    return con


def _add_to_resend_audience(email: str) -> None:
    """Best-effort audience add; the local row is the source of truth."""
    key = os.getenv("RESEND_API_KEY", "")
    audience = os.getenv("RESEND_AUDIENCE_ID", "")
    if not key or not audience:
        return
    try:
        response = httpx.post(
            f"https://api.resend.com/audiences/{audience}/contacts",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"email": email, "unsubscribed": False},
            timeout=10,
        )
        if response.status_code >= 300:
            logger.warning(f"waitlist: resend add {response.status_code} for {email}")
    except httpx.HTTPError as e:
        logger.warning(f"waitlist: resend unreachable: {e!r}")


@router.post("")
async def join(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Send JSON with an email field.") from None
    email = str(body.get("email", "")).strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "That email address does not look valid.")
    con = _connect()
    try:
        cursor = con.execute("INSERT OR IGNORE INTO waitlist (email) VALUES (?)", (email,))
        con.commit()
    finally:
        con.close()
    added = cursor.rowcount > 0
    if added:
        await asyncio.to_thread(_add_to_resend_audience, email)
    return JSONResponse({"ok": True, "already": not added})
