#!/usr/bin/env python3
"""hack-kit preflight — run before you start building.

Checks:
  1. ANTHROPIC_API_KEY is present and does a TINY real model call (graceful if absent).
  2. Reports which optional keys (OpenAI / Gemini / ElevenLabs) are set.
  3. Checks that uv / python / ffmpeg / gh are on PATH.
  4. Prints a GREEN/RED summary.

Pure stdlib + the `anthropic` package. Loads .env if python-dotenv is available,
but does not require it.

Usage:
    uv run python scripts/preflight.py
    # or
    make preflight
"""

from __future__ import annotations

import os
import shutil
import sys

# Primary model used for the tiny smoke-test call. Keep in sync with CLAUDE.md.
SMOKE_TEST_MODEL = "claude-haiku-4-5"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


_COLOR = _supports_color()


def c(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if _COLOR else text


def ok(label: str, detail: str = "") -> bool:
    print(f"  {c('PASS', GREEN)}  {label}" + (f"  {c(detail, DIM)}" if detail else ""))
    return True


def fail(label: str, detail: str = "") -> bool:
    print(f"  {c('FAIL', RED)}  {label}" + (f"  {c(detail, DIM)}" if detail else ""))
    return False


def warn(label: str, detail: str = "") -> None:
    print(f"  {c('warn', YELLOW)}  {label}" + (f"  {c(detail, DIM)}" if detail else ""))


def _load_dotenv() -> None:
    """Load .env if python-dotenv is installed. No-op otherwise."""
    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found]
    except ImportError:
        return
    load_dotenv()


def check_anthropic_key_and_call() -> bool:
    """Confirm ANTHROPIC_API_KEY works with a tiny real call. Returns True on success."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return fail(
            "ANTHROPIC_API_KEY",
            "missing — copy .env.example to .env and add your key",
        )

    try:
        import anthropic
    except ImportError:
        return fail(
            "anthropic SDK",
            "not installed — run `uv sync`",
        )

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=SMOKE_TEST_MODEL,
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        ).strip()
        return ok(
            "ANTHROPIC_API_KEY",
            f"live call to {SMOKE_TEST_MODEL} OK -> {text!r}",
        )
    except anthropic.AuthenticationError:
        return fail("ANTHROPIC_API_KEY", "key rejected (401) — check the value")
    except anthropic.APIStatusError as e:
        return fail("ANTHROPIC_API_KEY", f"API error {e.status_code} — {e.message}")
    except anthropic.APIConnectionError:
        return fail("ANTHROPIC_API_KEY", "network error — check your connection")
    except Exception as e:  # noqa: BLE001 — preflight must never crash
        return fail("ANTHROPIC_API_KEY", f"unexpected error: {type(e).__name__}: {e}")


def report_optional_keys() -> None:
    optional = {
        "OPENAI_API_KEY": "OpenAI fallback",
        "GEMINI_API_KEY": "Gemini fallback",
        "ELEVENLABS_API_KEY": "ElevenLabs (voice/TTS)",
    }
    for env_name, desc in optional.items():
        if os.environ.get(env_name, "").strip():
            ok(f"{env_name}", f"set — {desc} available")
        else:
            warn(f"{env_name}", f"not set — {desc} disabled (optional)")


def check_tooling() -> list[str]:
    """Return a list of MISSING required tools (empty == all present)."""
    required = {
        "uv": "env/dep manager — required",
        "python3": "Python 3.12+ — required",
    }
    optional = {
        "ffmpeg": "demo recording/encode — needed for /demo",
        "gh": "GitHub CLI — needed for /ship (PRs)",
    }
    missing_required: list[str] = []

    for tool, desc in required.items():
        path = shutil.which(tool)
        if path:
            ok(tool, desc)
        else:
            fail(tool, f"{desc} — not on PATH")
            missing_required.append(tool)

    for tool, desc in optional.items():
        path = shutil.which(tool)
        if path:
            ok(tool, desc)
        else:
            warn(tool, f"{desc} — not on PATH")

    return missing_required


def main() -> int:
    _load_dotenv()

    print(c("\nhack-kit preflight", BOLD))
    print(c("=" * 40, DIM))

    print(c("\nAnthropic (primary):", BOLD))
    anthropic_ok = check_anthropic_key_and_call()

    print(c("\nOptional providers:", BOLD))
    report_optional_keys()

    print(c("\nTooling:", BOLD))
    missing_required = check_tooling()

    print(c("\n" + "=" * 40, DIM))
    all_green = anthropic_ok and not missing_required
    if all_green:
        print(c("GREEN — ready to build. Run `/brainstorm <topic>` to start.", GREEN + BOLD))
        return 0

    print(c("RED — fix the FAIL items above before building:", RED + BOLD))
    if not anthropic_ok:
        print(c("  - Anthropic is the primary provider; nothing AI works without it.", DIM))
    if missing_required:
        print(c(f"  - Missing required tools: {', '.join(missing_required)}", DIM))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
