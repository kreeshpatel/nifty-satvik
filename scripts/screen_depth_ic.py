"""Cheap probe (MEASUREMENT, no trial) — do the PIT-clean fundamentals-depth features carry 63d
cross-sectional signal? The go/no-go before building the learning-bot conviction model (Parts 4-6).

For each eligible (date, ticker) in the ranked panel, compute the Part-2 depth features (PIT-safe, from
data/fundamentals_pit_depth.pkl) and correlate each cross-sectionally (Spearman) with the forward-63d stock
return. Reports mean IC + IC-IR per feature. Read: |mean IC| >= ~0.03 with a consistent-sign IC-IR = a real,
learner-worthy signal (like the base sma200_slope_63 |IC| 0.062); |IC| < ~0.02 = weak, the learner would just
overfit noise. This is the fundamentals analogue of scripts/screen_macro_ic.py Part B (finding 0016).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import (DEPTH_FEATURE_COLS, depth_feature_series,  # noqa: E402
                                  load_fund_store)
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402

FWD = 63
DEPTH_STORE = ROOT / "data" / "fundamentals_pit_depth.pkl"


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    store = load_fund_store(DEPTH_STORE)
    if store is None:
        print(f"no depth store at {DEPTH_STORE} — run scripts/scrape_screener.py --mode all "
              f"--out data/fundamentals_pit_depth.pkl --no-merge first")
        return 1
    n_depth = sum(1 for f in store.values() if hasattr(f, "columns") and "sales" in f.columns)
    print(f"depth store: {len(store)} names ({n_depth} with depth levels)", flush=True)

    print("panel build ...", flush=True)
    from nq.data.fundamentals import load_fund_store as _lfs  # the PINNED store for panel eligibility
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=_lfs(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    elig = set(map(tuple, panel[["date", "ticker"]].to_numpy()))

    rows = []
    for tkr, gdf in ohlcv.items():
        idx = pd.to_datetime(gdf.index)
        close = gdf["Close"].to_numpy(dtype=float)
        feats = depth_feature_series(tkr, store, idx)   # PIT-safe, strict-before
        fwd = np.full(len(close), np.nan)
        if len(close) > FWD:
            fwd[:-FWD] = close[FWD:] / close[:-FWD] - 1.0
        d = pd.DataFrame({"date": idx, "ticker": tkr, "fwd": fwd, **feats})
        rows.append(d)
    allf = pd.concat(rows, ignore_index=True)
    allf = allf[[tuple(x) in elig for x in allf[["date", "ticker"]].to_numpy()]].dropna(subset=["fwd"])
    print(f"eligible feature rows: {len(allf)}\n", flush=True)

    print(f"=== DEPTH-FEATURE cross-sectional IC vs forward-{FWD}d return ===")
    print(f"{'feature':<18}{'mean_IC':>9}{'IC_IR':>8}{'coverage':>10}{'  read'}")
    print("-" * 55)
    verdicts = []
    for f in DEPTH_FEATURE_COLS:
        sub = allf[["date", f, "fwd"]].dropna()
        daily = sub.groupby("date").apply(
            lambda g: g[f].corr(g["fwd"], method="spearman") if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        cov = len(sub) / max(len(allf), 1)
        if len(daily) < 100:
            print(f"{f:<18}{'n/a':>9}{'':>8}{cov*100:>9.0f}%")
            continue
        ic, ir = daily.mean(), daily.mean() / daily.std()
        tag = "REAL" if abs(ic) >= 0.03 else "weak" if abs(ic) >= 0.02 else "~0"
        print(f"{f:<18}{ic:>+9.4f}{ir:>+8.3f}{cov*100:>9.0f}%  {tag}")
        verdicts.append((f, ic, ir))
    strong = [v for v in verdicts if abs(v[1]) >= 0.03]
    print(f"\nGO/NO-GO: {len(strong)} feature(s) with |IC| >= 0.03 "
          f"({', '.join(v[0] for v in strong) or 'none'}). "
          f"{'-> learner justified on these.' if strong else '-> fundamentals-depth weak; learner would overfit. Cheap KILL.'}")

    # ── robustness slices for the flagged feature(s): is the IC concentrated in suspect data? ──
    from scripts.run_cpcv import _recoverable_delisted
    delisted = set(_recoverable_delisted())
    def _ic(df, col):
        d = df[["date", col, "fwd"]].dropna()
        daily = d.groupby("date").apply(
            lambda g: g[col].corr(g["fwd"], method="spearman") if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        return (daily.mean(), daily.mean() / daily.std(), len(daily)) if len(daily) >= 60 else (float("nan"),) * 3
    for f, _ic0, _ir0 in strong:
        print(f"\n--- robustness: {f} ---")
        for tag, mask in (
            (">=2019 (trusted folds)", allf["date"] >= "2019-01-01"),
            ("2022-2026 (live regime)", allf["date"] >= "2022-01-01"),
            ("pre-2019 (survivor-biased)", allf["date"] < "2019-01-01"),
            ("current names only", ~allf["ticker"].isin(delisted)),
            ("delisted names only", allf["ticker"].isin(delisted)),
        ):
            ic, ir, nd = _ic(allf[mask], f)
            print(f"  {tag:<28} IC {ic:+.4f}  IR {ir:+.3f}  (n_days {nd})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
