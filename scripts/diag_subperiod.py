"""Sub-period gate — CORRECT method: run ONCE continuously, then SLICE the equity path.

Fixes the earlier bug where each sub-period was a fresh simulate(start=...) with reset capital
(phantom peak -> phantom DD -40.0 / phantom Sharpe 0.762). Slicing the single continuous run
preserves the true equity peak (mid-2024) and the boundary position seasoning, matching how
nq.runner.research.evaluate_overlay computes the promotion-bar sub-period gate.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

from config import load_frozen_cfg
from nq.data.membership import load_membership
from nq.data.features import compute_all_features
from nq.data.fundamentals import load_fund_store
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import simulate

FULL = ("2017-01-01", "2026-06-30")


def slice_metrics(equity_curve, start, end):
    s = pd.Series([e["equity"] for e in equity_curve],
                  index=pd.to_datetime([e["date"] for e in equity_curve]), dtype=float)
    sl = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    r = sl.pct_change().dropna()
    if len(r) < 30 or r.std() == 0:
        return (float("nan"),) * 3
    sharpe = r.mean() / r.std() * np.sqrt(252)
    dn = r[r < 0]
    sortino = r.mean() / dn.std() * np.sqrt(252) if len(dn) and dn.std() > 0 else float("nan")
    dd = (sl / sl.cummax() - 1.0).min() * 100
    return sharpe, sortino, dd


def main():
    cfg = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())

    variants = {
        "base (22.52)": {},
        "target=30": {"target_pct": 30.0},
        "uncapped": {"target_pct": 999.0},
        "uncapped+trail8": {"target_pct": 999.0, "trailing_pct": 8.0},
        "uncapped+trail6": {"target_pct": 999.0, "trailing_pct": 6.0},
    }
    windows = {"FULL 17-26": FULL, "BULL 17-21": ("2017-01-01", "2021-12-31"),
               "LIVE 22-26": ("2022-01-01", "2026-06-30")}

    print(f"\n{'variant':<18}" + "".join(f"{w+' Sh':>14}{'So':>6}{'DD':>7}" for w in windows))
    print("-" * (18 + 27 * len(windows)))
    base_live = None
    rows = {}
    for name, over in variants.items():
        c = dict(cfg); c.update(over)
        ec = simulate(panel, c, start=FULL[0], end=FULL[1])["equity_curve"]
        cells = {w: slice_metrics(ec, s, e) for w, (s, e) in windows.items()}
        rows[name] = cells
        if name == "base (22.52)":
            base_live = cells["LIVE 22-26"][0]
        line = f"{name:<18}"
        for w in windows:
            sh, so, dd = cells[w]
            line += f"{sh:>14.3f}{so:>6.2f}{dd:>7.1f}"
        print(line, flush=True)

    print(f"\nCORRECTED 2022-26 GATE = base sliced Sharpe {base_live:.3f} "
          f"(vs the phantom 0.762 from the fresh-capital re-run).")
    print("Pass = LIVE 22-26 Sharpe > corrected gate:")
    for name, cells in rows.items():
        if name == "base (22.52)":
            continue
        sh = cells["LIVE 22-26"][0]
        print(f"  {name:<18} live Sharpe {sh:.3f}  -> {'PASS' if sh > base_live else 'FAIL'}")


if __name__ == "__main__":
    main()
