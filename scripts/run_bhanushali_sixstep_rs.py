"""Pre-reg 0086 — comparative relative-strength entry gate on the six-step runner-trail book (0085).

The 0085 configuration is unchanged; the only difference is the signal mask: a signal candle is valid
only when the stock's RS line vs the pinned Nifty-500 TRI (RS_t = close_t / tri_close_t, TRI ffilled to
the stock's calendar) is above its OWN 100-day EMA (`ewm(span=100, adjust=False)`). Entry-side only —
open positions and exits are untouched. Before the TRI's 100-session warmup (benchmark starts
2017-09-14 → gate evaluable ~2018-02) the gate passes through, frozen in the pre-reg. Motivated by the
finding-0027 diagnosis of 2025 (signal failure in the Jan–Feb breadth collapse, not costs).

Frozen in diagnostics/research/preregistry/0086-bhanushali-sixstep-rs-gate.md.

Usage:
    python scripts/run_bhanushali_sixstep_rs.py            # run of record
    python scripts/run_bhanushali_sixstep_rs.py --ledger   # dump per-trade CSV
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices, prep  # noqa: E402
from run_bhanushali_sixstep_runner import add_ema  # noqa: E402
from run_bhanushali_sixstep_runner import backtest as backtest_0085  # noqa: E402

RS_EMA_SPAN = 100
TRI_CSV = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"


def apply_rs_gate(P):
    """AND the frozen RS gate into each ticker's signal mask. Returns (P, kept, dropped)."""
    tri = pd.read_csv(TRI_CSV, parse_dates=["date"]).set_index("date")["tri_close"]
    warmup_end = tri.index[min(RS_EMA_SPAN - 1, len(tri) - 1)]
    kept = dropped = 0
    for s in P.values():
        t = tri.reindex(s["dates"], method="ffill").to_numpy(float)
        rs = s["c"] / t
        ema = pd.Series(rs).ewm(span=RS_EMA_SPAN, adjust=False).mean().to_numpy()
        gate = rs > ema
        # pre-warmup / missing-benchmark dates pass through (frozen)
        passthrough = np.isnan(t) | np.asarray(s["dates"] < warmup_end)
        gate = gate | passthrough
        before = int(s["sig"].sum())
        s["sig"] = s["sig"] & np.nan_to_num(gate, nan=False)
        after = int(s["sig"].sum())
        kept += after; dropped += before - after
    return P, kept, dropped


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0086: comparative-RS entry gate (RS vs N500-TRI > EMA100) on the 0085 book ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = add_ema(prep(ohlcv))
    P, kept, dropped = apply_rs_gate(P)
    print(f"corrected universe: {len(P)} names | signal candles kept {kept} / gated away {dropped} "
          f"({dropped/(kept+dropped)*100:.0f}%)\n")

    ledger: list = []
    net = backtest_0085(P, mem, ledger=ledger)
    gross = backtest_0085(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {net['reasons']} | cash-skipped fills: {net['skipped_cash']}")

    led = pd.DataFrame(ledger)
    if len(led):
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"])
        print("    per-year entries / net_pnl: " +
              " | ".join(f"{y} {int(r['count'])}/{r['sum']/1e5:+.1f}L" for y, r in yr.iterrows()))
        g25 = led[led["yr"] == 2025]
        print(f"    2025 (motivating year): {len(g25)} trades | net_pnl {g25['net_pnl'].sum():,.0f} "
              f"(0085 reference: 48 trades / -608,835)")

    arr = net["ret"].to_numpy(float)
    n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}] "
          f"| DSR @ n_trials={n_tr}: {dsr:.3f}")
    gates = {"DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
             "CI_low>0": bool(ci.lower > 0),
             "all_slices>0": bool(a > 0 and b > 0 and c > 0)}
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
    print("\n  references (same cell): 0085 runner-trail +0.587 | 0084 target-capped +0.477 | baseline_v1 0.667")

    # pre-declared sensitivity: drop the two pinned INDIAMART bad-tick bars
    P2, _, _ = apply_rs_gate(add_ema(prep(ohlcv, drop_erratum=True)))
    net_err = backtest_0085(P2, mem)
    print(_row("erratum-dropped NET", net_err))

    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_sixstep_rs_0086_trades.csv"
        led.drop(columns=["yr"]).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0086; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
