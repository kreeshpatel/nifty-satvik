"""MEASUREMENT: drawdown-based sizing for the 70/30 blend - block-length sensitivity of the bootstrap drawdown, why
the 52-week p95 equals the backtest worst, and the volatility target the -25% system bar implies.

Owner request 2026-11-18 (research/robust-sizing). Analysis only: the blend's vol target is NOT changed here -
choosing it is the owner's decision. No trial, no sealed read (swing prices cut 2024-06-30, asserted by nq.lab).

INPUTS (identical construction to pipelines/lifecycle/build_bands.py):
  swing     nq.lab.runs.replay({}) - the live book, PIT membership, 2019-01-01 start, prices cut 2024-06-30
  momentum  0001 run of record, pipelines/research/run_0001_xsec_momentum.py BOOK, 2017-01-01..2026-06-30
  blend     pipelines/lifecycle/core.py::vol_target_blend - 70/30 daily fixed weights, exposure =
            min(1, target / (20-session realised vol of the combined book, lagged one day) * sqrt(252)), the rest
            in cash at 6%/yr; both legs windowed to 2019-03-01..2024-06-28 first (build_bands.COMMON)

METRICS
  weekly returns   core.weekly_returns: Friday-to-Friday returns of the daily NAV (W-FRI last)
  drawdown depth   core._path_stats: max over the path of 1 - NAV/running peak, NAV starting at 1.0, in %
  bootstrap        Politis-Romano stationary bootstrap of the weekly-return series: start uniform, each later week
                   continues the block with probability 1 - 1/b and jumps to a uniform new start otherwise,
                   wrapping around (same rule as core.stationary_bootstrap, vectorised; seed below)
  CAGR / Sharpe    of the blend's daily return series over the common window: CAGR from the compounded NAV and
                   calendar years; Sharpe = mean/std * sqrt(252), no risk-free rate (the engine's convention)

DEPENDENCE: weekly returns are serially dependent; the block bootstrap is the handling, and the mean block length
is exactly what this study varies (8, 13, 26 weeks). Draws are not independent of one another in the sense of
sharing one 278-week history - every percentile is a property of that ONE history resampled.

    python pipelines/diagnostics/explore_blend_drawdown_sizing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402

CACHE = ROOT / ".cache" / "robust_sizing"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_blend_drawdown_sizing.json"
COMMON = ("2019-03-01", "2024-06-28")
BLOCKS = (8, 13, 26)
HORIZONS = (52, 104, 156)
N_DRAWS = 10_000
SEED = 20261118
TARGETS = tuple(round(x / 100, 2) for x in range(8, 16))
BAR = 25.0


def navs() -> dict:
    """Unperturbed daily NAVs: swing (live book) and 0001 momentum. Cached; the anchors are checked by the caller."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "navs.pkl"
    if f.exists():
        return pd.read_pickle(f)
    from nq.lab import runs as L
    import run_0001_xsec_momentum as M
    import diag_system_inventory_2026_11 as INV
    from nq.data.membership import load_membership
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    sw = L.replay({})
    p = M.add_signals(build_universe(corrected_universe(), load_membership(), start=M.START, end=M.END))
    b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**M.BOOK), start=M.START, end=M.END, initial_capital=1_000_000.0)
    out = {"swing": sw["nav"], "swing_ledger": sw["ledger"], "swing_position_log": sw["position_log"],
           "swing_metrics": {"sharpe": sw["sharpe"], "cagr": sw["cagr"], "maxdd": sw["maxdd"]},
           "momentum": INV.to_nav(bt["equity_curve"]), "momentum_trades": pd.DataFrame(bt["trades"]),
           "momentum_metrics": {"cagr_pct": float(bt["metrics"]["cagr_pct"]), "sharpe": float(bt["metrics"]["sharpe"])}}
    pd.to_pickle(out, f)
    return out


def window(nav: pd.Series) -> pd.Series:
    return nav[(nav.index >= pd.Timestamp(COMMON[0])) & (nav.index <= pd.Timestamp(COMMON[1]))]


def blend_daily(mom: pd.Series, sw: pd.Series, target: float = 0.15) -> pd.Series:
    a, b = window(mom), window(sw)
    r, _ = C.vol_target_blend(a.pct_change().dropna(), b.pct_change().dropna(), target=target)
    return r


def to_nav(r: pd.Series) -> pd.Series:
    return 1_000_000.0 * (1 + r).cumprod()


def cagr_sharpe(r: pd.Series) -> tuple[float, float]:
    nav = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return float(nav.iloc[-1] ** (1 / yrs) - 1) * 100, float(r.mean() / r.std() * np.sqrt(252))


def boot_dd(weekly: np.ndarray, h: int, block: int, n: int = N_DRAWS, seed: int = SEED) -> np.ndarray:
    """Vectorised stationary bootstrap -> drawdown depth % of each of n draws of h weeks."""
    r = np.asarray(weekly, float)
    T = len(r)
    rng = np.random.default_rng(seed + 1000 * block + h)
    idx = np.empty((n, h), dtype=np.int64)
    idx[:, 0] = rng.integers(0, T, n)
    jump = rng.random((n, h)) < 1.0 / block
    fresh = rng.integers(0, T, (n, h))
    for k in range(1, h):
        idx[:, k] = np.where(jump[:, k], fresh[:, k], (idx[:, k - 1] + 1) % T)
    nav = np.concatenate([np.ones((n, 1)), np.cumprod(1 + r[idx], axis=1)], axis=1)
    return (1 - nav / np.maximum.accumulate(nav, axis=1)).max(axis=1) * 100


def pctl(dd: np.ndarray) -> dict:
    return {f"p{p}": round(float(np.percentile(dd, p)), 2) for p in (50, 95, 99)}


def table(weekly: np.ndarray) -> dict:
    return {f"block{b}": {f"h{h}": pctl(boot_dd(weekly, h, b)) for h in HORIZONS} for b in BLOCKS}


def explain_52w_p95(weekly: pd.Series) -> dict:
    """Why the frozen band's 52-week bootstrap p95 (22.85) equals the backtest's worst drawdown (22.85) exactly."""
    r = weekly.to_numpy(float)
    nav = np.concatenate([[1.0], np.cumprod(1 + r)])
    peak = np.maximum.accumulate(nav)
    depth = 1 - nav / peak
    trough = int(depth.argmax())
    pk = int(np.where(nav[:trough + 1] == peak[trough])[0][-1])
    worst = float(depth.max() * 100)
    # the band's exact procedure: core.stationary_bootstrap, mean block 8, 5000 draws, seed 20261113 + h
    _c, dd = C.stationary_bootstrap(r, 52)
    p95 = float(np.percentile(dd, 95))
    exact = np.isclose(dd, worst, atol=0.005)
    # the episode's run of weeks: weekly returns r[pk : trough] (nav index i = after week i-1)
    ep = list(range(pk, trough))
    # re-run the same draw generator to recover each draw's indices and test whether it holds the episode intact
    T, h, block, n = len(r), 52, C.BLOCK_WEEKS, C.N_DRAWS
    rng = np.random.default_rng(20261113 + h)
    contains = np.zeros(n, bool)
    for j in range(n):
        idx = np.empty(h, dtype=int)
        i = rng.integers(0, T)
        for k in range(h):
            if k and rng.random() < 1.0 / block:
                i = rng.integers(0, T)
            idx[k] = i % T
            i += 1
        s = "," + ",".join(map(str, idx)) + ","
        contains[j] = ("," + ",".join(map(str, ep)) + ",") in s
    n_exact = int(exact.sum())
    rank_lo = int((dd < worst - 0.005).sum())
    return {"worst_backtest_dd_pct": round(worst, 3), "episode": {"peak_week": str(weekly.index[pk - 1].date()) if pk else "start",
                                                                 "trough_week": str(weekly.index[trough - 1].date()),
                                                                 "length_weeks": len(ep)},
            "band_bootstrap_p95_reproduced": round(p95, 3),
            "draws": n, "draws_equal_to_worst": n_exact, "share_equal_to_worst": round(n_exact / n, 4),
            "draws_deeper_than_worst": int((dd > worst + 0.005).sum()),
            "p95_rank_position": "the 95th percentile sits at draw rank 4750; draws ranked "
                                 f"{rank_lo + 1}..{rank_lo + n_exact} all equal the worst",
            "draws_containing_the_whole_episode_contiguously": int(contains.sum()),
            "exact_draws_that_contain_the_episode": int((contains & exact).sum()),
            "clip_in_code": "none - core.stationary_bootstrap and core._path_stats have no clip/cap",
            "wider_of_two": "not the cause - the BOOTSTRAP column itself reads 22.85 before core.wider is applied; the "
                            "ensemble column reads 21.33 and the band takes the deeper of the two"}


def main() -> int:
    d = navs()
    sw_m, mo_m = d["swing_metrics"], d["momentum_metrics"]
    anchors = {"swing_unperturbed_2019_01_01": {k: round(float(v), 4) for k, v in sw_m.items()},
               "momentum_0001": {"cagr_pct": round(mo_m["cagr_pct"], 2), "sharpe": round(mo_m["sharpe"], 3)}}
    print("ANCHORS", anchors, flush=True)
    if (anchors["momentum_0001"]["cagr_pct"], anchors["momentum_0001"]["sharpe"]) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")
    if round(sw_m["sharpe"], 3) != 1.025 or round(sw_m["maxdd"] * 100, 1) != -40.1:
        raise SystemExit("live swing anchor mismatch (1.025 / -40.1%): stop")

    rb = blend_daily(d["momentum"], d["swing"], 0.15)
    wb = C.weekly_returns(to_nav(rb))
    blend_worst = float((to_nav(rb) / to_nav(rb).cummax() - 1).min() * 100)
    weekly_worst = C._path_stats(wb.to_numpy())[1]
    print("blend daily worst", round(blend_worst, 2), "weekly worst", round(weekly_worst, 2), flush=True)
    # The frozen band's worst_backtest_drawdown_pct is the DAILY NAV drawdown (build_bands.maxdd_pct(d["nav"])).
    if round(blend_worst, 2) != -22.85:
        raise SystemExit(f"blend anchor mismatch: daily worst {blend_worst:.2f} != -22.85 (frozen band): stop")

    res = {"window": COMMON, "n_draws": N_DRAWS, "seed": SEED, "blocks": BLOCKS, "horizons": HORIZONS,
           "anchors": anchors, "blend_worst_dd_pct": {"daily": round(blend_worst, 2), "weekly": round(weekly_worst, 2)},
           "n_weeks": int(len(wb))}
    res["q1_blend_vt15"] = table(wb.to_numpy())
    res["q2_why_52w_p95_equals_worst"] = {**explain_52w_p95(wb), "band_worst_is_daily_nav_dd_pct": round(blend_worst, 2),
                                          "weekly_series_worst_dd_pct": round(weekly_worst, 3)}
    # Q3: most conservative block = deepest 156-week p95 at the current 15% target
    p95_156 = {b: res["q1_blend_vt15"][f"block{b}"]["h156"]["p95"] for b in BLOCKS}
    blk = max(p95_156, key=p95_156.get)
    sweep = []
    for t in TARGETS:
        r = blend_daily(d["momentum"], d["swing"], t)
        w = C.weekly_returns(to_nav(r))
        cg, sh = cagr_sharpe(r)
        dd156 = boot_dd(w.to_numpy(), 156, blk)
        sweep.append({"target_pct": int(round(t * 100)), "cagr_pct": round(cg, 2), "sharpe": round(sh, 3),
                      "backtest_worst_dd_pct": round(float((to_nav(r) / to_nav(r).cummax() - 1).min() * 100), 2),
                      "boot156_p50": round(float(np.percentile(dd156, 50)), 2),
                      "boot156_p95": round(float(np.percentile(dd156, 95)), 2),
                      "boot156_p99": round(float(np.percentile(dd156, 99)), 2),
                      "meets_bar": bool(np.percentile(dd156, 95) <= BAR)})
    ok = [s for s in sweep if s["meets_bar"]]
    res["q3_vol_target"] = {"block_used": blk, "why": f"deepest 156-week p95 at 15%: {p95_156}",
                            "rule": "highest target whose 156-week bootstrap p95 drawdown depth <= 25%",
                            "sweep": sweep, "highest_meeting_bar": (max(ok, key=lambda s: s["target_pct"]) if ok else None)}
    # Q4: components alone, reference only
    res["q4_momentum_alone"] = table(C.weekly_returns(window(d["momentum"])).to_numpy())
    res["q4_swing_alone"] = table(C.weekly_returns(window(d["swing"])).to_numpy())
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
