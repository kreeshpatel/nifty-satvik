"""Reactive exposure gates — the one market-timing form with documented out-of-sample evidence.

WHY THIS SHAPE. Goyal-Welch (2008/2022) tested 15 macro/valuation PREDICTORS on ~a century of US
data and found most fail out-of-sample. Faber (2007) instead used a REACTIVE rule -- exit after
price closes below its own 10-month SMA -- and its POST-PUBLICATION out-of-sample record
(2006-2012: max drawdown -9.5% vs -46.0% buy-and-hold) is the strongest documented drawdown
reduction in the literature. The distinction is the whole point: Faber never forecasts a downturn,
it notices one has started. 0134 showed forecasting is not available to us; reacting might be.

THE NEW IDEA BEING TESTED (gate D). 0133 §6b established that this family's bad years are NOT bad
market years -- it lost in 2018 (Nifty +3.2%) and 2025 (Nifty +10.5%) and gained in 2026 (Nifty
-8.7%). If that is true, then gating on the MARKET's trend is gating on the wrong series, and the
mechanically correct target is the BOOK'S OWN equity trend. Gate D applies Faber's rule to the
strategy's own ungated equity curve.

  PIT legality of gate D: the signal is the UNGATED (paper) equity curve, which stays observable
  while the traded book sits in cash -- you keep scoring the strategy, you just stop funding it.
  No circularity: the decision series never depends on the gated series.

GATES (fixed before running):
  A  none                      the ungated book
  B  Nifty 10-month SMA        Faber canonical
  C  Nifty 200-day SMA         the daily analogue, and the incumbent from 0133 §5
  D  OWN-EQUITY 10-month SMA   the new candidate
  E  clairvoyant annual switch the CEILING -- perfect foresight of next year's sign, unreachable

**POWER WARNING, stated before the results.** The family has exactly TWO negative years in the
usable window (2018, 2025). A gate that "fixes" them is fitting two events. The number that
matters is therefore not CAGR but the count of independent EXIT EPISODES, reported below -- that is
the true sample size, and it will be small. Nothing here can be promoted; the honest destination
for anything that looks good is the forward wall.

Window starts 2017-01-01: the 2016 bars carry only ~21 eligible names (0133 §3a-CORRECTION) and are
excluded.

MEASUREMENT class; `n_trials` stays 138.

    python scripts/diag_reactive_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_swing_strategy_survey import SPECS, build_base, run  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END = "2017-01-01", "2026-06-30"      # 2016 excluded: ~21 eligible names (0133 §3a)


def month_end_flags(sig: pd.Series, n_months: int) -> pd.Series:
    """True where the month-end value is above its own n-month SMA. Decision for month m+1 uses
    only data through the close of month m (shift(1) below)."""
    me = sig.resample("ME").last()
    on = me > me.rolling(n_months).mean()
    return on.shift(1).fillna(False)


def apply_gate(daily_ret: pd.Series, on_monthly: pd.Series) -> pd.Series:
    key = daily_ret.index.to_period("M")
    on = on_monthly.copy()
    on.index = on.index.to_period("M")
    mask = pd.Series(key, index=daily_ret.index).map(on).fillna(False).astype(bool)
    return daily_ret.where(mask, 0.0)


def stats(daily_ret: pd.Series, exposure: pd.Series | None = None) -> dict:
    eq = (1 + daily_ret.fillna(0)).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    ann = eq.resample("YE").last().pct_change().dropna()
    first = eq.resample("YE").last().iloc[0] / eq.iloc[0] - 1
    ann = pd.concat([pd.Series([first], index=[eq.resample("YE").last().index[0]]), ann])
    epi = 0
    if exposure is not None:
        e = exposure.astype(int)
        epi = int(((e.diff() == -1)).sum())
    return dict(cagr=eq.iloc[-1] ** (1 / yrs) - 1, dd=(eq / eq.cummax() - 1).min(),
                sharpe=daily_ret.mean() / daily_ret.std() * np.sqrt(252) if daily_ret.std() else np.nan,
                neg_years=int((ann < 0).sum()), n_years=len(ann),
                worst=ann.min(), ann=ann,
                inmkt=float((daily_ret != 0).mean()) if exposure is None else float(exposure.mean()),
                episodes=epi)


def line(tag, s):
    print(f"  {tag:<34} CAGR {s['cagr']*100:>7.2f}%  Sh {s['sharpe']:>6.3f}  MaxDD {s['dd']*100:>7.1f}%  "
          f"neg yrs {s['neg_years']}/{s['n_years']}  worst {s['worst']*100:>7.1f}%  "
          f"in-mkt {s['inmkt']*100:>5.1f}%  exits {s['episodes']}")


def main() -> int:
    print("=== REACTIVE EXPOSURE GATES (Faber-class) — react, do not predict ===")
    print(f"    window {START}..{END}  (2016 excluded: ~21 eligible names, 0133 §3a-CORRECTION)\n")
    P = build_base(corrected_universe(), load_membership())

    rets = {}
    for tag, fn, prov in SPECS:
        if "RANDOM" in tag.upper():
            continue
        m = run(P, fn, start=START, end=END)
        rets[tag.split("(")[0].strip()[:22]] = m["eq"].pct_change()
    R = pd.DataFrame(rets)
    fam = R.mean(axis=1).dropna()
    print(f"  family factor from {R.shape[1]} strategies, {len(fam):,} days\n")

    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index()).reindex(fam.index, method="ffill")

    fam_eq = (1 + fam).cumprod()
    gates = {
        "B  Nifty 10-month SMA": month_end_flags(n50, 10),
        "C  Nifty 200-day SMA": month_end_flags(n50, 10) * 0 + (
            (n50 > n50.rolling(200).mean()).resample("ME").last().shift(1).fillna(False)),
        "D  OWN-EQUITY 10-month SMA": month_end_flags(fam_eq, 10),
    }

    print("=== THE FAMILY FACTOR under each gate ===")
    base = stats(fam)
    line("A  no gate (baseline)", base)
    results = {"A  no gate (baseline)": base}
    for tag, on in gates.items():
        g = apply_gate(fam, on)
        expo = pd.Series(fam.index.to_period("M"), index=fam.index).map(
            on.set_axis(on.index.to_period("M"))).fillna(False).astype(bool)
        s = stats(g, expo)
        results[tag] = s
        line(tag, s)

    # E — clairvoyant ceiling: perfect foresight of the calendar year's sign
    yr_sign = fam_eq.resample("YE").last().pct_change()
    yr_sign.iloc[0] = fam_eq.resample("YE").last().iloc[0] / fam_eq.iloc[0] - 1
    good = {d.year for d, v in yr_sign.items() if v > 0}
    clair = fam.where(pd.Series(fam.index.year, index=fam.index).isin(good), 0.0)
    s = stats(clair, pd.Series(fam.index.year, index=fam.index).isin(good))
    results["E  CLAIRVOYANT annual (ceiling)"] = s
    line("E  CLAIRVOYANT annual (ceiling)", s)

    print("\n=== PER-YEAR (%) — did the gates actually fix 2018 and 2025? ===")
    tags = list(results)
    print("  year " + "".join(f"{t.split('  ')[0]:>12}" for t in tags))
    years = sorted({d.year for d in results["A  no gate (baseline)"]["ann"].index})
    for y in years:
        row = ""
        for t in tags:
            a = results[t]["ann"]
            v = a[[d.year == y for d in a.index]]
            row += f"{v.iloc[0]*100:>11.1f}%" if len(v) else f"{'-':>12}"
        print(f"  {y}" + row)

    print("\n=== SANITY: does the Faber rule work on the NIFTY itself? ===")
    nret = n50.pct_change().dropna()
    line("nifty buy-and-hold", stats(nret))
    on = month_end_flags(n50, 10)
    expo = pd.Series(nret.index.to_period("M"), index=nret.index).map(
        on.set_axis(on.index.to_period("M"))).fillna(False).astype(bool)
    line("nifty + 10-month SMA gate", stats(apply_gate(nret, on), expo))

    print("\n=== SAMPLE-SIZE REALITY CHECK ===")
    for t in tags[1:]:
        e = results[t]["episodes"]
        print(f"  {t:<34} {e} independent exit episodes  -> effective n = {e}")
    print("  The family has TWO negative years in this window. Any gate that 'fixes' them is")
    print("  fitting two events. Judge on episode count, not on CAGR.")
    print("\n  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
