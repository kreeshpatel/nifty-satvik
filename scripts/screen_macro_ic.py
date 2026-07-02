"""Cheap probe (MEASUREMENT, no trial) — does the cross-asset/macro data carry 63d signal the price doesn't?

Two honest tests, because macro is market-level (one value/day, can't rank stocks directly):
  A. TIME-SERIES (regime): does the macro state predict the STRATEGY's forward-63d return? (Spearman +
     regime buckets.) Note: an entry GATE on this is a §11 KILL (O-001); the only open use is
     regime-conditional SIZING. This just measures whether the signal exists.
  B. CROSS-SECTIONAL (the genuinely-new, rankable one): each stock's trailing beta to crude/USD/VIX ->
     rank stocks by beta -> IC vs forward-63d stock return. Orthogonal to price if it has IC.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.macro import load_macro_pit  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402

FWD, BETA_WIN = 63, 126
# clean PIT factors: *_ret (daily) + *_trend (63d trailing ROC, like-for-like vs finding 0016's trend betas).
# The go/no-go compares clean *_trend betas directly to 0016 (usd −0.034, crude +0.027).
CLEAN_FACS = ["usd_ret", "usd_trend", "crude_ret", "crude_trend", "vix_chg", "vix_trend"]


def _cross_sectional_ic(macro: pd.DataFrame, facs: list[str]) -> None:
    """Part B: per-stock trailing beta to each macro factor -> rank -> IC vs forward-63d stock return."""
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print("\npanel build for the cross-sectional test ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    elig = set(map(tuple, panel[["date", "ticker"]].to_numpy()))
    rows = []
    for tkr, gdf in ohlcv.items():
        c = gdf["Close"]
        ret = c.pct_change()
        idx = pd.to_datetime(gdf.index)
        m = macro.reindex(idx)[facs]
        fwd_s = c.shift(-FWD) / c - 1
        d = pd.DataFrame({"ret": ret.to_numpy(), "fwd": fwd_s.to_numpy()}, index=idx)
        for f in facs:
            fv = m[f]
            # min_periods < BETA_WIN so a few cross-calendar holes (crude/VIX vs NSE holidays) don't
            # NaN the whole 126d window; ~half-window of valid pairs still yields a stable beta.
            mp = BETA_WIN // 2
            cov = ret.rolling(BETA_WIN, min_periods=mp).cov(fv)
            var = fv.rolling(BETA_WIN, min_periods=mp).var()
            d[f + "_beta"] = (cov / var).to_numpy()
        d["ticker"] = tkr
        d["date"] = idx
        rows.append(d.reset_index(drop=True))
    allb = pd.concat(rows, ignore_index=True)
    allb = allb[[tuple(x) in elig for x in allb[["date", "ticker"]].to_numpy()]].dropna(subset=["fwd"])
    print("\n=== B. CROSS-SECTIONAL: per-stock macro-beta rank vs forward-63d stock return ===")
    print(f"{'macro-beta signal':<20}{'mean_IC':>9}{'IC_IR':>8}")
    for f in facs:
        col = f + "_beta"
        sub = allb[["date", col, "fwd"]].dropna()
        daily = sub.groupby("date").apply(
            lambda g: g[col].corr(g["fwd"], method="spearman") if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        if len(daily) < 100:
            print(f"{col:<20}{'n/a':>9}")
            continue
        print(f"{col:<20}{daily.mean():>+9.4f}{daily.mean() / daily.std():>+8.3f}")
    print("\nRead: |IC| < ~0.02 or Spearman ~0 = no orthogonal 63d signal in the macro data (as with the "
          "price-derived zoo). A real |IC| >= ~0.03 in Part B = a genuinely-new cross-sectional feature.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true",
                    help="use the PIT-clean macro_pit.parquet (nq.data.macro) + run only the go/no-go Part B")
    args = ap.parse_args()

    if args.clean:
        macro = load_macro_pit()
        macro.index = pd.to_datetime(macro.index)
        print("=== CLEAN (PIT) re-confirm — data/macro_pit.parquet, factors=%s ===" % CLEAN_FACS)
        _cross_sectional_ic(macro, CLEAN_FACS)
        return 0

    macro = pd.DataFrame(pickle.load(open(ROOT / "data" / "macro_data.pkl", "rb"))).T
    macro.index = pd.to_datetime(macro.index)
    macro = macro.sort_index().apply(pd.to_numeric, errors="coerce")

    # ── A. time-series: macro state vs the STRATEGY's forward-63d return ──
    dr = pd.read_csv(ROOT / "research" / "exports" / "daily_returns.csv", parse_dates=["date"]).set_index("date")
    r = dr["ret_net"].dropna()
    fwd = (1 + r[::-1]).rolling(FWD).apply(np.prod, raw=True)[::-1].shift(-1) - 1   # forward-63d compound
    fwd = fwd.dropna()
    j = macro.join(fwd.rename("fwd63"), how="inner").dropna(subset=["fwd63"])
    print(f"=== A. TIME-SERIES: macro[t] vs strategy forward-63d return (n={len(j)}) ===")
    print(f"{'macro var':<18}{'Spearman':>10}{'  (overlapping -> indicative only)'}")
    for c in macro.columns:
        s = j[[c, "fwd63"]].dropna()
        ic = s[c].corr(s["fwd63"], method="spearman") if s[c].nunique() > 3 else float("nan")
        print(f"{c:<18}{ic:>+10.3f}")
    print("\n  strategy mean fwd-63d return by regime bucket:")
    for c, q in (("india_vix", 3), ("market_regime", None), ("market_breadth", None)):
        if c not in j:
            continue
        g = pd.qcut(j[c], q, duplicates="drop") if q else j[c]
        buck = j.groupby(g, observed=True)["fwd63"].mean() * 100
        print(f"    {c}: " + "  ".join(f"{str(k)[:12]}={v:+.1f}%" for k, v in buck.items()))

    # ── B. cross-sectional: per-stock beta to crude/USD/VIX -> rank -> IC vs fwd-63d stock return ──
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print("\npanel build for the cross-sectional test ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    elig = set(map(tuple, panel[["date", "ticker"]].to_numpy()))
    facs = ["crude_trend", "usd_inr_trend", "vix_trend"]
    rows = []
    for tkr, gdf in ohlcv.items():
        c = gdf["Close"]
        ret = c.pct_change()
        idx = pd.to_datetime(gdf.index)
        m = macro.reindex(idx)[facs]
        fwd_s = c.shift(-FWD) / c - 1
        d = pd.DataFrame({"ret": ret.to_numpy(), "fwd": fwd_s.to_numpy()}, index=idx)
        for f in facs:
            fv = m[f]
            # min_periods < BETA_WIN so a few cross-calendar holes (crude/VIX vs NSE holidays) don't
            # NaN the whole 126d window; ~half-window of valid pairs still yields a stable beta.
            mp = BETA_WIN // 2
            cov = ret.rolling(BETA_WIN, min_periods=mp).cov(fv)
            var = fv.rolling(BETA_WIN, min_periods=mp).var()
            d[f + "_beta"] = (cov / var).to_numpy()
        d["ticker"] = tkr
        d["date"] = idx
        rows.append(d.reset_index(drop=True))
    allb = pd.concat(rows, ignore_index=True)
    allb = allb[[tuple(x) in elig for x in allb[["date", "ticker"]].to_numpy()]].dropna(subset=["fwd"])
    print("\n=== B. CROSS-SECTIONAL: per-stock macro-beta rank vs forward-63d stock return ===")
    print(f"{'macro-beta signal':<20}{'mean_IC':>9}{'IC_IR':>8}")
    for f in facs:
        col = f + "_beta"
        sub = allb[["date", col, "fwd"]].dropna()
        daily = sub.groupby("date").apply(
            lambda g: g[col].corr(g["fwd"], method="spearman") if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        if len(daily) < 100:
            print(f"{col:<20}{'n/a':>9}")
            continue
        print(f"{col:<20}{daily.mean():>+9.4f}{daily.mean() / daily.std():>+8.3f}")
    print("\nRead: |IC| < ~0.02 or Spearman ~0 = no orthogonal 63d signal in the macro data (as with the "
          "price-derived zoo). A real |IC| >= ~0.03 in Part B = a genuinely-new cross-sectional feature.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
