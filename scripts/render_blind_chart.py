"""0123 — BLIND, ENTRY-TRUNCATED weekly chart renderer for the vision-grader screen.

Diagnostics-only (lives outside nq/**). Renders ONE trade's weekly chart cropped at the
signal-week decision point (last weekly close strictly before entry_date) with NO future bar,
NO ticker, NO dates, NO title, NO axis tick labels, NO outcome hint. 44-line is the SMA
(reuses render_chart.weekly, which is rolling(44).mean). Filenames are opaque hashes.

Two crop lengths via `hist_weeks` support the leakage truncation-trick (same right edge / decision
point, different left start; grades must not drift).

Usage (library): render_blind(ticker, entry_date, hist_weeks=60) -> png path (or None if no data).
"""
from __future__ import annotations
import sys, hashlib
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
import run_bhanushali_weekly_crs as CRS
from run_bhanushali_path1 import corrected_universe
from render_chart import weekly  # reuse the exact weekly panel builder (SMA44/20, slope, qg, rsok)

OUTDIR = Path(r"C:\Users\KREES~1.KRE\AppData\Local\Temp\claude\C--nifty-satvik"
              r"\23894ff0-e0c4-4a5c-8d6c-4a9bff3cd36c\scratchpad\blind_charts")
OUTDIR.mkdir(parents=True, exist_ok=True)

_PANEL = None


def load_panel():
    global _PANEL
    if _PANEL is None:
        ohlcv = corrected_universe()          # {ticker: daily DataFrame w/ Volume}
        P = R94.prep_weekly_rank(ohlcv)
        n50 = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
               .set_index("date")["nifty50_close"].sort_index())
        _PANEL = (P, n50, ohlcv)
    return _PANEL


def _weekly_volume(ticker, P, ohlcv):
    """Real weekly volume aligned index-for-index with render_chart.weekly()'s wd.
    Replicates weekly()'s exact consecutive ISO (year,week) grouping over P[t]['dates'],
    summing the raw daily Volume (prep_weekly_rank drops volume, so weekly() renders zeros)."""
    s = P[ticker]
    idx = pd.DatetimeIndex(s["dates"])
    iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
    daily_v = (ohlcv[ticker]["Volume"].reindex(idx).fillna(0.0).to_numpy()
               if ticker in ohlcv else np.zeros(len(idx)))
    weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    return np.array([daily_v[d].sum() for d in weeks])


def render_blind(ticker: str, entry_date, hist_weeks: int = 60, out_path=None):
    P, n50, ohlcv = load_panel()
    if ticker not in P:
        return None
    w = weekly(ticker, P, n50)
    wv = _weekly_volume(ticker, P, ohlcv)      # real volume (weekly() gives zeros)
    wd = w["wd"]
    ed = pd.Timestamp(entry_date)
    # Decision point = last completed weekly bar STRICTLY BEFORE the entry date.
    # This includes the signal-week Friday and excludes the entry week + all future -> no lookahead.
    idxs = [i for i, x in enumerate(wd) if x < ed]
    if not idxs:
        return None
    b = idxs[-1] + 1                       # exclusive end
    a = max(b - hist_weeks, 0)
    if b - a < 20:                          # too little history to show structure
        return None

    fig, (ax, axv) = plt.subplots(2, 1, figsize=(12, 7),
                                  gridspec_kw={"height_ratios": [4, 1]}, sharex=True)
    for i in range(a, b):
        up = w["wc"][i] >= w["wo"][i]
        col = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [w["wl"][i], w["wh"][i]], color=col, lw=0.9, zorder=2)
        lo, hi = sorted([w["wo"][i], w["wc"][i]])
        ax.add_patch(Rectangle((i - 0.3, lo), 0.6, max(hi - lo, 1e-6), color=col, zorder=3))
        axv.bar(i, wv[i] if i < len(wv) else 0.0, color=col, width=0.6)
    x = np.arange(a, b)
    ax.plot(x, w["ws"][a:b], color="#2962ff", lw=1.7, zorder=4)   # 44-wk SMA
    ax.plot(x, w["w20"][a:b], color="#ff9800", lw=1.1, ls="--", zorder=4)  # 20-wk SMA

    # BLIND: strip every identifying / period / outcome cue.
    ax.set_title("")
    ax.set_xticks([]); axv.set_xticks([])
    ax.set_yticklabels([]); axv.set_yticklabels([])   # hide absolute price/volume levels
    ax.set_xlim(a - 1, b)                              # right edge = decision point; no space for future
    ax.legend(["44-wk MA", "20-wk MA"], loc="upper left", fontsize=9)
    ax.grid(alpha=0.15); axv.grid(alpha=0.15)

    if out_path is None:
        h = hashlib.sha1(f"{ticker}|{pd.Timestamp(entry_date).date()}|{hist_weeks}".encode()).hexdigest()[:12]
        out_path = OUTDIR / f"c_{h}.png"
    fig.tight_layout(); fig.savefig(out_path, dpi=90); plt.close(fig)
    return str(out_path)


if __name__ == "__main__":
    # smoke test: render 3 train trades at two crop lengths, print paths
    df = pd.read_parquet(ROOT / "research" / "substrate" / "context_windows.parquet")
    tr = df[df["entry_date"] <= "2024-06-30"].reset_index(drop=True)
    for _, r in tr.iloc[[100, 900, 1800]].iterrows():
        for hw in (60, 90):
            p = render_blind(r["ticker"], r["entry_date"], hist_weeks=hw)
            print(r["ticker"], str(r["entry_date"])[:10], "hw", hw, "->", p)
