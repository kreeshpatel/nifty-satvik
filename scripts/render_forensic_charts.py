"""Render the Stage-2 focused-forensic sample: touch/trend LOSERS (the -0.94R stop-out engine)
+ a WINNER contrast set, as weekly charts an AI-vision agent can reason over. Emits PNGs +
research/substrate/vision_charts/manifest.json (the list passed to the vision Workflow as args).

    python scripts/render_forensic_charts.py [N_LOSERS N_WINNERS]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.weekly import load_weekly_panel  # noqa: E402

OUT = ROOT / "research" / "substrate" / "vision_charts"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260716
N_LOSERS = int(sys.argv[1]) if len(sys.argv) > 1 else 180
N_WINNERS = int(sys.argv[2]) if len(sys.argv) > 2 else 120


def render_one(wp_t, row, path):
    """BLIND entry-context chart: weekly bars up to and including the ENTRY week only (no future,
    no outcome, no R in the title), so an AI triage of setup quality is unbiased by hindsight."""
    ed = pd.Timestamp(row["entry_date"])
    ci = (wp_t.week_end - ed).abs().idxmin()
    lo, hi = max(ci - 45, 0), min(ci + 1, len(wp_t))   # through the entry week only
    sub = wp_t.iloc[lo:hi].reset_index(drop=True)
    x = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, r in sub.iterrows():
        col = "#0a0" if r.c >= r.o else "#c00"
        ax.plot([i, i], [r.l, r.h], color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((i - 0.32, min(r.o, r.c)), 0.64, abs(r.c - r.o) + 1e-9, color=col, alpha=0.75))
    ax.plot(x, sub.sma44, color="blue", lw=1.3, label="44w SMA")
    ei = int((sub.week_end - ed).abs().idxmin())
    ax.axvline(ei, color="black", ls="--", lw=1.2, alpha=0.8)
    ax.scatter([ei], [sub.iloc[ei].l * 0.985], marker="^", color="black", s=160, zorder=6, label="ENTRY week")
    ax.axhline(row["entry"], color="black", ls=":", lw=0.8, label="entry px")
    ax.axhline(row["stop"], color="red", ls=":", lw=0.9, label="stop")
    # volume strip along the bottom
    vmax = sub.v.max() or 1
    y0 = sub[["l", "sma44"]].min().min()
    vscale = (sub.h.max() - y0) * 0.15 / vmax
    for i, r in sub.iterrows():
        col = "#0a0" if r.c >= r.o else "#c00"
        ax.add_patch(plt.Rectangle((i - 0.32, y0), 0.64, r.v * vscale, color=col, alpha=0.3))
    ax.set_title(f"{row['ticker']}  {row['setup']}  entry week {str(ed)[:10]}  "
                 f"(black ^ = entry, buy next week)", fontsize=10)
    ax.set_xticks(x[::4]); ax.set_xticklabels([str(d)[:7] for d in sub.week_end[::4]], rotation=45, fontsize=7)
    ax.legend(fontsize=8, loc="upper left")
    plt.tight_layout(); plt.savefig(path, dpi=85); plt.close(fig)


def main():
    df = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    core = df[df.setup.isin(["touch44", "trend_pullback"])]
    losers = core[core.R < 0].sample(min(N_LOSERS, (core.R < 0).sum()), random_state=SEED)
    winners = core[core.R >= 2].sample(min(N_WINNERS, (core.R >= 2).sum()), random_state=SEED)
    sample = pd.concat([losers, winners]).reset_index(drop=True)
    wp = load_weekly_panel(cache=True)
    manifest = []
    for _, row in sample.iterrows():
        wp_t = wp[wp.ticker == row["ticker"]].reset_index(drop=True)
        tag = "L" if row["R"] < 0 else "W"
        fn = f"{tag}_{row['setup']}_{row['ticker']}_{str(row['entry_date'])[:10]}.png"
        path = OUT / fn
        try:
            render_one(wp_t, row, path)
        except Exception as e:
            print(f"skip {fn}: {e}"); continue
        manifest.append(dict(
            file=str(path), label=("loser" if row["R"] < 0 else "winner"),
            ticker=row["ticker"], setup=row["setup"], entry_date=str(row["entry_date"])[:10],
            R=round(float(row["R"]), 2), reason=row["reason"], split=row["split"],
            ext_vs_sma=None if pd.isna(row["ext_vs_sma"]) else round(float(row["ext_vs_sma"]), 1),
            mfe_pct=round(float(row["mfe_pct"]), 1), mae_first2wk=round(float(row["mae_first2wk"]), 1)))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"rendered {len(manifest)} charts -> {OUT}  ({ (sample.R<0).sum()} losers, {(sample.R>=2).sum()} winners)")


if __name__ == "__main__":
    main()
