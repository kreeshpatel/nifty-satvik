"""Pre-reg 0091 — all-SMA correction of the 0089 fully-weekly book (no EMA anywhere).

Exactly 0089 except: the weekly 44-line that drives the signal is a 44-week SMA (was EMA), and the runner
trail follows a 20-day SMA (was EMA). Owner spec fix. Reuses the 0089 engine unchanged by (a) building the
weekly signal/entry windows on the 44-week SMA and (b) aliasing a 20-day SMA into the `ema20` slot the
0089 trail reads.

Frozen in diagnostics/research/preregistry/0091-bhanushali-weekly-sma.md.

Usage:
    python scripts/run_bhanushali_weekly_sma.py            # run of record
    python scripts/run_bhanushali_weekly_sma.py --ledger   # dump per-trade CSV
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

TOUCH_BAND = W89.TOUCH_BAND     # 7%, unchanged


def prep_weekly_sma(ohlcv, drop_erratum: bool = False):
    """0089's prep with the weekly line = 44-week SMA and the trail line = 20-day SMA (aliased to ema20)."""
    P = prep(ohlcv, drop_erratum=drop_erratum)   # daily arrays (o/h/l/c/dsma/adv20)
    for t, s in P.items():
        c = s["c"]
        s["ema20"] = pd.Series(c).rolling(20).mean().to_numpy()   # 20-day SMA aliased into the trail slot
        idx = pd.DatetimeIndex(s["dates"])
        iso = idx.isocalendar()
        keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        o, h, l = s["o"], s["h"], s["l"]
        wopen = np.array([o[dd[0]] for dd in weeks])
        whigh = np.array([h[dd].max() for dd in weeks])
        wlow = np.array([l[dd].min() for dd in weeks])
        wclose = np.array([c[dd[-1]] for dd in weeks])
        wsma = pd.Series(wclose).rolling(44).mean().to_numpy()    # 44-week SMA (was EMA in 0089)
        rising = np.full(len(wsma), False)
        rising[4:] = wsma[4:] > wsma[:-4]
        trend = (wclose > wsma) & rising
        green = wclose > wopen
        touch = wlow <= wsma * (1 + TOUCH_BAND)
        wsig = green & touch & (wclose > wsma) & trend
        s["weekend"] = {dd[-1] for dd in weeks}
        s["entry_win"] = {}
        for k in np.flatnonzero(np.nan_to_num(wsig, nan=False)):
            if k + 1 >= len(weeks):
                continue
            edays = weeks[k + 1]
            s["entry_win"][edays[0]] = (edays, float(wlow[k]), float(whigh[k]))
    return P


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0091: all-SMA correction of 0089 (44-week SMA signal + 20-day SMA trail) ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = prep_weekly_sma(ohlcv)
    print(f"corrected universe: {len(P)} names | SMA everywhere | 7% touch | weekly-close/Mon exits\n")

    ledger: list = []
    net = W89.backtest(P, mem, ledger=ledger)
    gross = W89.backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    {net['trades']} fills | win {net['wr']*100:.0f}% | exits: {net['reasons']}")
    led = pd.DataFrame(ledger)
    if len(led):
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"])
        print("    per-year: " + " | ".join(f"{y} {int(x['count'])}/{x['sum']/1e5:+.1f}L" for y, x in yr.iterrows()))

    arr = net["ret"].to_numpy(float)
    n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    calmar = net["cagr"] / abs(net["dd"]) if net["dd"] else float("nan")
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | CAGR {net['cagr']*100:+.1f}% | MaxDD {net['dd']*100:.1f}% "
          f"| Calmar {calmar:.2f}")
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
    print(f"\n  0089 (EMA) reference: Sharpe +0.626 / CAGR +11.8% / MaxDD -54.3% / Calmar 0.22")
    print(f"  delta vs 0089-EMA: dSharpe {net['sharpe']-0.626:+.3f} | dCAGR {net['cagr']*100-11.8:+.1f}pp "
          f"| dMaxDD {net['dd']*100-(-54.3):+.1f}pp")
    print("  other refs: 0085 +0.587/-37.5% | baseline_v1 0.667 | TRI +12.6%/-38%")

    net_err = W89.backtest(prep_weekly_sma(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))

    if "--ledger" in args and ledger:
        out = ROOT / "research" / "exports" / "bhanushali_weekly_sma_0091_trades.csv"
        pd.DataFrame(ledger).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(ledger)} trades)")
    print("\n(run of record for pre-reg 0091; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
