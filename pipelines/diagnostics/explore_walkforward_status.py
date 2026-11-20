"""MEASUREMENT: walk-forward / CPCV status of the live swing, 0001 momentum and the 70/30 blend, 2019 to mid-2024.

Owner request 2026-11-18 (research/robust-sizing). Nothing is tuned; no trial; no sealed read (swing prices cut at
2024-06-30). Every return series is a CONTINUOUS SLICE of one full run (never a fresh-capital re-run).

WINDOW  swing and momentum 2019-01-01..2024-06-28; blend 2019-03-01..2024-06-28 (its frozen-band window). The
        momentum series is sliced out of the 2017-01-01 run of record.

CPCV    nq.validation.cpcv.cpcv_splits with the module's defaults (n_groups=10, n_test_groups=2, horizon=0,
        embargo=0) over the daily-return index; nq.validation.cpcv.cpcv_paths rebuilds the C(10,2)*2/10 = 9 OOS
        paths. These are FROZEN RULES: no parameter is fitted on a training set, so each test group's OOS returns are
        the same whichever split it comes from, and every path is the same stitched series. That is the
        degeneracy nq/runner/research.py documents. With nothing fitted per split, each path is identical BY
        CONSTRUCTION; the path-Sharpe spread is printed as the check, not as evidence.
        "Out-of-sample Sharpe per fold" = annualised Sharpe of each of the 10 contiguous groups.

DSR     the harness's frozen-baseline path, nq.runner.research: non-overlapping 63-day block returns
        (_window_sig), cross-trial variance from the 63-day block-bootstrap Sharpe CI (block_bootstrap_metric, 5000
        draws, seed 12345), n_trials = nq.validation.dsr.cumulative_n_trials() read from the ledger (not memory).

PBO     nq.validation.pbo.cscv_pbo, n_blocks=16 (the repo standard, adjudicate_family). PBO needs a FAMILY; the
        family is fixed here, before any PBO is computed: the unperturbed run of every +/-10% / +/-20% one-at-a-time
        nudge from explore_param_sensitivity (the base included). Blend family = each swing-nudged book blended
        with base momentum, plus each momentum-nudged book blended with base swing, all at 15% vol.

    python pipelines/diagnostics/explore_walkforward_status.py
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
import explore_blend_drawdown_sizing as B  # noqa: E402
import explore_param_sensitivity as S  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_walkforward_status.json"
CACHE = ROOT / ".cache" / "robust_sizing"
WIN = ("2019-01-01", "2024-06-28")


def existing() -> dict:
    a1 = ROOT / "diagnostics" / "research" / "certify_live_config_A1.json"
    m = json.loads((ROOT / "research" / "0001-xsec-momentum" / "results.json").read_text(encoding="utf-8"))
    return {
        "live_swing": {"walk_forward_or_cpcv": None,
                       "nearest": "diagnostics/research/certify_live_config_A1.md|.json - sub-period slices "
                                  "(2017-18, 2019-21, 2022-on) + DSR + bootstrap CI; no folds, no CPCV",
                       "a1_exists": a1.exists()},
        "xsec_momentum_0001": {"walk_forward_or_cpcv": None,
                               "nearest": "research/0001-xsec-momentum/results.json - CSCV PBO over a 9-config "
                                          f"(top_n x buffer) family: pbo {round(m['pbo']['pbo'], 3)}, "
                                          f"n_configs {m['pbo']['n_configs']}; no folds, no CPCV"},
        "blend_70_30_vt15": {"walk_forward_or_cpcv": None, "nearest": "none - only the frozen lifecycle bands"}}


def sl(nav: pd.Series, lo=WIN[0], hi=WIN[1]) -> pd.Series:
    return nav[(nav.index >= pd.Timestamp(lo)) & (nav.index <= pd.Timestamp(hi))]


def ann_sharpe(r) -> float:
    r = np.asarray(r, float)
    return float(r.mean() / r.std() * np.sqrt(252)) if r.size > 2 and r.std() > 0 else float("nan")


def cpcv_report(r: pd.Series) -> dict:
    from nq.validation.cpcv import cpcv_paths, cpcv_splits, make_groups
    x = r.to_numpy(float)
    splits = cpcv_splits(len(x))
    paths = cpcv_paths(splits, 10)
    spans = make_groups(len(x), 10)
    path_sh = []
    for p in paths:
        stitched = np.concatenate([x[spans[g][0]:spans[g][1]] for g in sorted(p)])   # OOS returns of group g
        path_sh.append(ann_sharpe(stitched))
    folds = [{"fold": g + 1, "from": str(r.index[s].date()), "to": str(r.index[e - 1].date()),
              "oos_sharpe": round(ann_sharpe(x[s:e]), 3)} for g, (s, e) in enumerate(spans)]
    return {"n_splits": len(splits), "n_paths": len(paths), "path_sharpes": [round(v, 4) for v in path_sh],
            "path_sharpe_spread": round(float(np.ptp(path_sh)), 6), "folds": folds}


def dsr_report(r: pd.Series) -> dict:
    from nq.runner.research import _dsr_from_bootstrap, _window_sig, block_bootstrap_metric, sharpe
    from nq.validation.dsr import cumulative_n_trials
    x = r.to_numpy(float)
    nt = cumulative_n_trials()
    ci = block_bootstrap_metric(x, sharpe, block_size=63, n_samples=5000, seed=12345)
    sig = _window_sig(x)
    return {"n_trials": nt, "sharpe_full": round(ann_sharpe(x), 3), "sharpe_ci_5_95": [round(ci.lower, 3), round(ci.upper, 3)],
            "n_eff_63d_windows": int(sig[1]) if sig else 0, "dsr": round(_dsr_from_bootstrap(x, nt, (ci.lower, ci.upper)), 4)}


def family_navs(navs: dict) -> dict:
    """Unperturbed (start 2019-01-01 / 2017-01-01, no cost jitter) NAV of every nudge, swing and momentum. Cached."""
    f = CACHE / "family_navs.pkl"
    if f.exists():
        return pd.read_pickle(f)
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    R94 = L._engine()[0]
    fam_sw = {"base": navs["swing"]}
    ctx = E.prepare_context()

    def one(ctx_, kw_over=None, exit_over=None, a_grade=None):
        cfg = L.normalize_config({})
        kw = L.engine_kwargs(cfg)
        if kw_over:
            kw.update(kw_over)
        if exit_over:
            kw["scaled_exit"] = {**kw["scaled_exit"], **exit_over}
        out = R94.backtest(ctx_.P, ctx_.mem, ledger=[], a_grade=a_grade if a_grade is not None else ctx_.a_grade("default"),
                           **kw, demerger_events=ctx_.events)
        nav = pd.Series(out["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        return nav[~nav.index.duplicated(keep="last")].sort_index()
    for name, group, base, is_int in S.SWING_PARAMS:
        if group == "sma":
            continue                                   # needs the engine-copy worker; added below
        for v in sorted({S.nudged(base, is_int, fr) for fr in S.NUDGES} - {base}):
            if group == "prep":
                attr = S.PREP_ATTR[name]
                orig = getattr(R94, attr)
                setattr(R94, attr, v)
                try:
                    fam_sw[f"{name}={v}"] = one(E.prepare_context())
                finally:
                    setattr(R94, attr, orig)
            elif group == "grade":
                fam_sw[f"{name}={v}"] = one(ctx, a_grade=R94.grade_a_entries(ctx.P, top_n=v))
            elif group == "kw":
                fam_sw[f"{name}={v}"] = one(ctx, kw_over={name: v})
            else:
                fam_sw[f"{name}={v}"] = one(ctx, exit_over={name: v})
            print("family swing", name, v, flush=True)
    pd.to_pickle({"swing": fam_sw}, f)
    return {"swing": fam_sw}


def family_momentum(navs: dict) -> dict:
    f = CACHE / "family_mom.pkl"
    if f.exists():
        return pd.read_pickle(f)
    import run_0001_xsec_momentum as M
    import diag_system_inventory_2026_11 as INV
    from nq.data.membership import load_membership
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    from nq.signals import SKIP_DAYS, nse_momentum_score, vol_adjusted_return
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    u = build_universe(corrected_universe(), load_membership(), start=M.START, end=M.END)

    def signals(l12=231, l6=105):
        parts = []
        for _t, g in u.groupby("ticker", sort=True):
            g = g.sort_values("date").copy()
            c = g["close"].to_numpy(float)
            g["mr12"] = vol_adjusted_return(c, l12, skip=SKIP_DAYS)
            g["mr6"] = vol_adjusted_return(c, l6, skip=SKIP_DAYS)
            parts.append(g)
        p = pd.concat(parts, ignore_index=True)
        p.loc[~p["eligible"], ["mr12", "mr6"]] = np.nan
        p = nse_momentum_score(p)
        b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
        b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
        return b

    def run(b, book):
        bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**book), start=M.START, end=M.END, initial_capital=1_000_000.0)
        return INV.to_nav(bt["equity_curve"])
    b0 = signals()
    fam = {"base": navs["momentum"]}
    for name, base, is_int in S.MOM_PARAMS:
        for v in sorted({S.nudged(base, is_int, fr) for fr in S.NUDGES} - {base}):
            if name == "mr12_lookback":
                fam[f"{name}={v}"] = run(signals(l12=v), M.BOOK)
            elif name == "mr6_lookback":
                fam[f"{name}={v}"] = run(signals(l6=v), M.BOOK)
            else:
                fam[f"{name}={v}"] = run(b0, {**M.BOOK, name: v})
            print("family momentum", name, v, flush=True)
    pd.to_pickle(fam, f)
    return fam


def pbo_of(fam: dict, lo=WIN[0], hi=WIN[1]) -> dict:
    from nq.validation.pbo import cscv_pbo
    rets = pd.DataFrame({k: sl(v, lo, hi).pct_change() for k, v in fam.items()}).dropna()
    res = cscv_pbo(rets.to_numpy(), n_blocks=16)
    cols = list(rets.columns)
    full = {k: ann_sharpe(rets[k]) for k in cols}
    top = max(full, key=full.get)
    return {"pbo": round(res.pbo, 4), "n_configs": res.n_configs, "n_periods": res.n_periods, "n_splits": res.n_splits,
            "median_logit": round(res.median_logit, 3), "full_sample_best": top, "full_sample_best_sharpe": round(full[top], 3),
            "base_rank_full_sample": int(sorted(full.values(), reverse=True).index(full["base"]) + 1),
            "most_frequent_is_winner": cols[max(res.winner_counts, key=res.winner_counts.get)]}


def main() -> int:
    navs = B.navs()
    out = {"existing": existing(), "window": WIN}
    fam_sw = family_navs(navs)["swing"]
    fam_mo = family_momentum(navs)
    series = {"live_swing": sl(navs["swing"]).pct_change().dropna(),
              "xsec_momentum_0001": sl(navs["momentum"]).pct_change().dropna(),
              "blend_70_30_vt15": B.blend_daily(navs["momentum"], navs["swing"])}
    for k, r in series.items():
        out[k] = {"cpcv": cpcv_report(r), "dsr": dsr_report(r)}
    out["live_swing"]["pbo"] = pbo_of(fam_sw)
    out["xsec_momentum_0001"]["pbo"] = pbo_of(fam_mo)
    fam_bl = {}
    for k, v in fam_sw.items():
        fam_bl[f"swing:{k}"] = B.to_nav(B.blend_daily(navs["momentum"], v))
    for k, v in fam_mo.items():
        if k != "base":
            fam_bl[f"momentum:{k}"] = B.to_nav(B.blend_daily(v, navs["swing"]))
    fam_bl["base"] = fam_bl.pop("swing:base")
    out["blend_70_30_vt15"]["pbo"] = pbo_of(fam_bl, *B.COMMON)
    out["pbo_family_note"] = ("swing family excludes sma_len (its nudges need the engine-copy worker); "
                              "momentum cadence is categorical and not in the family")
    OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
