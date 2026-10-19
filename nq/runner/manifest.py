"""Run manifest: every engine run says whether it IS the live book, and if not, why not.

WHY THIS EXISTS

Research scripts drifted from the live cron: several passed ``mem=None`` (no point-in-time Nifty-500
membership gate) and so measured a different book (Sharpe 1.67) from the one that trades (1.03).
Nothing on the output said so. A run now carries a manifest whose ``label`` is either ``LIVE BOOK`` or
``NOT LIVE BOOK: <first differing key>``, so a number can never be quoted without knowing which book
produced it.

The live book is read, not restated: the ``LIVE_*`` blocks are imported from
``scripts/run_bhanushali_cron.py`` (the single source of truth for what the cron passes to
``R94.backtest``). Read-only; nothing here changes an engine path.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]

# Keys that do not define WHICH book is run (the evaluation window start is a reporting choice).
IGNORED_KEYS = frozenset({"start"})
# Engine switches the cron leaves at their default; absent from the LIVE_* blocks but must still match.
LIVE_DEFAULTS: dict[str, Any] = {"uncapped": False, "grade_gate": True}


def _live_blocks() -> dict[str, dict]:
    for p in (ROOT, ROOT / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import run_bhanushali_cron as C
    return {"LIVE_DISCIPLINE": C.LIVE_DISCIPLINE, "LIVE_EXIT": C.LIVE_EXIT,
            "LIVE_STALENESS": C.LIVE_STALENESS, "LIVE_PREP": C.LIVE_PREP}


def live_engine_kwargs() -> dict[str, Any]:
    """The union of the cron's LIVE_* blocks, flat (the kwargs the cron hands the engine)."""
    out: dict[str, Any] = {}
    for blk in _live_blocks().values():
        out.update(blk)
    return out


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def live_config_fingerprint() -> str:
    """sha256 of the canonical JSON of the live engine kwargs + ``{"membership": "pit"}``."""
    return _sha({**_live_blocks(), "membership": "pit"})


def diff_from_live(engine_kwargs: Mapping[str, Any], membership: str) -> list[str]:
    """Keys on which a run differs from the live book (membership first, then sorted).

    ``LIVE_PREP`` keys (``complete_weeks_only``) configure ``prep_weekly_rank``, not ``backtest``; a
    caller that does not pass them is not flagged for omitting them, but one that passes a different
    value is.
    """
    live = {**LIVE_DEFAULTS, **live_engine_kwargs()}
    prep_keys = set(_live_blocks()["LIVE_PREP"])
    mine = {k: v for k, v in engine_kwargs.items() if k not in IGNORED_KEYS}
    diffs = []
    for k in sorted(set(live) | set(mine)):
        if k in live and k in mine:
            if _canon(live[k]) != _canon(mine[k]):
                diffs.append(k)
        elif k in live:                     # live sets it, the run does not
            if k not in LIVE_DEFAULTS and k not in prep_keys:
                diffs.append(k)
        else:                               # the run sets something the live book does not
            diffs.append(k)
    return (["membership"] if membership != "pit" else []) + diffs


def _code_sha() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10)
        return (r.stdout.strip() or None) if r.returncode == 0 else None
    except Exception:
        return None


def build_manifest(engine_kwargs: Mapping[str, Any], *, membership: str, data_vintage: str | None = None,
                   window: Sequence | None = None) -> dict[str, Any]:
    """Provenance record for one engine run. ``membership`` is ``"pit"`` or ``"none"``."""
    if membership not in ("pit", "none"):
        raise ValueError(f"membership must be 'pit' or 'none', got {membership!r}")
    import pandas as pd
    diffs = diff_from_live(engine_kwargs, membership)
    return {
        "config_hash": _sha({"engine_kwargs": dict(engine_kwargs), "membership": membership}),
        "live_fingerprint": live_config_fingerprint(),
        "is_live_book": not diffs,
        "label": "LIVE BOOK" if not diffs else f"NOT LIVE BOOK: {diffs[0]}",
        "differs_on": diffs,
        "membership": membership,
        "data_vintage": data_vintage,
        "window": list(window) if window is not None else None,
        "code_sha": _code_sha(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
