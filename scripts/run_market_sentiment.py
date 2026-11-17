"""Append this week's market-sentiment reading to results/sentiment_forward.jsonl (owner approval 2026-11-17).

Forward-only and append-only: one row per scan week, written once, never rewritten or backfilled. It decides
nothing — no signal, rank, size, stop or exit reads this file, and a test pins that.

Runs in the Saturday scan as a non-blocking step. Without ANTHROPIC_API_KEY it writes nothing and exits 0.

    python scripts/run_market_sentiment.py [--as-of YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nq.research.market_sentiment import SERIES_ID, read_market  # noqa: E402

OUT = ROOT / "results" / "sentiment_forward.jsonl"


def scan_as_of() -> str | None:
    p = ROOT / "results" / "signals_today_weekly.json"
    return json.loads(p.read_text(encoding="utf-8")).get("generated_at") if p.is_file() else None


def already(as_of: str) -> bool:
    if not OUT.exists():
        return False
    return any(json.loads(ln).get("as_of") == as_of and json.loads(ln).get("series_id") == SERIES_ID
               for ln in OUT.read_text(encoding="utf-8").splitlines() if ln.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    as_of = a.as_of or scan_as_of()
    if not as_of:
        sys.stdout.write("::warning::market sentiment: no scan as-of; nothing written\n")
        return 0
    if already(as_of):
        sys.stdout.write(f"market sentiment: {as_of} already recorded (append-only); nothing written\n")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stdout.write("::warning::market sentiment: ANTHROPIC_API_KEY not set; nothing written\n")
        return 0
    try:
        import anthropic
        row = read_market(anthropic.Anthropic(), as_of=as_of)
    except Exception as exc:                                    # noqa: BLE001 — never block the scanner
        sys.stdout.write(f"::warning::market sentiment failed ({type(exc).__name__}: {exc})\n")
        return 0
    if a.dry_run:
        sys.stdout.buffer.write((json.dumps(row, indent=1)[:900] + "\n").encode("utf-8"))
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if row.get("ok"):
        sys.stdout.write(f"market sentiment {as_of}: {row['sentiment']:+.2f} ({row['confidence']}), "
                         f"tags {row.get('stress_tags')}, {row.get('n_headlines')} headlines — recorded, decides nothing\n")
    else:
        sys.stdout.write(f"::warning::market sentiment {as_of} recorded as a failed reading: {row.get('error')}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
