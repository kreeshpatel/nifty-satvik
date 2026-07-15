"""Phase-2 EXIT packets: for each 0094 trade, the weekly HOLD path (entry→exit) + 8 weeks AFTER exit, with the
2R target, the 20-SMA trail level, and running MFE-in-R marked — so an AI agent can judge whether each exit was
EARLY (kept running after), LATE (gave back a peak), or RIGHT (rolled over). Determinism-gated. Output:
research/losers_analysis/exit_packets/*.json"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from run_bhanushali_weekly_rank import TRAIL_PCT
OUT = ROOT / "research" / "losers_analysis" / "exit_packets"; OUT.mkdir(parents=True, exist_ok=True)
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership

ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}


def weeks_of(t):
    s = P[t]; idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy())); weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    o, h, l, c = s["o"], s["h"], s["l"], s["c"]
    wo = np.array([o[d[0]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
    wl = np.array([l[d].min() for d in weeks]); wc = np.array([c[d[-1]] for d in weeks])
    ws = pd.Series(wc).rolling(44).mean().to_numpy(); w20 = pd.Series(wc).rolling(20).mean().to_numpy()
    wd = [pd.Timestamp(s["dates"][d[-1]]) for d in weeks]
    d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
    return dict(wo=wo, wh=wh, wl=wl, wc=wc, ws=ws, w20=w20, wd=wd, d2w=d2w)


led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
assert abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255, "determinism FAIL"
print(f"determinism PASS ({m['sharpe']:.3f}/{m['trades']}) — building exit packets")
WK = {}; built = 0
for r in led:
    t = r["tkr"]
    if t not in WK:
        WK[t] = weeks_of(t)
    w = WK[t]; en = r["entry"]; st = r["stop0"]; risk = en - st; tp2 = en + 2 * risk
    we = w["d2w"][didx[t][pd.Timestamp(r["entry_date"])]]      # entry week
    wx = w["d2w"][didx[t][pd.Timestamp(r["exit_date"])]]       # exit week
    path = []; peak = en
    for k in range(we, min(wx + 9, len(w["wc"]))):             # hold + 8 weeks after exit
        peak = max(peak, w["wh"][k])
        path.append(dict(
            week=w["wd"][k].strftime("%Y-%m-%d"), C=round(w["wc"][k], 1), H=round(w["wh"][k], 1),
            L=round(w["wl"][k], 1),
            R_close=round((w["wc"][k] - en) / risk, 2) if risk > 0 else None,     # close in R
            R_high=round((w["wh"][k] - en) / risk, 2) if risk > 0 else None,      # intraweek high in R
            mfe_so_far_R=round((peak - en) / risk, 2) if risk > 0 else None,
            trail_20sma=round(w["w20"][k] * (1 - TRAIL_PCT), 1) if w["w20"][k] == w["w20"][k] else None,
            sma44=round(w["ws"][k], 1) if w["ws"][k] == w["ws"][k] else None,
            is_exit_week=(k == wx)))
    pk = dict(ticker=t, won=bool(r["R"] > 0), R=round(r["R"], 2), reason=r["reason"],
              entry_date=str(r["entry_date"])[:10], exit_date=str(r["exit_date"])[:10],
              entry=round(en, 1), stop=round(st, 1), tp2_target=round(tp2, 1), risk_pct=round(risk / en * 100, 1),
              held_weeks=int(r["held_weeks"]), half_booked=(r.get("half_date") is not None),
              mfe_R=round((max(w["wh"][we:wx + 1]) - en) / risk, 2) if risk > 0 else None,
              hold_path=path)
    fn = f"{r['reason']}_{t}_{pk['entry_date']}.json"
    (OUT / fn).write_text(json.dumps(pk, indent=1)); built += 1
    r["_mfeR"] = pk["mfe_R"]; r["_fn"] = fn
print(f"built {built} exit packets -> {OUT}")
# manifest of the giveback cohort (peaked >=1.8R but exited on time/trail) for the agents
gb = [r["_fn"] for r in led if r["reason"] in ("time", "trail") and (r.get("_mfeR") or 0) >= 1.8]
(OUT / "_giveback_cohort.txt").write_text("\n".join(gb))
print(f"giveback cohort (time/trail exit, MFE>=1.8R): {len(gb)} -> _giveback_cohort.txt")
