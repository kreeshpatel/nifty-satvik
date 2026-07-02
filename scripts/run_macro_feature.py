"""Pre-reg 0082 — USD/INR-sensitivity as a rank-component TILT (the first PIT-clean orthogonal feature).

Tilt the momentum ranker AWAY from high-USD/INR-sensitivity names (confirmed NEGATIVE cross-sectional IC,
finding 0017): trend_rank <- pctile(trend_rank + lambda*(1 - usd_beta_rank)). usd_beta = trailing rolling-126d
beta of the stock's daily return on the clean `usd_trend` factor (nq.data.macro / macro_pit.parquet) — the
identical construction that carried the confirmed IC. Two fixed arms lambda={0.15,0.25}. Sign fixed by the IC,
not fit in-sample. Crude EXCLUDED (0017: crude-beta IC was a lookahead artifact). Panel re-ordering only, no
engine change (golden byte-identical). Primary window 2019-2026 (clean membership); 2017-2026 for context.

Paired 63d block-bootstrap dSharpe/dSortino vs base + DSR@100 + continuous-slice 2022-26 + >=2019 fold, per
the pre-committed 7-gate bar. A PROMOTE routes USD-sensitivity to the forward wall, never the frozen cfg.
Writes research/exports/macro_feature_0082.json.
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
from nq.data.macro import load_macro_pit  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import (_after_tax_cagr, _daily_returns, _dsr_from_bootstrap,  # noqa: E402
                                _fold_pass, _subperiod_cagr, run_backtest)
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sharpe, sortino  # noqa: E402

NT = 100
BETA_WIN, MP, MACRO_FAC = 126, 63, "usd_trend"   # trailing beta window / min_periods / the confirmed factor
LAMBDAS = [0.15, 0.25]
WINDOWS = [("2019-01-01", "2026-06-30", "PRIMARY"), ("2017-01-01", "2026-06-30", "context")]


def slice_sh(ec, s, e):
    q = pd.Series([r["equity"] for r in ec], index=pd.to_datetime([r["date"] for r in ec]), dtype=float)
    q = q[(q.index >= pd.Timestamp(s)) & (q.index <= pd.Timestamp(e))]
    r = q.pct_change().dropna()
    return (r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
            float((q / q.cummax() - 1).min() * 100))


def usd_beta_panel(panel: pd.DataFrame, ohlcv: dict, macro: pd.DataFrame) -> pd.DataFrame:
    """Per-(date,ticker) usd_beta_rank column: trailing-126d beta of stock return on the clean usd_trend."""
    fac = macro[MACRO_FAC]
    rows = []
    for tkr, gdf in ohlcv.items():
        idx = pd.to_datetime(gdf.index)
        ret = gdf["Close"].pct_change()
        fv = fac.reindex(idx)
        cov = ret.rolling(BETA_WIN, min_periods=MP).cov(fv)
        var = fv.rolling(BETA_WIN, min_periods=MP).var()
        rows.append(pd.DataFrame({"date": idx, "ticker": tkr, "usd_beta": (cov / var).to_numpy()}))
    b = pd.concat(rows, ignore_index=True)
    b["usd_beta_rank"] = b.groupby("date")["usd_beta"].rank(pct=True)
    return b[["date", "ticker", "usd_beta_rank"]]


def make_arm(panel: pd.DataFrame, betas: pd.DataFrame, lam: float) -> pd.DataFrame:
    c = panel.merge(betas, on=["date", "ticker"], how="left")
    # negative IC -> favor LOW usd-beta: macro_score = 1 - rank (fixed sign, not fit). Missing beta -> neutral 0.5.
    macro_score = 1.0 - c["usd_beta_rank"].fillna(0.5)
    c["trend_rank"] = (c["trend_rank"] + lam * macro_score).groupby(c["date"]).rank(pct=True)
    return c


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    macro = load_macro_pit()
    macro.index = pd.to_datetime(macro.index)
    print(f"panel build ({len(ohlcv)} names) + usd_beta ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    betas = usd_beta_panel(panel, ohlcv, macro)

    out = {"prereg": "0082", "n_trials": NT, "macro_factor": MACRO_FAC, "windows": {}}
    for start, end, tag in WINDOWS:
        base_bt = run_backtest(panel, cfg, start=start, end=end)
        b = _daily_returns(base_bt["equity_curve"])
        bm = base_bt["metrics"]
        b22 = slice_sh(base_bt["equity_curve"], "2022-01-01", end)
        base_sub22 = _subperiod_cagr(base_bt["equity_curve"], "2022-01-01", end)
        base_atx = _after_tax_cagr(base_bt, 1e6)
        print(f"\n=== {tag} window {start}..{end} ===")
        print(f"BASE  Sharpe {bm['sharpe']:.3f}  Sortino {bm['sortino']:.3f}  CAGR {bm['cagr_pct']:.1f}  "
              f"DD {bm['max_drawdown_pct']:.1f}  Calmar {bm.get('calmar', float('nan')):.3f}  "
              f"aftertax {base_atx:.2f}  | 22-26 Sh {b22[0]:.3f} DD {b22[1]:.1f}")
        hdr = (f"{'lambda':<9}{'Sharpe':>8}{'Sortino':>8}{'CAGR':>7}{'DD':>7}{'Calmar':>8}"
               f"{'dSharpe [CI]':>24}{'dSort':>8}{'DSR':>6}{'dCalmar':>9}{'sub22dCAGR':>11}{'fold':>6}  verdict")
        print(hdr)
        print("-" * len(hdr))
        arms = []
        for lam in LAMBDAS:
            cand = make_arm(panel, betas, lam)
            cb = run_backtest(cand, cfg, start=start, end=end)
            c = _daily_returns(cb["equity_curve"])
            cm = cb["metrics"]
            common = b.index.intersection(c.index)
            av, bv = c.loc[common].to_numpy(float), b.loc[common].to_numpy(float)
            dsh = bootstrap_delta(av, bv, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
            dso = bootstrap_delta(av, bv, sortino, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
            ci = block_bootstrap_metric(av, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
            dsr = _dsr_from_bootstrap(av, NT, (ci.lower, ci.upper))
            d_cal = cm.get("calmar", float("nan")) - bm.get("calmar", float("nan"))
            sub22 = _subperiod_cagr(cb["equity_curve"], "2022-01-01", end)
            d_sub22 = ((sub22 or float("nan")) - (base_sub22 or float("nan")))
            fold = _fold_pass(common, av, bv, 2019)[0]
            atx = _after_tax_cagr(cb, 1e6)
            # pre-committed 7-gate bar (this window)
            promote = (dsh.lower > 0 and dsh.point >= 0.10 and dsr > 0.95 and d_cal >= 0.05
                       and d_sub22 > 0 and fold >= 0.60)
            verdict = ("KILL" if (dsh.point <= 0 or d_sub22 <= 0) else
                       "PROMOTE" if promote else "UNDERPOWERED")
            dsh_s = f"{dsh.point:+.3f}[{dsh.lower:+.2f},{dsh.upper:+.2f}]"
            print(f"{lam:<9.2f}{cm['sharpe']:>8.3f}{cm['sortino']:>8.3f}{cm['cagr_pct']:>7.1f}"
                  f"{cm['max_drawdown_pct']:>7.1f}{cm.get('calmar', float('nan')):>8.3f}{dsh_s:>24}"
                  f"{dso.point:>+8.3f}{dsr:>6.2f}{d_cal:>+9.3f}{d_sub22:>+11.2f}{fold:>6.2f}  {verdict}", flush=True)
            arms.append({"lambda": lam, "sharpe": cm["sharpe"], "sortino": cm["sortino"],
                         "cagr": cm["cagr_pct"], "dd": cm["max_drawdown_pct"],
                         "calmar": cm.get("calmar"), "after_tax_cagr": atx,
                         "dSharpe": round(dsh.point, 3), "dSharpe_ci": [round(dsh.lower, 3), round(dsh.upper, 3)],
                         "dSortino": round(dso.point, 3), "dsr": round(float(dsr), 3),
                         "dCalmar": round(float(d_cal), 4), "sub22_dCAGR": round(float(d_sub22), 3),
                         "fold": round(float(fold), 3), "verdict": verdict})
        out["windows"][tag] = {
            "window": [start, end],
            "base": {k: bm[k] for k in ("sharpe", "sortino", "cagr_pct", "max_drawdown_pct")}
            | {"calmar": bm.get("calmar"), "after_tax_cagr": base_atx,
               "live22_sharpe": round(b22[0], 3), "live22_dd": round(b22[1], 1)},
            "arms": arms}
    p = ROOT / "research" / "exports" / "macro_feature_0082.json"
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
