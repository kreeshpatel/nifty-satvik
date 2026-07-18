"""Render an EXIT-analysis gallery: real trades with ENTRY / actual EXIT / MFE peak marked + weeks AFTER exit,
so we can SEE where the ideal exit was. Covers the 4 exit archetypes: cap-severed runners, givebacks, clean
winners, stop-outs. Output: exit_*.png in scratchpad + a manifest. Usage: python scripts/render_exit_gallery.py"""
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

ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
assert abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255
# pick a diverse, informative sample by name (the AI forensic flagged these archetypes)
want = [
    ("MAZDOCK", "cap-severed monster"), ("ALKYLAMINE", "cap-severed monster"), ("KALYANKJIL", "cap-severed"),
    ("SWANENERGY", "cap-severed"), ("DIVISLAB", "cap-severed"), ("GUJGASLTD", "cap-severed fresh-breakout"),
    ("TRIVENI", "giveback→loss"), ("SAIL", "giveback"), ("YESBANK", "giveback 6.3R→1.4R"),
    ("IOB", "giveback trail"), ("CENTURYPLY", "giveback"), ("HINDPETRO", "half-book drag"),
    ("QUESS", "clean big winner"), ("THYROCARE", "clean winner"),
    ("JSL", "stop gap"), ("AXISBANK", "stop"),
]
manifest = []
for tk, tag in want:
    trs = [r for r in led if r["tkr"] == tk]
    if not trs:
        continue
    r = max(trs, key=lambda z: abs(z["R"]))          # the most notable trade for that name
    fn = RC.render_trade(tk, str(r["entry_date"])[:10], str(r["exit_date"])[:10], r["entry"], r["stop0"],
                         r["entry"] + 2 * (r["entry"] - r["stop0"]), r["reason"], r["R"], P=P, n50=n50)
    manifest.append((Path(fn).name, tk, tag, r["reason"], round(r["R"], 2)))
print("=== EXIT GALLERY MANIFEST ===")
for fn, tk, tag, reason, R in manifest:
    print(f"  {tk:12s} {reason:6s} R={R:+.2f}  [{tag}]  -> {fn}")
