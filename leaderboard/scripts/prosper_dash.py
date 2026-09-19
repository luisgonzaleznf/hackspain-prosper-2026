"""Drive the Prosper dashboard from the shell, with no browser in the loop.

    uv run python scripts/prosper_dash.py status              # eligibility, board, headroom
    uv run python scripts/prosper_dash.py runs                # our recent runs and their cases
    uv run python scripts/prosper_dash.py queue <problem_id>  # POST a scored run
    uv run python scripts/prosper_dash.py wait                # block until the cooldown clears

The leaderboard routes are authenticated by the `prosper_dashboard` SESSION COOKIE, not by the
agent's X-Api-Key: the public OpenAPI has no run route at all (17 routes, none containing "run"),
so the dashboard cookie is the only way to start a run without a browser.

Put the cookie in .env as PROSPER_DASHBOARD_COOKIE. This script reads it from the environment and
never prints it; nothing here echoes the value, and errors quote only status codes. Copy it from
Chrome DevTools -> Application -> Cookies -> prosper_dashboard (the value alone, no "name=").

The cookie expires. When it does every call returns 401 and the script says so rather than
pretending the board is empty.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://hackspain.getprosperapp.com/leaderboard/api"
TEAM = "9a279f4e-d8e1-4811-a7a4-3c86da8447fd"
ROOT = Path(__file__).resolve().parents[1]


def _cookie_from_har(path: Path) -> str:
    """The newest prosper_dashboard cookie in a HAR, ignoring every other secret it carries.

    Same source scripts/prosper_autopilot.py uses, so one capture serves both.
    """
    har = json.loads(path.read_text())
    found = ""
    for entry in har.get("log", {}).get("entries", []):
        for header in entry.get("request", {}).get("headers", []):
            if header.get("name", "").lower() != "cookie":
                continue
            for part in header.get("value", "").split(";"):
                name, _, value = part.strip().partition("=")
                if name == "prosper_dashboard" and value:
                    found = value  # later entries win: take the freshest
    if not found:
        sys.exit(f"{path.name} contains no prosper_dashboard cookie — capture it while signed in.")
    return found


def cookie() -> str:
    """The dashboard session cookie. Read from env, .env or a HAR. Never logged."""
    value = os.environ.get("PROSPER_DASHBOARD_COOKIE", "").strip()
    if not value:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("PROSPER_DASHBOARD_COOKIE="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not value:
        har = os.environ.get("PROSPER_HAR", "").strip()
        if har and Path(har).expanduser().exists():
            value = _cookie_from_har(Path(har).expanduser())
    if not value:
        sys.exit(
            "No dashboard cookie. Either:\n"
            "  1. export a HAR while signed in and point at it:\n"
            "       PROSPER_HAR=~/Downloads/prosper.har uv run python scripts/prosper_dash.py status\n"
            "     (Chrome DevTools -> Network -> reload the dashboard -> download icon 'Export HAR')\n"
            "  2. or put PROSPER_DASHBOARD_COOKIE=<value> in .env\n"
            "The HAR holds other secrets: keep it out of git and delete it when done."
        )
    return value


def call(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers={
            "Cookie": f"prosper_dashboard={cookie()}",
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = (e.read() or b"")[:200].decode(errors="replace")
        if e.code in (401, 403):
            sys.exit(f"HTTP {e.code}: the dashboard cookie is missing or expired. Refresh it in .env.")
        sys.exit(f"HTTP {e.code} on {path}: {detail}")


def headroom() -> list[tuple[str, int, int, int]]:
    """(problem_id, weight, credited, points still available) — credit caps at 4 per problem."""
    team, problems = call(f"/teams/{TEAM}"), call("/problems")
    credited = {p.get("problem_id") or p.get("id"): p.get("credited", 0) for p in team.get("progress", [])}
    rows = [
        (p["id"], p["weight"], credited.get(p["id"], 0), (4 - credited.get(p["id"], 0)) * p["weight"])
        for p in problems["problems"]
    ]
    return sorted(rows, key=lambda r: -r[3])


def status() -> None:
    team, board = call(f"/teams/{TEAM}"), call("/board")
    e = team["eligibility"]
    print(f"endpoint   {team['integration']['endpoint']}")
    print(f"active_run {e['active_run']}   private_wait {e['private_wait']}s   public_wait {e['public_wait']}s")
    rows = headroom()
    total = sum(c * w for _, w, c, _ in rows)
    print(f"points     {total}   headroom {sum(g for *_, g in rows)}   frozen={board.get('frozen')}")
    for pid, w, c, gain in rows:
        if gain:
            print(f"  {pid:18s} w{w}  {c}/4  +{gain}")
    for i, t in enumerate(board.get("entries", [])[:6], 1):
        print(f"  {i}. {t['name']:14s} {t.get('points', t.get('score'))}")


def runs() -> None:
    for r in call(f"/teams/{TEAM}").get("runs", [])[:5]:
        cases = " ".join(
            f"{(c.get('status') or c.get('state'))[:4]}/{c.get('points', '')}" for c in r.get("cases", [])
        )
        print(f"{r['run_id'][:8]}  {r.get('problem_id', '?'):16s} {r['state']:10s} {cases}")


def wait() -> None:
    while True:
        e = call(f"/teams/{TEAM}")["eligibility"]
        if not e["active_run"] and e["private_wait"] == 0:
            print(f"SLOT OPEN {time.strftime('%H:%M:%S')}", flush=True)
            return
        print(f"  {time.strftime('%H:%M:%S')} active={e['active_run']} wait={e['private_wait']}s", flush=True)
        time.sleep(min(15, max(2, e["private_wait"] or 5)))


def queue(problem: str) -> None:
    """Start a scored run, but only when the dashboard itself says we are eligible."""
    team = call(f"/teams/{TEAM}")
    e = team["eligibility"]
    if e["active_run"] or e["private_wait"]:
        sys.exit(f"not eligible: active_run={e['active_run']} private_wait={e['private_wait']}s")
    print(f"endpoint at POST: {team['integration']['endpoint']}")
    out = call(f"/problems/{problem}/scored-runs", {})
    print(f"QUEUED {problem} run {out.get('run_id')} {time.strftime('%H:%M:%S')}")


def endpoint_live(registered: str) -> bool:
    """The tunnel must answer AND be the address the dashboard will dial."""
    health = registered.replace("wss://", "https://").replace("ws://", "http://")
    health = health.rsplit("/ws", 1)[0] + "/health"
    try:
        with urllib.request.urlopen(health, timeout=8) as r:
            return json.loads(r.read()).get("ok") is True
    except Exception:
        return False


def autonew(poll: float = 10.0, also: tuple[str, ...] = ()) -> None:
    """Queue whichever open lane pays most, as slots free up. Highest points first, ties arbitrary.

    Built for the roster opening more problems mid-event: a brand-new lane is credited 0/4, so it
    is worth 4 x weight -- more than any repeat of a lane we already hold. When several open at
    once we take the most valuable; a tie is genuinely a coin flip, so we take the first.

    `also` names lanes to re-run for DIAGNOSIS once nothing pays any more (credit caps at 4, so
    those runs are worth 0 points and cannot lose any either). Without it, a fully-credited board
    simply idles.

    It refuses to spend a slot on a dead endpoint -- that mistake nearly cost us a run earlier --
    and never runs two at once, because the API rejects that anyway.
    """
    seen = {p["id"] for p in call("/problems")["problems"]}
    print(f"watching {len(seen)} problems, polling every {poll:g}s", flush=True)
    if also:
        print(f"diagnostic re-runs when nothing pays: {', '.join(also)}", flush=True)
    while True:
        rows = headroom()
        openable = [r for r in rows if r[3] > 0]          # already sorted by points, descending
        current = {r[0] for r in rows}
        fresh = current - seen
        if fresh:
            gains = {r[0]: r[3] for r in rows}
            listed = ", ".join(f"{p} (+{gains.get(p, 0)})" for p in sorted(fresh, key=lambda p: -gains.get(p, 0)))
            print(f"NEW PROBLEM(S): {listed}  {time.strftime('%H:%M:%S')}", flush=True)
            seen |= fresh
        if not openable and also:
            # nothing pays; fall back to the diagnostic lanes, in the order given
            openable = [r for name in also for r in rows if r[0] == name]
            if openable:
                print(f"  {time.strftime('%H:%M:%S')} board fully credited — diagnostic re-run", flush=True)
        if not openable:
            print(f"  {time.strftime('%H:%M:%S')} every lane 4/4 — nothing to queue", flush=True)
            time.sleep(poll)
            continue
        team = call(f"/teams/{TEAM}")
        e = team["eligibility"]
        if e["active_run"] or e["private_wait"]:
            time.sleep(min(poll, max(2, e["private_wait"] or poll)))
            continue
        registered = team["integration"]["endpoint"]
        if not endpoint_live(registered):
            print(f"  ENDPOINT DOWN ({registered}) — refusing to spend a slot", flush=True)
            time.sleep(poll)
            continue
        target = openable[0]
        print(f"  queueing {target[0]} (+{target[3]}) via {registered}", flush=True)
        try:
            out = call(f"/problems/{target[0]}/scored-runs", {})
            print(f"QUEUED {target[0]} run {out.get('run_id')} {time.strftime('%H:%M:%S')}", flush=True)
        except SystemExit as err:  # a 409 just means someone beat us to the slot
            print(f"  not queued: {err}", flush=True)
        time.sleep(poll)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "runs":
        runs()
    elif cmd == "wait":
        wait()
    elif cmd == "queue":
        if len(sys.argv) < 3:
            sys.exit("queue needs a problem id, e.g. no_slot_free")
        queue(sys.argv[2])
    elif cmd == "autonew":
        rest = sys.argv[2:]
        secs = float(rest[0]) if rest and rest[0].replace(".", "", 1).isdigit() else 10.0
        lanes = tuple(a for r in rest if r.startswith("--also=") for a in r[7:].split(",") if a)
        autonew(secs, lanes)
    else:
        sys.exit(__doc__)
