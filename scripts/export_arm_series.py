"""Export per-arm daily series + trade logs for 0078 (base + blend/veto arms) for external analysis.

For each book (base, blend λ=0.25/0.50, veto q=0.20/0.10) writes the daily return/equity path and the
full trade log, plus a manifest of recomputed metrics — so a downstream analysis can VERIFY every
headline (Sharpe/Sortino/skew/DD/vol/vol-match) independently and research the arm, not the base.

Outputs (research/exports/):
  arm_daily_returns.csv   — date + {arm}_ret / {arm}_eq / {arm}_npos for all 5 books (wide)
  arm_tradelogs.csv       — long: arm, entry_date, exit_date, symbol, trade_ret, exit_reason, hold_days, pnl
  arm_series_manifest.json — params + recomputed metrics per arm
  ff_india_factors.csv    — the Market+HML factor series (CSV copy of the parquet), for residual verification
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

from config import DATA_DIR, load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _after_tax_cagr, run_backtest  # noqa: E402
from run_residual_blend_veto import live_dd, make_arm, skew  # noqa: E402
from run_residual_momentum import residual_ranks  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
REASON = {"stop": "atr_stop", "time": "time_exit", "target": "target", "trailing": "trailing", "stale": "stale"}
ARMS = [("base", None, None), ("blend-0.25", "blend", 0.25), ("blend-0.5", "blend", 0.5),
        ("veto-0.2", "veto", 0.20), ("veto-0.1", "veto", 0.10)]


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    factors = pd.read_parquet(DATA_DIR / "ff_india_factors.parquet").set_index("date").sort_index()
    print("residualizing ...", flush=True)
    rr = residual_ranks(panel, factors)

    exp = ROOT / "research" / "exports"
    daily = None
    trades = []
    manifest = {}
    for name, kind, p in ARMS:
        pnl_panel = panel if kind is None else make_arm(panel, rr, kind, p)
        bt = run_backtest(pnl_panel, cfg, start=START, end=END)
        ec = bt["equity_curve"]
        s = pd.DataFrame({"date": pd.to_datetime([e["date"] for e in ec]),
                          f"{name}_eq": [e["equity"] for e in ec],
                          f"{name}_npos": [e["n_positions"] for e in ec]})
        s[f"{name}_ret"] = s[f"{name}_eq"].pct_change()
        daily = s if daily is None else daily.merge(s, on="date", how="outer")
        for t in bt["trades"]:
            trades.append({"arm": name, "entry_date": t["entry_date"], "exit_date": t["exit_date"],
                           "symbol": t["ticker"], "trade_ret": round(t["return_pct"] / 100.0, 6),
                           "exit_reason": REASON.get(t["reason"], t["reason"]),
                           "hold_days": t["days_held"], "pnl": round(t["pnl"], 2)})
        m = bt["metrics"]
        r = s[f"{name}_ret"].to_numpy()
        rs = pd.Series(r, index=s["date"]).dropna()
        manifest[name] = {"kind": kind, "param": p, "gross_cagr": m["cagr_pct"],
                          "after_tax_cagr": _after_tax_cagr(bt, 1e6), "sharpe": m["sharpe"],
                          "sortino": m["sortino"], "calmar": m["calmar"], "max_dd": m["max_drawdown_pct"],
                          "skew_daily": round(skew(r), 3), "ann_vol": round(float(rs.std() * np.sqrt(252)), 3),
                          "live_dd_2022_26": round(live_dd(rs), 1), "n_trades": m["n_trades"],
                          "win_rate": m["win_rate_pct"], "exit_reasons": m.get("exit_reasons", {})}
        print(f"  {name:<11} CAGR {m['cagr_pct']:.1f}  Sortino {m['sortino']:.3f}  "
              f"skew {skew(r):+.3f}  liveDD {live_dd(rs):.1f}  nTr {m['n_trades']}", flush=True)

    daily = daily.sort_values("date")
    cols = ["date"] + [f"{n}_{x}" for n, _, _ in ARMS for x in ("ret", "eq", "npos")]
    daily["date"] = daily["date"].dt.strftime("%Y-%m-%d")
    daily[cols].to_csv(exp / "arm_daily_returns.csv", index=False, float_format="%.8g")
    pd.DataFrame(trades).to_csv(exp / "arm_tradelogs.csv", index=False)
    factors.reset_index().to_csv(exp / "ff_india_factors.csv", index=False, float_format="%.8g")
    (exp / "arm_series_manifest.json").write_text(
        json.dumps({"anchor": "baseline_v1 dataset-pin-20260701", "window": [START, END],
                    "note": "arm books are full-period 2017-2026; base = sma200_slope_63; "
                            "veto/blend inject residual momentum. live_dd is the 2022-26 slice.",
                    "arms": manifest}, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote arm_daily_returns.csv ({len(daily)} rows), arm_tradelogs.csv ({len(trades)} trades), "
          f"ff_india_factors.csv, arm_series_manifest.json  -> {exp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
