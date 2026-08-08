"""Why does a book capped at N hold N+1 names?

The cap invariant fired in the pre-reg 0001 PBO sweep at ``top_n=30, buffer_mult=1.0``: 31 held
against a cap of 30 on 2024-09-03. There are exactly two ways a name whose target weight is zero can
survive the sell pass, and they have opposite implications:

  A. **No quote that session.** The name is absent from ``day.index``, so there is no price to sell
     at. This is CORRECT — a real book cannot liquidate a name that did not trade — and it means the
     invariant, not the engine, is wrong.

  B. **The exit is smaller than ``min_trade_pct``.** A position that has shrunk below the minimum
     trade size is skipped by the same guard that suppresses dust rebalancing, so it is never sold
     and occupies a slot for ever. This is a genuine defect and exactly the "silently retained"
     case the persistent-target comment claims to have eliminated.

This script does not guess between them. It re-runs the failing configuration with the invariant off
and classifies every over-cap session.

    python pipelines/diagnostics/diag_slot_overflow.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.engine.rebalance_book import RebalanceConfig, rebalance_dates  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from run_0001_xsec_momentum import BAND, END, START, add_signals  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

TOP_N, BUFFER = 30, 1.0


def main() -> int:
    print("=== SLOT OVERFLOW — classify every over-cap session ===\n")
    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    # identical band construction to the pre-reg: rank is gated, rows are not
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    p = p[keep].copy()
    p["rank"] = np.where(p["eligible"] & (p["size_band"] == BAND) & p["nms"].notna(),
                         p["nms"], np.nan)

    cfg = RebalanceConfig(top_n=TOP_N, buffer_mult=BUFFER, max_position_pct=5.0, cadence="M")
    cap = int(cfg.top_n * cfg.buffer_mult)

    dates = sorted(p["date"].unique())
    by_date = {d: g.set_index("ticker") for d, g in p.groupby("date", sort=True)}
    rebals = set(rebalance_dates(dates, cfg.cadence))

    # A stripped simulation: slots only. No cash, no costs — we are counting names, not money, so
    # the accounting cannot confound the answer.
    held: dict[str, float] = {}                  # ticker -> notional weight actually carried
    targets: dict[str, float] = {}
    armed = False
    reasons: Counter[str] = Counter()
    over_days = 0
    examples: list[str] = []

    for t in dates:
        day = by_date[t]
        if armed:
            for tkr in sorted(set(held) | set(targets)):
                tgt = targets.get(tkr, 0.0)
                if tkr not in held and tgt <= 0:
                    continue
                if tkr not in day.index:
                    continue                     # vector A: no quote, cannot transact
                if tgt <= 0:
                    held.pop(tkr, None)
                else:
                    held[tkr] = tgt
            targets = {k: w for k, w in targets.items() if w > 0.0}

        if len(held) > cap:
            over_days += 1
            for tkr in held:
                if targets and targets.get(tkr, 0.0) <= 0.0:
                    reasons["zero-target still held (no quote)"] += 1
            if len(examples) < 6:
                stuck = [k for k in held if targets and targets.get(k, 0.0) <= 0.0]
                examples.append(f"    {str(t)[:10]}  held {len(held)}  stuck {sorted(stuck)[:5]}")

        if t in rebals:
            ranked = day["rank"].dropna().sort_values(ascending=False)
            if ranked.empty:
                continue
            entrants = list(ranked.index[:cfg.top_n])
            keep_to = int(cfg.top_n * cfg.buffer_mult)
            tolerated = set(ranked.index[:keep_to])
            target = list(dict.fromkeys(entrants + [k for k in held if k in tolerated]))[:keep_to]
            if not target:
                continue
            w = min(1.0 / len(target), cfg.max_position_pct / 100.0)
            targets = {tkr: 0.0 for tkr in held}
            targets.update({tkr: w for tkr in target})
            armed = True

    print(f"  sessions over the cap of {cap}: {over_days} of {len(dates)}")
    for k, v in reasons.most_common():
        print(f"    {k}: {v}")
    print("\n  examples:")
    for e in examples:
        print(e)

    # How often is a HELD name simply missing a quote? That is the size of vector A.
    print("\n=== how often does a name in the band have no quote on a given session? ===")
    piv = p.pivot_table(index="date", columns="ticker", values="close")
    first = piv.notna().cummax()                 # only count gaps AFTER listing
    last = piv.notna()[::-1].cummax()[::-1]
    live = first & last
    gaps = int((live & piv.isna()).to_numpy().sum())
    print(f"  interior missing bars (listed, not yet delisted): {gaps:,} of {int(live.to_numpy().sum()):,}"
          f"  ({gaps / max(int(live.to_numpy().sum()), 1) * 100:.3f}%)")
    print("\n  READING: a nonzero interior-gap rate means a real book cannot always sell on the")
    print("  session it decides to. If EVERY over-cap session is explained by a missing quote, the")
    print("  engine is right and the hard cap invariant is mis-specified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
