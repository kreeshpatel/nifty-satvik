"""Build the frozen expectation bands (ADR-0020, Part B): forward/bands/<strategy>_bands_<date>.json, write-once.

For each strategy, the distribution of cumulative return and max drawdown at 13 / 26 / 52 / 104 weeks, from
  (i)  a 20-path ensemble (every overlapping window of every path, pooled), and
  (ii) a stationary block bootstrap (mean block 8 weeks, 5,000 draws) of the backtest's weekly returns,
reporting the 5 / 25 / 50 / 75 / 95 percentiles of each and using the wider of the two for each percentile.

Strategies and the window each band is built on (each strategy's own validated window; sealed slice B is not read for
the swing, whose prices are cut at 2024-06-30):
  live_swing            2019-03-01..2024-06-28   20 paths: cost jitter +/-10bp and start date (nq.lab.ensemble)
  xsec_momentum_0001    2017-01-02..2026-06-29   20 paths: the same draws; cost jitter applied through the engine's
                                                 cost_mult (1 + delta / 0.35% per leg), start within the first 20 sessions
  long_horizon          2017-09-14..2026-06-29   20 paths: start date only (the engine has no cost hook)
  blend_70_30_vt15      2019-03-01..2024-06-28   path i = momentum path i with swing path i, 70/30, 15% volatility target

Nothing is tuned; no live config, engine or trial counter is touched. This script refuses to overwrite a band file.

    LIFECYCLE_CACHE=<dir> python pipelines/lifecycle/build_bands.py [--date YYYY-MM-DD] [--only name ...]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"), str(ROOT / "pipelines" / "diagnostics"),
                str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402

BANDS_DIR = ROOT / "forward" / "bands"
CACHE = Path(os.environ.get("LIFECYCLE_CACHE", ROOT / ".cache" / "lifecycle"))
COMMON = ("2019-03-01", "2024-06-28")
N_PATHS = 20
LEG_COST_REF = 0.0035                                   # momentum result.md: ~0.35% per leg


def cached(name, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}.pkl"
    if f.exists():
        return pd.read_pickle(f)
    out = fn()
    pd.to_pickle(out, f)
    return out


def maxdd_pct(nav: pd.Series) -> float:
    return float((nav / nav.cummax() - 1).min() * 100)


def inputs() -> dict:
    """Unperturbed backtest NAV + 20 path NAVs per strategy (daily)."""
    import diag_system_inventory_2026_11 as INV
    from nq.lab import ensemble as E
    from nq.data.membership import load_membership
    from run_bhanushali_path1 import corrected_universe
    INV.CACHE = CACHE
    sw = cached("swing", INV.run_swing)["swing_live"]                      # prices cut 2024-06-30, asserted inside
    full, mem = corrected_universe(), load_membership()

    def momentum():
        import run_0001_xsec_momentum as M
        from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
        from nq.universe import build_universe
        p = M.add_signals(build_universe(full, mem, start=M.START, end=M.END))
        b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
        b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)

        def one(start, mult):
            bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**{**M.BOOK, "cost_mult": float(mult)}), start=str(start), end=M.END,
                                         initial_capital=1_000_000.0)
            return INV.to_nav(bt["equity_curve"])
        base = one(M.START, 1.0)
        draws = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED, start_base=str(base.index[0].date()))
        return {"nav": base, "paths": [one(d["start"], 1.0 + float(d["cost_delta"]) / LEG_COST_REF) for _, d in draws.iterrows()]}

    def long_horizon():
        from config import load_frozen_cfg
        from nq.data.features import compute_all_features
        from nq.data.fundamentals import load_fund_store
        from nq.engine.panel import compose_ranked_panel
        from nq.runner.research import run_backtest
        panel = compose_ranked_panel(compute_all_features(full), full, fund_store=load_fund_store(), membership=mem)
        panel["date"] = pd.to_datetime(panel["date"])
        cfg = load_frozen_cfg()
        one = lambda start: INV.to_nav(run_backtest(panel, cfg, start=str(start), end="2026-06-30")["equity_curve"])
        base = one("2017-01-01")
        draws = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED, start_base=str(base.index[0].date()))
        return {"nav": base, "paths": [one(d["start"]) for _, d in draws.iterrows()]}

    mom = cached("momentum_paths", momentum)
    lh = cached("long_horizon_paths", long_horizon)

    def blend(nm: pd.Series, ns: pd.Series) -> pd.Series:
        a, b = INV.window(nm, *COMMON), INV.window(ns, *COMMON)
        r, _ = C.vol_target_blend(a.pct_change().dropna(), b.pct_change().dropna())
        return 1_000_000.0 * (1 + r).cumprod()

    return {
        "live_swing": {"nav": INV.window(sw["nav"], *COMMON), "paths": [INV.window(p, *COMMON) for p in sw["paths"]],
                       "meta": {"window": COMMON, "paths": "cost jitter +/-10bp and start date; prices cut at 2024-06-30 (sealed slice B not read)"}},
        "xsec_momentum_0001": {"nav": mom["nav"], "paths": mom["paths"],
                               "meta": {"window": [str(mom["nav"].index[0].date()), str(mom["nav"].index[-1].date())],
                                        "paths": "same draws; cost jitter through cost_mult = 1 + delta / 0.35%; start in the first 20 sessions"}},
        "long_horizon": {"nav": lh["nav"], "paths": lh["paths"],
                         "meta": {"window": [str(lh["nav"].index[0].date()), str(lh["nav"].index[-1].date())],
                                  "paths": "start date only; the engine has no cost hook, so this ensemble is narrower than the others"}},
        "blend_70_30_vt15": {"nav": blend(mom["nav"], sw["nav"]), "paths": [blend(m, s) for m, s in zip(mom["paths"], sw["paths"])],
                             "meta": {"window": COMMON, "definition": "70% momentum 0001 / 30% live swing, daily fixed weights, 15% volatility "
                                      "target on 20-session realised vol, exposure capped at 1.0, rest in cash at 6% a year",
                                      "paths": "momentum path i paired with swing path i"}},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=str(pd.Timestamp.today().date()))
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    targets = {s: BANDS_DIR / f"{s}_bands_{a.date}.json" for s in ("live_swing", "xsec_momentum_0001", "long_horizon", "blend_70_30_vt15")
               if not a.only or s in a.only}
    for s, f in targets.items():                       # refuse BEFORE doing any work
        if f.exists():
            raise FileExistsError(f"{f} already exists and is frozen. Build under a new --date instead.")
    data = inputs()
    for s, f in targets.items():
        d = data[s]
        band = C.build_band(s, C.weekly_returns(d["nav"]).to_numpy(), [C.weekly_returns(p).to_numpy() for p in d["paths"]],
                            maxdd_pct(d["nav"]), meta=d["meta"], built=a.date)
        C.check_monotone(band)
        C.write_once(f, band)
        h = band["horizons"]
        sys.stdout.write(f"{s}: worst backtest DD {band['worst_backtest_drawdown_pct']}% | 26w {h['26']['cum_return_pct']['band']} | "
                         f"52w {h['52']['cum_return_pct']['band']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
