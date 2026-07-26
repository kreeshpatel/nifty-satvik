"""MEASUREMENT ONLY (0 trials): is the momentum-vs-low-vol tilt LEARNABLE from regime state, OOS?

The owner wants an adaptive 'dial' that tilts between the momentum sleeve and the low-vol sleeve as the
market changes. Before building any ML model we answer the go/no-go: does observable PIT regime state
predict which sleeve wins next quarter well enough that a WALK-FORWARD switch beats the fixed
inverse-vol ERC (0081) out-of-sample? If simple transparent regime rules can't beat fixed ERC OOS, a
black-box model on the same ~37 independent windows / ~5 regime episodes certainly can't (it would only
overfit). Judged OOS only (owner rule); in-sample fit is discarded.

Reproduces r_mom (frozen base) + r_lv (low-vol sole-ranker, O-016) exactly as pre-reg 0081, caches them,
then: (A) Spearman IC of each regime feature vs forward 63d relative return (mom-lv); (B) walk-forward
switch rules vs fixed ERC / 50-50 / sleeve-alone benchmarks.

    python scripts/diag_regime_sleeve_learnability.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.data.options_oi import OI_PIT_PATH  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, run_backtest  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
CACHE = ROOT / "research" / "exports" / "sleeve_daily_returns.csv"
H = 63  # quarter horizon


def _sleeves() -> pd.DataFrame:
    """r_mom + r_lv daily (cached). Exact 0081 construction."""
    if CACHE.exists():
        d = pd.read_csv(CACHE, parse_dates=["date"]).set_index("date")
        print(f"[cache] loaded sleeve returns {d.index.min().date()}..{d.index.max().date()} ({len(d)})")
        return d
    cfg = load_frozen_cfg(); ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) — this is the heavy LH pipeline ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    rv = pd.concat([pd.DataFrame({"date": pd.to_datetime(g.index), "ticker": t,
                                  "rvol": g["Close"].pct_change().rolling(63).std().to_numpy()})
                    for t, g in ohlcv.items()], ignore_index=True)
    lv_panel = panel.merge(rv, on=["date", "ticker"], how="left").copy()
    lv_panel["trend_rank"] = (-lv_panel["rvol"]).groupby(lv_panel["date"]).rank(pct=True)
    r_mom = _daily_returns(run_backtest(panel, cfg, start=START, end=END)["equity_curve"])
    r_lv = _daily_returns(run_backtest(lv_panel, cfg, start=START, end=END)["equity_curve"])
    d = pd.concat([r_mom.rename("r_mom"), r_lv.rename("r_lv")], axis=1).dropna()
    d.to_csv(CACHE); print(f"[cache] wrote {CACHE}")
    return d


def _sharpe(r):
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 20 and r.std() else float("nan")


def _erc_weight(r_mom, r_lv):
    """Quarterly inverse-vol weight on momentum (0081's fixed benchmark), as-of prior day."""
    vm = r_mom.rolling(63).std().shift(1); vl = r_lv.rolling(63).std().shift(1)
    w = (1 / vm) / (1 / vm + 1 / vl)
    q = w.resample("QS").first().reindex(w.index, method="ffill")
    return q.clip(0, 1)


def main() -> int:
    print("=== MEASUREMENT: is the momentum<->low-vol tilt learnable from regime, OOS? (0 trials) ===")
    s = _sleeves()
    r_mom, r_lv = s["r_mom"], s["r_lv"]
    rel = r_mom - r_lv
    print(f"corr(mom,lv) {r_mom.corr(r_lv):+.2f} | mom Sharpe {_sharpe(r_mom):+.2f} | "
          f"lv Sharpe {_sharpe(r_lv):+.2f}")

    # ── regime features (PIT / trailing) ──
    oi = pd.read_parquet(OI_PIT_PATH); oi.index = pd.to_datetime(oi.index)
    nif = oi["spot"].reindex(r_mom.index).ffill()
    F = pd.DataFrame(index=r_mom.index)
    F["mkt_vol"] = nif.pct_change().rolling(63).std()                    # market vol regime
    F["mkt_trend"] = nif / nif.rolling(200).mean() - 1                   # trending up/down
    F["iv"] = oi["atm_straddle_pct"].reindex(r_mom.index).ffill()        # implied vol level
    F["iv_term"] = oi["iv_term_slope"].reindex(r_mom.index).ffill()      # backwardation
    F["put_skew"] = oi["put_skew"].reindex(r_mom.index).ffill()
    F["rel_mom63"] = rel.rolling(63).sum()                              # does the winning sleeve persist?
    F["rel_vol_ratio"] = r_mom.rolling(63).std() / r_lv.rolling(63).std()

    # forward 63d relative cum return (mom - lv); >0 = momentum wins next quarter
    fwd = rel.shift(-H).rolling(H).sum().shift(-(0))  # sum of next H via reverse
    fwd = rel[::-1].rolling(H).sum()[::-1].shift(-1)   # forward H-day sum of rel

    # ── (A) IC: does each regime feature predict the forward sleeve winner? ──
    print("\n(A) Spearman IC: regime feature_t  vs  forward-63d (mom-lv) relative return")
    print("     (want |IC| large & stable: e.g. high vol -> low-vol wins -> negative IC)")
    for c in F.columns:
        d = pd.concat([F[c], fwd], axis=1).dropna()
        ic = spearmanr(d.iloc[:, 0], d.iloc[:, 1]).statistic if len(d) > 200 else np.nan
        print(f"     {c:<14} IC {ic:+.3f}")

    # ── (B) walk-forward switch vs fixed benchmarks (OOS only) ──
    # rebalance quarterly; burn-in 2y; each rule decides next-quarter weight on momentum using PAST data only.
    dates = r_mom.index
    reb = pd.date_range(dates[0], dates[-1], freq="QS")
    burn = dates[0] + pd.Timedelta(days=730)
    w_erc = _erc_weight(r_mom, r_lv)

    def run_weight(wfunc):
        w = pd.Series(np.nan, index=dates)
        for t in reb:
            if t < burn or t > dates[-1]:
                continue
            past = dates[dates <= t]
            w.loc[t] = wfunc(past)
        w = w.ffill().reindex(dates).fillna(0.5)
        return (w.shift(1) * r_mom + (1 - w.shift(1)) * r_lv)

    def rule_trailing_sharpe(past):       # allocate to the sleeve with higher trailing-126d Sharpe
        p = past[-126:]
        return 1.0 if _sharpe(r_mom.loc[p]) >= _sharpe(r_lv.loc[p]) else 0.0

    def rule_vol_regime(past):            # low-vol when market vol above its trailing median, else momentum
        v = F["mkt_vol"].loc[past].dropna()
        return 0.0 if (len(v) and v.iloc[-1] > v.median()) else 1.0

    def rule_bestfeat(past):              # pick the best-IC feature SO FAR, use its sign to tilt (adaptive)
        best_c, best_ic = None, 0.0
        for c in F.columns:
            d = pd.concat([F[c].loc[past], fwd.loc[past]], axis=1).dropna()
            if len(d) < 250:
                continue
            ic = spearmanr(d.iloc[:, 0], d.iloc[:, 1]).statistic
            if abs(ic) > abs(best_ic):
                best_ic, best_c = ic, c
        if best_c is None:
            return 0.5
        cur = F[best_c].loc[past].dropna().iloc[-1]
        med = F[best_c].loc[past].dropna().median()
        hi = cur > med
        # IC>0 means high feature -> momentum wins
        return 1.0 if (hi == (best_ic > 0)) else 0.0

    bench = {
        "momentum-alone": r_mom, "low-vol-alone": r_lv,
        "fixed 50/50": 0.5 * r_mom + 0.5 * r_lv,
        "fixed ERC (0081)": (w_erc.shift(1) * r_mom + (1 - w_erc.shift(1)) * r_lv),
        "SWITCH trailing-Sharpe": run_weight(rule_trailing_sharpe),
        "SWITCH vol-regime": run_weight(rule_vol_regime),
        "SWITCH best-IC-feat": run_weight(rule_bestfeat),
    }
    oos = dates[dates >= burn]
    print(f"\n(B) OOS ({oos[0].date()}..{oos[-1].date()}, post-2y-burn-in) Sharpe — the switch must BEAT fixed ERC")
    erc_sh = _sharpe(bench["fixed ERC (0081)"].loc[oos])
    for tag, r in bench.items():
        sh = _sharpe(r.loc[oos]); mark = ""
        if tag.startswith("SWITCH"):
            mark = "  BEATS ERC" if sh > erc_sh + 0.02 else ("  ~ties ERC" if sh > erc_sh - 0.02 else "  loses to ERC")
        print(f"     {tag:<24} Sharpe {sh:+.3f}{mark}")

    print("\nReadout: if no SWITCH beats fixed ERC OOS, the tilt is NOT learnably better than static "
          "risk-parity -> ship the fixed ERC (0081) to the wall, DON'T build a model. If a simple rule "
          "beats ERC OOS, a small regularized model is worth building (forward-wall judged).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
