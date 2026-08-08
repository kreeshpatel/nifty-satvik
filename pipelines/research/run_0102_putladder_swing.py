"""Pre-reg 0102 - always-on deep-OTM put ladder (Universa-style) on the weekly-swing-0094 book.

Book leg = frozen 0094 (engine untouched). Hedge leg = a NAV sidecar that, every month, spends a fixed
premium budget (1%/yr) on a ~10%-OTM front-monthly NIFTY put (ACTUAL bhavcopy premium), monetizes it if
intrinsic reaches 2x premium, else settles intrinsic at expiry. Naked put (full convexity, no put-spread
cap). Scored against the pre-committed DD-overlay bar in
diagnostics/research/preregistry/0102-continuous-putladder-swing.md.

    python scripts/run_0102_putladder_swing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.options_oi import OI_PIT_PATH, OI_RAW_PATH  # noqa: E402
from run_0100_tailhedge_swing import _curve_metrics, _calmar, _dsharpe_ci  # noqa: E402  (reuse)
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

# ── FIXED params (pre-reg 0102; not retunable) ──
OTM = 0.10             # deep-OTM put strike = nearest listed <= (1-OTM)*spot
ANNUAL_BUDGET = 0.01   # premium spend = 1% of NAV / year, spread evenly monthly
MONETIZE_X = 2.0       # realize the put if intrinsic reaches this multiple of premium (harvest the spike)
REC_SHARPE, REC_DD = 1.132, -0.424


def _deep_otm_put(pe_close, day, expiry, spot):
    """(K, premium) for the ~OTM% put from ACTUAL PE close, or (None, None) if unfillable."""
    try:
        chain = pe_close.loc[(day, expiry)]
    except KeyError:
        return None, None
    if not isinstance(chain, pd.Series) or chain.empty:
        return None, None
    ks = np.sort(chain.index.values.astype(float))
    le = ks[ks <= spot * (1 - OTM)]
    if not len(le):
        return None, None
    K = float(le.max()); prem = float(chain.loc[K])
    return (K, prem) if prem > 0 else (None, None)


def build_ladder_pnl(book_curve, oi, raw):
    """Daily sidecar cashflow + per-cycle ledger for the always-on deep-OTM put ladder."""
    pe = raw[raw["otype"] == "PE"].copy()
    pe["date"] = pd.to_datetime(pe["date"]); pe["expiry"] = pd.to_datetime(pe["expiry"])
    pe_close = pe.groupby(["date", "expiry", "strike"])["close"].last().sort_index()
    spot = oi["spot"]; fexp = pd.to_datetime(oi["front_expiry"])

    cf = pd.Series(0.0, index=book_curve.index)
    ledger, active, last_armed = [], None, None
    for t in book_curve.index:
        S = spot.get(t, np.nan)
        # ── manage the live put: monetize on a spike, else settle at expiry ──
        if active is not None and np.isfinite(S):
            intr = max(active["K"] - float(S), 0.0)
            if intr >= MONETIZE_X * active["premium"]:                    # harvest the convex spike
                cf.loc[t] += intr * active["units"]
                active.update(exit_date=t, exit="monetize", payoff=intr); ledger.append(active); active = None
            elif t >= active["expiry"]:                                    # expiry settle (intrinsic)
                S_E = spot.asof(active["expiry"]); pay = max(active["K"] - float(S_E), 0.0)
                cf.loc[t] += pay * active["units"]
                active.update(exit_date=t, exit="expiry", payoff=pay); ledger.append(active); active = None
        # ── roll: arm a fresh put once per NEW front-month, when flat ──
        E = fexp.get(t)
        if active is None and pd.notna(E) and E != last_armed and np.isfinite(S):
            budget = ANNUAL_BUDGET / 12.0 * float(book_curve.loc[t])
            K, prem = _deep_otm_put(pe_close, t, pd.Timestamp(E), float(S))
            if K is not None:
                units = budget / prem
                cf.loc[t] -= budget
                active = dict(arm_date=t, expiry=pd.Timestamp(E), K=K, premium=prem, units=units,
                              spot=float(S), budget=budget)
                last_armed = E
    return cf, pd.DataFrame(ledger)


def main() -> int:
    print("=== pre-reg 0102: always-on deep-OTM put ladder (Universa-style) on the weekly-swing-0094 book ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    oi = pd.read_parquet(OI_PIT_PATH); oi.index = pd.to_datetime(oi.index)
    raw = pd.read_parquet(OI_RAW_PATH)
    print(f"corrected universe: {len(P)} names | {int(OTM*100)}%-OTM put, {ANNUAL_BUDGET*100:.1f}%/yr budget, "
          f"monetize at {MONETIZE_X:g}x intrinsic, always-on monthly roll\n")

    base = backtest(P, mem)
    ok = abs(base["sharpe"] - REC_SHARPE) < 0.02 and abs(base["dd"] - REC_DD) < 0.01
    print(f"[invariant] book Sharpe {base['sharpe']:+.3f} | DD {base['dd']*100:.1f}% -> "
          f"{'OK reproduces 0094' if ok else 'MISMATCH - stop'}\n")

    cf, led = build_ladder_pnl(base["curve"], oi, raw)
    hedged = base["curve"] + cf.cumsum()
    cand = _curve_metrics(hedged, base)

    print(_row("book only (ladder OFF)", base))
    print(_row("book + put ladder     ", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe book  : 2017-18* {ba:+.2f} | 2019-21 {bb:+.2f} | 2022-26 {bc:+.2f}")
    print(f"    slice Sharpe ladder: 2017-18* {ca:+.2f} | 2019-21 {cb:+.2f} | 2022-26 {cc:+.2f}")

    if len(led):
        won = (led["payoff"] > led["premium"]).sum(); mon = (led["exit"] == "monetize").sum()
        gdebit = led["budget"].sum(); gpay = (led["payoff"] * led["units"]).sum()
        print(f"\n  ladder cycles: {len(led)} | monetized {mon} | premium-positive {won} "
              f"({100*won/len(led):.0f}%) | total spend Rs{gdebit:,.0f} -> payoff Rs{gpay:,.0f} "
              f"(net Rs{gpay-gdebit:,.0f})")
        by = led.assign(yr=led["arm_date"].dt.year).groupby("yr").apply(
            lambda g: (g["payoff"] * g["units"]).sum() - g["budget"].sum(), include_groups=False)
        print("  net Rs by year: " + " | ".join(f"{y} {v/1000:+.0f}k" for y, v in by.items()))

    d_sharpe = cand["sharpe"] - base["sharpe"]; d_cagr = (cand["cagr"] - base["cagr"]) * 100
    d_dd_pp = (cand["dd"] - base["dd"]) * 100; d_slice22 = cc - bc
    print(f"\n  dSharpe {d_sharpe:+.3f} | dCAGR {d_cagr:+.2f}pp | dMaxDD {d_dd_pp:+.2f}pp (positive=shallower) "
          f"| Calmar {_calmar(base):.2f}->{_calmar(cand):.2f}")
    print(f"  d(2022-26 slice Sharpe) {d_slice22:+.3f}")
    lo, hi = _dsharpe_ci(base["ret"], cand["ret"])
    print(f"  dSharpe block-bootstrap 95% CI [{lo:+.3f}, {hi:+.3f}] | n_independent~{len(base['ret'])/63:.0f}")

    bar = {"dMaxDD >= +3.0pp": d_dd_pp >= 3.0, "dSharpe >= -0.05": d_sharpe >= -0.05,
           "2022-26 slice not worse by >0.05": d_slice22 >= -0.05, "dCAGR >= -2.0pp": d_cagr >= -2.0}
    print("\n  pre-committed bar (0102, DD-overlay class):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    verdict = ("SHADOW -> route the put ladder to the forward wall" if all(bar.values())
               else "KILL / UNDERPOWERED - does not clear the 0102 bar")
    from nq.validation.dsr import cumulative_n_trials
    print(f"\n  n_trials (this run counted): {cumulative_n_trials()}\n  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
