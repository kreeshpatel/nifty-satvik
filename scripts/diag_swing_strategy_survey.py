"""Uniform survey of the SWING + POSITIVE strategies from the owner's finfluencer-strategy table.

Nine strategies, each implemented as a COMPLETE system (its own entry, its own stop, its own exit
per the researched published rules), all run through the SAME book, the SAME universe, the SAME
costs and the SAME fill ranker — so differences between cells are differences between strategies,
not between harnesses.

METHOD, fixed before running (this is the part that makes the answer worth having):

    TRAIN   2019-01-01 .. 2023-12-31   <- everything is selected here
    HOLDOUT 2024-01-01 .. 2026-06-30   <- looked at ONCE, never selected on

Picking the best of nine on in-sample CAGR and then tuning it is how fake edges are manufactured;
with nine candidates the best one looks good by chance alone. The train/holdout split is what
converts "which looked best" into "which was actually best". Both numbers are reported for every
cell so the size of the selection bias is visible rather than hidden.

A RANDOM-ENTRY control is included. It is not decoration: it is the null. Any strategy that does
not clearly beat the random cell on the same book has demonstrated nothing.

MEASUREMENT class — a survey of external claims, no PROMOTE/KILL against the honest base, so
`n_trials` stays 138. Promoting anything here requires its own pre-registration.

Spec provenance is recorded per strategy in SPECS below: SOURCED (published rules found and
followed) or RECONSTRUCTED (no usable public spec; standard reading used, flagged as such).

    python scripts/diag_swing_strategy_survey.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
from diag_supertrend_system import rma, supertrend, wilder_rsi  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

EQ0, RISK, NOTIONAL_CAP, MAXPOS, COST = 1_000_000.0, 0.02, 0.10, 10, 0.0025
TRAIN = ("2019-01-01", "2023-12-31")
HOLDOUT = ("2024-01-01", "2026-06-30")
MIN_BARS, SEED = 400, 20260806


# ----------------------------------------------------------------------------- indicators
def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, l, c, n=14):
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = h[0] - l[0]
    return rma(tr, n)


def macd(c, fast=12, slow=26, sig=9):
    line = ema(c, fast) - ema(c, slow)
    return line, ema(line, sig)


def stochastic(h, l, c, k=14, d=3):
    hh = pd.Series(h).rolling(k).max().to_numpy()
    ll = pd.Series(l).rolling(k).min().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        pk = 100.0 * (c - ll) / np.where(hh - ll > 0, hh - ll, np.nan)
    return pk, sma(pk, d)


def period_pivot(idx: pd.DatetimeIndex, h, l, c, freq: str = "M", level: str = "P"):
    """Traditional pivot of the PRIOR completed period, held for the whole current period.

    freq: pandas period alias -- "M" (monthly) or "Q" (quarterly). level: "P" or "R1".
        P = (H+L+C)/3        R1 = 2P - L        (H/L/C of the prior completed period)

    CORRECTNESS NOTE (bug fixed 2026-08-06). The previous implementation did
    ``resample("ME").shift(1).reindex(idx, method="ffill")``, which double-shifts: period-END labels
    sort AFTER the dates they should govern, so an ffill reindex picks up the PREVIOUS label, whose
    value is already shifted. Net effect: the level in force was TWO periods stale for the whole
    period (and NaN for the first one). Verified on a synthetic quarter: dates in Q3 received Q1's
    pivot instead of Q2's. It is conservative (older data, no lookahead) but it is not the rule.
    Mapping each date to its OWN period and reading that period's shifted value is the fix.
    """
    per = idx.to_period(freq)
    df = pd.DataFrame({"h": h, "l": l, "c": c}, index=idx)
    g = df.groupby(per).agg({"h": "max", "l": "min", "c": "last"})
    P = (g["h"] + g["l"] + g["c"]) / 3.0
    val = P if level == "P" else 2 * P - g["l"]
    prev = val.shift(1)                       # prior completed period, indexed BY period
    return pd.Series(per.map(prev), index=idx).to_numpy(dtype=float)


def monthly_pivot(idx: pd.DatetimeIndex, h, l, c):
    """Back-compatible wrapper: prior-calendar-month central pivot."""
    return period_pivot(idx, h, l, c, freq="M", level="P")


def weekly_rsi_daily(idx: pd.DatetimeIndex, c, n=14):
    """RSI on weekly closes, forward-filled onto daily bars (prior completed week only)."""
    w = pd.Series(c, index=idx).resample("W-FRI").last().dropna()
    r = pd.Series(wilder_rsi(w.to_numpy(), n), index=w.index).shift(1)
    return r.reindex(idx, method="ffill").to_numpy()


def fresh(b: np.ndarray) -> np.ndarray:
    return b & ~np.concatenate([[False], b[:-1]])


# ----------------------------------------------------------------------------- strategies
# Each returns (entry_bool, stop_price, target_r, exit_rule_bool_or_None, maxhold)
def s_supertrend_pivot(d):                                   # CA Rachana Ranade — SOURCED
    _, up = supertrend(d["h"], d["l"], d["c"], 10, 3.0)
    piv = monthly_pivot(d["idx"], d["h"], d["l"], d["c"])
    cross = (d["c"] > piv) & (np.concatenate([[np.nan], d["c"][:-1]]) <= np.concatenate([[np.nan], piv[:-1]]))
    sig = fresh(up & (d["c"] > ema(d["c"], 200)) & np.nan_to_num(cross, nan=False))
    return sig, d["c"] - 2.0 * d["atr"], 2.0, None, 252


def s_triple_supertrend(d):                                  # P R Sundar — SOURCED (7,3)(7,2)(10,4)
    l1, u1 = supertrend(d["h"], d["l"], d["c"], 7, 3.0)
    l2, u2 = supertrend(d["h"], d["l"], d["c"], 7, 2.0)
    l3, u3 = supertrend(d["h"], d["l"], d["c"], 10, 4.0)
    allg = u1 & u2 & u3
    stop = np.nanmin(np.vstack([l1, l2, l3]), axis=0)
    return fresh(allg), stop, None, ~allg, 252


def s_ma44(d):                                               # "44 MA" swing — SOURCED (house lineage)
    m = sma(d["c"], 44)
    rising = m > np.concatenate([np.full(22, np.nan), m[:-22]])
    touch = (d["l"] <= m * 1.03) & (d["c"] > m) & (d["c"] > d["o"])
    sig = fresh(np.nan_to_num(rising & touch, nan=False))
    below = d["c"] < m
    three = below & np.concatenate([[False], below[:-1]]) & np.concatenate([[False, False], below[:-2]])
    return sig, d["l"] * 0.999, 3.0, three, 252


def s_rsi_macd_stoch(d):                                     # Trend Trader Karan — RECONSTRUCTED
    # canonical published form: Stoch K/D OVERSOLD and turning up (the pullback), RSI above the
    # midline (trend intact), MACD above its signal (trend intact); stop = last swing low;
    # take-profit = 1.5x risk. Amended to this form BEFORE any output was read.
    ml, msig = macd(d["c"])
    pk, pd_ = stochastic(d["h"], d["l"], d["c"])
    prev_k, prev_d = np.concatenate([[np.nan], pk[:-1]]), np.concatenate([[np.nan], pd_[:-1]])
    ok = (d["rsi"] > 50) & (ml > msig) & (pk > pd_) & (prev_k <= prev_d) & (prev_k < 30)
    low10 = pd.Series(d["l"]).rolling(10).min().to_numpy()
    return fresh(np.nan_to_num(ok, nan=False)), low10 * 0.999, 1.5, None, 252


def s_rsi_oversold(d):                                       # Strategic Stocks — SOURCED (standard)
    prev = np.concatenate([[np.nan], d["rsi"][:-1]])
    sig = np.nan_to_num((prev < 30) & (d["rsi"] >= 30), nan=False)
    return sig, d["c"] - 2.0 * d["atr"], 2.0, None, 252


def s_5star_rsi(d):                                          # Vishal Malkan — SOURCED (60/40 range shift)
    wr = d["wrsi"]
    prev = np.concatenate([[np.nan], d["rsi"][:-1]])
    dipped = pd.Series(d["rsi"] <= 45).rolling(5).max().to_numpy() > 0
    sig = np.nan_to_num((wr > 60) & dipped & (prev < 50) & (d["rsi"] >= 50), nan=False)
    low10 = pd.Series(d["l"]).rolling(10).min().to_numpy()
    return sig, low10 * 0.999, 2.0, None, 252


def s_flag_breakout(d):                                      # Price Action — SOURCED
    c, h, l = d["c"], d["h"], d["l"]
    pole = np.full(len(c), np.nan)
    pole[20:] = c[20:] / c[:-20] - 1.0
    # flag = the 8 bars after a >=20% pole; breakout = close above the flag high on volume
    flag_hi = pd.Series(h).shift(1).rolling(8).max().to_numpy()
    flag_lo = pd.Series(l).shift(1).rolling(8).min().to_numpy()
    pole_ok = pd.Series(np.nan_to_num(pole, nan=0.0) >= 0.20).shift(8).rolling(4).max().to_numpy() > 0
    retrace_ok = (flag_hi - flag_lo) <= 0.5 * np.abs(np.nan_to_num(pole, nan=0.0)) * c
    vol_ok = d["v"] >= 1.2 * d["vma"]
    sig = np.nan_to_num(pole_ok & retrace_ok & (c > flag_hi) & vol_ok, nan=False)
    return fresh(sig), flag_lo, 2.0, None, 126


def s_consolidation_breakout(d):                             # Price Action — SOURCED
    c, h, l = d["c"], d["h"], d["l"]
    hi15 = pd.Series(h).shift(1).rolling(15).max().to_numpy()
    lo15 = pd.Series(l).shift(1).rolling(15).min().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        tight = (hi15 - lo15) / lo15 <= 0.10
    vol_ok = d["v"] >= 1.5 * d["vma"]
    sig = np.nan_to_num(tight & (c > hi15) & vol_ok, nan=False)
    return fresh(sig), lo15, 2.0, None, 126


def s_ma66_stoch(d):                                         # "SS" — RECONSTRUCTED (no public spec)
    pk, pd_ = stochastic(d["h"], d["l"], d["c"])
    prev_k, prev_d = np.concatenate([[np.nan], pk[:-1]]), np.concatenate([[np.nan], pd_[:-1]])
    cross_up = (pk > pd_) & (prev_k <= prev_d) & (prev_k < 30)
    ok = (d["c"] > sma(d["c"], 66)) & cross_up
    return fresh(np.nan_to_num(ok, nan=False)), d["c"] - 2.0 * d["atr"], 2.0, None, 252


def s_random(d):                                             # the NULL — matched-rate random entries
    rng = np.random.default_rng(SEED + (abs(hash(d["tkr"])) % 100_000))
    sig = rng.random(len(d["c"])) < 0.004                    # ~1 signal per name per 250 bars
    sig[:200] = False
    return sig, d["c"] - 2.0 * d["atr"], 2.0, None, 252


SPECS = [
    ("Supertrend + Pivot Points   (CA Rachana Ranade)", s_supertrend_pivot, "SOURCED"),
    ("Triple Supertrend           (P R Sundar)", s_triple_supertrend, "SOURCED"),
    ("44 MA                       (SS)", s_ma44, "SOURCED"),
    ("RSI + MACD + Stochastic     (Trend trader Karan)", s_rsi_macd_stoch, "RECONSTRUCTED"),
    ("RSI Oversold                (Strategic Stocks)", s_rsi_oversold, "SOURCED *KILLED 0020/22/24"),
    ("5 Star RSI                  (Malkansview)", s_5star_rsi, "SOURCED"),
    ("Flag Pattern Breakout       (Price Action)", s_flag_breakout, "SOURCED"),
    ("Consolidation Breakout      (Price Action)", s_consolidation_breakout, "SOURCED"),
    ("66 MA + Stochastic          (SS)", s_ma66_stoch, "RECONSTRUCTED"),
    (">> RANDOM ENTRY CONTROL (the null)", s_random, "CONTROL"),
]


# ----------------------------------------------------------------------------- engine
def build_base(ohlcv, membership):
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < MIN_BARS or not membership.get(tkr.upper()):
            continue
        idx = pd.DatetimeIndex(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        v = (df["Volume"].to_numpy(float) if "Volume" in df.columns else np.full(len(c), np.nan))
        ia = n50.reindex(idx, method="ffill").to_numpy(float)
        rs55 = np.full(len(c), np.nan)
        if len(c) > 55:
            with np.errstate(divide="ignore", invalid="ignore"):
                rs55[55:] = (c[55:] / c[:-55]) / (ia[55:] / ia[:-55]) - 1.0
        mem = np.zeros(len(idx), dtype=bool)
        for a, b in membership[tkr.upper()]:
            mem |= (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(b))
        P[tkr] = dict(tkr=tkr, idx=idx, o=o, h=h, l=l, c=c, v=v, vma=sma(v, 20),
                      atr=atr(h, l, c), rsi=wilder_rsi(c), wrsi=weekly_rsi_daily(idx, c),
                      rs55=rs55, mem=mem, pos={d: i for i, d in enumerate(idx)})
    return P


def run(P, fn, *, start, end):
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    specs, cands = {}, {}
    for tkr, d in P.items():
        sig, stop, tgt, exrule, mh = fn(d)
        sig = np.asarray(sig, bool) & d["mem"]
        specs[tkr] = (stop, tgt, exrule, mh)
        for i in np.flatnonzero(sig):
            if i + 1 >= len(d["c"]) or not np.isfinite(d["rs55"][i]):
                continue
            dt = d["idx"][i]
            if lo <= dt <= hi:
                cands.setdefault(dt, []).append((float(d["rs55"][i]), tkr, int(i)))

    all_dates = [x for x in sorted(set().union(*[set(d["idx"]) for d in P.values()])) if lo <= x <= hi]
    cash = equity = EQ0
    open_pos, eqc, trades = {}, [], []
    prev = None
    for dt in all_dates:
        for tkr in list(open_pos):
            p, d = open_pos[tkr], P[tkr]
            i = d["pos"].get(dt)
            if i is None:
                continue
            stop, tgt, exrule, mh = specs[tkr]
            p["held"] += 1
            px = why = None
            if d["l"][i] <= p["stop"]:
                px, why = min(d["o"][i], p["stop"]), "stop"
            elif p["target"] is not None and d["h"][i] >= p["target"]:
                px, why = max(d["o"][i], p["target"]), "target"
            elif p["pending"]:
                px, why = d["o"][i], "rule"
            elif p["held"] >= mh:
                px, why = d["c"][i], "maxhold"
            if px is not None:
                cash += p["shares"] * px * (1 - COST)
                trades.append(dict(r=(px - p["entry"]) / p["r_unit"], why=why,
                                   ret=(px * (1 - COST) - p["entry"] * (1 + COST)) / p["entry"],
                                   held=p["held"], entry_date=p["date"]))
                del open_pos[tkr]
                continue
            p["pending"] = bool(exrule[i]) if exrule is not None else False

        for _s, tkr, i in sorted(cands.get(prev, []), reverse=True) if prev else []:
            if len(open_pos) >= MAXPOS or tkr in open_pos:
                continue
            d = P[tkr]
            j = d["pos"].get(dt)
            if j is None or j != i + 1:
                continue
            stop, tgt, exrule, mh = specs[tkr]
            entry, s0 = d["o"][j], (stop[i] if np.ndim(stop) else stop)
            if not np.isfinite(entry) or not np.isfinite(s0) or entry <= s0:
                continue
            sh = min(equity * RISK / (entry - s0), equity * NOTIONAL_CAP / entry)
            notion = sh * entry * (1 + COST)
            if sh <= 0 or notion > cash:
                continue
            cash -= notion
            open_pos[tkr] = dict(entry=entry, stop=s0, r_unit=entry - s0, shares=sh, held=0,
                                 target=(entry + tgt * (entry - s0)) if tgt else None,
                                 date=dt, pending=bool(exrule[j]) if exrule is not None else False)

        mtm = sum(p["shares"] * (P[t]["c"][P[t]["pos"][dt]] if dt in P[t]["pos"] else p["entry"])
                  for t, p in open_pos.items())
        equity = cash + mtm
        eqc.append((dt, equity))
        prev = dt

    eq = pd.Series(dict(eqc)).sort_index()
    ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    t = pd.DataFrame(trades)
    return dict(cagr=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan,
                sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else np.nan,
                dd=(eq / eq.cummax() - 1).min(), trades=len(t),
                win=(t["ret"] > 0).mean() if len(t) else np.nan,
                meanR=t["r"].mean() if len(t) else np.nan,
                hold=t["held"].median() if len(t) else np.nan,
                eq=eq)          # equity path, for per-year / correlation work (additive only)


def row(tag: str, m: dict) -> str:
    return (f"CAGR {m['cagr']*100:>7.2f}%  Sh {m['sharpe']:>6.3f}  DD {m['dd']*100:>6.1f}%  "
            f"n {m['trades']:>5,}  win {m['win']*100:>4.1f}%  R {m['meanR']:>+5.2f}  hold {m['hold']:>4.0f}d")


def main() -> int:
    print("=== SWING + POSITIVE strategy survey — 9 strategies + random control ===")
    print(f"    same universe (corrected PIT Nifty-500) | same book ({MAXPOS} slots, {RISK:.0%} risk, "
          f"{NOTIONAL_CAP:.0%} cap) | same costs ({COST:.2%}/leg) | same ranker (RS55)")
    print(f"    TRAIN {TRAIN[0]}..{TRAIN[1]}   HOLDOUT {HOLDOUT[0]}..{HOLDOUT[1]}\n")
    P = build_base(corrected_universe(), load_membership())
    print(f"  names {len(P)}\n")
    out = []
    for tag, fn, prov in SPECS:
        tr, ho = run(P, fn, start=TRAIN[0], end=TRAIN[1]), run(P, fn, start=HOLDOUT[0], end=HOLDOUT[1])
        out.append((tag, prov, tr, ho))
        print(f"  {tag}   [{prov}]")
        print(f"      TRAIN    {row(tag, tr)}")
        print(f"      HOLDOUT  {row(tag, ho)}")
    print("\n=== RANKED BY TRAIN CAGR (selection happens here) ===")
    for tag, prov, tr, ho in sorted(out, key=lambda x: -x[2]["cagr"]):
        print(f"  {tr['cagr']*100:>7.2f}%  train   ->  {ho['cagr']*100:>7.2f}%  holdout   {tag}")
    print("\n  reference: baseline_v1 CAGR 15.46% / Sharpe 0.667 / MaxDD -46.26%")
    print("  standing counts: screens 17 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
