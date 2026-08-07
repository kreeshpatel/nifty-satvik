"""Uncapped per-trade census of the owner's daily Supertrend(10,3) + RS(14) + RSI(14)>60 system.

MEASUREMENT, not a trial — no cash constraint, no slot cap, no fill ranker, so it makes no
PROMOTE/KILL decision on the honest base and does not touch n_trials.json (standing 138). It
answers the question a date-demeaned forward-return test cannot: a trend book earns its money
from ASYMMETRIC TRUNCATION (cut at the line, hold the tail), so a flat mean entry edge does not
settle it. This prices the R distribution the rules actually produce.

Rules as given by the owner, literally:
  ENTRY  all three true at the daily close -> buy the NEXT open
           1. Supertrend(10,3) green          2. RS(14) of Nifty > 0        3. RSI(14) > 60
  EXIT   any TWO of {Supertrend red, RS<0, RSI<60} true at a close -> sell the NEXT open
  STOP   the Supertrend line, trailing (owner choice)

Two readings of the stop are reported side by side, because they are not the same strategy:
  A  LITERAL   — the line is an intraday trailing stop AND the 2-of-3 close rule is live.
                 Consequence: a close below the line is then unreachable except through a gap, so
                 the exit degenerates toward "stop OR (RS<0 AND RSI<60)".
  B  RULE-ONLY — no intraday stop; the line only sets R for sizing; exits are purely the 2-of-3
                 close rule. Keeps the owner's stated exit intact.
This is mechanism extraction (how much is the stop, how much is the rule), not a parameter search.

PIT discipline: the stop level in force on bar j is the Supertrend line as of bar j-1 (known at the
prior close). The line on bar j is computed from bar j's own high/low and must never be traded on
intrabar. R denominator = entry - (line at the signal bar).

    python scripts/diag_supertrend_census.py
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
from diag_supertrend_system import (RSI_THR, RS_LEN, START, supertrend,  # noqa: E402
                                    wilder_rsi)
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

COST = 0.0025           # per leg (brokerage + STT + impact), the house flat approximation
MAXHOLD = 252           # backstop only; the rules have no time exit
MIN_BARS = 300


def prep(ohlcv: dict, membership) -> dict:
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < MIN_BARS:
            continue
        periods = membership.get(tkr.upper()) if membership else None
        if not periods:
            continue
        idx = pd.DatetimeIndex(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        line, up = supertrend(h, l, c)
        rsi = wilder_rsi(c)
        ia = n50.reindex(idx, method="ffill").to_numpy(float)
        rs = np.where(ia > 0, c / ia, np.nan)
        rs_sma = pd.Series(rs).rolling(RS_LEN).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            rs_ok = (rs / rs_sma - 1.0) > 0.0
        mem = np.zeros(len(idx), dtype=bool)
        for d_from, d_to in periods:
            mem |= (idx >= pd.Timestamp(d_from)) & (idx <= pd.Timestamp(d_to))
        rsi_ok = np.nan_to_num(rsi, nan=0.0) > RSI_THR
        ok = np.isfinite(line) & np.isfinite(rsi) & np.isfinite(rs_sma)
        triple = up & rsi_ok & np.nan_to_num(rs_ok, nan=False) & ok
        # exit condition: any two of {ST red, RS<0, RSI<60}
        nfalse = (~up).astype(int) + (~np.nan_to_num(rs_ok, nan=False)).astype(int) + (~rsi_ok).astype(int)
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, line=line, mem=mem, ok=ok,
                      rs_dist=(rs / rs_sma - 1.0), triple=triple,
                      exit2=(nfalse >= 2) & ok, st_red=(~up) & ok)
    return P


def census(P: dict, *, intraday_stop: bool, exit_mode: str = "two_of_three") -> pd.DataFrame:
    """Every fresh triple becomes a trade. No cash, no slots, no ranking — the entry, judged alone.

    exit_mode: "two_of_three" = the owner's rule. "st_red" = the MECHANISM PROBE only (exit when
    Supertrend alone flips red), used to price how much tail the 2-of-3 rule truncates. The probe
    is not a promote candidate; a config picked because it scored better here needs its own pre-reg.
    """
    rows = []
    for tkr, s in P.items():
        dates, o, h, l, c = s["dates"], s["o"], s["h"], s["l"], s["c"]
        line, triple, mem, ok = s["line"], s["triple"], s["mem"], s["ok"]
        exit2 = s["exit2"] if exit_mode == "two_of_three" else s["st_red"]
        rsd = s["rs_dist"]
        n = len(c)
        i = 1
        while i < n - 1:
            if not (triple[i] and not triple[i - 1] and mem[i] and ok[i]):
                i += 1
                continue
            entry_i = i + 1
            entry = o[entry_i]
            risk_ref = line[i]                       # the line at the signal close = the stop of record
            if not np.isfinite(entry) or not np.isfinite(risk_ref) or entry <= risk_ref:
                i += 1
                continue
            r_unit = entry - risk_ref
            exit_px = exit_i = reason = None
            for j in range(entry_i, min(n, entry_i + MAXHOLD)):
                stop_lvl = line[j - 1]               # PIT: level known at the prior close
                if intraday_stop and np.isfinite(stop_lvl) and l[j] <= stop_lvl:
                    exit_px = min(o[j], stop_lvl) if j > entry_i else min(o[j], stop_lvl)
                    exit_i, reason = j, "stop"
                    break
                if exit2[j] and j + 1 < n:
                    exit_px, exit_i, reason = o[j + 1], j + 1, "rule"
                    break
            if exit_px is None:
                exit_i = min(n - 1, entry_i + MAXHOLD - 1)
                exit_px, reason = c[exit_i], "maxhold"
            gross = (exit_px - entry) / entry
            net = (exit_px * (1 - COST) - entry * (1 + COST)) / entry
            rows.append(dict(ticker=tkr, entry_date=dates[entry_i], exit_date=dates[exit_i],
                             entry=entry, exit=exit_px, stop0=risk_ref, reason=reason,
                             held=exit_i - entry_i, r_gross=(exit_px - entry) / r_unit,
                             r_net=(exit_px * (1 - COST) - entry * (1 + COST)) / r_unit,
                             ret_gross=gross, ret_net=net, rs_dist=rsd[i],
                             stop_pct=(entry - risk_ref) / entry))
            i = exit_i + 1                            # one position per name at a time
    return pd.DataFrame(rows)


def report(t: pd.DataFrame, label: str) -> None:
    print(f"\n--- {label} ---")
    if t.empty:
        print("  no trades")
        return
    r, rn = t["r_gross"].to_numpy(), t["r_net"].to_numpy()
    se = rn.std(ddof=1) / np.sqrt(len(rn))
    print(f"  trades {len(t):,}   win {(rn > 0).mean()*100:.1f}%   median hold {t['held'].median():.0f}d   "
          f"median stop width {t['stop_pct'].median()*100:.1f}%")
    print(f"  meanR  gross {r.mean():+.3f}   net {rn.mean():+.3f} ± {1.96*se:.3f} (95% CI)   "
          f"medianR net {np.median(rn):+.3f}")
    print(f"  R dist  p10 {np.percentile(rn,10):+.2f}  p25 {np.percentile(rn,25):+.2f}  "
          f"p75 {np.percentile(rn,75):+.2f}  p90 {np.percentile(rn,90):+.2f}  max {rn.max():+.1f}")
    print(f"  mean net return/trade {t['ret_net'].mean()*100:+.2f}%   "
          f"payoff (mean win / mean loss) {rn[rn>0].mean()/abs(rn[rn<=0].mean()):.2f}")
    ex = t["reason"].value_counts(normalize=True) * 100
    print("  exit mix  " + "  ".join(f"{k} {v:.0f}%" for k, v in ex.items()))
    print("  per-year net meanR:  ", end="")
    yrs = []
    for yr, g in t.groupby(t["entry_date"].dt.year):
        if len(g) < 50:
            continue
        yrs.append((yr, g["r_net"].mean()))
    print("  ".join(f"{y} {v:+.2f}" for y, v in yrs))
    pos = sum(1 for _, v in yrs if v > 0)
    print(f"  per-year sign consistency: {pos}/{len(yrs)} positive")


def rank_probe(t: pd.DataFrame) -> None:
    """Does the CRS fill-ranker rescue the population? Book fills go to the strongest RS first, so
    the only slice that ever reaches a capped book is the top of this sort."""
    print("\n--- PROBE 1: does the RS(14) fill-ranker select a better slice? ---")
    s = t[np.isfinite(t["rs_dist"])].copy()
    ic = s["rs_dist"].corr(s["r_net"], method="spearman")
    print(f"  rank-IC (Spearman, RS distance at entry vs realized net R) = {ic:+.4f}   n={len(s):,}")
    s["q"] = pd.qcut(s["rs_dist"], 5, labels=["Q1 weak", "Q2", "Q3", "Q4", "Q5 strong"])
    for q, g in s.groupby("q", observed=True):
        se = g["r_net"].std(ddof=1) / np.sqrt(len(g))
        print(f"    {q:<10} n={len(g):>6,}  net meanR {g['r_net'].mean():+.3f} ± {1.96*se:.3f}  "
              f"win {(g['r_net']>0).mean()*100:.1f}%")
    top = s.nlargest(max(len(s) // 20, 1), "rs_dist")
    se = top["r_net"].std(ddof=1) / np.sqrt(len(top))
    print(f"    top 5% by RS  n={len(top):>6,}  net meanR {top['r_net'].mean():+.3f} ± {1.96*se:.3f}")


def main() -> int:
    print("=== uncapped per-trade census: Supertrend(10,3) + RS(14)>0 + RSI(14)>60, daily ===")
    P = prep(corrected_universe(), load_membership())
    print(f"  names {len(P)}  window from {START.date()}")
    literal = None
    for label, intraday in (("A  LITERAL  (ST line = intraday trailing stop + 2-of-3 close rule)", True),
                            ("B  RULE-ONLY (no intraday stop; exits are the 2-of-3 close rule alone)", False)):
        t = census(P, intraday_stop=intraday)
        t = t[t["entry_date"] >= START]
        report(t, label)
        t.to_csv(ROOT / "diagnostics" / "research" /
                 f"supertrend_census_{'literal' if intraday else 'ruleonly'}.csv", index=False)
        if intraday:
            literal = t
    rank_probe(literal)

    print("\n--- PROBE 2: is the 2-of-3 rule what truncates the tail? ---")
    print("  Same entry, same intraday ST stop; exit ONLY when Supertrend flips red (pure trend hold).")
    print("  MECHANISM ONLY — not a promote candidate, not a tuned variant.")
    probe = census(P, intraday_stop=True, exit_mode="st_red")
    report(probe[probe["entry_date"] >= START], "PROBE  ST-red-only exit")
    print("\n  standing counts: screens 16 · sealed opens 1 · n_trials 138 (unchanged — measurement)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
