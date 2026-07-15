"""Render weekly candlestick charts (SMA44 + SMA20 + volume) with our DETECTOR overlays drawn on top, so we
can VISUALLY validate that the box / support-resistance detectors mark what a human sees. Not a backtest —
a seeing tool. Usage: python scripts/render_chart.py GAIL 2022-06 2024-06 [box|sr|trend]  -> PNG in scratchpad."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from run_bhanushali_weekly_rank import SLOPE_MIN, SLOPE_LOOKBACK, TOUCH_BAND, CRS_LEN
import run_bhanushali_weekly_crs as CRS
from run_bhanushali_path1 import corrected_universe

OUT = Path(r"C:\Users\KREES~1.KRE\AppData\Local\Temp\claude\C--nifty-satvik\7384ecb1-802d-40eb-9f1a-22d2e2d5efc6\scratchpad")
OUT.mkdir(parents=True, exist_ok=True)


def weekly(t, P, n50):
    s = P[t]; idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy())); weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    o, h, l, c, v = s["o"], s["h"], s["l"], s["c"], s.get("v", np.zeros(len(s["c"])))
    wo = np.array([o[d[0]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
    wl = np.array([l[d].min() for d in weeks]); wc = np.array([c[d[-1]] for d in weeks])
    wv = np.array([v[d].sum() for d in weeks]); wd = [pd.Timestamp(s["dates"][d[-1]]) for d in weeks]
    ws = pd.Series(wc).rolling(44).mean().to_numpy(); w20 = pd.Series(wc).rolling(20).mean().to_numpy()
    slope = np.full(len(ws), np.nan); slope[SLOPE_LOOKBACK:] = ws[SLOPE_LOOKBACK:] / ws[:-SLOPE_LOOKBACK] - 1.0
    rng = wh - wl; qg = (wc > wo) & (rng > 0) & ((wc - wl) >= 0.5 * rng)
    ia = n50.reindex(idx, method="ffill").to_numpy(float); iw = np.array([ia[d[-1]] for d in weeks])
    rs = np.where(iw > 0, wc / iw, np.nan); rs_sma = pd.Series(rs).rolling(CRS_LEN).mean().to_numpy()
    rsok = np.nan_to_num(rs > rs_sma, nan=False)
    return dict(wo=wo, wh=wh, wl=wl, wc=wc, wv=wv, wd=wd, ws=ws, w20=w20, slope=slope, qg=qg, rsok=rsok)


def render(t, d0, d1, overlay, box_len=12, box_tight=0.35, sr_len=12, sr_test_band=0.03):
    ohlcv = corrected_universe(); P = R94.prep_weekly_rank(ohlcv)
    n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
    w = weekly(t, P, n50)
    wd = w["wd"]; m = [(pd.Timestamp(d0) <= x <= pd.Timestamp(d1)) for x in wd]
    idxs = [i for i, keep in enumerate(m) if keep]
    if not idxs:
        print("no weeks in range"); return
    a, b = idxs[0], idxs[-1] + 1
    fig, (ax, axv) = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [4, 1]}, sharex=True)
    x = np.arange(a, b)
    for i in range(a, b):
        up = w["wc"][i] >= w["wo"][i]; col = "#26a69a" if up else "#ef5350"
        ax.plot([i, i], [w["wl"][i], w["wh"][i]], color=col, lw=0.8, zorder=2)
        lo, hi = sorted([w["wo"][i], w["wc"][i]])
        ax.add_patch(Rectangle((i - 0.3, lo), 0.6, max(hi - lo, 1e-6), color=col, zorder=3))
        axv.bar(i, w["wv"][i], color=col, width=0.6)
    ax.plot(x, w["ws"][a:b], color="#2962ff", lw=1.6, label="44-wk SMA", zorder=4)
    ax.plot(x, w["w20"][a:b], color="#ff9800", lw=1.1, ls="--", label="20-wk SMA", zorder=4)

    fired = []
    if overlay == "box":
        for k in range(max(a, box_len), b):
            if not (np.nan_to_num(w["slope"][k], nan=-9) >= SLOPE_MIN):
                continue
            bh = w["wh"][k - box_len:k].max(); bl = w["wl"][k - box_len:k].min()
            if not (bl > 0 and (bh - bl) / bl <= box_tight):
                continue
            sm = w["ws"][k]
            if not (sm == sm and np.nanmin(w["wc"][k - box_len:k]) > sm):
                continue
            if w["qg"][k] and w["wc"][k] > bh and w["rsok"][k]:
                ax.add_patch(Rectangle((k - box_len, bl), box_len, bh - bl, fill=False,
                                       edgecolor="#ffd54f", lw=1.5, ls="-", zorder=5))
                ax.scatter([k], [w["wc"][k]], marker="^", s=120, color="#ffd54f", edgecolor="k", zorder=6)
                ax.plot([k - box_len, k + 2], [bl, bl], color="red", lw=1.0, ls=":", zorder=5)  # stop=box low
                fired.append((wd[k].strftime("%Y-%m-%d"), round(bl, 1), round(bh, 1)))
    elif overlay == "sr2":
        # PROPER horizontal S/R: a level where >=2 PIVOT HIGHS cluster at the same price (rejected repeatedly),
        # roughly FLAT, then a green close breaks above it; stop just below the level (broken resistance=support).
        piv = np.zeros(len(w["wh"]), bool)
        for i in range(2, len(w["wh"]) - 2):
            if w["wh"][i] >= w["wh"][i - 2:i + 3].max():
                piv[i] = True
        for k in range(max(a, 14), b):
            if not (np.nan_to_num(w["slope"][k], nan=-9) >= SLOPE_MIN and w["qg"][k] and w["rsok"][k]):
                continue
            pv = [w["wh"][i] for i in range(k - 14, k - 1) if piv[i]]          # pivot highs in the base window
            if len(pv) < 2:
                continue
            lvl = np.median(pv)                                                # the clustered level
            near = [p for p in pv if abs(p / lvl - 1) <= 0.03]                 # pivots within 3% of the level
            sm = w["ws"][k]
            if (len(near) >= 2 and w["wc"][k - 1] <= lvl and w["wc"][k] > lvl
                    and sm == sm and w["wc"][k] > sm):
                stop = lvl * 0.94                                              # tight stop just below the level
                ax.plot([k - 14, k + 2], [lvl, lvl], color="#ffd54f", lw=2.0, zorder=5)
                ax.plot([k - 14, k + 2], [stop, stop], color="red", lw=1.0, ls=":", zorder=5)
                for i in range(k - 14, k - 1):
                    if piv[i] and abs(w["wh"][i] / lvl - 1) <= 0.03:
                        ax.scatter([i], [w["wh"][i]], marker="v", s=60, color="#ffd54f", edgecolor="k", zorder=6)
                ax.scatter([k], [w["wc"][k]], marker="^", s=120, color="lime", edgecolor="k", zorder=7)
                fired.append((wd[k].strftime("%Y-%m-%d"), f"lvl{round(lvl,1)}", f"stop{round((lvl-stop)/lvl*100)}%"))
    elif overlay == "sr":
        for k in range(max(a, sr_len), b):
            if not (np.nan_to_num(w["slope"][k], nan=-9) >= SLOPE_MIN and w["qg"][k] and w["rsok"][k]):
                continue
            lo = k - sr_len; res = w["wh"][lo:k].max()
            tested = int(np.sum(w["wh"][lo:k] >= res * (1 - sr_test_band)))
            sm = w["ws"][k]
            if tested >= 2 and w["wc"][k - 1] <= res and w["wc"][k] > res and sm == sm and w["wc"][k] > sm:
                stop = w["wl"][lo:k].min()
                ax.plot([lo, k + 2], [res, res], color="#ffd54f", lw=1.8, zorder=5)         # resistance
                ax.plot([lo, k + 2], [stop, stop], color="red", lw=1.0, ls=":", zorder=5)   # stop=base low
                ax.scatter([k], [w["wc"][k]], marker="^", s=120, color="#ffd54f", edgecolor="k", zorder=6)
                fired.append((wd[k].strftime("%Y-%m-%d"), f"R{round(res,1)}", f"stop{round(stop,1)} ({round((res-stop)/res*100)}%)"))

    ax.set_title(f"{t}  weekly  {d0}..{d1}   overlay={overlay}   fires={fired}", fontsize=10)
    ax.legend(loc="upper left"); ax.grid(alpha=0.15); axv.grid(alpha=0.15)
    ax.set_xticks(x[::4]); ax.set_xticklabels([wd[i].strftime("%b-%y") for i in x[::4]], rotation=45, fontsize=8)
    fn = OUT / f"chart_{t}_{overlay}.png"
    fig.tight_layout(); fig.savefig(fn, dpi=90); plt.close(fig)
    print(f"saved {fn}  | fires: {fired}")
    return str(fn)


if __name__ == "__main__":
    t = sys.argv[1]; d0 = sys.argv[2]; d1 = sys.argv[3]
    overlay = sys.argv[4] if len(sys.argv) > 4 else "box"
    render(t, d0, d1, overlay)
