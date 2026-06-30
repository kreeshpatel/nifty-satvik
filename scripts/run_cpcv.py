"""Canonical cloud research run — baseline reproduction + CPCV path distribution.

Runs on GitHub Actions (`.github/workflows/cpcv-research.yml`); yfinance is the data source. The
LOCAL universe is a degenerate ~20-survivor subset (~15% CAGR, inadmissible), so this cloud run is
the ONLY admissible source of headline numbers. It:

  1. assembles the universe (current NIFTY_500, or the union with current index members),
  2. downloads OHLCV (yfinance, cached to data/ohlcv.pkl so re-runs skip the network),
  3. builds the ranked eligible panel (membership → clean → large+mid → PIT D/E → solvency → rank),
  4. reproduces baseline_v0 via the frozen-cfg backtest (the F3.3 / Stage-A gate, ≤1pp on CAGR),
  5. runs the CPCV-over-time path distribution + Deflated Sharpe (the anti-overfit read),

then writes ``results/cpcv_long.json``.

CAVEATS this run still carries (label them when quoting): yfinance floors ~2015 + pre-2018
membership is survivor-biased (trust ≥2019); ~114 hard-bankruptcy delisted names are unrecoverable
from yfinance (the documented survivorship gap). The full corrected-universe build (delisted
rehydration → baseline_v1) is Stage B. Usage:

    python scripts/run_cpcv.py --mode current --start 2017-01-01
    python scripts/run_cpcv.py --mode union --start 2017-01-01 --end 2026-06-30
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import NIFTY_500, RESULTS_DIR, load_frozen_cfg  # noqa: E402
from nq.data.membership import current_members, load_membership  # noqa: E402


def _recoverable_delisted() -> set[str]:
    """Dropped-from-index tickers whose history yfinance can still serve (the survivorship
    rehydration set) — ``data/nse_circulars/dropped_available.csv`` rows with status OK. PIT
    membership later masks each to its real in-index dates. ~114 hard-bankruptcy names are NOT
    in here (yfinance 404) — the documented unrecoverable survivorship gap."""
    import csv
    from config import DATA_DIR
    out: set[str] = set()
    p = DATA_DIR / "nse_circulars" / "dropped_available.csv"
    if not p.exists():
        return out
    with open(p, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("status") or "").strip().upper() == "OK":
                t = (row.get("ticker") or "").strip().upper()
                if t:
                    out.add(t)
    return out


def build_universe(mode: str, ref_date: date | None = None) -> list[str]:
    """The download/backtest universe (PIT membership masks each name's in-index dates later).
      * ``current``   — the carried NIFTY_500 snapshot.
      * ``union``     — NIFTY_500 ∪ current index members (the AUD-007 fix).
      * ``corrected`` — union ∪ recoverable delisted names (the survivorship correction → the
                        Stage-A baseline_v1 universe). Financials are still dropped by the solvency
                        mask downstream (baseline_v0-consistent) until the capital-adequacy proxy
                        (W-04) is adopted as a separate, decided change."""
    if mode == "current":
        return list(NIFTY_500)
    members = current_members(load_membership(), ref_date)
    if mode == "union":
        return sorted(set(NIFTY_500) | members)
    if mode == "corrected":
        return sorted(set(NIFTY_500) | members | _recoverable_delisted())
    raise ValueError(f"unknown universe mode: {mode!r} (use current/union/corrected)")


def _anchor() -> dict:
    """baseline_v0 gross anchor (the reproduction target): {cagr_pct, sharpe}."""
    try:
        g = json.loads((ROOT / "research" / "baseline_v0.json").read_text(encoding="utf-8"))["gross"]
        return {"cagr_pct": g.get("cagr_pct"), "sharpe": g.get("sharpe")}
    except Exception:
        return {}


def _universe_diagnostics(panel, trades: list) -> dict:
    """Per-year breadth of the eligible (post-solvency) ranked panel vs the names actually traded —
    the A4 probe for the survivor-thin-historical-universe hypothesis (is 2017-2019 starved of
    names vs baseline_v0's ~397 solvent / corrected-682?)."""
    import pandas as pd

    p = panel.copy()
    p["year"] = pd.to_datetime(p["date"]).dt.year
    per_year_universe = {int(y): int(n) for y, n in p.groupby("year")["ticker"].nunique().items()}
    traded: dict[int, set] = {}
    for t in trades:
        y = int(str(t["entry_date"])[:4])
        traded.setdefault(y, set()).add(t["ticker"])
    return {
        "n_panel_names_total": int(p["ticker"].nunique()),
        "per_year_eligible_universe": per_year_universe,
        "per_year_distinct_names_traded": {y: len(s) for y, s in sorted(traded.items())},
        "total_distinct_names_traded": len({t["ticker"] for t in trades}),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Canonical cloud CPCV research run")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="current")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None, help="default: today")
    ap.add_argument("--out", default=str(RESULTS_DIR / "cpcv_long.json"))
    ap.add_argument("--cache", default=None, help="OHLCV pickle cache path (download if absent)")
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap resamples (smoke)")
    args = ap.parse_args(argv)

    # Heavy imports deferred so build_universe stays unit-testable without the data stack.
    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import OHLCV_CACHE, download_ohlcv, load_ohlcv_cache, save_ohlcv_cache
    from nq.engine.panel import compose_ranked_panel
    from nq.runner.research import _daily_returns, _dsr_from_bootstrap, run_backtest
    from nq.validation.bootstrap import block_bootstrap_metric
    from nq.validation.dsr import cumulative_n_trials
    from nq.validation.metrics import sharpe

    cfg = load_frozen_cfg()
    universe = build_universe(args.mode)
    end = args.end or date.today().isoformat()
    cache = Path(args.cache) if args.cache else OHLCV_CACHE

    ohlcv = load_ohlcv_cache(cache)
    if not ohlcv:
        print(f"downloading OHLCV for {len(universe)} names ({args.start}..{end}) ...", flush=True)
        ohlcv = download_ohlcv(universe, start=args.start, end=end)
        save_ohlcv_cache(ohlcv, cache)
    print(f"universe={args.mode} requested={len(universe)} with-data={len(ohlcv)}", flush=True)

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty — check data/membership/fundamentals", flush=True)
        return 1

    print("running backtest + block-bootstrap Sharpe CI + DSR ...", flush=True)
    bt = run_backtest(panel, cfg, start=args.start, end=end)
    m = bt["metrics"]
    rets = _daily_returns(bt["equity_curve"]).to_numpy(dtype=float)
    nt = cumulative_n_trials()
    ci = (block_bootstrap_metric(rets, sharpe, n_samples=(1000 if args.quick else 5000))
          if rets.size > 63 else None)
    dsr = _dsr_from_bootstrap(rets, nt, (ci.lower, ci.upper) if ci else None)
    diag = _universe_diagnostics(panel, bt["trades"])
    anchor = _anchor()
    anchor_cagr = anchor.get("cagr_pct")
    repro_delta = (round(abs(m.get("cagr_pct", 0.0) - anchor_cagr), 3)
                   if isinstance(anchor_cagr, (int, float)) else None)

    out: dict = {
        "config": {"mode": args.mode, "start": args.start, "end": end,
                   "n_requested": len(universe), "n_with_data": len(ohlcv),
                   "frozen_cfg": dict(cfg)},
        "baseline": m,
        "sharpe_point": round(ci.point, 3) if ci else None,
        "sharpe_ci_95": [round(ci.lower, 3), round(ci.upper, 3)] if ci else None,
        "dsr": dsr, "n_trials": nt, "n_obs": int(rets.size),
        "diagnostics": diag,
        "anchor_baseline_v0": {"cagr_pct": anchor_cagr, "sharpe": anchor.get("sharpe")},
        "reproduction_cagr_abs_delta_pp": repro_delta,
        "reproduction_within_1pp": (repro_delta is not None and repro_delta <= 1.0),
        "caveats": ["yfinance floors ~2015; pre-2018 membership survivor-biased (trust >=2019)",
                    "~114 hard-bankruptcy delisted names unrecoverable (survivorship gap)",
                    "current-universe run is survivor-biased; corrected baseline_v1 is Stage B"],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"baseline CAGR {m.get('cagr_pct')}% / Sharpe {m.get('sharpe')} "
          f"| anchor {anchor_cagr}% | delta {repro_delta}pp | within1pp "
          f"{out['reproduction_within_1pp']} -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
