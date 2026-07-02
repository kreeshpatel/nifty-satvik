"""Reproduce the veto-0.1 PnL cascade vs base — the auditable basis for the forward-wall §6 null.

The forward-wall pre-reg cites a removed/replacement/shared decomposition for veto-0.1's in-sample
edge as the "expect reversion" null. That decomposition was never in the committed record, so this
reproduces it from the pinned pipeline with an explicit methodology (trade-key = ticker+entry_date):

  removed      = base trades on names veto vetoed (key in base, not in veto) -> PnL base forwent
  replacement  = veto trades not in base (key in veto, not in base) -> PnL from freed-slot re-picks
  shared_delta = sum(veto_pnl - base_pnl) over shared keys -> sizing/exit differences
  net check    : veto_total - base_total ~= replacement - removed + shared_delta

Path-dependence makes this an approximate attribution (freeing a slot changes the whole downstream
path), but it is reproducible and auditable — unlike a transcript figure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DATA_DIR, load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import run_backtest  # noqa: E402
from run_residual_blend_veto import make_arm  # noqa: E402
from run_residual_momentum import residual_ranks  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
L = 1e5  # rupees -> lakh


def tdf(bt):
    d = pd.DataFrame(bt["trades"])
    d["key"] = d["ticker"] + "|" + d["entry_date"].astype(str)
    return d


def main() -> int:
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    factors = pd.read_parquet(DATA_DIR / "ff_india_factors.parquet").set_index("date").sort_index()
    print("residualizing ...", flush=True)
    rr = residual_ranks(panel, factors)

    base = tdf(run_backtest(panel, cfg, start=START, end=END))
    veto = tdf(run_backtest(make_arm(panel, rr, "veto", 0.10), cfg, start=START, end=END))
    bk, vk = set(base["key"]), set(veto["key"])

    removed = base[~base["key"].isin(vk)]
    replacement = veto[~veto["key"].isin(bk)]
    sb = base[base["key"].isin(vk)].set_index("key")["pnl"]
    sv = veto[veto["key"].isin(bk)].set_index("key")["pnl"]
    shared_delta = float((sv - sb.reindex(sv.index)).sum())

    bt_pnl, vt_pnl = float(base["pnl"].sum()), float(veto["pnl"].sum())
    print(f"\nbase trades {len(base)} (PnL {bt_pnl/L:+.1f}L)   veto-0.1 trades {len(veto)} (PnL {vt_pnl/L:+.1f}L)")
    print(f"net veto-base = {(vt_pnl-bt_pnl)/L:+.1f}L\n")
    print(f"  removed      ({len(removed):>4} base trades veto vetoed):  {removed['pnl'].sum()/L:+8.1f}L  "
          f"(win {100*(removed['pnl']>0).mean():.0f}%)")
    print(f"  replacement  ({len(replacement):>4} veto-only trades):      {replacement['pnl'].sum()/L:+8.1f}L  "
          f"(win {100*(replacement['pnl']>0).mean():.0f}%)")
    print(f"  shared_delta ({len(sv):>4} shared keys):               {shared_delta/L:+8.1f}L")
    recon = (replacement['pnl'].sum() - removed['pnl'].sum() + shared_delta) / L
    print(f"  recon (repl - removed + shared) = {recon:+.1f}L  vs net {(vt_pnl-bt_pnl)/L:+.1f}L")
    print("\nInterpretation: if 'removed' names were PROFITABLE in base and 'replacement' names merely "
          "earned more (path/reshuffle), the veto edge is largely luck+compounding, not mechanism -> "
          "expect forward reversion (the §6 null).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
