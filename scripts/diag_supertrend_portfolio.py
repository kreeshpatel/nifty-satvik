"""AmiBroker-style PORTFOLIO backtest of the daily Supertrend(10,3) + RS(14) + RSI(14)>60 system,
and a waterfall decomposing the gap between a retail-configured backtest and an honest one.

Why this exists: finding 0132 priced the strategy per-trade (meanR). The owner has seen a published
backtest of the same rules reporting ~20% returns. A per-trade R statistic cannot refute a CAGR
claim, so this reproduces the disputed object directly — a compounding equity curve with a slot cap,
a PositionScore ranker and position sizing, which is exactly what AmiBroker's portfolio backtester
computes.

The waterfall runs the SAME rules and changes one setup knob at a time, retail -> honest:

  1  RETAIL      survivor-only universe (today's index, no delisted), 0.03%/leg, 2020-2023
  2  + full period                                    -> 2019-2026
  3  + honest costs                                   -> 0.25%/leg (brokerage+STT+impact)
  4  HONEST      + survivorship-corrected PIT universe (the repo's corrected universe)

Each step is a KNOWN accounting difference, not a parameter search: none of the four is chosen
because it scored well, and the ordering is fixed before running. The purpose is attribution — to
say which knob the published number lives in — not to select a configuration.

MEASUREMENT class. Finding 0132 already reached NO TRIAL; this reproduces a disputed external claim
and changes no verdict, so `n_trials` stays 138. Promoting this strategy would require its own
pre-registered trial.

    python scripts/diag_supertrend_portfolio.py
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
from diag_supertrend_system import RS_LEN, RSI_THR, supertrend, wilder_rsi  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

EQ0 = 1_000_000.0
RISK = 0.02                 # owner: live-swing sizing
NOTIONAL_CAP = 0.10         # owner: max 10% of equity per name
MAXPOS = 10
MIN_BARS = 300


def build_panel(ohlcv: dict, membership) -> dict:
    """membership=None => survivor-only/naive (no PIT mask), the retail setup."""
    n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < MIN_BARS:
            continue
        if membership is not None and not membership.get(tkr.upper()):
            continue
        idx = pd.DatetimeIndex(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        line, up = supertrend(h, l, c)
        rsi = wilder_rsi(c)
        ia = n50.reindex(idx, method="ffill").to_numpy(float)
        rs = np.where(ia > 0, c / ia, np.nan)
        rs_sma = pd.Series(rs).rolling(RS_LEN).mean().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            rs_dist = rs / rs_sma - 1.0
        rs_ok = np.nan_to_num(rs_dist, nan=-9.0) > 0.0
        rsi_ok = np.nan_to_num(rsi, nan=0.0) > RSI_THR
        ok = np.isfinite(line) & np.isfinite(rsi) & np.isfinite(rs_sma)
        if membership is None:
            mem = np.ones(len(idx), dtype=bool)
        else:
            mem = np.zeros(len(idx), dtype=bool)
            for d_from, d_to in membership[tkr.upper()]:
                mem |= (idx >= pd.Timestamp(d_from)) & (idx <= pd.Timestamp(d_to))
        triple = up & rsi_ok & rs_ok & ok & mem
        nfalse = (~up).astype(int) + (~rs_ok).astype(int) + (~rsi_ok).astype(int)
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, line=line, rs_dist=rs_dist,
                      triple=triple, exit2=(nfalse >= 2) & ok,
                      pos={d: i for i, d in enumerate(idx)})
    return P


def run_portfolio(P: dict, *, start: str, end: str, cost: float, maxpos: int = MAXPOS,
                  notional_cap: float = NOTIONAL_CAP, risk: float = RISK,
                  intraday_stop: bool = True, rank: bool = True) -> dict:
    """AmiBroker-equivalent: signal on close -> buy next open, PositionScore = RS distance,
    MaxOpenPositions = maxpos, risk-based size capped at notional_cap, full compounding."""
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    all_dates = sorted(set().union(*[set(s["dates"]) for s in P.values()]))
    all_dates = [d for d in all_dates if lo <= d <= hi]

    # precompute fresh-triple candidates per date (signal day; execution is the NEXT date)
    cands: dict[pd.Timestamp, list] = {}
    for tkr, s in P.items():
        t = s["triple"]
        fresh = t & ~np.concatenate([[False], t[:-1]])
        for i in np.flatnonzero(fresh):
            if i + 1 >= len(t):
                continue
            d = s["dates"][i]
            if lo <= d <= hi and np.isfinite(s["rs_dist"][i]):
                cands.setdefault(d, []).append((float(s["rs_dist"][i]), tkr, int(i)))

    cash = equity = EQ0
    open_pos: dict[str, dict] = {}
    eqc, trades = [], []
    prev_date = None
    for d in all_dates:
        # --- exits: stop intraday, else the 2-of-3 close rule executed at this open
        for tkr in list(open_pos):
            p, s = open_pos[tkr], P[tkr]
            i = s["pos"].get(d)
            if i is None:
                continue
            px = reason = None
            if p["pending_exit"]:
                px, reason = s["o"][i], "rule"
            elif intraday_stop and np.isfinite(s["line"][i - 1]) and s["l"][i] <= s["line"][i - 1]:
                px, reason = min(s["o"][i], s["line"][i - 1]), "stop"
            if px is not None:
                cash += p["shares"] * px * (1 - cost)
                trades.append(dict(ticker=tkr, entry_date=p["date"], exit_date=d, reason=reason,
                                   r=(px - p["entry"]) / p["r_unit"],
                                   ret=(px * (1 - cost) - p["entry"] * (1 + cost)) / p["entry"]))
                del open_pos[tkr]
                continue
            p["pending_exit"] = bool(s["exit2"][i])

        # --- entries: candidates that signalled on the PREVIOUS trading day, best RS first
        pending = cands.get(prev_date, []) if prev_date is not None else []
        if pending and len(open_pos) < maxpos:
            pending = sorted(pending, reverse=True) if rank else list(pending)
            for _score, tkr, i in pending:
                if len(open_pos) >= maxpos or tkr in open_pos:
                    continue
                s = P[tkr]
                j = s["pos"].get(d)
                if j is None or j != i + 1:
                    continue
                entry, stop0 = s["o"][j], s["line"][i]
                if not np.isfinite(entry) or not np.isfinite(stop0) or entry <= stop0:
                    continue
                shares = min(equity * risk / (entry - stop0), equity * notional_cap / entry)
                notion = shares * entry * (1 + cost)
                if shares <= 0 or notion > cash:
                    continue
                cash -= notion
                open_pos[tkr] = dict(entry=entry, shares=shares, r_unit=entry - stop0,
                                     date=d, pending_exit=bool(s["exit2"][j]))

        mtm = 0.0
        for tkr, p in open_pos.items():
            s = P[tkr]
            k = s["pos"].get(d)
            mtm += p["shares"] * (s["c"][k] if k is not None else p["entry"])
        equity = cash + mtm
        eqc.append((d, equity, len(open_pos)))
        prev_date = d

    eq = pd.Series({d: e for d, e, _ in eqc}).sort_index()
    npos = pd.Series({d: n for d, _, n in eqc}).sort_index()
    ret = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    t = pd.DataFrame(trades)
    return dict(cagr=(eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan,
                sharpe=ret.mean() / ret.std() * np.sqrt(252) if ret.std() else np.nan,
                dd=(eq / eq.cummax() - 1).min(), mult=eq.iloc[-1] / EQ0, years=yrs,
                trades=len(t), win=(t["ret"] > 0).mean() if len(t) else np.nan,
                meanR=t["r"].mean() if len(t) else np.nan,
                avg_pos=npos.mean(), eq=eq)


def line(tag: str, m: dict) -> None:
    print(f"  {tag:<52} CAGR {m['cagr']*100:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
          f"MaxDD {m['dd']*100:>7.1f}%  {m['mult']:>5.2f}x  trades {m['trades']:>5,}  "
          f"win {m['win']*100:>4.1f}%  avgpos {m['avg_pos']:>4.1f}")


def main() -> int:
    print("=== AmiBroker-style portfolio backtest: Supertrend(10,3) + RS(14)>0 + RSI(14)>60 ===")
    print(f"    signal on close -> buy next open | PositionScore = RS distance | MaxOpenPositions {MAXPOS}")
    print(f"    size = min({RISK:.0%} risk / stop-distance, {NOTIONAL_CAP:.0%} notional) | full compounding\n")

    print("  building panels...")
    survivor = build_panel(load_ohlcv_cache(OHLCV_CACHE), None)
    honest = build_panel(corrected_universe(), load_membership())
    print(f"    survivor-only (pinned cache, no PIT mask): {len(survivor)} names")
    print(f"    corrected + PIT membership:                {len(honest)} names\n")

    print("=== THE WATERFALL — one accounting knob at a time, retail -> honest ===")
    steps = [
        ("1  RETAIL   survivor universe, 0.03%/leg, 2020-2023", survivor, "2020-01-01", "2023-12-31", 0.0003),
        ("2  + full period 2019-2026", survivor, "2019-01-01", "2026-06-30", 0.0003),
        ("3  + honest costs 0.25%/leg", survivor, "2019-01-01", "2026-06-30", 0.0025),
        ("4  HONEST  + survivorship-corrected PIT universe", honest, "2019-01-01", "2026-06-30", 0.0025),
    ]
    res = []
    for tag, panel, s, e, c in steps:
        m = run_portfolio(panel, start=s, end=e, cost=c)
        res.append((tag, m))
        line(tag, m)

    print("\n=== ATTRIBUTION (CAGR handed back at each step) ===")
    for (t0, m0), (t1, m1) in zip(res, res[1:]):
        print(f"  {t1.split('  ')[0]:<3} {m0['cagr']*100:>7.2f}% -> {m1['cagr']*100:>7.2f}%   "
              f"delta {(m1['cagr']-m0['cagr'])*100:>+7.2f}pp   ({t1.strip()})")

    print("\n=== CONTROLS on the honest panel (is the strategy doing anything?) ===")
    hp = dict(start="2019-01-01", end="2026-06-30", cost=0.0025)
    line("honest, RS ranker REPLACED by arbitrary order", run_portfolio(honest, **hp, rank=False))
    line("honest, ZERO costs (upper bound, unreachable)",
         run_portfolio(honest, start="2019-01-01", end="2026-06-30", cost=0.0))
    line("honest, 2020-2023 only (the retail window)",
         run_portfolio(honest, start="2020-01-01", end="2023-12-31", cost=0.0025))

    print("\n=== PER-YEAR equity return, honest configuration ===")
    eq = res[-1][1]["eq"]
    yr = eq.resample("YE").last()
    yr = pd.concat([pd.Series([eq.iloc[0]], index=[eq.index[0]]), yr])
    for a, b in zip(yr.index[:-1], yr.index[1:]):
        print(f"    {b.year}  {(yr[b]/yr[a]-1)*100:>+7.2f}%")

    print(f"\n  baseline_v1 reference: CAGR 15.46% / Sharpe 0.667 / MaxDD -46.26%")
    print(f"  standing counts: screens 17 · sealed opens 1 · n_trials 138 (unchanged — measurement)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
