"""Export EVERY trade of the LIVE book with cash constraints OFF — for owner entry/exit chart review.

Owner request 2026-07-16: "rerun the full backtest and dont consider cash. i just want to see trades.
i want to check for the perfect entry and exit."

`uncapped=True` fills EVERY signal (the engine's ledger mode), so the list is the strategy's pure
signal->entry->exit behaviour, unclouded by which fills the Rs10L book could afford. This is a REVIEW
artifact, not a performance claim: the uncapped book is not tradable (it has no capital limit) and its
aggregate stats are NOT the live book's.

Config = the live cron exactly: A-only (top-5 CRS/week) + LIVE_DISCIPLINE + P2 exit.

    python scripts/export_all_trades.py            # live config (A-only + discipline)
    python scripts/export_all_trades.py all        # all-grades variant (research reference)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.data.ohlcv import load_demerger_reference
from run_bhanushali_cron import LIVE_DISCIPLINE, P2_EXIT
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from export_tv_review2 import find_splits, weekly_meta

OUT = ROOT / "research" / "substrate" / "tv_review"; OUT.mkdir(parents=True, exist_ok=True)
COLS = ["tv_symbol", "grade", "signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct",
        "entry_date", "entry", "stop", "risk_pct", "ext_vs_sma", "crs_rank",
        "exit_date", "exit_px", "pct_move", "R", "mfe_pct", "mfe_R", "mae_pct", "reason",
        "weeks_held", "split_flag"]


def main():
    all_grades = len(sys.argv) > 1 and sys.argv[1] == "all"
    ohlcv = corrected_universe(); mem = load_membership(); dem = load_demerger_reference()
    splits = find_splits(ohlcv, dem)
    P = R94.prep_weekly_rank(ohlcv)
    a_set = R94.grade_a_entries(P)

    # R1 — the baseline assertion must hold before any export built on this engine is trusted.
    base = R94.backtest(P, mem, start="2017-01-01", eq0=EQ0, a_grade=a_set, **P2_EXIT)
    assert abs(base["sharpe"] - 1.004) < 0.005 and base["trades"] == 171, "R1 A-only baseline FAILED"

    led: list = []
    m = R94.backtest(P, mem, ledger=led, start="2017-01-01", eq0=EQ0, uncapped=True,
                     a_grade=None if all_grades else a_set, **LIVE_DISCIPLINE, **P2_EXIT)
    print(f"config  : {'ALL-GRADES' if all_grades else 'A-only (LIVE)'} + LIVE_DISCIPLINE + P2 exit, "
          f"cash OFF (uncapped)")
    print(f"trades  : {len(led)}   (the Rs10L book only affords ~184 of these — cash is off here)\n")

    t = pd.DataFrame(led)
    t["entry_date"] = pd.to_datetime(t.entry_date); t["exit_date"] = pd.to_datetime(t.exit_date)
    t = t.rename(columns={"tkr": "ticker", "stop0": "stop", "rank": "crs_rank"})

    meta = weekly_meta(P)
    for k in ("signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct", "sma"):
        t[k] = [meta.get((r.ticker, r.entry_date), {}).get(k) for r in t.itertuples()]
    t = t.dropna(subset=["signal_week"])

    di = {tk: pd.Timestamp(d).normalize() for tk in () for d in ()}
    ent_idx = {}
    for tk, s in P.items():
        ent_idx[tk] = {pd.Timestamp(d).normalize(): i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))}
    a_dates = set()
    for tk, i in a_set:
        a_dates.add((tk, pd.Timestamp(P[tk]["dates"][i]).normalize()))
    t["grade"] = ["A" if (r.ticker, r.entry_date.normalize()) in a_dates else "B" for r in t.itertuples()]

    t["tv_symbol"] = "NSE:" + t.ticker
    t["risk_pct"] = (t.entry - t.stop) / t.entry * 100
    t["ext_vs_sma"] = (t.entry / t.sma - 1) * 100
    t["pct_move"] = (t.exit_px / t.entry - 1) * 100
    t["weeks_held"] = ((t.exit_date - t.entry_date).dt.days / 7).round(1)
    # Split flag rather than a drop: this list is for EYES, and a flagged split is information
    # (the CGCL class of data bug the owner caught). Dropping them would hide the bug.
    t["split_flag"] = ["SPLIT?" if any(r.entry_date <= d <= r.exit_date for d in splits.get(r.ticker, []))
                       else "" for r in t.itertuples()]

    mfe, mae = [], []
    for r in t.itertuples():
        w = ohlcv[r.ticker].loc[r.entry_date:r.exit_date]
        mfe.append((w["High"].max() / r.entry - 1) * 100 if len(w) else np.nan)
        mae.append((w["Low"].min() / r.entry - 1) * 100 if len(w) else np.nan)
    t["mfe_pct"], t["mae_pct"] = mfe, mae
    t["mfe_R"] = t.mfe_pct / t.risk_pct                      # how many R the trade REACHED intraweek

    t = t.sort_values("entry_date")
    fn = OUT / ("all_trades_uncapped_allgrades.csv" if all_grades else "all_trades_uncapped.csv")
    t[COLS].round(2).to_csv(fn, index=False)
    print(f"wrote {fn}  ({len(t)} rows)\n")

    R = t.R.values
    print("=== the uncapped signal book (NOT a tradable book — no capital limit) ===")
    print(f"  trades {len(t)}  win {(R>0).mean()*100:.0f}%  meanR {R.mean():+.2f}  medR {np.median(R):+.2f}")
    print(f"  median risk% {t.risk_pct.median():.1f}   median ext vs SMA {t.ext_vs_sma.median():+.1f}%")
    print(f"  splits flagged: {(t.split_flag!='').sum()}")
    print("\n  exit mix:")
    for k, v in t.reason.value_counts().items():
        g = t[t.reason == k]
        print(f"    {k:14s} n={v:4d}  meanR {g.R.mean():+5.2f}  mean MFE {g.mfe_R.mean():5.2f}R")
    print("\n=== THE EXIT QUESTION — how much of what we reached did we keep? ===")
    w = t[t.R > 0]; l = t[t.R <= 0]
    print(f"  winners n={len(w):4d}  reached {w.mfe_R.mean():5.2f}R on average, kept {w.R.mean():5.2f}R "
          f"({w.R.mean()/w.mfe_R.mean()*100:.0f}% of the excursion)")
    print(f"  losers  n={len(l):4d}  reached {l.mfe_R.mean():5.2f}R on average, kept {l.R.mean():5.2f}R")
    hit2 = t[t.mfe_R >= 2.0]
    print(f"  trades that REACHED >=2R intraweek: {len(hit2)} ({len(hit2)/len(t)*100:.0f}%) — "
          f"of those, {(hit2.R < 0).sum()} ({(hit2.R<0).mean()*100:.0f}%) still closed NEGATIVE")


if __name__ == "__main__":
    main()
