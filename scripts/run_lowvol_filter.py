"""Pre-reg 0080 — trend ranked, low-vol FILTERED: keep the slope ranker, drop the high-vol names first.

Each day: mark ineligible any name whose realized-63d vol is above the cutoff quantile, then rank the
remainder by the incumbent sma200_slope_63. Distinct from O-006 (low-vol signal-blend) and O-016 (low-vol
sole ranker) — a conditional universe filter. 2 fixed cutoffs. Full fresh-trade backtest, paired vs base.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import (_daily_returns, _dsr_from_bootstrap, _fold_pass,  # noqa: E402
                                _subperiod_cagr, run_backtest)
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sharpe, sortino  # noqa: E402

START, END, NT = "2017-01-01", "2026-06-30", 97
CUTOFFS = [0.50, 0.33]


def slice_sh(ec, s, e):
    q = pd.Series([r["equity"] for r in ec], index=pd.to_datetime([r["date"] for r in ec]), dtype=float)
    q = q[(q.index >= pd.Timestamp(s)) & (q.index <= pd.Timestamp(e))]
    r = q.pct_change().dropna()
    return (r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
            float((q / q.cummax() - 1).min() * 100))


def skew(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float((((x - x.mean()) / x.std()) ** 3).mean()) if x.size > 8 and x.std() else float("nan")


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    rv = pd.concat([pd.DataFrame({"date": pd.to_datetime(g.index), "ticker": t,
                                  "rvol": g["Close"].pct_change().rolling(63).std().to_numpy()})
                    for t, g in ohlcv.items()], ignore_index=True)
    panel = panel.merge(rv, on=["date", "ticker"], how="left")
    panel["rvol_pct"] = panel.groupby("date")["rvol"].rank(pct=True)

    base_bt = run_backtest(panel, cfg, start=START, end=END)
    b = _daily_returns(base_bt["equity_curve"])
    bm = base_bt["metrics"]
    b22 = slice_sh(base_bt["equity_curve"], "2022-01-01", END)
    print(f"\nBASE  Sharpe {bm['sharpe']:.3f}  Sortino {bm['sortino']:.3f}  CAGR {bm['cagr_pct']:.1f}  "
          f"DD {bm['max_drawdown_pct']:.1f}  skew {skew(b.to_numpy()):+.3f}  | 22-26 Sh {b22[0]:.3f} DD {b22[1]:.1f}")
    hdr = f"{'cutoff':<10}{'Sharpe':>8}{'Sortino':>8}{'CAGR':>7}{'DD':>7}{'dSharpe [CI]':>22}{'dSort':>8}{'DSR':>6}{'22-26Sh':>9}{'22-26DD':>9}{'fold':>6}  verdict"
    print("\n" + hdr)
    print("-" * len(hdr))
    out = []
    for q in CUTOFFS:
        cand = panel.copy()
        cand.loc[cand["rvol_pct"] > q, "trend_rank"] = np.nan   # drop high-vol names; keep low-vol trend
        cb = run_backtest(cand, cfg, start=START, end=END)
        c = _daily_returns(cb["equity_curve"])
        cm = cb["metrics"]
        common = b.index.intersection(c.index)
        av, bv = c.loc[common].to_numpy(float), b.loc[common].to_numpy(float)
        dsh = bootstrap_delta(av, bv, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        dso = bootstrap_delta(av, bv, sortino, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        ci = block_bootstrap_metric(av, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        dsr = _dsr_from_bootstrap(av, NT, (ci.lower, ci.upper))
        c22 = slice_sh(cb["equity_curve"], "2022-01-01", END)
        d_cagr22 = ((_subperiod_cagr(cb["equity_curve"], "2022-01-01", END) or float("nan"))
                    - (_subperiod_cagr(base_bt["equity_curve"], "2022-01-01", END) or float("nan")))
        fold = _fold_pass(common, av, bv, 2019)[0]
        verdict = ("KILL" if (dsh.lower <= 0 or d_cagr22 <= 0) else
                   "PROMOTE?" if (dsh.point > 0.30 and dsr > 0.95) else "UNDERPOWERED")
        dsh_s = f"{dsh.point:+.3f}[{dsh.lower:+.2f},{dsh.upper:+.2f}]"
        print(f"keep<={q:<6.2f}{cm['sharpe']:>8.3f}{cm['sortino']:>8.3f}{cm['cagr_pct']:>7.1f}"
              f"{cm['max_drawdown_pct']:>7.1f}{dsh_s:>22}{dso.point:>+8.3f}{dsr:>6.2f}{c22[0]:>9.3f}"
              f"{c22[1]:>9.1f}{fold:>6.2f}  {verdict}", flush=True)
        out.append({"cutoff": q, "sharpe": cm["sharpe"], "sortino": cm["sortino"], "cagr": cm["cagr_pct"],
                    "dd": cm["max_drawdown_pct"], "skew": round(skew(av), 3),
                    "dSharpe": round(dsh.point, 3), "dSharpe_ci": [round(dsh.lower, 3), round(dsh.upper, 3)],
                    "dSortino": round(dso.point, 3), "dsr": round(float(dsr), 3),
                    "live22_sharpe": round(c22[0], 3), "live22_dd": round(c22[1], 1),
                    "sub22_dCAGR": round(float(d_cagr22), 3), "fold": round(float(fold), 3), "verdict": verdict})
    payload = {"prereg": "0080", "n_trials": NT,
               "base": {k: bm[k] for k in ("sharpe", "sortino", "cagr_pct", "max_drawdown_pct")},
               "base_live22": {"sharpe": round(b22[0], 3), "dd": round(b22[1], 1)}, "arms": out}
    p = ROOT / "research" / "exports" / "lowvol_filter_0080.json"
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
