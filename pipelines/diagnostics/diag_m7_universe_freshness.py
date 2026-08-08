"""M7 — universe freshness: NIFTY_500 snapshot vs the membership CSV (read-only).

Constitution B-1(data)/B-10/D1: the live book scans `config.NIFTY_500`, a hard-coded snapshot dated
2025-07-20, intersected at card/entry time with `data/nifty500_membership.csv` (manually refreshed).
Post-snapshot index entrants can never signal; names the index dropped keep trading until the
membership file says otherwise. The September semi-annual NSE rebalance lands BEFORE the Oct-1
review, so the gap matters now.

This reports, offline and read-only:
  * NIFTY_500 snapshot size vs the membership file's CURRENTLY-ACTIVE set, and both directions of
    the difference (in-snapshot-but-not-active = likely index exits still scannable;
    active-but-not-in-snapshot = current members the live scan can never see);
  * the sentinel handling check — how many active rows carry the open-ended 2030-12-31 to_date vs a
    real future date, since `current_members()` treats both as active and a mis-parsed sentinel
    would silently empty the universe;
  * membership file mtime / row counts, and coverage of both sets by the live OHLCV cache.

An optional `--fetch-nse` attempts the live NSE constituent list; it is OFF by default and degrades
to a clearly-labelled offline report if the request is blocked (the NSE bot-wall is documented in
this repo). Nothing is written to the universe; this is a report.

    python scripts/diag_m7_universe_freshness.py [--fetch-nse] [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import NIFTY_500  # noqa: E402
from nq.data.membership import (  # noqa: E402
    MEMBERSHIP_PATH,
    current_members,
    load_membership,
    membership_stats,
)
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

SENTINEL = "2030-12-31"


def _fetch_nse() -> tuple[list[str] | None, str]:
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        import io

        import pandas as pd
        import requests
        hdr = {"User-Agent": "Mozilla/5.0", "Accept": "*/*",
               "Referer": "https://www.nseindia.com/"}
        r = requests.get(url, headers=hdr, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} (NSE bot-wall / archive unavailable)"
        df = pd.read_csv(io.StringIO(r.text))
        col = next((c for c in df.columns if "symbol" in c.lower()), None)
        if col is None:
            return None, "unexpected CSV schema (no Symbol column)"
        return sorted({str(s).strip().upper() for s in df[col] if str(s).strip()}), "ok"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M7 universe freshness (read-only)")
    ap.add_argument("--fetch-nse", action="store_true",
                    help="attempt the live NSE constituent list (bot-wall tolerated)")
    ap.add_argument("--json", default=str(ROOT / "diagnostics" / "research" / "m7_universe_freshness.json"))
    args = ap.parse_args(argv)

    mem = load_membership()
    active = current_members(mem)
    snap = set(NIFTY_500)
    stats = membership_stats(mem)

    # sentinel handling: how many active periods use the open-ended 2030 marker
    n_sentinel = n_real_future = 0
    today = date.today()
    for periods in (mem or {}).values():
        for _f, t in periods:
            if t.isoformat() == SENTINEL:
                n_sentinel += 1
            elif t >= today:
                n_real_future += 1

    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    cached = set(ohlcv)

    only_snap = sorted(snap - active)
    only_active = sorted(active - snap)

    rep = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot": {"source": "config.NIFTY_500", "dated": "2025-07-20", "n": len(snap)},
        "membership_file": {
            "path": str(MEMBERSHIP_PATH.relative_to(ROOT)),
            "mtime": datetime.fromtimestamp(MEMBERSHIP_PATH.stat().st_mtime,
                                            tz=timezone.utc).isoformat()
            if MEMBERSHIP_PATH.exists() else None,
            "n_tickers": stats.get("n_tickers"), "n_period_rows": stats.get("n_period_rows"),
            "n_active_today": len(active),
            "sentinel_2030_rows": n_sentinel, "real_future_to_date_rows": n_real_future,
            "sentinel_parse_ok": bool(n_sentinel > 0 and len(active) > 0),
        },
        "in_snapshot_not_active": {"n": len(only_snap), "tickers": only_snap},
        "active_not_in_snapshot": {"n": len(only_active), "tickers": only_active},
        "cache_coverage": {
            "n_cached": len(cached),
            "snapshot_missing_from_cache": sorted(snap - cached)[:50],
            "n_snapshot_missing_from_cache": len(snap - cached),
            "active_missing_from_cache": sorted(active - cached)[:50],
            "n_active_missing_from_cache": len(active - cached),
        },
        "note": ("Read-only. The live scan universe is the SNAPSHOT; membership only masks it. A "
                 "name in active_not_in_snapshot can never produce a live signal regardless of "
                 "membership (constitution D1)."),
    }

    if args.fetch_nse:
        nse, status = _fetch_nse()
        rep["nse_live"] = {"status": status, "n": (len(nse) if nse else None)}
        if nse:
            rep["nse_live"].update(
                nse_not_in_snapshot=sorted(set(nse) - snap),
                snapshot_not_in_nse=sorted(snap - set(nse)),
                nse_not_active_in_membership=sorted(set(nse) - active),
                membership_active_not_in_nse=sorted(active - set(nse)))
    else:
        rep["nse_live"] = {"status": "not attempted (offline report; pass --fetch-nse to try)"}

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2, default=str) + "\n", encoding="utf-8")

    print("=== M7 universe freshness ===")
    print(f"snapshot config.NIFTY_500 (2025-07-20): {len(snap)}")
    print(f"membership active today: {len(active)} (file mtime {rep['membership_file']['mtime']})")
    print(f"  sentinel 2030 rows {n_sentinel} | real future to_date rows {n_real_future} | "
          f"parse ok {rep['membership_file']['sentinel_parse_ok']}")
    print(f"in snapshot but NOT active: {len(only_snap)} -> {only_snap[:15]}")
    print(f"active but NOT in snapshot (invisible to the live scan): {len(only_active)} -> {only_active[:15]}")
    print(f"cache: {len(cached)} names | snapshot missing {rep['cache_coverage']['n_snapshot_missing_from_cache']} "
          f"| active missing {rep['cache_coverage']['n_active_missing_from_cache']}")
    print(f"NSE live: {rep['nse_live']['status']}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
