"""One ledger of every Prosper call we have, keyed the way the dashboard keys them.

    uv run python scripts/call_ledger.py                                  # rebuild from the snapshot
    uv run python scripts/call_ledger.py --dashboard ~/path/export.json   # refresh the snapshot first

The backbone is the dashboard export (GET /leaderboard/api/teams/{team_id}, logged-in session),
kept trimmed in docs/private-calls/dashboard-export.json. It is authoritative: every run's official
`run_id`, whether it is public (practice) or private (scored), and `cases[]` in website order, each
with its `call_id`, real `status`, `label`, `problem_id`, `attribution` and `signal_codes`.

Keys in the ledger:
- call_id      Prosper's callSid. Joins our logs, /api/v1/submissions and the dashboard.
- run_key      From the dashboard run: RA-MMDD-HHMMZ = private Run All (UTC start minute, as the
               Runs page shows it), SB-MMDD-HHMMZ = public Switchboard burst (5/10/20 cases),
               PR-MMDD-HHMMSSZ = public practice call.
- case_key     <run_key>#NN where NN is the website row ("Private case NN").
- lane         private | switchboard | practice from the dashboard; not_scored = Prosper placed the
               call but it is on no dashboard run (e.g. a caller dialled again, only the redial
               counts); no_dashboard = after the snapshot, or never matched (keys rebuilt from timing).
- example_key  caller number | patient (or NEW) | ask topics. Browsing hint, not case identity.
- outcome_fingerprint  Order-independent digest of all observed submitted action payloads.
                       Not a scenario identity or proof that an outcome is correct or complete.

Sources for what happened on each call: Fran's server (calls.udarc.com), logs/calls and
logs/autopilot/calls in every git worktree, the call logs committed on origin/main, and our latest
200 submissions (/api/v1/submissions, needs PLATFORM_API_KEY) for calls with no log. Only
Prosper-placed calls count (version-5 call ids; our simulators mint version-4). Remote calls are
cached under logs/remote/. Writes docs/private-calls/call-ledger.csv (+ .json).
"""

import argparse
import contextlib
import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FRAN = "https://calls.udarc.com/api/calls"
CACHE = ROOT / "logs" / "remote" / "fran"
OUT = ROOT / "docs" / "private-calls" / "call-ledger"
SNAPSHOT = ROOT / "docs" / "private-calls" / "dashboard-export.json"
UTC, MAD = dt.UTC, ZoneInfo("Europe/Madrid")
TOPICS = {
    "orthopaedics": r"orthop|hip|shoulder|wrist|knee|back",
    "gynaecology": r"gyn|contracept|smear",
    "dermatology": r"dermat|mole|rash|skin|eczema",
    "general_practice": r"general practice|\bgp\b|cough|prescription|hay fever|sleep|blood pressure|flu",
    "paediatrics": r"paediat|pediat|my (son|daughter|child|kid)",
    "physiotherapy": r"physio",
    "register": r"register|new to the clinic|new patient",
}


def fran_calls():
    CACHE.mkdir(parents=True, exist_ok=True)
    ids = [c["call_id"] for c in json.load(urllib.request.urlopen(FRAN, timeout=60))["calls"]]
    for cid in ids:
        path = CACHE / f"{cid}.json"
        if not path.exists():
            path.write_bytes(urllib.request.urlopen(f"{FRAN}/{cid}", timeout=60).read())
        yield cid, "fran-server", json.loads(path.read_text())["events"]


def is_prosper(call_id):
    """Prosper's call ids are version-5 UUIDs; our simulators mint version-4 ones."""
    parts = call_id.split("-")
    return len(parts) == 5 and parts[2][:1] == "5"


def parse_jsonl(text):
    events = []
    for line in text.splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            events.append(json.loads(line))
    return events


def outcome_fingerprint(actions):
    """Hash observed payloads, preserving all fields and duplicates except call_id.

    Sorting removes submission completion order; values remain case-sensitive.
    Missing payloads are unresolved. A digest does not validate action schemas.
    """
    if not actions or any(not isinstance(a, dict) or not a.get("action") for a in actions):
        return "unresolved"
    payloads = sorted(
        json.dumps(
            {k: v for k, v in action.items() if k != "call_id"},
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for action in actions
    )
    canonical = json.dumps(payloads, ensure_ascii=False, separators=(",", ":"))
    return "v1:" + hashlib.sha256(canonical.encode()).hexdigest()


def outcome_fields(actions):
    return {
        "action": "|".join(sorted({a.get("action", "") for a in actions if isinstance(a, dict)})),
        "submitted": json.dumps(actions, ensure_ascii=False) if actions else "",
        "outcome_fingerprint": outcome_fingerprint(actions),
    }


def local_calls():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "worktree", "list", "--porcelain"], capture_output=True, text=True
    ).stdout
    checkouts = [
        Path(line.split(" ", 1)[1]) for line in out.splitlines() if line.startswith("worktree ")
    ] or [ROOT]
    for checkout in checkouts:
        for d in ("logs/calls", "logs/autopilot/calls"):
            for f in sorted((checkout / d).glob("*.jsonl")):
                if is_prosper(f.stem):
                    yield (
                        f.stem,
                        f"local:{checkout.name}",
                        parse_jsonl(f.read_text(errors="replace")),
                    )
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-tree", "--name-only", "origin/main", "logs/calls/"],
        capture_output=True,
        text=True,
    ).stdout
    for name in listed.split():
        cid = Path(name).stem
        if name.endswith(".jsonl") and is_prosper(cid):
            text = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"origin/main:{name}"],
                capture_output=True,
                text=True,
            ).stdout
            yield cid, "git:origin/main", parse_jsonl(text)


def summarize(cid, source, ev):
    start = next((e for e in ev if e.get("kind") == "call_started"), None)
    if not start or not is_prosper(cid):
        return None  # our own simulator/eval call, not Prosper
    t0 = ev[0]["t"]
    user = [e for e in ev if e.get("kind") == "transcript" and e.get("role") == "user"]
    agent = [e for e in ev if e.get("kind") == "transcript" and e.get("role") == "agent"]
    end = next(
        (e["t"] for e in ev if e.get("kind") in ("stop_received", "socket_closed")), ev[-1]["t"]
    )
    last_user = max(
        [e["t"] for e in user]
        + [e["t"] for e in ev if e.get("kind") == "speech_boundary" and e.get("role") == "user"]
        or [t0]
    )
    last_agent = max([e["t"] for e in agent] or [t0])
    subs = [e.get("action") for e in ev if e.get("kind") == "submit"]
    lookup = next((e.get("matches") for e in ev if e.get("kind") == "caller_id_lookup"), None) or []
    text = " ".join(e.get("text", "") for e in user).lower()
    topics = sorted(t for t, rx in TOPICS.items() if re.search(rx, text))
    patients = sorted(
        {a["patient_id"] for a in subs if isinstance(a, dict) and a.get("patient_id")}
    )
    patient = ",".join(patients) or (lookup[0] if len(lookup) == 1 else "")
    return {
        "call_id": cid,
        "source": source,
        "t_start": t0,
        "t_end": end,
        "connect_utc": dt.datetime.fromtimestamp(t0, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "connect_madrid": dt.datetime.fromtimestamp(t0, MAD).strftime("%a %H:%M:%S"),
        "seconds": round(end - t0, 1),
        "from_number": start.get("from_number") or "",
        "patient": patient,
        "topics": ",".join(topics),
        "example_key": f"{start.get('from_number') or '?'}|{patient or ('NEW' if 'register' in topics else '?')}|{','.join(t for t in topics if t != 'register') or '-'}",
        **outcome_fields(subs),
        "caller_turns": len(user),
        "caller_stalled": last_agent > last_user and end - last_user >= 20,
        "fallback": any(e.get("kind") == "fallback" for e in ev),
    }


def submissions():
    """Our latest 200 submissions: call_id -> (received_at, actions). Empty if no API key."""
    import sys

    sys.path.insert(0, str(ROOT))
    from app import config

    if not config.PLATFORM_API_KEY:
        return {}
    req = urllib.request.Request(
        f"{config.PLATFORM_API_BASE_URL}/api/v1/submissions?limit=200",
        headers={"X-Api-Key": config.PLATFORM_API_KEY},
    )
    subs = json.load(urllib.request.urlopen(req, timeout=60))["submissions"]
    return {s["call_id"]: (s["received_at"], s["record"]["actions"]) for s in subs}


def refresh_snapshot(export_path):
    """Trim a full dashboard export into the committed snapshot (no endpoint, no transcripts)."""
    d = json.loads(Path(export_path).read_text())
    runs = [
        {
            **{
                k: r.get(k)
                for k in ("run_id", "public", "state", "started_at", "voided", "explanation")
            },
            "cases": [
                {k: v for k, v in c.items() if k != "transcript"} for c in r.get("cases") or []
            ],
        }
        for r in d["runs"]
    ]
    snap = {
        "team": d.get("name"),
        "generated_at": d.get("generated_at"),
        "stats": d.get("stats"),
        "runs": runs,
    }
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1))
    return snap


def dashboard_cases():
    """call_id -> case info from the snapshot, plus the snapshot's generation time."""
    if not SNAPSHOT.exists():
        return {}, ""
    snap = json.loads(SNAPSHOT.read_text())
    out = {}
    for r in snap["runs"]:
        start = dt.datetime.fromisoformat(r["started_at"].replace("Z", "+00:00"))
        n = len(r["cases"])
        if not r["public"]:
            lane, key = "private", "RA-" + start.strftime("%m%d-%H%MZ")
        elif n > 1:
            lane, key = "switchboard", "SB-" + start.strftime("%m%d-%H%MZ")
        else:
            lane, key = "practice", "PR-" + start.strftime("%m%d-%H%M%SZ")
        for row, c in enumerate(r["cases"], 1):
            if c.get("call_id"):
                out[c["call_id"]] = {
                    "lane": lane,
                    "run_key": key,
                    "case_key": f"{key}#{row:02d}" if lane != "practice" else key,
                    "dash_run_id": r["run_id"],
                    "dash_row": row,
                    "dash_voided": r.get("voided"),
                    "dash_label": c.get("label"),
                    "dash_problem": c.get("problem_id"),
                    "dash_status": c.get("status"),
                    "dash_attribution": c.get("attribution"),
                    "dash_signals": ",".join(c.get("signal_codes") or []),
                    "dash_points": c.get("points"),
                    "dash_points_available": c.get("points_available"),
                    "t_run": start.timestamp(),
                }
    return out, snap.get("generated_at") or ""


def assign_runs(calls):
    calls.sort(key=lambda c: c["t_start"])
    clusters: list[list[dict]] = []
    cur: list[dict] = []
    cur_end = 0.0
    for c in calls:
        if cur and c["t_start"] - cur_end > 10:  # nothing open for 10 s: a new group
            clusters.append(cur)
            cur = []
        cur.append(c)
        cur_end = max(cur_end, c["t_end"]) if len(cur) > 1 else c["t_end"]
    if cur:
        clusters.append(cur)
    for cl in clusters:
        edges = sorted([(c["t_start"], 1) for c in cl] + [(c["t_end"], -1) for c in cl])
        live = peak = 0
        for _, d in edges:
            live += d
            peak = max(peak, live)
        burst = sum(1 for c in cl if c["t_start"] - cl[0]["t_start"] < 30)
        if peak >= 3 and burst == len(cl) and len(cl) in (5, 10, 20):
            key = "SB-" + dt.datetime.fromtimestamp(cl[0]["t_start"], UTC).strftime("%m%d-%H%MZ")
            for i, c in enumerate(cl, 1):
                c.update(
                    lane="switchboard",
                    run_key=key,
                    case_key=f"{key}#{i:02d}",
                    run_peak_concurrency=peak,
                )
        elif peak >= 3:
            key = "RA-" + dt.datetime.fromtimestamp(cl[0]["t_start"], UTC).strftime("%m%d-%H%MZ")
            for i, c in enumerate(cl, 1):
                c.update(
                    lane="run_all",
                    run_key=key,
                    case_key=f"{key}#{i:02d}",
                    run_peak_concurrency=peak,
                )
        else:
            for c in cl:
                key = "PR-" + dt.datetime.fromtimestamp(c["t_start"], UTC).strftime("%m%d-%H%M%SZ")
                c.update(lane="practice", run_key=key, case_key=key, run_peak_concurrency=peak)


def public_phones():
    raw = json.loads((ROOT / "docs/prosper/data/public-cases.json").read_text())
    phones: dict[str, list[str]] = {}
    for case in raw if isinstance(raw, list) else raw.get("cases", []):
        p = case["persona"]
        digits = re.sub(r"\D", "", str(p.get("phone") or p["data"].get("phone") or ""))[-9:]
        if digits:
            phones.setdefault(digits, []).append(case["id"])
    return phones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dashboard",
        help="full export of GET /leaderboard/api/teams/{team_id}: refresh the snapshot from it",
    )
    ap.add_argument(
        "--no-remote", action="store_true", help="skip Fran's server and the submissions API"
    )
    args = ap.parse_args()
    if args.dashboard:
        snap = refresh_snapshot(args.dashboard)
        print(f"snapshot refreshed: {len(snap['runs'])} runs, generated {snap['generated_at']}")
    seen = {}
    for src in ([] if args.no_remote else [fran_calls()]) + [local_calls()]:
        for cid, where, ev in src:
            if cid not in seen and ev and (row := summarize(cid, where, ev)):
                seen[cid] = row
    calls = list(seen.values())
    assign_runs(calls)  # timing-based keys: only used where the dashboard has nothing
    for c in calls:
        c["rebuilt_key"] = c["case_key"]
    subs = {} if args.no_remote else submissions()
    dash, generated = dashboard_cases()
    stub = lambda cid, source, t: {  # noqa: E731
        "call_id": cid,
        "source": source,
        "t_start": t,
        "t_end": t,
        "lane": "",
        "run_key": "",
        "case_key": "",
        "rebuilt_key": "",
        "outcome_fingerprint": "unresolved",
        "caller_stalled": "",
        "connect_utc": "",
        "from_number": "",
        "action": "",
        "submitted": "",
        "connect_madrid": dt.datetime.fromtimestamp(t, MAD).strftime("%a %H:%M:%S"),
    }
    for cid, (received, actions) in subs.items():
        if cid not in seen and is_prosper(cid):
            row = stub(
                cid,
                "submissions",
                dt.datetime.fromisoformat(received.replace("Z", "+00:00")).timestamp(),
            )
            row.update(outcome_fields(actions))
            row["connect_madrid"] += " (submitted)"
            seen[cid] = row
            calls.append(row)
    for cid, info in dash.items():
        if cid not in seen:
            row = stub(cid, "dashboard", info["t_run"])
            row["connect_madrid"] += " (run start)"
            seen[cid] = row
            calls.append(row)
    cutoff = (
        dt.datetime.fromisoformat(generated.replace("Z", "+00:00")).timestamp() if generated else 0
    )
    for c in calls:
        c["has_log"] = c["source"] not in ("submissions", "dashboard")
        c["submitted_utc"] = subs.get(c["call_id"], ("", None))[0]
        info = dash.get(c["call_id"])
        if info:
            c.update({k: v for k, v in info.items() if k != "t_run"})
        elif c["lane"] in ("run_all", "switchboard") and c["t_start"] < cutoff:
            c["lane"] = "not_scored"
        else:
            c["lane"] = "no_dashboard"
    phones = public_phones()
    for c in calls:
        hits = phones.get(re.sub(r"\D", "", c.get("from_number") or "")[-9:], [])
        c["public_case"] = "|".join(hits) if c["lane"] in ("practice", "switchboard") else ""
    cols = [
        "case_key",
        "run_key",
        "lane",
        "call_id",
        "dash_run_id",
        "dash_row",
        "dash_label",
        "dash_problem",
        "dash_status",
        "dash_attribution",
        "dash_signals",
        "dash_points",
        "dash_points_available",
        "dash_voided",
        "connect_utc",
        "connect_madrid",
        "seconds",
        "source",
        "has_log",
        "from_number",
        "patient",
        "topics",
        "example_key",
        "outcome_fingerprint",
        "public_case",
        "caller_turns",
        "caller_stalled",
        "fallback",
        "action",
        "submitted",
        "submitted_utc",
        "rebuilt_key",
    ]
    calls.sort(key=lambda c: (c["t_start"], c.get("dash_row") or 0))
    with open(f"{OUT}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(calls)
    Path(f"{OUT}.json").write_text(
        json.dumps([{k: c.get(k, "") for k in cols} for c in calls], ensure_ascii=False, indent=1)
    )
    print(
        f"{len(calls)} Prosper calls → {OUT.relative_to(ROOT)}.csv  (dashboard snapshot {generated or 'missing'})"
    )
    runs: dict[tuple[str, str], list[dict]] = {}
    for c in calls:
        if c["lane"] in ("private", "switchboard"):
            runs.setdefault((c["lane"], c["run_key"]), []).append(c)
    for (lane, key), cs in sorted(runs.items(), key=lambda kv: kv[0][1][3:]):
        status: dict[str | None, int] = {}
        for c in cs:
            status[c.get("dash_status")] = status.get(c.get("dash_status"), 0) + 1
        print(
            f"  {key}  {lane:11} {len(cs):3} cases  with log {sum(bool(c['has_log']) for c in cs):3}  {status}"
        )
    for lane in ("practice", "not_scored", "no_dashboard"):
        print(f"  + {sum(1 for c in calls if c['lane'] == lane)} {lane}")


if __name__ == "__main__":
    main()
