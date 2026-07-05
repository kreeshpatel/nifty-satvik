"""Pre-reg 0092 — tightened weekly six-step: pullback to a VISIBLY-rising 44-week SMA.

Owner chart-QA spec. Same as 0091 EXCEPT three signal tightenings that encode "price dips to a clearly
rising 44-week SMA and bounces" (reject flat/rolling MAs and extended names):
  1. slope floor : 44w-SMA up >= 3% over the last 13 weeks (a visible quarter-long climb)
  2. tight touch : week low <= SMA*1.03 AND SMA < close <= SMA*1.06 (dips to & closes near the line)
  3. quality green: close > open AND close in the upper half of the week's range (a decisive bounce)
Entry / stop / exits / sizing / universe / costs are byte-identical to 0091 (reuses W89.backtest).

Frozen in diagnostics/research/preregistry/0092-weekly-tightened-pullback.md.

    python scripts/run_bhanushali_weekly_tight.py [--ledger]
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

SLOPE_MIN = 0.03      # 44-week SMA must be up >= 3% over SLOPE_LOOKBACK weeks
SLOPE_LOOKBACK = 13   # ~one quarter
LOW_BAND = 0.03       # week low within 3% above the MA (a real dip to the line)
CLOSE_CAP = 0.06      # week close within 6% above the MA (near the line, not extended)


def prep_weekly_tight(ohlcv, drop_erratum: bool = False):
    """0091's prep, but with the tightened pullback-to-rising-MA signal (slope floor + tight band + qgreen)."""
    P = prep(ohlcv, drop_erratum=drop_erratum)
    for t, s in P.items():
        c = s["c"]
        s["ema20"] = pd.Series(c).rolling(20).mean().to_numpy()      # 20-day SMA, trail line (aliased)
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
        rising = slope >= SLOPE_MIN                                   # (1) visibly-rising MA
        rng = whigh - wlow
        qgreen = (wclose > wopen) & (rng > 0) & ((wclose - wlow) >= 0.5 * rng)   # (3) quality green
        touch = (wlow <= wsma * (1 + LOW_BAND)) & (wclose > wsma) & (wclose <= wsma * (1 + CLOSE_CAP))  # (2)
        wsig = rising & qgreen & touch & (wclose > wsma)
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
    args = sys.argv[1:]
    print("=== pre-reg 0092: tightened weekly (rising-MA slope floor + tight pullback + quality green) ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_tight(ohlcv)
    print(f"corrected universe: {len(P)} names | slope>={SLOPE_MIN:.0%}/{SLOPE_LOOKBACK}w | "
          f"low<={LOW_BAND:.0%} close<={CLOSE_CAP:.0%} of MA | quality green | 0091 entry/exits\n")

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
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"])
        tot = led["net_pnl"].sum()
        big = yr["sum"].max()
        print("    per-year: " + " | ".join(f"{y} {int(x['count'])}/{x['sum']/1e5:+.1f}L" for y, x in yr.iterrows()))
        print(f"    concentration: biggest year = {big/tot*100:.0f}% of profit (0091 was 2023=49%)")

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
    print(f"\n  0091 (loose) reference: Sharpe +0.869 / CAGR +18.2% / MaxDD -41.5% / Calmar 0.44 / win 52%")
    print(f"  head-to-head: dSharpe {net['sharpe']-0.869:+.3f} | dCAGR {net['cagr']*100-18.2:+.1f}pp "
          f"| dMaxDD {net['dd']*100-(-41.5):+.1f}pp | trades {net['trades']} vs ~275")

    net_err = W89.backtest(prep_weekly_tight(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))
    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_weekly_tight_0092_trades.csv"
        led.drop(columns=["yr"]).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0092; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
