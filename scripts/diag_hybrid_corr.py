"""Build step 1 — the decision that shapes the hybrid model: is the working momentum-pullback strategy
(strong visible-uptrend 44-SMA + pullback + wide ATR-2.5 stop + let-winners-run) NEW alpha or our base
momentum re-dressed? Answered by the daily-return correlation to baseline_v1.

Low corr (< ~0.5)  -> genuinely diversifying -> build it as its own sleeve, forward-wall it.
High corr          -> the base momentum edge in a new wrapper -> fold the wide-stop/volume insight into base.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from diag_ma44_pullback import backtest, prep  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    base = pd.read_csv(ROOT / "research" / "exports" / "daily_returns.csv", parse_dates=["date"]).set_index("date")
    b = base["ret_net"].dropna()

    configs = [
        ("ATR2.5 1:3/40d", dict(stop_mode="atr25", RR=3.0, maxhold=40, exit_mode="target")),
        ("ATR2.5 drift-40d", dict(stop_mode="atr25", RR=2.0, maxhold=40, exit_mode="drift")),
    ]
    print(f"baseline_v1 daily returns: {len(b)} days {b.index.min().date()}..{b.index.max().date()}\n")
    print(f"{'hybrid config':<18}{'overlap':>8}{'Pearson r':>11}{'Spearman':>10}{'hybrid Sh':>11}{'read'}")
    print("-" * 70)
    for name, kw in configs:
        m = backtest(P, "sig_strong", **kw)
        h = m["curve"].pct_change().dropna()
        common = h.index.intersection(b.index)
        hp, bp = h.loc[common], b.loc[common]
        pear = hp.corr(bp)
        spear = hp.corr(bp, method="spearman")
        read = "NEW sleeve" if pear < 0.5 else "base-redundant"
        print(f"{name:<18}{len(common):>8}{pear:>+11.3f}{spear:>+10.3f}{m['sharpe']:>+11.3f}  {read}")
    print("\nDecision rule: Pearson < ~0.5 -> new diversifying sleeve (forward-wall it); "
          ">= ~0.5 -> base momentum re-dressed (fold the insight into base). (measurement, no verdict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
