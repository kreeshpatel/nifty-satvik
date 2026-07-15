"""Unbiased EXIT map: RANDOM-sample 20 winners + 20 losers + 20 stop-outs from the 0094 ledger (seeded),
render each with entry/exit/MFE + post-exit weeks, and split into 6 batch-lists for AI agents to read. No
cherry-picking. Usage: python scripts/render_random_exit_gallery.py"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
import render_chart as RC
import run_bhanushali_weekly_crs as CRS
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership

OUT = RC.OUT
GAL = OUT / "rexit"; GAL.mkdir(parents=True, exist_ok=True)
ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
assert abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255
df = pd.DataFrame(led)
df["is_stop"] = df["reason"].isin(["stop", "stop_half"])
good = df[(df["R"] > 0) & (~df["is_stop"])]
bad = df[(df["R"] <= 0) & (~df["is_stop"])]
stop = df[df["is_stop"]]
rng = np.random.RandomState(20260715)
def pick(sub, n):
    idx = rng.choice(sub.index.to_numpy(), size=min(n, len(sub)), replace=False)
    return df.loc[idx]
sample = pd.concat([pick(good, 20).assign(cat="GOOD"), pick(bad, 20).assign(cat="BAD"),
                    pick(stop, 20).assign(cat="STOP")])
print(f"pool: good={len(good)} bad={len(bad)} stop={len(stop)} -> sampling 20 each ({len(sample)} total)")
manifest = []
for _, r in sample.iterrows():
    tk = r["tkr"]; ed = str(r["entry_date"])[:10]
    fn = RC.render_trade(tk, ed, str(r["exit_date"])[:10], r["entry"], r["stop0"],
                         r["entry"] + 2 * (r["entry"] - r["stop0"]), r["reason"], r["R"],
                         P=P, n50=n50, suffix="rx")
    manifest.append((r["cat"], tk, ed, r["reason"], round(float(r["R"]), 2), Path(fn).name))
# split into 6 batch files (10 each), each stratified across cats
paths = [f"{c}|{t}|{d}|{rs}|{R}|{fn}" for c, t, d, rs, R, fn in manifest]
rng.shuffle(paths)
for b in range(6):
    (GAL / f"batch_{b}.txt").write_text("\n".join(paths[b::6]))
print("=== RANDOM EXIT MANIFEST (cat | ticker | entry | reason | R | file) ===")
for c, t, d, rs, R, fn in manifest:
    print(f"  {c:4s} {t:12s} {d} {rs:9s} R={R:+.2f}  {fn}")
print(f"\nimages in {GAL}  |  6 agent batch lists: batch_0..5.txt")
