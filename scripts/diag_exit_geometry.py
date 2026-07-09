"""In-sample DIAGNOSTIC: reveal the latent right tail the fixed 22.52% target truncates.

Loads the pinned panel once, then re-runs the frozen backtest under exit-geometry variants and
reports headline metrics + right-tail trade stats. This is a MEASUREMENT, not a promotion — every
variant is an in-sample re-fit and must clear the walk-forward promotion bar before it is trusted.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

from config import load_frozen_cfg
from nq.data.membership import load_membership
from nq.data.features import compute_all_features
from nq.data.fundamentals import load_fund_store
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import simulate
from run_cpcv import build_universe

START, END = "2017-01-01", "2026-06-30"


def tail(trades):
    r = np.array([t["return_pct"] / 100.0 for t in trades], dtype=float)
    return dict(n=len(r), maxr=r.max(), p95=np.percentile(r, 95), p99=np.percentile(r, 99),
                gt225=int((r > 0.225).sum()), gt30=int((r > 0.30).sum()), gt50=int((r > 0.50).sum()),
                mean_win=r[r > 0].mean(), skew=float(((r - r.mean()) ** 3).mean() / r.std() ** 3))


def run(panel, cfg, **over):
    c = dict(cfg); c.update(over)
    bt = simulate(panel, c, start=START, end=END)
    m, t = bt["metrics"], tail(bt["trades"])
    return m, t


def main():
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())

    variants = {
        "base (target=22.52)": {},
        "uncapped (target=999)": {"target_pct": 999.0},
        "uncapped + wider trail 8%": {"target_pct": 999.0, "trailing_pct": 8.0},
        "uncapped + wider trail 12%": {"target_pct": 999.0, "trailing_pct": 12.0},
        "target=30 (0071 dir.)": {"target_pct": 30.0},
        "tighter stop 2.5x ATR": {"stop_atr_mult": 2.5},
    }
    hdr = (f"{'variant':<28}{'CAGR':>7}{'Shrp':>7}{'Sort':>7}{'MaxDD':>8}{'Calm':>6}"
           f"{'WR%':>6}{'nTr':>6}{'maxR':>7}{'>22.5':>6}{'>30':>5}{'>50':>5}{'p99':>7}{'mWin':>7}")
    print("\n" + hdr); print("-" * len(hdr))
    for name, over in variants.items():
        m, t = run(panel, cfg, **over)
        print(f"{name:<28}{m['cagr_pct']:>7.1f}{m['sharpe']:>7.3f}{m['sortino']:>7.3f}"
              f"{m['max_drawdown_pct']:>8.1f}{m['calmar']:>6.2f}{m['win_rate_pct']:>6.1f}"
              f"{m['n_trades']:>6}{t['maxr']*100:>6.1f}%{t['gt225']:>6}{t['gt30']:>5}"
              f"{t['gt50']:>5}{t['p99']*100:>6.1f}%{t['mean_win']*100:>6.1f}%", flush=True)
    print("\nNOTE: in-sample diagnostic only; walk-forward + DSR + block-bootstrap dSortino "
          "required before any of these is trusted (promotion bar).")


if __name__ == "__main__":
    main()
