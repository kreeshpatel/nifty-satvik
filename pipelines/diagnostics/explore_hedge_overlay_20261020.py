"""EXPLORATORY (tier 0) — drawdown-switched Nifty beta hedge on the live capped book, as a BOUND.

No pre-registration, no screen row, no n_trials change. Nothing here touches the engine or any
production path: the live-config book's daily NAV is replayed (nq.lab.runs.replay, DEFAULT_CONFIG, PIT
membership, train-only with the CUT asserted) and a hedge overlay is applied to its daily returns.

Hedge: short Nifty notional = h * beta_63d(lagged) * book equity, ON only while Nifty (prior close) is
>= X% below its trailing-252d high, OFF otherwise. Costs: 0.02% per side on notional CHANGES + roll
0.05%/month (0.05%/21 per trading day) on notional while on. Futures are assumed to track spot (no basis,
carry, dividend or margin-funding drag). Beta is the trailing-63d OLS slope of book vs Nifty daily
returns ending the PRIOR day, floored at 0; the hedge is OFF until 63 returns exist.

    python pipelines/diagnostics/explore_hedge_overlay_20261020.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from nq.lab import runs  # noqa: E402

START, CUT = runs.MIN_START, runs.CUT
SUBPERIODS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
SIDE_COST, ROLL_MONTH, BETA_WIN, HI_WIN = 0.0002, 0.0005, 63, 252
OUT = ROOT / "diagnostics" / "research" / "explore" / "hedge_overlay_20261020.json"
CACHE = ROOT / "lab_cache"


def stats(r: pd.Series, n_trials: int) -> dict:
    """Daily-return stats. CAGR is calendar-annualised; deflation via nq.lab.runs (per-window basis)."""
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    sh = float(r.mean() / r.std() * np.sqrt(252))
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1)
    dd = float((eq / eq.cummax() - 1).min())
    d = runs.deflated_sharpe(sh, len(r), n_trials, skew=float(r.skew()), kurt=float(r.kurt() + 3))
    yr = (1 + r).groupby(r.index.year).prod() - 1
    return {"sharpe": sh, "sharpe_deflated": d["deflated_sharpe"], "dsr_prob": d["dsr"], "cagr": cagr,
            "maxdd": dd, "calmar": cagr / abs(dd) if dd else None,
            "worst_year": float(yr.min()), "worst_year_label": int(yr.idxmin()),
            "years": {int(k): float(v) for k, v in yr.items()}}


def sub_stats(r: pd.Series, lo: str, hi: str) -> dict:
    """CONTINUOUS SLICE of the one full-run return stream (never a fresh-capital re-run)."""
    s = r[(r.index >= pd.Timestamp(lo)) & (r.index <= pd.Timestamp(hi))]
    eq = (1 + s).cumprod()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return {"sharpe": float(s.mean() / s.std() * np.sqrt(252)),
            "cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "maxdd": float((eq / eq.cummax() - 1).min())}


def trailing_beta(rb: pd.Series, rn: pd.Series) -> pd.Series:
    cov = rb.rolling(BETA_WIN).cov(rn)
    var = rn.rolling(BETA_WIN).var()
    return (cov / var).shift(1).clip(lower=0)            # known at the prior close


def overlay(rb, rn, beta, on, h):
    """Hedged daily returns + diagnostics. `on` is the (already-lagged) boolean state used for day t."""
    w = (h * beta * on.astype(float)).fillna(0.0)
    pnl = -w * rn
    cost = w.diff().abs().fillna(w.abs()) * SIDE_COST + w * ROLL_MONTH / 21.0
    return rb + pnl - cost, w


def episodes(nifty: pd.Series, x: float):
    """Peak->trough windows of every Nifty drawdown episode that reached x (the clairvoyant ceiling)."""
    peak_run = nifty.cummax()                              # all-time, only for episode segmentation
    dd = nifty / peak_run - 1
    on = pd.Series(False, index=nifty.index)
    i, n = 0, len(nifty)
    while i < n:
        if dd.iloc[i] < 0:
            j = i - 1                                      # peak day = last day at a new high
            k = i
            while k < n and dd.iloc[k] < 0:
                k += 1
            seg = nifty.iloc[j:k]
            if seg.min() / nifty.iloc[j] - 1 <= -x:
                t = seg.idxmin()
                on.loc[nifty.index[j]:t] = True
            i = k
        else:
            i += 1
    return on


def main() -> None:
    res = runs.replay(cache_dir=CACHE)
    nav, man = res["nav"], res["manifest"]
    assert man["is_live_book"] and man["membership"] == "pit", man
    assert nav.index.max() <= pd.Timestamp(CUT)
    nifty_full = runs.load_nifty()
    assert nifty_full.index.max() <= pd.Timestamp(CUT)
    nifty = nifty_full.reindex(nifty_full.index.union(nav.index)).ffill()
    rn_full = nifty.pct_change()
    rb = nav.pct_change().dropna()
    rn = rn_full.reindex(rb.index)
    assert rn.notna().all()
    beta = trailing_beta(rb, rn)
    hi252 = nifty.rolling(HI_WIN, min_periods=HI_WIN).max()
    dd_nifty = (nifty / hi252 - 1).reindex(rb.index)

    variants = [(x, h) for x in (0.05, 0.10) for h in (0.5, 1.0)]
    n_tr = 1 + 3 * len(variants)                           # control + causal + zero-lag + episode ceiling
    out = {"label": "EXPLORATORY — tier 0, train window 2019-01-01..2024-06-30, not evidence",
           "manifest": man, "n_deflation_trials": n_tr,
           "program_counts": {"screens": 23, "sealed_opens": 3, "n_trials": 2},
           "assumptions": {"side_cost": SIDE_COST, "roll_per_month": ROLL_MONTH, "beta_window": BETA_WIN,
                           "high_window": HI_WIN, "beta_floor": 0.0,
                           "futures_track_spot": True, "no_margin_or_carry_drag": True},
           "beta_summary": {"mean": float(beta.mean()), "median": float(beta.median())}}
    out["unhedged"] = {**stats(rb, n_tr), "sub": {k: sub_stats(rb, *v) for k, v in SUBPERIODS.items()}}

    valid = beta.notna()
    on_causal = lambda x: ((dd_nifty.shift(1) <= -x) & valid)         # prior close  # noqa: E731
    on_lag0 = lambda x: ((dd_nifty <= -x) & beta.notna())             # same-day state (peeks)  # noqa: E731
    rows = {}
    for x, h in variants:
        key = f"X{int(x*100)}_h{h}"
        for kind, on in (("causal", on_causal(x)),
                         ("ceiling_zero_lag", on_lag0(x)),
                         ("ceiling_peak_to_trough", episodes(nifty.reindex(rb.index), x) & valid)):
            rh, w = overlay(rb, rn, beta, on, h)
            s = stats(rh, n_tr)
            s["sub"] = {k: sub_stats(rh, *v) for k, v in SUBPERIODS.items()}
            s["time_hedged"] = float(on.mean())
            s["mean_notional_when_on"] = float(w[on].mean()) if on.any() else None
            s["turnover_cost_total"] = float((w.diff().abs().fillna(0) * SIDE_COST).sum()
                                             + (w * ROLL_MONTH / 21).sum())
            s["d_sharpe"] = s["sharpe"] - out["unhedged"]["sharpe"]
            s["d_maxdd_pp"] = (s["maxdd"] - out["unhedged"]["maxdd"]) * 100
            s["d_cagr_pp"] = (s["cagr"] - out["unhedged"]["cagr"]) * 100
            rows[f"{key}/{kind}"] = s
    out["variants"] = rows

    # context: how the book behaved on hedge-ON days vs Nifty (is hedge direction right?)
    ctx = {}
    for x in (0.05, 0.10):
        m = on_causal(x)
        ctx[f"X{int(x*100)}"] = {"days_on": int(m.sum()), "share": float(m.mean()),
                                 "book_mean_daily_on": float(rb[m].mean()), "nifty_mean_daily_on": float(rn[m].mean()),
                                 "book_vol_on": float(rb[m].std()), "beta_mean_on": float(beta[m].mean())}
        # on-days restricted to non-COVID (excl. 2020-02-15..2020-06-30)
        nc = m & ~((rb.index >= "2020-02-15") & (rb.index <= "2020-06-30"))
        ctx[f"X{int(x*100)}"]["ex_covid_days_on"] = int(nc.sum())
        ctx[f"X{int(x*100)}"]["ex_covid_beta_on"] = float(beta[nc].mean())
        for_ols = rb[nc]; n_ols = rn[nc]
        ctx[f"X{int(x*100)}"]["ex_covid_ols_beta_pooled"] = float(np.cov(for_ols, n_ols)[0, 1] / n_ols.var())
    out["context"] = ctx
    out["nifty_dd_days"] = {f"X{int(x*100)}": int((dd_nifty <= -x).sum()) for x in (0.05, 0.10)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    u = out["unhedged"]
    print(f"unhedged  Sh {u['sharpe']:.3f} (defl {u['sharpe_deflated']:.3f}) CAGR {u['cagr']*100:.1f}% "
          f"DD {u['maxdd']*100:.1f}% Calmar {u['calmar']:.2f} worst {u['worst_year_label']} {u['worst_year']*100:.1f}% "
          f"| {u['sub']['2019-21']['sharpe']:.2f}/{u['sub']['2022-24H1']['sharpe']:.2f}")
    for k, s in rows.items():
        print(f"{k:34s} Sh {s['sharpe']:.3f} (defl {s['sharpe_deflated']:.3f}) CAGR {s['cagr']*100:5.1f}% "
              f"DD {s['maxdd']*100:6.1f}% Cal {s['calmar']:.2f} worst {s['worst_year']*100:6.1f}% "
              f"hdg {s['time_hedged']*100:4.1f}% | {s['sub']['2019-21']['sharpe']:.2f}/{s['sub']['2022-24H1']['sharpe']:.2f} "
              f"dd {s['sub']['2019-21']['maxdd']*100:.1f}/{s['sub']['2022-24H1']['maxdd']*100:.1f}")
    print(json.dumps(ctx, indent=1)); print(out["beta_summary"], out["nifty_dd_days"])


if __name__ == "__main__":
    main()
