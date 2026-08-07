"""M6 — demerger / corporate-action suspect scan over the LIVE swing cache (read-only).

Constitution B-8: the swing path runs NO OHLCV cleaner. `clean_ohlcv_for_features` (holiday phantom
bars, zero-volume placeholders, split back-adjustment, bad-tick drop, CA-aware demerger handling)
and the `demerger_suspect_names` quarantine guard are wired into the MOMENTUM path only. The swing
engine trusts yfinance's adjustment plus the cron's >0.5%-overlap re-fetch guard.

A value-leaving demerger mid-hold shows up as a huge red weekly bar: it can drag the 44-week SMA,
trigger a spurious stop or runner sma_break, or manufacture a fake "touch" that fires an entry.

This scan is read-only and changes nothing: it runs the EXISTING `demerger_suspect` detector over
the live cache and intersects the suspects with (a) the book's current holdings, (b) this week's
cards, and (c) the current index universe. Nothing is quarantined — the swing engine has no
quarantine hook, and adding one is an owner decision.

    python scripts/diag_m6_demerger_scan.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from config import NIFTY_500, RESULTS_DIR  # noqa: E402
from nq.data.ohlcv import (  # noqa: E402
    DEMERGER_DROP_THRESH,
    DEMERGER_LOOKBACK_BARS,
    OHLCV_CACHE,
    file_sha256,
    demerger_suspect_names,
    load_demerger_reference,
    load_ohlcv_cache,
)


def _read(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except Exception:
        return default


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M6 demerger-suspect scan (read-only)")
    ap.add_argument("--json", default=str(ROOT / "diagnostics" / "research" / "m6_demerger_scan.json"))
    args = ap.parse_args(argv)

    ohlcv = load_ohlcv_cache(OHLCV_CACHE) or {}
    suspects = sorted(demerger_suspect_names(ohlcv))
    ref = load_demerger_reference()

    env = _read(RESULTS_DIR / "signals_today_weekly.json", {})
    pf = _read(RESULTS_DIR / "paper_portfolio_weekly.json", {})
    cards = sorted({s.get("ticker") for s in env.get("signals", []) if s.get("ticker")})
    held = sorted(pf.get("positions") or {})
    universe = sorted(set(NIFTY_500))

    hits_held = sorted(set(suspects) & set(held))
    hits_cards = sorted(set(suspects) & set(cards))
    hits_universe = sorted(set(suspects) & set(universe))

    rep = {
        "ohlcv_sha256_prefix": file_sha256()[:16],
        "n_names_scanned": len(ohlcv),
        "detector": {"lookback_bars": DEMERGER_LOOKBACK_BARS,
                     "drop_threshold": DEMERGER_DROP_THRESH,
                     "source": "nq.data.ohlcv.demerger_suspect (existing momentum-path guard)"},
        "n_suspects": len(suspects), "suspects": suspects,
        "suspects_in_current_holdings": hits_held,
        "suspects_on_this_weeks_cards": hits_cards,
        "suspects_in_index_snapshot": hits_universe,
        "known_demerger_reference_names": sorted(ref),
        "swing_path_applies_cleaner": False,
        "swing_path_applies_quarantine": False,
        "note": ("Read-only. The swing engine has no cleaner and no quarantine hook; wiring either "
                 "is an owner decision (constitution B-8). Nothing here was acted on."),
        "verdict": ("CLEAR — no suspect touches the live book or cards"
                    if not hits_held and not hits_cards else
                    "ATTENTION — a suspect intersects the live book or cards"),
    }
    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")

    print(f"=== M6 demerger-suspect scan === {len(ohlcv)} names, cache {rep['ohlcv_sha256_prefix']}")
    print(f"detector: >={DEMERGER_DROP_THRESH:.0%} single-session drop within {DEMERGER_LOOKBACK_BARS} bars, "
          f"non-reverting")
    print(f"suspects: {len(suspects)} -> {suspects[:20]}{' …' if len(suspects) > 20 else ''}")
    print(f"  in current holdings ({len(held)}): {hits_held or 'none'}")
    print(f"  on this week's cards ({len(cards)}): {hits_cards or 'none'}")
    print(f"  in the index snapshot: {len(hits_universe)}")
    print(f"  committed demerger reference: {sorted(ref) or 'empty'}")
    print(f"VERDICT: {rep['verdict']}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
