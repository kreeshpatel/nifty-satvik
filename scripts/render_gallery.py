"""Render a VALIDATION GALLERY for the tight box detector: box-driven WINNERS + LOSERS + known MISSES, each as
a weekly chart with the box overlay, so we can see systematically where the detector is right/false/missed.
Output: PNGs in scratchpad + a printed manifest. Usage: python scripts/render_gallery.py"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
import render_chart as RC
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership

BL, BT = 8, 0.15
ohlcv = corrected_universe(); mem = load_membership()
# base (touch-only) trades vs box-augmented trades -> the NEW ones are box-driven
ledb = []; R94.backtest(R94.prep_weekly_rank(ohlcv), mem, ledger=ledb, start="2017-01-01")
base_keys = set((r["tkr"], str(r["entry_date"])[:10]) for r in ledb)
led = []; R94.backtest(R94.prep_weekly_rank(ohlcv, box_breakout=True, box_len=BL, box_tight=BT),
                       mem, ledger=led, start="2017-01-01")
box_new = [r for r in led if (r["tkr"], str(r["entry_date"])[:10]) not in base_keys]
box_new.sort(key=lambda r: r["R"])
losers = box_new[:6]; winners = box_new[-6:]
sample = winners[::-1] + losers
misses = [("MAZDOCK", "2022-08-16"), ("RRKABEL", "2026-05-04"), ("BAJFINANCE", "2018-05-21")]

manifest = []
for r in sample:
    t = r["tkr"]; ed = pd.Timestamp(str(r["entry_date"])[:10])
    d0 = (ed - pd.Timedelta(weeks=70)).strftime("%Y-%m"); d1 = (ed + pd.Timedelta(weeks=35)).strftime("%Y-%m")
    sfx = ed.strftime("%y%m%d")
    RC.render(t, d0, d1, "box", box_len=BL, box_tight=BT, suffix=sfx)
    tag = "WIN" if r["R"] > 0 else "LOSS"
    manifest.append((f"chart_{t}_box_{sfx}.png", t, str(ed.date()), tag, round(r["R"], 2)))
for t, ed in misses:
    ed = pd.Timestamp(ed); sfx = ed.strftime("%y%m%d")
    d0 = (ed - pd.Timedelta(weeks=70)).strftime("%Y-%m"); d1 = (ed + pd.Timedelta(weeks=25)).strftime("%Y-%m")
    RC.render(t, d0, d1, "box", box_len=BL, box_tight=BT, suffix=sfx)
    manifest.append((f"chart_{t}_box_{sfx}.png", t, str(ed.date()), "MISS?", None))

print(f"\n=== GALLERY MANIFEST (box {BL}wk/{int(BT*100)}%, {len(box_new)} box-new trades total) ===")
for fn, t, ed, tag, R in manifest:
    print(f"  {tag:5s} {t:12s} entry {ed}  R={R}  -> {fn}")
