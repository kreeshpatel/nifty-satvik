"""Append-only ARCHIVE for the weekly-swing forward record — constitution D2.

The Saturday cron recomputes the entire book from inception every run, so the "forward record" is
mutable: a yfinance revision, a corporate-action re-adjustment, or a membership edit can change a
PAST weekly bar, hence a past signal, hence a past fill — silently rewriting history that the
Oct-1 gates are supposed to judge. The repo already documents that yfinance history drifts
(identical commands produced CAGR 14.2 / 15.6 / 16.25; see nq/data/ohlcv.py:file_sha256).

This module does NOT try to make yfinance immutable. It PINS AND MEASURES:

  * every run writes a dated, immutable snapshot under ``results/archive/<as_of>/`` containing the
    book (paper portfolio), the NAV series, the closed-trade ledger/history, the analytics, and a
    FINGERPRINT of the inputs (OHLCV cache sha256 + row/name counts, membership file sha256, index
    CSV sha256, engine config);
  * it then DIFFS this run against the most recent previous snapshot and appends one row per run to
    ``results/archive/drift_log.jsonl`` — closed-trade count delta, NAV delta, and crucially
    RESTATEMENTS: closed trades whose entry/exit price, date, or R changed retroactively, and
    trades that vanished from or appeared in history.

A restatement is not automatically wrong (a split re-adjustment legitimately re-bases prices), but
it must never be silent. Drift becomes a logged, attributable event.

Snapshots are write-once: an existing ``<as_of>`` directory is never overwritten (a re-run of the
same week is recorded as a re-run in the drift log, with the previous snapshot left intact).

    python scripts/archive_weekly_snapshot.py                 # archive + diff (cron step)
    python scripts/archive_weekly_snapshot.py --baseline      # label this the frozen baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import DATA_DIR, RESULTS_DIR  # noqa: E402

ARCHIVE_DIR = RESULTS_DIR / "archive"
DRIFT_LOG = ARCHIVE_DIR / "drift_log.jsonl"

# the run outputs that constitute "the record"
SNAPSHOT_FILES = (
    "signals_today_weekly.json",
    "signals_history_weekly.json",
    "signal_analytics_weekly.json",
    "paper_portfolio_weekly.json",
    "portfolio_history_weekly.csv",
    "weekly_review_scorecard.json",
)


def _sha256(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except Exception:
        return default


def input_fingerprint(results_dir: Path) -> dict:
    """Hashes + shapes of everything that can move a past bar. This is what makes a restatement
    attributable instead of mysterious."""
    from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache

    fp: dict = {
        "ohlcv_cache_sha256": _sha256(OHLCV_CACHE),
        "membership_csv_sha256": _sha256(DATA_DIR / "nifty500_membership.csv"),
        "nifty50_csv_sha256": _sha256(ROOT / "research" / "exports" / "benchmark_nifty50.csv"),
    }
    try:
        ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
        fp["ohlcv_n_names"] = len(ohlcv)
        fp["ohlcv_n_rows"] = int(sum(len(df) for df in ohlcv.values() if df is not None))
        last = [df.index[-1] for df in ohlcv.values() if df is not None and len(df)]
        fp["ohlcv_last_bar"] = str(max(last).date()) if last else None
    except Exception as exc:  # noqa: BLE001 — fingerprinting must never break the cron
        fp["ohlcv_error"] = f"{type(exc).__name__}: {exc}"
    try:
        from run_bhanushali_cron import (
            INCEPTION_DEFAULT,
            LIVE_DISCIPLINE,
            LIVE_EXIT,
            LIVE_STALENESS,
        )
        fp["engine"] = "run_bhanushali_weekly_rank (R94)"
        fp["inception_default"] = INCEPTION_DEFAULT
        fp["live_discipline"] = LIVE_DISCIPLINE
        fp["live_exit"] = LIVE_EXIT
        fp["live_staleness"] = LIVE_STALENESS
    except Exception as exc:  # noqa: BLE001
        fp["engine_error"] = f"{type(exc).__name__}: {exc}"
    return fp


def _closed_index(history: list) -> dict:
    """Closed trades keyed by (ticker, signal_date) -> the fields a restatement would move."""
    out = {}
    for h in history if isinstance(history, list) else []:
        if not isinstance(h, dict) or h.get("status") == "ACTIVE":
            continue
        key = f"{h.get('ticker')}|{h.get('signal_date')}"
        out[key] = {"entry": h.get("entry"), "close_price": h.get("close_price"),
                    "close_date": h.get("close_date"), "r_multiple": h.get("r_multiple"),
                    "status": h.get("status"), "exit_reason": h.get("exit_reason")}
    return out


def diff_snapshots(prev_dir: Path, cur_dir: Path) -> dict:
    """What moved between two snapshots — including RETROACTIVE restatements of closed trades."""
    pv_hist = _read_json(prev_dir / "signals_history_weekly.json", [])
    cu_hist = _read_json(cur_dir / "signals_history_weekly.json", [])
    pv, cu = _closed_index(pv_hist), _closed_index(cu_hist)

    restated = []
    for k in sorted(set(pv) & set(cu)):
        moved = {f: [pv[k][f], cu[k][f]] for f in pv[k] if pv[k][f] != cu[k][f]}
        if moved:
            restated.append({"trade": k, "changed": moved})
    vanished = sorted(set(pv) - set(cu))
    appeared = sorted(set(cu) - set(pv))

    pv_pf = _read_json(prev_dir / "paper_portfolio_weekly.json", {})
    cu_pf = _read_json(cur_dir / "paper_portfolio_weekly.json", {})
    pv_fp = _read_json(prev_dir / "input_fingerprint.json", {})
    cu_fp = _read_json(cur_dir / "input_fingerprint.json", {})
    inputs_moved = sorted(k for k in set(pv_fp) | set(cu_fp) if pv_fp.get(k) != cu_fp.get(k))

    def _nav(pf):
        try:
            return float(pf.get("total_value"))
        except (TypeError, ValueError):
            return None

    nav_prev, nav_cur = _nav(pv_pf), _nav(cu_pf)
    return {
        "prev_snapshot": prev_dir.name, "cur_snapshot": cur_dir.name,
        "closed_prev": len(pv), "closed_cur": len(cu),
        "closed_delta": len(cu) - len(pv),
        "nav_prev": nav_prev, "nav_cur": nav_cur,
        "nav_delta": (None if nav_prev is None or nav_cur is None else round(nav_cur - nav_prev, 2)),
        "n_restated": len(restated), "restated": restated,
        "n_vanished": len(vanished), "vanished": vanished,
        "n_appeared": len(appeared), "appeared": appeared,
        "inputs_changed": inputs_moved,
        "clean": not restated and not vanished,
    }


def latest_snapshot(exclude: str | None = None) -> Path | None:
    if not ARCHIVE_DIR.exists():
        return None
    dirs = sorted((d for d in ARCHIVE_DIR.iterdir()
                   if d.is_dir() and d.name != exclude and (d / "input_fingerprint.json").exists()),
                  key=lambda d: d.name)
    return dirs[-1] if dirs else None


def archive(results_dir: Path = RESULTS_DIR, *, baseline: bool = False) -> dict:
    env = _read_json(results_dir / "signals_today_weekly.json", {})
    as_of = env.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / str(as_of)

    prev = latest_snapshot(exclude=str(as_of))
    rerun = dest.exists()
    if rerun:
        # write-once: never overwrite an existing dated snapshot
        dest = ARCHIVE_DIR / f"{as_of}__rerun-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    dest.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in SNAPSHOT_FILES:
        src = results_dir / name
        if src.exists():
            shutil.copy2(src, dest / name)
            copied.append(name)
    (dest / "input_fingerprint.json").write_text(
        json.dumps(input_fingerprint(results_dir), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    (dest / "snapshot_meta.json").write_text(json.dumps({
        "as_of": as_of, "archived_utc": datetime.now(timezone.utc).isoformat(),
        "files": copied, "is_rerun_of_existing_as_of": rerun,
        "is_baseline": bool(baseline),
        "note": ("Immutable snapshot of the weekly-swing forward record (constitution D2). The "
                 "working copy in results/ is recomputed from inception every Saturday and is "
                 "therefore mutable; THIS is the artifact the Oct-1 gates should read."),
    }, indent=2) + "\n", encoding="utf-8")

    d = diff_snapshots(prev, dest) if prev else {
        "prev_snapshot": None, "cur_snapshot": dest.name, "clean": True,
        "note": "first snapshot — no predecessor to diff against",
    }
    d["as_of"] = as_of
    d["logged_utc"] = datetime.now(timezone.utc).isoformat()
    d["is_baseline"] = bool(baseline)
    with open(DRIFT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(d, default=str) + "\n")
    (dest / "drift_vs_prev.json").write_text(json.dumps(d, indent=2, default=str) + "\n",
                                             encoding="utf-8")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="archive + drift-check the weekly-swing record")
    ap.add_argument("--results-dir", default=str(RESULTS_DIR))
    ap.add_argument("--baseline", action="store_true",
                    help="label this snapshot the frozen baseline artifact")
    args = ap.parse_args(argv)

    d = archive(Path(args.results_dir), baseline=args.baseline)
    print(f"archived {d['cur_snapshot']} (as-of {d['as_of']})"
          + ("  [BASELINE]" if d.get("is_baseline") else ""))
    if d.get("prev_snapshot"):
        print(f"  vs {d['prev_snapshot']}: closed {d['closed_prev']} -> {d['closed_cur']} "
              f"({d['closed_delta']:+d}) | NAV delta {d['nav_delta']}")
        print(f"  restated {d['n_restated']} | vanished {d['n_vanished']} | appeared {d['n_appeared']}")
        if d["inputs_changed"]:
            print(f"  inputs changed: {', '.join(d['inputs_changed'])}")
        for r in d["restated"][:10]:
            print(f"    RESTATED {r['trade']}: {r['changed']}")
        if not d["clean"]:
            print("  ** NOT CLEAN — a past trade was rewritten; attribute it before the next gate read **")
    else:
        print("  (first snapshot — baseline for all future drift measurement)")
    print(f"-> {DRIFT_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
