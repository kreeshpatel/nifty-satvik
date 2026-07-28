"""Corrected-universe anchor harness — September item 1 runs THIS script in full; those numbers are
the memo of record. This session only smoke-tests the plumbing on a truncated window.

Runs BOTH books on pinned (survivor) vs corrected (pinned + backfill + aliases, the committed
`corrected_universe()` path) data via the existing harnesses, and emits the side-by-side anchor table
(Sharpe / CAGR / MaxDD / after-tax approx / per-year) plus the swing trade-level diff (recovered
delisted names). After-tax uses the standing 0114 approximation (annual positive returns haircut at
STCG 20.8%) — the September memo may refine via the full cost model.

    python scripts/run_corrected_anchor.py --smoke          # truncated window (plumbing proof)
    python scripts/run_corrected_anchor.py                  # full window (September's run of record)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, run_backtest  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest as swing_backtest  # noqa: E402
from run_bhanushali_weekly_rank import prep_weekly_rank  # noqa: E402

STCG = 0.208


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {}
    e = (1 + r).cumprod()
    yrs = len(r) / 252
    per_year = {int(y): round(((1 + g).cumprod().iloc[-1] - 1) * 100, 1)
                for y, g in r.groupby(r.index.year)}
    at = np.prod([1 + (v / 100 if v <= 0 else v / 100 * (1 - STCG)) for v in per_year.values()])
    return {"sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3),
            "cagr_%": round(float((e.iloc[-1] ** (1 / yrs) - 1) * 100), 2),
            "maxdd_%": round(float((e / e.cummax() - 1).min() * 100), 1),
            "aftertax_cagr_%": round(float(at ** (1 / yrs) - 1) * 100, 2),
            "per_year_%": per_year}


def lh_book(ohlcv, start, end) -> pd.Series:
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    return _daily_returns(run_backtest(panel, load_frozen_cfg(), start=start, end=end)["equity_curve"])


def swing_book(ohlcv, mem, start) -> tuple[pd.Series, pd.DataFrame]:
    led: list = []
    m = swing_backtest(prep_weekly_rank(ohlcv), mem, ledger=led, start=start)
    return m["ret"].dropna(), pd.DataFrame(led)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="truncated window: plumbing proof only")
    a = ap.parse_args()
    start, end = ("2019-01-01", "2021-12-31") if a.smoke else ("2017-01-01", "2026-06-30")
    tag = "SMOKE (truncated — NOT the record)" if a.smoke else "FULL (September's record)"
    print(f"=== corrected-universe anchor harness [{tag}] window {start}..{end} ===")
    mem = load_membership()
    pinned = load_ohlcv_cache(OHLCV_CACHE)
    corrected = corrected_universe()
    print(f"universes: pinned {len(pinned)} names | corrected {len(corrected)} names "
          f"(+{len(set(corrected) - set(pinned))} recovered)")

    rows = []
    for book, fn in (("LH base", lambda u: lh_book(u, start, end)),):
        for uni, oh in (("pinned", pinned), ("corrected", corrected)):
            rows.append({"book": book, "universe": uni, **metrics(fn(oh))})
            print(f"  {book} / {uni}: done")
    leds = {}
    for uni, oh in (("pinned", pinned), ("corrected", corrected)):
        r, led = swing_book(oh, mem, start)
        led = led[pd.to_datetime(led["entry_date"]) <= end] if len(led) else led
        r = r[r.index <= end]
        leds[uni] = led
        rows.append({"book": "swing base", "universe": uni, **metrics(r)})
        print(f"  swing base / {uni}: done ({len(led)} trades)")

    t = pd.DataFrame(rows)
    print("\n=== ANCHOR TABLE ===")
    print(t.drop(columns=["per_year_%"]).to_string(index=False))
    print("\nper-year:")
    for _, r0 in t.iterrows():
        print(f"  {r0['book']} / {r0['universe']}: {r0.get('per_year_%')}")

    # trade diff (swing): which trades exist only under the corrected universe (recovered names)
    if all(len(leds[u]) for u in leds):
        def keys(df):
            return set(zip(df["tkr"], pd.to_datetime(df["entry_date"]).dt.strftime("%G-%V")))
        only_corr = keys(leds["corrected"]) - keys(leds["pinned"])
        only_pin = keys(leds["pinned"]) - keys(leds["corrected"])
        rec_names = sorted({t_ for t_, _ in only_corr})
        print(f"\n=== TRADE DIFF (swing) ===")
        print(f"trades only in corrected: {len(only_corr)} | only in pinned: {len(only_pin)}")
        print(f"names driving the corrected-only trades (recovered/delisted + reshuffle): {rec_names[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
