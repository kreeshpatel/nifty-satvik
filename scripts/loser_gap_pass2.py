"""Pass 2 of the losing-trade gap hunt: 84% of losers entered >12% above the SMA — but so do the winners.
So 'extended' alone is not the gap. This pass finds the FINER separator between extended winners and
extended losers (the path/MAE, the stop width, the exit). Pinned, determinism-gated."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership
OUT = ROOT / "research" / "losers_analysis"

ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}


def wsma_at(t, j):
    s = P[t]; iso = pd.DatetimeIndex(s["dates"]).isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy())); weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    wc = np.array([s["c"][d[-1]] for d in weeks]); ws = pd.Series(wc).rolling(44).mean().to_numpy()
    d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
    return ws[d2w[j]] if j in d2w else np.nan


led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
assert abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255, "determinism FAIL"
print(f"determinism PASS ({m['sharpe']:.3f}/{m['trades']})\n")
L = pd.DataFrame(led); L["ed"] = pd.to_datetime(L["entry_date"]); L["xd"] = pd.to_datetime(L["exit_date"])
rows = []
for _, r in L.iterrows():
    t = r["tkr"]; j0 = didx[t].get(r["ed"]); j1 = didx[t].get(r["xd"])
    sm = wsma_at(t, j0) if j0 is not None else np.nan
    ext = (r["entry"] / sm - 1) * 100 if sm and sm > 0 else np.nan
    lows = P[t]["l"][j0:j1 + 1] if (j0 is not None and j1 is not None) else np.array([])
    mae = (lows.min() / r["entry"] - 1) * 100 if len(lows) else 0.0
    # MAE in the first 2 weeks (does it work immediately?)
    e2 = P[t]["l"][j0:min(j0 + 11, j1 + 1)] if (j0 is not None and j1 is not None) else np.array([])
    mae2 = (e2.min() / r["entry"] - 1) * 100 if len(e2) else 0.0
    rows.append(dict(tkr=t, R=r["R"], ext=ext, risk=(r["entry"] - r["stop0"]) / r["entry"] * 100,
                     mae=mae, mae2w=mae2, held=r["held_weeks"], giveback=pd.notna(r.get("half_date")),
                     reason=r["reason"], win=r["R"] > 0))
D = pd.DataFrame(rows).dropna(subset=["ext"])
X = D[D.ext > 12]                      # the extended population (where 84% of losers live)
print(f"EXTENDED entries (>12% above SMA): {len(X)} trades | {(X.win).mean()*100:.0f}% win, {(X.R>=2).mean()*100:.0f}% runners")
print("\nWinner vs loser WITHIN the extended population — what separates them:")
print(f"  {'feature':16}{'ext win':>10}{'ext loser':>10}")
for f, lbl in [("ext", "ext% above SMA"), ("risk", "stop width%"), ("mae", "worst drawdown (MAE)%"),
               ("mae2w", "MAE first 2 weeks%"), ("held", "weeks held")]:
    w = X[X.win][f].median(); l = X[~X.win][f].median()
    print(f"  {lbl:22}{w:>10.1f}{l:>10.1f}")
print(f"  {'giveback rate':22}{X[X.win].giveback.mean()*100:>9.0f}%{X[~X.win].giveback.mean()*100:>9.0f}%")

# the early-MAE tell: does a deep first-2-week drawdown flag the loser?
print("\nEARLY-MAE separator (first 2 weeks) among extended entries:")
for thr in (-6, -8, -10, -12):
    deep = X[X.mae2w <= thr]
    print(f"  MAE(2wk) <= {thr}%:  n={len(deep):>3} | win {deep.win.mean()*100:3.0f}% | runner {int((deep.R>=2).mean()*100)}% "
          f"-> a deep early dip is 'not a runner' with {(1-deep.win.mean())*100:.0f}% precision")
D.to_csv(OUT / "pass2_extended_winners_vs_losers.csv", index=False)
print(f"\nsaved -> {OUT/'pass2_extended_winners_vs_losers.csv'}")
