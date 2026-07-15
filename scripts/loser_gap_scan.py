"""Go through EVERY losing trade in the frozen 0094 book and tag the one dominant gap that caused it.
Pinned data, determinism-gated. Output: research/losers_analysis/loser_gaps.csv + a gap-frequency summary.
Run on /loop to keep deepening. See research/losers_analysis/PROBLEMS.md for the gap definitions."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership
OUT = ROOT / "research" / "losers_analysis"; OUT.mkdir(parents=True, exist_ok=True)

ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}


def wsma_at(t, day_idx):
    s = P[t]; idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
    weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    wc = np.array([s["c"][d[-1]] for d in weeks]); ws = pd.Series(wc).rolling(44).mean().to_numpy()
    d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
    return ws[d2w[day_idx]] if day_idx in d2w else np.nan


led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
ok = abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255
print(f"determinism: Sharpe {m['sharpe']:.3f} / {m['trades']} tr  [{'PASS' if ok else 'FAIL — STOP'}]")
if not ok:
    raise SystemExit(1)
L = pd.DataFrame(led)
L["ed"] = pd.to_datetime(L["entry_date"]); L["xd"] = pd.to_datetime(L["exit_date"])
losers = L[L["R"] <= 0].copy()

rows = []
# crash-cohort: >=3 stop-exits sharing the same exit ISO-week
xk = losers[losers.reason.str.startswith("stop")]["xd"].dt.strftime("%G-%V")
crash_weeks = set(xk.value_counts()[lambda s: s >= 3].index)
for _, r in losers.iterrows():
    t = r["tkr"]; j0 = didx[t].get(r["ed"])
    sm = wsma_at(t, j0) if j0 is not None else np.nan
    ext = (r["entry"] / sm - 1) * 100 if sm and sm > 0 else np.nan
    risk = (r["entry"] - r["stop0"]) / r["entry"] * 100
    pos = 200.0 / risk if risk else np.nan               # % of book at fixed 2% risk
    gap_through = r["reason"].startswith("stop") and r["exit_px"] < r["stop0"]
    fast = r["reason"].startswith("stop") and r["held_weeks"] <= 2
    time_bleed = r["reason"] == "time"
    giveback = pd.notna(r.get("half_date"))
    crash = r["xd"].strftime("%G-%V") in crash_weeks
    # dominant gap (root-cause priority)
    if pd.notna(ext) and ext > 12:      gap = "late/extended-entry"
    elif risk > 15:                      gap = "wide-stop"
    elif gap_through:                    gap = "gap-through-stop"
    elif giveback:                       gap = "exit-giveback"
    elif fast:                           gap = "fast-reversal"
    elif crash:                          gap = "crash-cohort"
    elif time_bleed:                     gap = "time-cap-bleed"
    else:                                gap = "other"
    rows.append(dict(ticker=t, bought=r["ed"].strftime("%Y-%m-%d"), buy=round(r["entry"], 1),
                     stop=round(r["stop0"], 1), **{"risk%": round(risk, 1), "ext_vs_SMA%": round(ext, 1) if pd.notna(ext) else np.nan,
                     "pos%": round(pos, 0) if pd.notna(pos) else np.nan},
                     exit=r["xd"].strftime("%Y-%m-%d"), exit_px=round(r["exit_px"], 1), why=r["reason"],
                     held_wk=int(r["held_weeks"]), R=round(r["R"], 2), gap_through=gap_through,
                     giveback=giveback, crash=crash, GAP=gap))
D = pd.DataFrame(rows).sort_values("bought")
D.to_csv(OUT / "loser_gaps.csv", index=False)
print(f"\n{len(D)} losing trades tagged -> {OUT/'loser_gaps.csv'}")
print("\nGAP FREQUENCY (the dominant gap per loser):")
gf = D.groupby("GAP").agg(n=("R", "size"), meanR=("R", "mean"), tot_R=("R", "sum")).sort_values("n", ascending=False)
gf["%"] = (gf.n / len(D) * 100).round(0)
print(gf.round(2).to_string())
print(f"\ntotal R lost: {D.R.sum():.0f} across {len(D)} losers")
