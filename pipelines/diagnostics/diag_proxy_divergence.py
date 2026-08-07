"""ENG-02 follow-up — WHERE does the turnover-rank proxy disagree with real membership?

Gate A passed (90.1% mean recovery) and Gate B failed (+1.49pp CAGR): the proxy picks nearly the
right names and still produces a measurably different, **more flattering** book. That combination is
the one worth diagnosing, because it says the disagreements are concentrated in names that matter
rather than spread evenly.

Three questions, in the order that narrows fastest:

  1. WHERE in the ranking do the two definitions disagree? The prior is the band boundary — a name a
     rupee either side of turnover rank 100 or 250 changes band, and the two definitions need not
     agree which side it is on.
  2. Is the disagreement SYMMETRIC? Proxy-only and real-only names in equal number is churn at the
     boundary. A persistent imbalance is a different instrument, not a noisy one.
  3. Do the disagreeing names EARN differently? This is what converts a set difference into a CAGR
     difference, and its sign says whether the proxy flatters or penalises.

Measurement only. Nothing is tuned here: no alternative proxy width is tried, because searching
widths until Gate B passes would be fitting the instrument to the answer.

    python pipelines/diagnostics/diag_proxy_divergence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from run_0001_xsec_momentum import add_signals  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))
from diag_membership_proxy import END, START, proxy_membership  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "proxy_divergence.json"


def main() -> int:
    print("=== ENG-02 follow-up — where the proxy and real membership disagree ===\n")
    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    screens = p["liq_ok"] & p["hist_ok"] & p["price_ok"] & p["circuit_ok"]
    p["real_ok"] = p["is_member"] & screens
    p["prox_ok"] = proxy_membership(p) & screens

    # band rank within each definition's own eligible set, per date
    for tag, col in (("real", "real_ok"), ("prox", "prox_ok")):
        rk = p[p[col]].groupby("date")["turnover_63d"].rank(ascending=False, method="first")
        p[f"{tag}_rank"] = rk.reindex(p.index)
        p[f"{tag}_mid"] = p[col] & p[f"{tag}_rank"].between(101, 250)

    both = p["real_mid"] & p["prox_mid"]
    real_only = p["real_mid"] & ~p["prox_mid"]
    prox_only = p["prox_mid"] & ~p["real_mid"]
    print("=== 2. is the disagreement symmetric? (name-days) ===")
    print(f"  in both       {int(both.sum()):>8,}")
    print(f"  real only     {int(real_only.sum()):>8,}   (proxy MISSES these)")
    print(f"  proxy only    {int(prox_only.sum()):>8,}   (proxy ADDS these)")
    imbalance = int(prox_only.sum()) - int(real_only.sum())
    print(f"  imbalance     {imbalance:>+8,}   "
          f"{'proxy band runs SMALLER' if imbalance < 0 else 'proxy band runs LARGER'}")

    print("\n=== 1. where in the ranking? (real_rank of the names the proxy misses) ===")
    ro = p.loc[real_only, "real_rank"].dropna()
    if len(ro):
        for lo, hi in ((101, 130), (131, 180), (181, 220), (221, 250)):
            share = float(((ro >= lo) & (ro <= hi)).mean())
            width = (hi - lo + 1) / 150.0
            print(f"  rank {lo:>3}-{hi:<3}  {share:>6.1%} of misses   "
                  f"(band share {width:>5.1%})  {'CONCENTRATED' if share > width * 1.5 else ''}")
        print(f"  median rank of a missed name: {ro.median():.0f}")

    print("\n=== 3. do the disagreeing names earn differently? (forward 63d return) ===")
    p = p.sort_values(["ticker", "date"])
    p["fwd63"] = p.groupby("ticker")["close"].shift(-63) / p["close"] - 1.0
    stats = {}
    for label, mask in (("in both", both), ("real only (missed)", real_only),
                        ("proxy only (added)", prox_only)):
        f = p.loc[mask, "fwd63"].dropna()
        stats[label] = {"n": int(f.size), "mean_pct": float(f.mean() * 100)}
        print(f"  {label:<20} n {f.size:>8,}   mean forward 63d {f.mean() * 100:>+7.2f}%")
    add, miss = stats["proxy only (added)"]["mean_pct"], stats["real only (missed)"]["mean_pct"]
    print(f"\n  added minus missed: {add - miss:+.2f}pp per name-day")
    print("  This is the mechanism behind Gate B's +1.49pp CAGR. A proxy whose ADDED names outperform")
    print("  its MISSED names does not merely differ from real membership — it FLATTERS, which is the")
    print("  one direction a holdout instrument must not fail in.")

    OUT.write_text(json.dumps({
        "name_days": {"both": int(both.sum()), "real_only": int(real_only.sum()),
                      "proxy_only": int(prox_only.sum()), "imbalance": imbalance},
        "missed_rank_median": float(ro.median()) if len(ro) else None,
        "forward_63d": stats, "added_minus_missed_pp": add - miss},
        indent=2, default=str), encoding="utf-8")
    print(f"\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
