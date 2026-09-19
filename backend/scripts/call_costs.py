"""What a batch of calls cost on the OpenAI API: our agent (VOICE=gptlive) and the eval caller.

    uv run python scripts/call_costs.py logs/calls/<id>.jsonl ...          # agent side
    uv run python scripts/call_costs.py --run evals/runs/<ts> logs/calls/  # + the eval caller

Agent: GPT-Live's billed audio seconds (the last cumulative `usage` entry of each call) plus
every brain response's tokens, both written by app/voice/gptlive. Eval caller: the Realtime
API token totals evals/caller.py sums per call (`caller_usage` in result.json). They carry no
audio/text/cached split, so the caller figure is an UPPER BOUND (all tokens priced as
uncached audio).

Prices are the constants below (USD, Sep 2026): GPT-Live from OpenAI's launch post, the rest from
secondary pricing tables. Check them against the OpenAI billing dashboard.
"""

import argparse
import json
import sys
from pathlib import Path

LIVE_USD_PER_MIN = {"gpt-live-1": 0.05}
# per 1M tokens: (uncached input, cached input, output)
BRAIN_USD_PER_M = {
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-5.6-terra": (1.00, 0.10, 6.00),
    "gpt-5.6-sol": (3.00, 0.30, 18.00),
}
# eval caller, Realtime API audio: (input, output) per 1M tokens
CALLER_USD_PER_M = {"gpt-realtime": (32.0, 64.0), "gpt-realtime-mini": (10.0, 20.0)}


def agent_cost(log: Path) -> dict:
    live_s, live_model, brain_usd, tokens = 0.0, "gpt-live-1", 0.0, [0, 0, 0]
    for line in log.read_text().splitlines():
        e = json.loads(line)
        if e.get("kind") != "usage":
            continue
        if "live_seconds" in e:
            live_s = max(live_s, float(e["live_seconds"]))
            live_model = e.get("model", live_model)
            continue
        price = next(
            (p for m, p in BRAIN_USD_PER_M.items() if str(e.get("model", "")).startswith(m)), None
        )
        cached = int(e.get("cached_tokens") or 0)
        uncached = int(e.get("input_tokens") or 0) - cached
        out = int(e.get("output_tokens") or 0)
        tokens = [tokens[0] + uncached, tokens[1] + cached, tokens[2] + out]
        if price:
            brain_usd += (uncached * price[0] + cached * price[1] + out * price[2]) / 1e6
    live_usd = live_s / 60 * LIVE_USD_PER_MIN.get(live_model, 0.05)
    return {
        "call": log.stem,
        "live_seconds": round(live_s, 1),
        "live_usd": live_usd,
        "brain_tokens": tokens,
        "brain_usd": brain_usd,
        "agent_usd": live_usd + brain_usd,
    }


def caller_cost(run_dir: Path, model: str) -> tuple[int, float]:
    price = CALLER_USD_PER_M.get(model, CALLER_USD_PER_M["gpt-realtime"])
    n, usd = 0, 0.0
    for f in run_dir.glob("*/result.json"):
        u = json.loads(f.read_text()).get("caller_usage") or {}
        n += 1
        usd += (u.get("input_tokens", 0) * price[0] + u.get("output_tokens", 0) * price[1]) / 1e6
    return n, usd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+", help="call logs, or directories of them")
    ap.add_argument("--run", type=Path, help="an evals/runs/<ts> dir, for the caller's cost")
    ap.add_argument("--caller-model", default="gpt-realtime")
    args = ap.parse_args()
    paths = [
        p for a in map(Path, args.logs) for p in (sorted(a.glob("*.jsonl")) if a.is_dir() else [a])
    ]
    rows = [r for r in map(agent_cost, paths) if r["live_seconds"] or r["brain_usd"]]
    for r in rows:
        print(
            f"{r['call'][:8]}  live {r['live_seconds']:6.1f}s ${r['live_usd']:.3f}  "
            f"brain {r['brain_tokens']} ${r['brain_usd']:.4f}  = ${r['agent_usd']:.3f}"
        )
    agent = sum(r["agent_usd"] for r in rows)
    print(
        f"AGENT: {len(rows)} calls, ${agent:.2f} "
        f"(live ${sum(r['live_usd'] for r in rows):.2f} + brain ${sum(r['brain_usd'] for r in rows):.2f})"
    )
    if args.run:
        n, usd = caller_cost(args.run, args.caller_model)
        print(f"EVAL CALLER: {n} calls, <= ${usd:.2f} (upper bound)")
        print(f"TOTAL: <= ${agent + usd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
