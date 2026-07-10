"""
hdfc_master.py — symbol -> HDFC {exchange, token} lookup.

Backed by data/hdfc_equity_master.json, a compact NSE/BSE cash-equity subset
compressed from HDFC's full Security Master CSV (~9MB, 120k+ rows across every
segment). Regenerate via scripts/build_hdfc_equity_master.py whenever a fresh
Security Master export is available (new listings need a re-run; existing
tokens are stable). Loaded once at import time — 9.4k symbols, ~500KB, cheap
to keep resident.
"""
from __future__ import annotations

import json
from pathlib import Path

_MASTER_PATH = Path(__file__).resolve().parent.parent / "data" / "hdfc_equity_master.json"

try:
    with open(_MASTER_PATH, encoding="utf-8") as f:
        _MASTER: dict[str, dict] = json.load(f)
except FileNotFoundError:
    _MASTER = {}


def resolve(symbol: str) -> dict | None:
    """`{"exchange": "NSE", "token": "2885"}` for a known symbol, else None."""
    return _MASTER.get((symbol or "").strip().upper())


def coverage_count() -> int:
    return len(_MASTER)
