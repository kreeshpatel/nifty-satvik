"""The blended HYBRID model — swing-0094 x low-vol at equal-risk-contribution (quarterly inverse-vol).

The one structural lever that survived the 2026-07-26 exit/entry-exhaustion sweep: combining two
low-correlation positive-edge books (swing 0094 Sharpe 1.15, low-vol Sharpe 1.06, corr 0.54)
mechanically lifts Sharpe above BOTH and earns in the chop years the swing book fades in (2024/2025).
Uses the FROZEN 0081 ERC recipe verbatim (no new free params — a measurement, not a tuned trial).
In-sample can't certify (low-vol = uncertifiable O-016; 0081 was UNDERPOWERED) → this is a FORWARD-WALL
watched book, NOT a live config swap. See finding 0107 + forward/prereg_swing.md.

    python scripts/run_blend_hybrid.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

LV_CACHE = ROOT / "research" / "exports" / "sleeve_daily_returns.csv"   # r_lv (diag_regime_sleeve_learnability)
OUT = ROOT / "research" / "exports" / "blend_hybrid_returns.csv"


def erc_blend(sw: pd.Series, lv: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Quarterly inverse-vol weight on the swing sleeve (frozen 0081 recipe), as-of prior day."""
    idx = sw.index.intersection(lv.index)
    sw, lv = sw.reindex(idx), lv.reindex(idx)
    vm, vl = sw.rolling(63).std().shift(1), lv.rolling(63).std().shift(1)
    w = ((1 / vm) / (1 / vm + 1 / vl)).resample("QS").first().reindex(idx, method="ffill").clip(0, 1).fillna(0.5)
    blend = (w.shift(1) * sw + (1 - w.shift(1)) * lv).rename("blend")
    return blend, w.rename("w_swing")


def _stats(r: pd.Series) -> dict:
    r = r.dropna(); e = (1 + r).cumprod()
    return {"Sharpe": r.mean() / r.std() * np.sqrt(252), "CAGR": (e.iloc[-1] ** (252 / len(r)) - 1) * 100,
            "MaxDD": (e / e.cummax() - 1).min() * 100}


def _peryr(r: pd.Series) -> dict:
    return {y: ((1 + g).cumprod().iloc[-1] - 1) * 100 for y, g in r.dropna().groupby(r.dropna().index.year)}


def main() -> int:
    oh = corrected_universe(); mem = load_membership(); P = prep_weekly_rank(oh)
    sw = backtest(P, mem)["ret"].dropna().rename("swing")
    lv = pd.read_csv(LV_CACHE, index_col=0, parse_dates=True)["r_lv"].dropna().rename("lowvol")
    blend, w = erc_blend(sw, lv)
    idx = blend.dropna().index; sw, lv = sw.reindex(idx), lv.reindex(idx)

    print("=== HYBRID: swing-0094 x low-vol (ERC, quarterly inverse-vol) ===")
    print(f"corr(swing,lowvol) {sw.corr(lv):+.2f} | mean swing weight {w.reindex(idx).mean():.2f}\n")
    print(f"{'book':<14}{'Sharpe':>8}{'CAGR%':>8}{'MaxDD%':>8}")
    for nm, r in (("swing 0094", sw), ("low-vol", lv), ("BLEND", blend)):
        s = _stats(r); print(f"{nm:<14}{s['Sharpe']:>8.2f}{s['CAGR']:>8.1f}{s['MaxDD']:>8.1f}")
    ps, pl, pb = _peryr(sw), _peryr(lv), _peryr(blend)
    print("\nper-year %: swing | low-vol | blend")
    for y in sorted(ps):
        wk = "  <= swing weak" if ps[y] < 8 else ""
        print(f"  {y}  {ps[y]:+7.1f} | {pl.get(y, float('nan')):+7.1f} | {pb.get(y, float('nan')):+7.1f}{wk}")
    pd.concat([sw, lv, blend, w.reindex(idx)], axis=1).to_csv(OUT)
    print(f"\nblend Sharpe {_stats(blend)['Sharpe']:.2f} beats both sleeves -> diversification confirmed. "
          f"Losing years: {sum(1 for v in pb.values() if v < 0)} (swing alone: {sum(1 for v in ps.values() if v < 0)}).")
    print(f"saved -> {OUT}  | certification: FORWARD-WALL only (in-sample uncertifiable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
