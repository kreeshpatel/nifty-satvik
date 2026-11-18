"""MEASUREMENT: parameter-sensitivity ("spike") gate re-run on the ADOPTED live swing and 0001 momentum parameters.

Owner request 2026-11-18 (research/robust-sizing). Analysis only: no live rule, no trial counter, no sealed read.
Nothing here can be adopted - every value is a nudge of an already-adopted parameter, reported for fragility.

THE GATE (skills/pre-register, skills/verify-before-report): every numeric parameter nudged by -20%, -10%, +10%,
+20%, one at a time, others fixed, over the 20-path ensemble (nq.lab.ensemble.draw_perturbations(20,
DEFAULT_SEED): cost jitter +/-10bp per side and start date in the first ~20 sessions). Pass = the median Sharpe
change stays positive at every +/-10% nudge and keeps >= half its unnudged size at every +/-20% nudge.

"SHARPE CHANGE" FOR A STANDALONE STRATEGY - fixed before any result was seen, both reported:
  vs_benchmark  path Sharpe - Sharpe of the Nifty Midcap150 Momentum 50 TRI over the same window (the mission's
                benchmark, diagnostics/research/benchmarks/tri/nifty_midcap150_momentum_50_tri.csv)
  vs_cash       path Sharpe itself (the change against holding cash; Sharpe is computed without a risk-free rate,
                exactly as the engine's own metric)
plus, descriptive only, the PAIRED change against the unnudged book on the same path (nudged - base).

Sharpe = mean(daily NAV return) / std * sqrt(252) over the reporting window.
  swing     nq/lab/ensemble.py::slice_metrics, reporting window 2019-03-01..2024-06-28 (prices cut 2024-06-30)
  momentum  the same formula on the engine equity curve, window = each path's start..2026-06-30

Integer parameters are rounded to the nearest integer after nudging (Python round); a nudge that rounds back to
the base value, or two nudges that round to the same value, are computed once and reported as such.

    python pipelines/diagnostics/explore_param_sensitivity.py swing  <param> [<param> ...]
    python pipelines/diagnostics/explore_param_sensitivity.py momentum <param> [<param> ...]
    python pipelines/diagnostics/explore_param_sensitivity.py report
"""
from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"), str(ROOT / "pipelines" / "diagnostics")]

OUT_DIR = ROOT / "diagnostics" / "research" / "explore" / "sensitivity"
OUT_MD = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_param_sensitivity.md"
TRI = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap150_momentum_50_tri.csv"
NUDGES = (-0.20, -0.10, 0.10, 0.20)
N_PATHS = 20
LEG_COST_REF = 0.0035                     # momentum: ~0.35% per leg, as pipelines/lifecycle/build_bands.py

# (name, group, base value, is_int). group: prep | sma | grade | kw | exit
SWING_PARAMS = [
    ("sma_len", "sma", 44, True), ("touch_band", "prep", 0.07, False), ("slope_min", "prep", 0.03, False),
    ("slope_lookback", "prep", 13, True), ("crs_len", "prep", 40, True), ("grade_top_n", "grade", 5, True),
    ("risk_pct", "kw", 0.02, False), ("ext_cap", "kw", 0.20, False), ("max_risk_pct", "kw", 0.10, False),
    ("max_notional_pct", "kw", 0.20, False), ("stale_absent_days", "kw", 10, True),
    ("tp1_r", "exit", 2.0, False), ("tp1_frac", "exit", 0.40, False), ("pattern_frac", "exit", 0.40, False),
    ("pattern_arm_r", "exit", 2.5, False)]
SWING_NOT_NUDGEABLE = {
    "tp2_frac": "0.0 - a zero value has no +/-% neighbourhood",
    "runner_sma_buffer": "0.0 - a zero value has no +/-% neighbourhood",
    "tp2_r": "3.0 but inert: tp2_frac = 0, so no tranche is ever booked at tp2_r"}
PREP_ATTR = {"touch_band": "TOUCH_BAND", "slope_min": "SLOPE_MIN", "slope_lookback": "SLOPE_LOOKBACK", "crs_len": "CRS_LEN"}
MOM_PARAMS = [("mr12_lookback", 231, True), ("mr6_lookback", 105, True), ("top_n", 30, True), ("buffer_mult", 1.5, False)]
MOM_NOT_NUDGEABLE = {"cadence": "'M' - categorical; the engine supports only W | 2W | M | Q, so a +/-10% or +/-20% "
                                "change in rebalance interval cannot be expressed"}


def nudged(base, is_int, f):
    v = base * (1 + f)
    return int(round(v)) if is_int else round(float(v), 6)


def sharpe(nav: pd.Series) -> float:
    r = nav.pct_change().dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 2 and r.std() > 0 else float("nan")


def tri_sharpe(lo, hi) -> float:
    d = pd.read_csv(TRI, parse_dates=["date"]).set_index("date").iloc[:, 0].sort_index()
    return sharpe(d[pd.Timestamp(lo):pd.Timestamp(hi)])


def _save(book, param, value, rows, extra=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    f = OUT_DIR / f"{book}__{param}__{value}.json"
    f.write_text(json.dumps({"book": book, "param": param, "value": value, "paths": rows, **(extra or {})},
                            indent=1, default=float), encoding="utf-8")


def _done(book, param, value) -> bool:
    return (OUT_DIR / f"{book}__{param}__{value}.json").exists()


# ----------------------------------------------------------------------------------------------- swing
def _patch_sma(n: int):
    """Load a COPY of the engine with the 44-week SMA literal replaced, registered under the engine's own name.

    Used only in a worker that runs sma_len; the self-check in run_swing proves n=44 reproduces the base."""
    src_path = ROOT / "scripts" / "run_bhanushali_weekly_rank.py"
    src = src_path.read_text(encoding="utf-8")
    assert src.count("pd.Series(wclose).rolling(44)") == 1, "SMA literal moved; the patch would be unsafe"
    src = src.replace("pd.Series(wclose).rolling(44)", "pd.Series(wclose).rolling(_SENS_SMA_N)")
    mod = types.ModuleType("run_bhanushali_weekly_rank")
    mod.__file__ = str(src_path)
    mod._SENS_SMA_N = int(n)
    sys.modules["run_bhanushali_weekly_rank"] = mod
    exec(compile(src, str(src_path), "exec"), mod.__dict__)
    return mod


def run_swing(params: list[str]) -> None:
    from nq.lab import ensemble as E
    from nq.lab import runs as L
    spec = {p[0]: p for p in SWING_PARAMS}
    draws = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED)
    sma_mode = params == ["sma_len"]
    if "sma_len" in params and not sma_mode:
        raise SystemExit("run sma_len in its own process (it replaces the engine module)")

    def paths(ctx, kw_over=None, exit_over=None, a_grade=None):
        R94 = L._engine()[0]
        rows = []
        for _, d in draws.iterrows():
            cfg = {**L.normalize_config({}), "start": str(pd.Timestamp(d["start"]).date())}
            kw = L.engine_kwargs(cfg)
            if kw_over:
                kw.update(kw_over)
            if exit_over:
                kw["scaled_exit"] = {**kw["scaled_exit"], **exit_over}
            led: list = []
            ag = a_grade if a_grade is not None else ctx.a_grade("default")
            with E.cost_jitter(float(d["cost_delta"])):
                out = R94.backtest(ctx.P, ctx.mem, ledger=led, a_grade=ag, **kw, demerger_events=ctx.events)
            nav = pd.Series(out["curve"], dtype=float)
            nav.index = pd.DatetimeIndex(nav.index).normalize()
            nav = nav[~nav.index.duplicated(keep="last")].sort_index()
            m = E.slice_metrics(nav, pd.DataFrame(led), E.REPORT_FROM)
            rows.append({"path": int(d["path"]), "sharpe": float(m["sharpe"]), "cagr": float(m["cagr"]),
                         "maxdd": float(m["maxdd"]), "trades": int(m["trades"])})
        return rows

    if sma_mode:
        base_n = 44
        for v in sorted({nudged(base_n, True, f) for f in NUDGES} | {base_n}):
            if _done("swing", "sma_len", v):
                continue
            _patch_sma(v)
            ctx = E.prepare_context()
            t0 = time.time()
            rows = paths(ctx)
            _save("swing", "sma_len", v, rows, {"seconds": round(time.time() - t0, 1)})
            print("swing sma_len", v, round(np.median([r["sharpe"] for r in rows]), 4), flush=True)
        return

    R94 = L._engine()[0]
    ctx0 = None
    if not _done("swing", "base", "base"):
        ctx0 = E.prepare_context()
        _save("swing", "base", "base", paths(ctx0))
        print("swing base done", flush=True)
    for p in params:
        name, group, base, is_int = spec[p]
        for v in sorted({nudged(base, is_int, f) for f in NUDGES} - {base}):
            if _done("swing", name, v):
                continue
            t0 = time.time()
            if group == "prep":
                attr = PREP_ATTR[name]
                orig = getattr(R94, attr)
                setattr(R94, attr, v)
                try:
                    rows = paths(E.prepare_context())
                finally:
                    setattr(R94, attr, orig)
            else:
                if ctx0 is None:
                    ctx0 = E.prepare_context()
                if group == "grade":
                    rows = paths(ctx0, a_grade=R94.grade_a_entries(ctx0.P, top_n=v))
                elif group == "kw":
                    rows = paths(ctx0, kw_over={name: v})
                else:
                    rows = paths(ctx0, exit_over={name: v})
            _save("swing", name, v, rows, {"seconds": round(time.time() - t0, 1)})
            print("swing", name, v, round(np.median([r["sharpe"] for r in rows]), 4), flush=True)


# ----------------------------------------------------------------------------------------------- momentum
def run_momentum(params: list[str]) -> None:
    import run_0001_xsec_momentum as M
    import diag_system_inventory_2026_11 as INV
    from nq.data.membership import load_membership
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    from nq.lab import ensemble as E
    from nq.signals import SKIP_DAYS, nse_momentum_score, vol_adjusted_return
    from nq.universe import build_universe
    from run_bhanushali_path1 import corrected_universe
    u = build_universe(corrected_universe(), load_membership(), start=M.START, end=M.END)

    def signals(l12=231, l6=105):
        parts = []
        for _tkr, g in u.groupby("ticker", sort=True):
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

    def one(b, start, mult, book):
        bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**{**book, "cost_mult": float(mult)}), start=str(start),
                                     end=M.END, initial_capital=1_000_000.0)
        return INV.to_nav(bt["equity_curve"]), bt["metrics"]

    b0 = signals()
    nav0, met0 = one(b0, M.START, 1.0, M.BOOK)
    anchor = (round(float(met0["cagr_pct"]), 2), round(float(met0["sharpe"]), 3))
    print("ANCHOR 0001 (cagr %, sharpe):", anchor, flush=True)
    if anchor != (21.73, 1.13):
        raise SystemExit(f"anchor mismatch {anchor} != (21.73, 1.13): the harness moved; stop")
    draws = E.draw_perturbations(N_PATHS, E.DEFAULT_SEED, start_base=str(nav0.index[0].date()))

    def paths(b, book):
        rows = []
        for _, d in draws.iterrows():
            nav, _ = one(b, d["start"], 1.0 + float(d["cost_delta"]) / LEG_COST_REF, book)
            yrs = (nav.index[-1] - nav.index[0]).days / 365.25
            rows.append({"path": int(d["path"]), "sharpe": sharpe(nav), "cagr": float((nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1),
                         "maxdd": float((nav / nav.cummax() - 1).min()), "start": str(nav.index[0].date()),
                         "end": str(nav.index[-1].date())})
        return rows

    if not _done("momentum", "base", "base"):
        _save("momentum", "base", "base", paths(b0, M.BOOK), {"anchor": anchor})
        print("momentum base done", flush=True)
    spec = {p[0]: p for p in MOM_PARAMS}
    for p in params:
        name, base, is_int = spec[p]
        for v in sorted({nudged(base, is_int, f) for f in NUDGES} - {base}):
            if _done("momentum", name, v):
                continue
            t0 = time.time()
            if name == "mr12_lookback":
                rows = paths(signals(l12=v), M.BOOK)
            elif name == "mr6_lookback":
                rows = paths(signals(l6=v), M.BOOK)
            else:
                rows = paths(b0, {**M.BOOK, name: v})
            _save("momentum", name, v, rows, {"seconds": round(time.time() - t0, 1)})
            print("momentum", name, v, round(np.median([r["sharpe"] for r in rows]), 4), flush=True)


# ----------------------------------------------------------------------------------------------- report
def _load(book, param, value):
    return pd.DataFrame(json.loads((OUT_DIR / f"{book}__{param}__{value}.json").read_text(encoding="utf-8"))["paths"])


def gate_row(book, name, base, is_int, bench_sharpe):
    """One row of the spike table. bench_sharpe: float (swing, one window) or callable(start, end) (momentum)."""
    b = _load(book, "base", "base").set_index("path")
    base_file = (book, name, base) if (book == "swing" and name == "sma_len") else (book, "base", "base")
    b = _load(*base_file).set_index("path")

    def bench(df):
        if callable(bench_sharpe):
            return df.apply(lambda r: bench_sharpe(r["start"], r["end"]), axis=1)
        return pd.Series(bench_sharpe, index=df.index)

    out = {"param": name, "base": base}
    base_vs_b = float(np.median(b["sharpe"] - bench(b)))
    base_vs_c = float(np.median(b["sharpe"]))
    out["base_median_sharpe"] = round(base_vs_c, 3)
    out["base_change_vs_benchmark"] = round(base_vs_b, 3)
    ok_b, ok_c = base_vs_b > 0, base_vs_c > 0
    for f in NUDGES:
        v = nudged(base, is_int, f)
        tag = f"{int(f * 100):+d}%"
        if v == base:
            n = b
        else:
            n = _load(book, name, v).set_index("path")
        vs_b = float(np.median(n["sharpe"] - bench(n)))
        vs_c = float(np.median(n["sharpe"]))
        paired = float(np.median(n["sharpe"] - b["sharpe"]))
        out[tag] = {"value": v, "median_sharpe": round(vs_c, 3), "change_vs_benchmark": round(vs_b, 3),
                    "paired_d_sharpe": round(paired, 3), "rounds_to_base": v == base}
        if abs(f) < 0.15:
            ok_b &= vs_b > 0
            ok_c &= vs_c > 0
        else:
            ok_b &= vs_b >= 0.5 * base_vs_b if base_vs_b > 0 else False
            ok_c &= vs_c >= 0.5 * base_vs_c if base_vs_c > 0 else False
    out["pass_vs_benchmark"] = bool(ok_b)
    out["pass_vs_cash"] = bool(ok_c)
    out["spike_vs_cash"] = not ok_c
    return out


def report() -> None:
    sw_bench = tri_sharpe("2019-03-01", "2024-06-28")
    tri_cache: dict = {}

    def mom_bench(lo, hi):
        if (lo, hi) not in tri_cache:
            tri_cache[(lo, hi)] = tri_sharpe(lo, hi)
        return tri_cache[(lo, hi)]
    rows = {"swing": [gate_row("swing", n, b, i, sw_bench) for n, _g, b, i in SWING_PARAMS],
            "momentum": [gate_row("momentum", n, b, i, mom_bench) for n, b, i in MOM_PARAMS]}
    res = {"benchmark": "Nifty Midcap150 Momentum 50 TRI", "benchmark_sharpe_swing_window": round(sw_bench, 3),
           "nudges": NUDGES, "n_paths": N_PATHS, "rows": rows,
           "not_nudgeable": {"swing": SWING_NOT_NUDGEABLE, "momentum": MOM_NOT_NUDGEABLE}}
    (OUT_DIR / "summary.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "swing":
        run_swing(args)
    elif mode == "momentum":
        run_momentum(args)
    else:
        report()
