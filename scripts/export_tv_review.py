"""Export trade lists for manual TradingView review — SPLIT-CLEANED and de-biased.

v2 (2026-07-16), after the owner found the CGCL data bug:
  * EXCLUDES trades that span an unadjusted split (see DATA_BUG_unadjusted_splits.md) — the v1 "worst"
    list was topped by CGCL -17.32R, which was a 1:4 stock split, not a loss.
  * WORST is ranked by ACTUAL % LOSS, not R. Ranking by R mechanically selects tiny stop distances
    (R = move / (entry-stop)), so v1's worst list was a stop-geometry artifact (mean risk 3.3%,
    e.g. ICICIBANK -4.47R from a -0.93% move on a 0.10% stop). % loss is what the eye sees on a chart.
  * The "SIDEWAYS" bucket is DROPPED — it does not exist (18 of 1,720, and 13 of those merely unresolved
    at the data cutoff; the P2 exit has no time cap, so trades either stop or trend). Replaced by
    STOPPED_THEN_RECOVERED: the setup was right, the stop was wrong — where an indicator genuinely might help.
  * GOOD_RANDOM unchanged: a random sample of R>=2 winners (not cherry-picked tops).

    python scripts/export_tv_review.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.ohlcv import load_demerger_reference
from run_bhanushali_path1 import corrected_universe

OUT = ROOT / "research" / "substrate" / "tv_review"; OUT.mkdir(parents=True, exist_ok=True)
SEED, N = 20260716, 20
COLS = ["bucket", "tv_symbol", "signal_week", "entry_date", "entry", "stop", "risk_pct", "ext_vs_sma",
        "exit_date", "exit_px", "pct_move", "R", "mfe_pct", "mae_pct", "reason", "split"]


def find_splits(ohlcv, dem):
    """(ticker -> [dates]) of <-45% single-session moves that neither revert nor are known demergers."""
    out = {}
    for t, df in ohlcv.items():
        c = df["Close"]; r = c.pct_change()
        for d, v in r[r < -0.45].items():
            fwd = c.loc[d:].iloc[:6]
            if (fwd.max() / c.loc[d] - 1) > 0.8:            # reverts => bad tick, not a split
                continue
            if t in dem and str(pd.Timestamp(d).date()) in dem.get(t, set()):
                continue                                     # genuine demerger — legitimately left
            out.setdefault(t, []).append(pd.Timestamp(d))
    return out


def main():
    ohlcv = corrected_universe(); dem = load_demerger_reference()
    splits = find_splits(ohlcv, dem)
    P = R94.prep_weekly_rank(ohlcv)

    df = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    t = df[df.setup == "touch44"].copy()
    t["entry_date"] = pd.to_datetime(t.entry_date); t["exit_date"] = pd.to_datetime(t.exit_date)

    # --- drop split-corrupted trades ---
    def hit(r):
        return any(r.entry_date <= d <= r.exit_date for d in splits.get(r.ticker, []))
    n0 = len(t); t = t[~t.apply(hit, axis=1)].copy()
    print(f"touch44: {n0} -> {len(t)} after dropping {n0-len(t)} split-corrupted trades")

    # --- signal week (the decision bar) ---
    sig = {}
    for tk, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for e0, w in s["entry_win"].items():
            if e0 < 1:
                continue
            for d in w[0]:
                sig[(tk, dates[d])] = dates[e0 - 1]
    t["signal_week"] = [sig.get((r.ticker, r.entry_date)) for r in t.itertuples()]
    t = t.dropna(subset=["signal_week"])
    t["tv_symbol"] = "NSE:" + t.ticker
    t["pct_move"] = (t.exit_px / t.entry - 1) * 100          # what the eye sees

    # --- STOPPED_THEN_RECOVERED: stopped out, but price exceeded the entry within 12wk after the exit ---
    rec = []
    for r in t[t.R < 0].itertuples():
        c = ohlcv[r.ticker]["Close"]
        fwd = c.loc[r.exit_date:].iloc[:60]                  # ~12 weeks of sessions
        if len(fwd) and fwd.max() > r.entry:
            rec.append(r.Index)
    t["recovered"] = t.index.isin(rec)

    worst = t.nsmallest(N, "pct_move").assign(bucket="WORST_BY_PCT")
    rpool = t[t.recovered]
    stoprec = rpool.sample(min(N, len(rpool)), random_state=SEED).assign(bucket="STOPPED_THEN_RECOVERED")
    gpool = t[t.R >= 2]
    good = gpool.sample(min(N, len(gpool)), random_state=SEED).assign(bucket="GOOD_RANDOM")
    print(f"pools -> stopped-then-recovered: {len(rpool)}   good (R>=2): {len(gpool)}\n")

    allx = pd.concat([worst, stoprec, good])
    for c in ("signal_week", "entry_date", "exit_date"):
        allx[c] = pd.to_datetime(allx[c]).dt.strftime("%Y-%m-%d")
    allx = allx[COLS].round(2)
    allx.to_csv(OUT / "tv_review_60.csv", index=False)
    for b, g in allx.groupby("bucket", sort=False):
        g.to_csv(OUT / f"{b.lower()}.csv", index=False)
        print(f"=== {b}  (n={len(g)}) ===")
        print(g.drop(columns=["bucket"]).to_string(index=False)); print()
    print("=== bucket profiles ===")
    for b, g in allx.groupby("bucket", sort=False):
        print(f"  {b:24s} mean %move={g.pct_move.mean():+6.1f}%  meanR={g.R.mean():+5.2f}  "
              f"mean risk%={g.risk_pct.mean():4.1f}  mean ext={g.ext_vs_sma.mean():5.1f}%")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
