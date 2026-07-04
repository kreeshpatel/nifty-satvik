"""Pre-reg 0090 — market-regime entry filter on the 0089 fully-weekly book.

Exactly 0089, plus one rule: take NO new entries on any day the Nifty-500 TRI's latest completed weekly
close is below its 44-week EMA (market in a weekly downtrend). Open positions are managed and exited
normally. Targets 0089's -54% drawdown (2018/2024 reversals). Leak-free (TRI weekly close is PIT-known).

Frozen in diagnostics/research/preregistry/0090-bhanushali-weekly-regime.md.

Usage:
    python scripts/run_bhanushali_weekly_regime.py            # run of record
    python scripts/run_bhanushali_weekly_regime.py --ledger   # dump per-trade CSV
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
from run_bhanushali_sixstep import _row, _slices  # noqa: E402

TRI_CSV = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"


def market_ok_daily(dates: pd.DatetimeIndex) -> np.ndarray:
    """PIT market filter: for each date, is the latest COMPLETED weekly TRI close above its 44-week EMA?
    Pre-warmup / missing -> True (pass through), frozen."""
    tri = pd.read_csv(TRI_CSV, parse_dates=["date"]).set_index("date")["tri_close"].sort_index()
    w = tri.resample("W-FRI").last().dropna()
    wema = w.ewm(span=44, adjust=False).mean()
    ok_wk = (w > wema)
    ok_wk.iloc[:44] = True                                   # warmup pass-through (frozen)
    # ffill the weekly flag to each daily date (uses the week that closed on/before the date)
    return ok_wk.reindex(dates, method="ffill").fillna(True).to_numpy(bool)


def apply_market_gate(P):
    """Neuter each ticker's entry windows on days the market filter is off. Returns (P, block_frac)."""
    dates_all = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    ok = pd.Series(market_ok_daily(dates_all), index=dates_all)
    blocked = 0; total = 0
    for s in P.items() if False else P.values():
        idx = pd.DatetimeIndex(s["dates"])
        gate = ok.reindex(idx).fillna(True).to_numpy(bool)
        s["mkt_ok"] = gate
        new_win = {}
        for first_i, (days, lo, hi) in s["entry_win"].items():
            # keep only the days of the window on which the market is OK
            kept = [i for i in days if gate[i]]
            total += 1
            if kept:
                new_win[kept[0]] = (kept, lo, hi)
            else:
                blocked += 1
        s["entry_win"] = new_win
    return P, (blocked / total if total else 0.0), float(1 - ok.mean())


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0090: market-regime entry filter (TRI < 44w EMA blocks new buys) on 0089 ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = W89.prep_weekly(ohlcv)
    P, blocked_frac, off_frac = apply_market_gate(P)
    print(f"corrected universe: {len(P)} names | market filter OFF {off_frac*100:.0f}% of days "
          f"| {blocked_frac*100:.0f}% of setups fully blocked\n")

    ledger: list = []
    net = W89.backtest(P, mem, ledger=ledger)
    gross = W89.backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    {net['trades']} fills | exits: {net['reasons']}")
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
    print(f"\n  0089 reference: Sharpe +0.626 / CAGR +11.8% / MaxDD -54.3% / Calmar 0.22")
    print(f"  delta vs 0089: dSharpe {net['sharpe']-0.626:+.3f} | dCAGR {net['cagr']*100-11.8:+.1f}pp "
          f"| dMaxDD {net['dd']*100-(-54.3):+.1f}pp")
    print("  other refs: 0085 +0.587/-37.5% | baseline_v1 0.667 | TRI +12.6%/-38%")

    net_err_P, _, _ = apply_market_gate(W89.prep_weekly(ohlcv, drop_erratum=True))
    net_err = W89.backtest(net_err_P, mem)
    print(_row("erratum-dropped NET", net_err))

    if "--ledger" in args and ledger:
        out = ROOT / "research" / "exports" / "bhanushali_weekly_regime_0090_trades.csv"
        pd.DataFrame(ledger).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(ledger)} trades)")
    print("\n(run of record for pre-reg 0090; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
