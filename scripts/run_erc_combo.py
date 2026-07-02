"""Pre-reg 0081 — momentum + low-vol at equal-risk-contribution vs momentum alone (the multi-sleeve test).

Build two book return series over the pinned window (r_mom = frozen base; r_lv = low-vol sole-ranker
sleeve, O-016), combine at quarterly inverse-vol (2-asset risk-parity) weights, and test the combined
series vs momentum-alone: block-bootstrap ΔSharpe/ΔSortino + DSR + the correlation that drives the
diversification. A PROMOTE routes low-vol to the forward wall, not the cfg. Writes erc_combo_0081.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, _dsr_from_bootstrap, run_backtest  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sharpe, sortino  # noqa: E402

START, END, NT = "2017-01-01", "2026-06-30", 98


def m(r: pd.Series) -> dict[str, float]:
    r = r.dropna()
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min() * 100)
    cagr = float((eq.iloc[-1] ** (252.0 / len(r)) - 1.0) * 100)
    dn = r[r < 0]
    return {"sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3),
            "sortino": round(float(r.mean() / dn.std() * np.sqrt(252)) if len(dn) and dn.std() else float("nan"), 3),
            "maxdd": round(dd, 1), "cagr": round(cagr, 1),
            "calmar": round(cagr / abs(dd), 2) if dd else float("nan")}


def erc(rm: pd.Series, rl: pd.Series) -> pd.Series:
    """Combined return: quarterly inverse-vol weights (trailing-63d, as-of the prior day), held the quarter."""
    common = rm.index.intersection(rl.index)
    df = pd.DataFrame({"rm": rm.loc[common], "rl": rl.loc[common]}, index=common)
    inv_m = 1.0 / df["rm"].rolling(63).std().shift(1)
    inv_l = 1.0 / df["rl"].rolling(63).std().shift(1)
    df["w"] = inv_m / (inv_m + inv_l)
    df["qtr"] = df.index.to_period("Q")
    df["w_q"] = df.groupby("qtr")["w"].transform("first").fillna(0.5)   # weight fixed at quarter start
    return (df["w_q"] * df["rm"] + (1.0 - df["w_q"]) * df["rl"]).rename("rc")


def live22(r: pd.Series) -> float:
    r = r[r.index >= pd.Timestamp("2022-01-01")].dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() else float("nan")


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])

    # low-vol sleeve: rank by inverse realized-63d vol
    rv = pd.concat([pd.DataFrame({"date": pd.to_datetime(g.index), "ticker": t,
                                  "rvol": g["Close"].pct_change().rolling(63).std().to_numpy()})
                    for t, g in ohlcv.items()], ignore_index=True)
    lv_panel = panel.merge(rv, on=["date", "ticker"], how="left").copy()
    lv_panel["trend_rank"] = (-lv_panel["rvol"]).groupby(lv_panel["date"]).rank(pct=True)

    r_mom = _daily_returns(run_backtest(panel, cfg, start=START, end=END)["equity_curve"])
    r_lv = _daily_returns(run_backtest(lv_panel, cfg, start=START, end=END)["equity_curve"])
    r_c = erc(r_mom, r_lv)

    common = r_mom.index.intersection(r_lv.index)
    rho = float(r_mom.loc[common].corr(r_lv.loc[common]))
    a = r_c.loc[r_c.index.intersection(r_mom.index)].dropna().to_numpy(float)
    b = r_mom.loc[r_c.dropna().index].to_numpy(float)
    dsh = bootstrap_delta(a, b, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dso = bootstrap_delta(a, b, sortino, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    ci = block_bootstrap_metric(a, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(a, NT, (ci.lower, ci.upper))

    mm, ml, mc = m(r_mom), m(r_lv), m(r_c)
    promote = (dsh.lower > 0 and dsh.point > 0.10 and dsr > 0.95 and mc["calmar"] - mm["calmar"] >= 0.05
               and live22(r_c) > live22(r_mom) and rho < 0.7)
    verdict = "PROMOTE-CANDIDATE" if promote else ("KILL" if (dsh.lower <= 0 and dsh.point <= 0) else "UNDERPOWERED")

    print(f"\ncorr(momentum, low-vol) = {rho:+.3f}   (< 0.7 = real diversification)")
    print(f"{'book':<12}{'Sharpe':>8}{'Sortino':>8}{'CAGR':>7}{'MaxDD':>8}{'Calmar':>8}{'22-26 Sh':>10}")
    for tag, mm_, r in (("momentum", mm, r_mom), ("low-vol", ml, r_lv), ("COMBINED", mc, r_c)):
        print(f"{tag:<12}{mm_['sharpe']:>8.3f}{mm_['sortino']:>8.3f}{mm_['cagr']:>7.1f}"
              f"{mm_['maxdd']:>8.1f}{mm_['calmar']:>8.2f}{live22(r):>10.3f}")
    print(f"\ncombined vs momentum: dSharpe {dsh.point:+.3f} [{dsh.lower:+.2f},{dsh.upper:+.2f}]   "
          f"dSortino {dso.point:+.3f} [{dso.lower:+.2f},{dso.upper:+.2f}]   DSR {dsr:.2f}   -> {verdict}")

    out = {"prereg": "0081", "n_trials": NT, "corr": round(rho, 3), "verdict": verdict,
           "momentum": mm, "lowvol": ml, "combined": mc,
           "momentum_22_26_sharpe": round(live22(r_mom), 3), "combined_22_26_sharpe": round(live22(r_c), 3),
           "dSharpe": round(dsh.point, 3), "dSharpe_ci": [round(dsh.lower, 3), round(dsh.upper, 3)],
           "dSortino": round(dso.point, 3), "dsr": round(float(dsr), 3)}
    p = ROOT / "research" / "exports" / "erc_combo_0081.json"
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
