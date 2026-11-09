"""Write-once capture of the signal-quality axes AT SIGNAL TIME (forward/prereg_signal_quality.md).

Why this exists. The three producer-side axes (body_ratio, signal_conviction, crs_rank) used to
survive only on FRESH cards inside the Saturday scan's archive. When a Saturday scan failed, the
signal was first archived already ACTIVE and its axes were gone for good (KNOWN_INCOMPLETE in
collect_signal_quality_forward.py lists the casualties). This module gives the axes a durable home
that does not depend on the archive: `results/signal_axes_capture.jsonl`.

Contract:
  * append-only, one JSON object per line, keyed by (ticker, signal_date);
  * FIRST WRITE WINS. A key already present is never rewritten, re-ordered or deleted;
  * a corrupt/partial line is skipped on read, never "repaired";
  * values are produced by the SAME helpers the FRESH card uses (see
    run_bhanushali_cron.capture_signal_axes), from the signal-week bars.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

CAPTURE_FIELDS = ("body_ratio", "signal_conviction", "crs_rank")


def capture_path(results_dir) -> Path:
    return Path(results_dir) / "signal_axes_capture.jsonl"


def load_capture(path) -> dict[tuple[str, str], dict]:
    """{(ticker, signal_date): record}; the first occurrence of a key wins on read as well."""
    out: dict[tuple[str, str], dict] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            key = (rec["ticker"], rec["signal_date"])
        except Exception:  # noqa: BLE001 -- a torn line must not poison the rest of the log
            continue
        out.setdefault(key, rec)
    return out


def append_write_once(path, records: list[dict]) -> list[dict]:
    """Append records whose key is not already logged. Returns the records actually written."""
    p = Path(path)
    seen = load_capture(p)
    new: list[dict] = []
    for r in records:
        key = (r["ticker"], r["signal_date"])
        if key in seen:
            continue
        seen[key] = r
        new.append(r)
    if new:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8", newline="\n") as fh:
            for r in new:
                fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    return new


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
