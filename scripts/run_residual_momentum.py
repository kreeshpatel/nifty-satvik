"""Pre-reg 0077 — multi-factor residual momentum as the sole ranker, graded on shape.

Residualize each name's trailing 252d daily returns on [mkt, hml] (data/ff_india_factors.parquet),
score = IR of residuals over t-252..t-21 (skip recent 21d, BHM), computed monthly and applied
strict-before, cross-sectionally ranked, injected as the strategy's rank column. Paired vs the
sma200_slope_63 base (C4 swap protocol). Reports skew/Sortino/Calmar/DD as the PRIMARY axes plus the
block-bootstrap dSharpe/dSortino CI + DSR. Writes research/exports/residmom_0077_results.json.
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
from nq.runner.research import (_daily_returns, _fold_pass,  # noqa: E402
                                _subperiod_cagr, run_backtest)
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sharpe, sortino  # noqa: E402

START, END, NT = "2017-01-01", "2026-06-30", 87
REG_WIN, SKIP = 252, 21


def skew(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 8 or x.std() == 0:
        return float("nan")
    return float((((x - x.mean()) / x.std()) ** 3).mean())


def slice_sh(ec, s, e):
    q = pd.Series([r["equity"] for r in ec], index=pd.to_datetime([r["date"] for r in ec]), dtype=float)
    q = q[(q.index >= pd.Timestamp(s)) & (q.index <= pd.Timestamp(e))]
    r = q.pct_change().dropna()
    dn = r[r < 0]
    return (r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
            r.mean() / dn.std() * np.sqrt(252) if len(dn) and dn.std() else float("nan"),
            float((q / q.cummax() - 1).min() * 100))


def residual_ranks(panel: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Long df [date, ticker, resid_rank] — monthly residual-momentum IR, strict-before, x-sec ranked."""
    rows = []
    for tkr, g in panel[["date", "ticker", "close"]].sort_values("date").groupby("ticker"):
        g = g.drop_duplicates("date")
        s = pd.Series(g["close"].to_numpy(float), index=pd.DatetimeIndex(g["date"].to_numpy()))
        df = pd.concat([s.pct_change().rename("r"), factors], axis=1, join="inner").dropna()
        if len(df) < REG_WIN + SKIP + 5:
            continue
        idx = df.index
        y_all = df["r"].to_numpy(float)
        x_all = np.column_stack([np.ones(len(df)), df["mkt"].to_numpy(float), df["hml"].to_numpy(float)])
        me = pd.Series(np.arange(len(idx)), index=idx).groupby(idx.to_period("M")).last().to_numpy()
        sc = {}
        for pos in me:
            if pos < REG_WIN - 1:
                continue
            xw, yw = x_all[pos - REG_WIN + 1:pos + 1], y_all[pos - REG_WIN + 1:pos + 1]
            coef = np.linalg.lstsq(xw, yw, rcond=None)[0]
            resid = (yw - xw @ coef)[:-SKIP]      # t-252..t-21
            if resid.std() > 0 and resid.size > 50:
                sc[idx[pos]] = resid.mean() / resid.std()
        if not sc:
            continue
        right = pd.DataFrame({"avail": list(sc.keys()), "score": list(sc.values())}).sort_values("avail")
        m = pd.merge_asof(pd.DataFrame({"date": idx}), right, left_on="date", right_on="avail",
                          direction="backward", allow_exact_matches=False)   # strict-before
        rows.append(pd.DataFrame({"date": idx, "ticker": tkr, "score": m["score"].to_numpy()}))
    long = pd.concat(rows, ignore_index=True).dropna(subset=["score"])
    long["resid_rank"] = long.groupby("date")["score"].rank(pct=True)
    return long[["date", "ticker", "resid_rank"]]


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    factors = pd.read_parquet(DATA_DIR / "ff_india_factors.parquet").set_index("date").sort_index()

    print("residualizing (252d OLS on [mkt,hml], monthly) ...", flush=True)
    rr = residual_ranks(panel, factors)
    cand = panel.merge(rr, on=["date", "ticker"], how="left")
    corr = cand[["trend_rank", "resid_rank"]].dropna().corr().iloc[0, 1]
    cov = cand.dropna(subset=["resid_rank"]).groupby(cand["date"].dt.year)["ticker"].nunique()
    print(f"  resid_rank coverage names/yr: {dict(cov)}")
    print(f"  corr(resid_rank, trend_rank) = {corr:.3f}", flush=True)
    cand["trend_rank"] = cand["resid_rank"]

    base_bt = run_backtest(panel, cfg, start=START, end=END)
    cand_bt = run_backtest(cand, cfg, start=START, end=END)
    a = _daily_returns(cand_bt["equity_curve"])
    b = _daily_returns(base_bt["equity_curve"])
    common = a.index.intersection(b.index)
    av, bv = a.loc[common].to_numpy(float), b.loc[common].to_numpy(float)
    dsh = bootstrap_delta(av, bv, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dso = bootstrap_delta(av, bv, sortino, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    _ = block_bootstrap_metric(av, sharpe, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    fold, nf = _fold_pass(common, av, bv, 2019)
    bm, cm = base_bt["metrics"], cand_bt["metrics"]
    b22 = slice_sh(base_bt["equity_curve"], "2022-01-01", END)
    c22 = slice_sh(cand_bt["equity_curve"], "2022-01-01", END)
    d_cagr22 = ((_subperiod_cagr(cand_bt["equity_curve"], "2022-01-01", END) or float("nan"))
                - (_subperiod_cagr(base_bt["equity_curve"], "2022-01-01", END) or float("nan")))

    def row(tag, m, sk, s22):
        return (f"{tag:<10} Sharpe {m['sharpe']:.3f}  Sortino {m['sortino']:.3f}  Calmar {m['calmar']:.2f}"
                f"  DD {m['max_drawdown_pct']:.1f}  skew {sk:+.3f}  CAGR {m['cagr_pct']:.1f}"
                f"  nTr {m['n_trades']}  | 22-26 Sh {s22[0]:.3f}/So {s22[1]:.2f}/DD {s22[2]:.1f}")
    print("\n" + row("BASE", bm, skew(bv), b22))
    print(row("RESID-MOM", cm, skew(av), c22))
    print(f"\ndSharpe {dsh.point:+.3f} [{dsh.lower:+.2f},{dsh.upper:+.2f}]   "
          f"dSortino {dso.point:+.3f} [{dso.lower:+.2f},{dso.upper:+.2f}]   "
          f"dSkew {skew(av)-skew(bv):+.3f}   fold {fold:.2f} ({nf})   "
          f"2022-26 dCAGR {d_cagr22:+.2f}   turnover {bm['turnover_per_year']:.0f}->{cm['turnover_per_year']:.0f}")

    shape_win = (cm["sortino"] > bm["sortino"] and cm["calmar"] > bm["calmar"]
                 and skew(av) > skew(bv) and c22[0] > b22[0])
    print(f"\nSHAPE verdict (Sortino AND Calmar AND skew AND 2022-26 Sharpe all improve): "
          f"{'YES -> SHADOW/forward-wall' if shape_win else 'NO -> KILL'}")

    out = {"prereg": "0077", "n_trials": NT, "corr_resid_vs_trend": round(float(corr), 3),
           "base": {k: bm[k] for k in ("sharpe", "sortino", "calmar", "max_drawdown_pct", "cagr_pct", "n_trades", "turnover_per_year")},
           "resid_mom": {k: cm[k] for k in ("sharpe", "sortino", "calmar", "max_drawdown_pct", "cagr_pct", "n_trades", "turnover_per_year")},
           "base_skew": round(skew(bv), 3), "resid_skew": round(skew(av), 3),
           "dSharpe": round(dsh.point, 3), "dSharpe_ci": [round(dsh.lower, 3), round(dsh.upper, 3)],
           "dSortino": round(dso.point, 3), "dSortino_ci": [round(dso.lower, 3), round(dso.upper, 3)],
           "fold_pass": round(float(fold), 3), "n_folds": nf, "subperiod_2022_dCAGR": round(float(d_cagr22), 3),
           "base_2022_26": {"sharpe": round(b22[0], 3), "sortino": round(b22[1], 3), "dd": round(b22[2], 1)},
           "resid_2022_26": {"sharpe": round(c22[0], 3), "sortino": round(c22[1], 3), "dd": round(c22[2], 1)},
           "shape_win": bool(shape_win)}
    p = ROOT / "research" / "exports" / "residmom_0077_results.json"
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
