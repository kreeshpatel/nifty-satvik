"""Append this week's issued cards to results/cards_archive.jsonl — the recommendation record.

Why this exists: `results/signals_today_weekly.json` is OVERWRITTEN every Saturday, and
`results/signals_history_weekly.json` retains only names the tracker marked bought. So a card
that was issued and then lapsed unfilled left no artifact at all — the Portfolio page could show
what the book bought, but never what it recommended and passed on. That absence hides exactly the
behaviour worth seeing: the system declining to chase a price that never entered the band.

This preserves what was RECOMMENDED, verbatim and at issue time. It never recomputes a past
recommendation and never revises a stored one — the whole point is that the record is what the
card printed (D5 parity). Rows are keyed (ticker, signal_date) and written once; a re-run is a
no-op, so the scanner can call it every week and a replayed workflow adds nothing.

    python scripts/archive_weekly_cards.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENVELOPE = ROOT / "results" / "signals_today_weekly.json"
ARCHIVE = ROOT / "results" / "cards_archive.jsonl"

# Exactly the card's printed fields — no derived or re-computed values.
KEEP = ("ticker", "signal_date", "entry", "entry_low", "entry_high", "stop", "target",
        "grade", "tier", "crs_rank", "pattern", "buy_window", "buy_window_until",
        "status", "bought_date")


def main() -> int:
    if not ENVELOPE.exists():
        print(f"no envelope at {ENVELOPE} — nothing to archive")
        return 0
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    signals = envelope.get("signals") or []

    seen: set[tuple[str, str]] = set()
    if ARCHIVE.exists():
        for line in ARCHIVE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            seen.add((str(row.get("ticker")), str(row.get("signal_date"))))

    added = 0
    with ARCHIVE.open("a", encoding="utf-8") as fh:
        for sig in signals:
            if not isinstance(sig, dict):
                continue
            key = (str(sig.get("ticker")), str(sig.get("signal_date")))
            if key[0] in ("None", "") or key in seen:
                continue
            fh.write(json.dumps({k: sig.get(k) for k in KEEP}, default=str) + "\n")
            seen.add(key)
            added += 1

    print(f"cards archived: +{added} (archive now {len(seen)} cards) -> {ARCHIVE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
