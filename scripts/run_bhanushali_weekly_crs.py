"""Pre-reg 0093 — weekly six-step with slope floor + quality green + comparative-RS filter.

Owner spec after the 0092 KILL:
  1. KEEP the slope floor      : close > 44w-SMA AND 44w-SMA up >= 3% over 13 weeks
  2. REVERT the pullback band  : back to 0091's LOOSE 7% (the tight band killed 0092 — finding 0035)
  3. KEEP quality green        : close > open AND close in the upper half of the week's range
  4. ADD comparative-RS (CRS)  : weekly RS = stock_close / index_close; buy only if RS > its 40-week SMA
Entry / stop / exits / sizing / universe / costs = 0091 (reuses W89.backtest).

Index = pinned Nifty-500 TRI (research/exports/benchmark_nifty500_tri.csv). The owner asked for Nifty-50;
it is not in the repo, so this uses the N500 TRI (highly correlated) — CAVEAT noted in the finding.
CRS is the 0086 lever (RS-vs-index-above-its-MA), a prior non-improvement; entry-tightening is 0-for-3.

Frozen in diagnostics/research/preregistry/0093-weekly-slope-qgreen-crs.md.

    python scripts/run_bhanushali_weekly_crs.py [--ledger]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_full as W89  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices, prep  # noqa: E402

SLOPE_MIN, SLOPE_LOOKBACK = 0.03, 13    # slope floor (kept from 0092)
TOUCH_BAND = 0.07                        # LOOSE band restored (0091)
CRS_LEN = 40                             # 40-week SMA on the RS line
TRI_CSV = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"
NIFTY50_CSV = ROOT / "research" / "exports" / "benchmark_nifty50.csv"
# index used for the CRS denominator. Pre-reg 0093 ran of record on the N500 TRI (proxy); the owner's
# INTENDED denominator is Nifty-50 (pinned 2015->, --nifty50), which is the confirmatory run (finding 0037).
INDEX = ("tri", TRI_CSV, "tri_close")


def _load_index():
    _, csv, col = INDEX
    return pd.read_csv(csv, parse_dates=["date"]).set_index("date")[col].sort_index()


def prep_weekly_crs(ohlcv, drop_erratum: bool = False):
    tri = _load_index()
    P = prep(ohlcv, drop_erratum=drop_erratum)
    for t, s in P.items():
        c = s["c"]
        s["ema20"] = pd.Series(c).rolling(20).mean().to_numpy()
        idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
        keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        o, h, l = s["o"], s["h"], s["l"]
        wopen = np.array([o[dd[0]] for dd in weeks]); whigh = np.array([h[dd].max() for dd in weeks])
        wlow = np.array([l[dd].min() for dd in weeks]); wclose = np.array([c[dd[-1]] for dd in weeks])
        wsma = pd.Series(wclose).rolling(44).mean().to_numpy()
        slope = np.full(len(wsma), np.nan); slope[SLOPE_LOOKBACK:] = wsma[SLOPE_LOOKBACK:] / wsma[:-SLOPE_LOOKBACK] - 1.0
        rising = slope >= SLOPE_MIN
        rng = whigh - wlow
        qgreen = (wclose > wopen) & (rng > 0) & ((wclose - wlow) >= 0.5 * rng)
        touch = (wlow <= wsma * (1 + TOUCH_BAND)) & (wclose > wsma)         # LOOSE band (0091)
        # comparative RS vs the index at each week's ending date -> RS > its 40-week SMA
        tri_at = tri.reindex(idx, method="ffill").to_numpy(float)           # TRI ffilled to stock days
        tri_w = np.array([tri_at[dd[-1]] for dd in weeks])
        rs = np.where(tri_w > 0, wclose / tri_w, np.nan)
        rs_sma = pd.Series(rs).rolling(CRS_LEN).mean().to_numpy()
        crs_ok = rs > rs_sma
        wsig = rising & qgreen & touch & (wclose > wsma) & np.nan_to_num(crs_ok, nan=False)
        s["weekend"] = {dd[-1] for dd in weeks}
        s["entry_win"] = {}
        for k in np.flatnonzero(np.nan_to_num(wsig, nan=False)):
            if k + 1 >= len(weeks):
                continue
            edays = weeks[k + 1]
            s["entry_win"][edays[0]] = (edays, float(wlow[k]), float(whigh[k]))
        s["last_signal"] = None
        _ws = np.nan_to_num(wsig, nan=False)
        if len(weeks) and _ws[len(weeks) - 1]:
            li = len(weeks) - 1
            s["last_signal"] = {"fri_idx": int(weeks[li][-1]), "lo": float(wlow[li]), "hi": float(whigh[li])}
    return P


def main() -> int:
    global INDEX
    args = sys.argv[1:]
    if "--nifty50" in args:
        INDEX = ("nifty50", NIFTY50_CSV, "nifty50_close")   # finding 0037 — owner's intended index
    print(f"=== pre-reg 0093: weekly slope-floor + quality-green + CRS>SMA40 (vs {INDEX[0].upper()}) ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_crs(ohlcv)
    print(f"corrected universe: {len(P)} names | slope>={SLOPE_MIN:.0%}/{SLOPE_LOOKBACK}w | loose band "
          f"{TOUCH_BAND:.0%} | quality green | CRS>{CRS_LEN}w-SMA (N500 TRI) | 0091 entry/exits\n")

    ledger: list = []
    net = W89.backtest(P, mem, ledger=ledger)
    gross = W89.backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross)); print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    {net['trades']} trades ({net['tpy']:.0f}/yr) | win {net['wr']*100:.0f}% | exits: {net['reasons']}")
    led = pd.DataFrame(ledger)
    if len(led):
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"]); tot = led["net_pnl"].sum()
        print("    per-year: " + " | ".join(f"{y} {int(x['count'])}/{x['sum']/1e5:+.1f}L" for y, x in yr.iterrows()))
        print(f"    concentration: biggest year = {yr['sum'].max()/tot*100:.0f}% of profit")

    arr = net["ret"].to_numpy(float); n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    calmar = net["cagr"] / abs(net["dd"]) if net["dd"] else float("nan")
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | CAGR {net['cagr']*100:+.1f}% | MaxDD {net['dd']*100:.1f}% | Calmar {calmar:.2f}")
    print(f"  bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}] | DSR @ n_trials={n_tr}: {dsr:.3f}")
    gates = {"DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
             "CI_low>0": bool(ci.lower > 0), "all_slices>0": bool(a > 0 and b > 0 and c > 0)}
    print("  gates:", {k: ("PASS" if v else "FAIL") for k, v in gates.items()})
    if all(gates.values()):
        verdict = "PROMOTE -> forward-wall watched sleeve"
    elif ci.lower > 0 and net["sharpe"] > 0:
        verdict = f"UNDERPOWERED (real-looking, not certified at n_trials={n_tr})"
    elif net["sharpe"] > 0:
        verdict = "UNDERPOWERED/WEAK (positive but CI straddles 0)"
    else:
        verdict = "KILL"
    print(f"  VERDICT: {verdict}")
    print(f"\n  0091 (loose) ref: +0.869 / +18.2% / -41.5% / win 52% | 0092 (tight) was +0.142 / +0.5% (KILL)")
    print(f"  head-to-head vs 0091: dSharpe {net['sharpe']-0.869:+.3f} | dCAGR {net['cagr']*100-18.2:+.1f}pp "
          f"| dMaxDD {net['dd']*100-(-41.5):+.1f}pp | trades {net['trades']} vs ~275")

    net_err = W89.backtest(prep_weekly_crs(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))
    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_weekly_crs_0093_trades.csv"
        led.drop(columns=["yr"]).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0093; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
