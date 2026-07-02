"""Pre-0078 diagnostic (no trial cost): is resid-mom's DD advantage real, or just a smaller engine?

Vol-match resid-mom's daily returns to the base book's volatility (single constant scalar) and
recompute the drawdown, full-period and 2022-26. If the live-window DD advantage survives the
vol-match, the structural (factor-avoidance) claim stands; if it evaporates, it was low-vol-as-low-DD.
Also probes size-tilt: corr(resid_rank, log ADV) — a check for SMB omission leaving size beta in the
"residual" (we residualized on [mkt, hml] only; SMB is data-gated).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
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
from nq.runner.research import _daily_returns, run_backtest  # noqa: E402
from run_residual_momentum import residual_ranks  # noqa: E402

START, END = "2017-01-01", "2026-06-30"


def dd(r: pd.Series, start: str | None = None) -> float:
    eq = (1.0 + r).cumprod()
    if start:
        eq = eq[eq.index >= pd.Timestamp(start)]
    return float((eq / eq.cummax() - 1.0).min() * 100)


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
    cand = panel.merge(rr, on=["date", "ticker"], how="left")

    # size-tilt probe (ADV proxy; universe is already large+mid so this is a coarse read)
    mm = cand.dropna(subset=["resid_rank", "adv_rupees_20d"])
    size_corr = np.corrcoef(mm["resid_rank"], np.log(mm["adv_rupees_20d"].clip(lower=1.0)))[0, 1]

    cand2 = cand.copy()
    cand2["trend_rank"] = cand2["resid_rank"]
    b = _daily_returns(run_backtest(panel, cfg, start=START, end=END)["equity_curve"])
    c = _daily_returns(run_backtest(cand2, cfg, start=START, end=END)["equity_curve"])
    common = b.index.intersection(c.index)
    b, c = b.loc[common], c.loc[common]
    bvol, cvol = b.std() * np.sqrt(252), c.std() * np.sqrt(252)
    k = b.std() / c.std()
    cm = c * k   # vol-matched to base

    print(f"\nann vol: base {bvol*100:.1f}%   resid {cvol*100:.1f}%   scalar k={k:.3f}")
    print(f"{'window':<12}{'base DD':>10}{'resid DD':>11}{'resid(vol-matched) DD':>24}")
    for tag, s in (("FULL 17-26", None), ("LIVE 22-26", "2022-01-01")):
        print(f"{tag:<12}{dd(b, s):>10.1f}{dd(c, s):>11.1f}{dd(cm, s):>24.1f}")
    print(f"\nsize-tilt: corr(resid_rank, log ADV) = {size_corr:+.3f}  "
          f"(|.|>~0.1 => residual is size-loaded; SMB omission matters)")
    print("Read: if LIVE vol-matched resid DD is still materially shallower than base -46.3, the "
          "factor-avoidance claim survives; if it approaches -46, the raw edge was low-vol-as-low-DD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
