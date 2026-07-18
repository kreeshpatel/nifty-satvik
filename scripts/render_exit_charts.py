"""Render the exit-forensic sample: each trade's FULL path (entry -> exit -> +12 weeks AFTER) so an
AI-vision agent can judge the EXIT as too-early / too-late / right, and spot structural exit tells.
Symmetric to render_forensic_charts.py (entry search), but outcome-AWARE (the post-exit path is the
whole point). Touch44 + box (the live-relevant families), stratified by exit quality.

    python scripts/render_exit_charts.py [N_TOUCH N_BOX]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.weekly import load_weekly_panel

OUT = ROOT / "research" / "substrate" / "exit_charts"; OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260716
N_TOUCH = int(sys.argv[1]) if len(sys.argv) > 1 else 120
N_BOX = int(sys.argv[2]) if len(sys.argv) > 2 else 80


def render_one(wp_t, row, path):
    ed, xd = pd.Timestamp(row["entry_date"]), pd.Timestamp(row["exit_date"])
    ci = (wp_t.week_end - ed).abs().idxmin(); xi = (wp_t.week_end - xd).abs().idxmin()
    lo, hi = max(ci - 25, 0), min(xi + 12, len(wp_t))          # entry-context .. exit .. +12wk AFTER
    sub = wp_t.iloc[lo:hi].reset_index(drop=True); x = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, r in sub.iterrows():
        col = "#0a0" if r.c >= r.o else "#c00"
        ax.plot([i, i], [r.l, r.h], color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((i - 0.32, min(r.o, r.c)), 0.64, abs(r.c - r.o) + 1e-9, color=col, alpha=0.75))
    ax.plot(x, sub.sma44, color="blue", lw=1.2, label="44w SMA")
    ei = int((sub.week_end - ed).abs().idxmin()); xii = int((sub.week_end - xd).abs().idxmin())
    ax.axvline(ei, color="black", ls="--", lw=1.1, alpha=.7); ax.axvline(xii, color="purple", ls="--", lw=1.2, alpha=.8)
    ax.scatter([ei], [sub.iloc[ei].l * .985], marker="^", color="black", s=150, zorder=6, label="ENTRY")
    ax.scatter([xii], [sub.iloc[xii].h * 1.015], marker="v", color="purple", s=160, zorder=6, label="EXIT")
    # MFE peak marker
    seg = sub.iloc[ei:xii + 1]
    if len(seg):
        pk = seg["h"].idxmax(); ax.scatter([pk], [sub.iloc[pk].h * 1.02], marker="*", color="orange", s=200, zorder=6, label="peak (MFE)")
    ax.axhline(row["entry"], color="black", ls=":", lw=.7); ax.axhline(row["stop"], color="red", ls=":", lw=.8, label="stop")
    vmax = sub.v.max() or 1; y0 = sub[["l", "sma44"]].min().min(); vs = (sub.h.max() - y0) * .15 / vmax
    for i, r in sub.iterrows():
        ax.add_patch(plt.Rectangle((i - .32, y0), .64, r.v * vs, color=("#0a0" if r.c >= r.o else "#c00"), alpha=.3))
    ax.set_title(f"{row['ticker']} {row['setup']}  entry {str(ed)[:10]} -> exit {str(xd)[:10]}  "
                 f"R={row['R']:+.2f} MFE={row['mfe_pct']:+.0f}% reason={row['reason']}  (bars right of purple = AFTER exit)", fontsize=9)
    ax.set_xticks(x[::4]); ax.set_xticklabels([str(d)[:7] for d in sub.week_end[::4]], rotation=45, fontsize=7)
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout(); plt.savefig(path, dpi=82); plt.close(fig)


def sample(df, setup, n):
    g = df[df.setup == setup].copy()
    g["mfe_R"] = g.mfe_pct / g.risk_pct
    give = g[(g.R > 0) & (g.mfe_R >= 2.5) & (g.mfe_R - g.R >= 1.5)]     # big-peak giveback
    clean = g[(g.R > 0) & (g.mfe_R - g.R < 1.0)]                        # kept most of the move
    stop = g[g.R < 0]                                                    # stop-outs
    parts = []
    for strat, k in [(give, n // 3), (clean, n // 3), (stop, n - 2 * (n // 3))]:
        parts.append(strat.sample(min(k, len(strat)), random_state=SEED))
    return pd.concat(parts)


def main():
    df = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    samp = pd.concat([sample(df, "touch44", N_TOUCH), sample(df, "box", N_BOX)]).reset_index(drop=True)
    wp = load_weekly_panel(cache=True)
    man = []
    for _, r in samp.iterrows():
        wp_t = wp[wp.ticker == r["ticker"]].reset_index(drop=True)
        fn = f"{r['setup']}_{r['ticker']}_{str(r['entry_date'])[:10]}.png"
        try:
            render_one(wp_t, r, OUT / fn)
        except Exception as e:
            print(f"skip {fn}: {e}"); continue
        man.append(dict(file=str(OUT / fn), ticker=r["ticker"], setup=r["setup"], R=round(float(r["R"]), 2),
                        reason=r["reason"], mfe_pct=round(float(r["mfe_pct"]), 1),
                        mfe_R=round(float(r["mfe_pct"] / r["risk_pct"]), 2) if r["risk_pct"] else None,
                        split=r["split"]))
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"rendered {len(man)} exit charts -> {OUT}")


if __name__ == "__main__":
    main()
