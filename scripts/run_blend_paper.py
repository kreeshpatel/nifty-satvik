"""Forward paper logger for the swing x low-vol BLEND hybrid (finding 0107, registered
forward/prereg_swing.md as a WATCHED book).

OBSERVATIONAL ONLY. Writes results/blend_hybrid_paper.json. It does NOT touch the certified swing paper
book (results/paper_portfolio_weekly.json) or the hash-chained momentum wall — the forward wall is the
certifier and a new sleeve must never risk corrupting it. This logger just combines two independently-
computed NAV streams at the frozen 0081 ERC weight:
  * swing NAV  = results/portfolio_history_weekly.csv (the live A-only paper book, run_bhanushali_cron.py)
  * low-vol NAV = run_backtest(low-vol sleeve, frozen cfg) from the same inception forward

Like the swing book, it is EMPTY until fresh post-inception bars exist (the research OHLCV cache lags; the
real cron downloads). ERC weight defaults to 0.5 until 63 sessions of forward vol accrue, then inverse-vol.

    python scripts/run_blend_paper.py --start 2026-07-04
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from config import RESULTS_DIR, load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, run_backtest  # noqa: E402

OUT = RESULTS_DIR / "blend_hybrid_paper.json"
INCEPTION = "2026-07-04"


def _lowvol_nav(start: str) -> pd.Series:
    """Low-vol sleeve equity curve from `start` forward (frozen cfg, inverse-63d-vol ranker — 0081)."""
    cfg = load_frozen_cfg(); ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    rv = pd.concat([pd.DataFrame({"date": pd.to_datetime(g.index), "ticker": t,
                                  "rvol": g["Close"].pct_change().rolling(63).std().to_numpy()})
                    for t, g in ohlcv.items()], ignore_index=True)
    lv = panel.merge(rv, on=["date", "ticker"], how="left").copy()
    lv["trend_rank"] = (-lv["rvol"]).groupby(lv["date"]).rank(pct=True)
    return run_backtest(lv, cfg, start=start, end=str(pd.Timestamp.today().date()))["equity_curve"]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default=INCEPTION)
    args = ap.parse_args()

    sw_path = RESULTS_DIR / "portfolio_history_weekly.csv"
    swing = (pd.read_csv(sw_path, parse_dates=["date"]).set_index("date")["total_value"]
             if sw_path.exists() else pd.Series(dtype=float))
    lvnav = _lowvol_nav(args.start)
    lvnav = pd.Series(lvnav, dtype=float) if not isinstance(lvnav, pd.Series) else lvnav
    if len(lvnav):
        lvnav.index = pd.to_datetime(lvnav.index)
        lvnav = lvnav[lvnav.index >= pd.Timestamp(args.start)]
    swing.index = pd.to_datetime(swing.index)

    idx = (swing.index.intersection(lvnav.index) if (len(swing) and len(lvnav))
           else pd.DatetimeIndex([]))
    state = {"model": "swing x low-vol ERC blend (0107, WATCHED)", "inception": args.start,
             "observational": True, "n_points": int(len(idx))}
    if len(idx) >= 2:
        sr = swing.reindex(idx).pct_change(); lr = _daily_returns(lvnav).reindex(idx)
        vm, vl = sr.rolling(63).std().shift(1), lr.rolling(63).std().shift(1)
        w = ((1 / vm) / (1 / vm + 1 / vl)).clip(0, 1).fillna(0.5)   # ERC once 63d accrues, else 0.5
        br = (w * sr + (1 - w) * lr).fillna(0.0)
        nav = 1_000_000.0 * (1 + br).cumprod()
        state.update(asof=str(idx[-1].date()), blend_nav=round(float(nav.iloc[-1]), 2),
                     swing_nav=round(float(swing.reindex(idx).iloc[-1]), 2),
                     lowvol_nav=round(float(lvnav.reindex(idx).iloc[-1]), 2),
                     swing_weight=round(float(w.iloc[-1]), 3))
        note = f"blend NAV {state['blend_nav']:,.0f} over {len(idx)} pts (asof {state['asof']})"
    else:
        state["note"] = ("awaiting fresh post-inception bars in BOTH sleeves (research OHLCV cache lags "
                         f"inception {args.start}; the real cron downloads) — empty is valid, not an error")
        note = state["note"]
    OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"blend paper logger (observational): {note}\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
