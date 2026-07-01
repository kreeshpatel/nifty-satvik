"""Stage E — paper-book PARITY gate: the paper book must equal the validated backtest.

The non-negotiable correctness property before real capital: PaperBook stepped day-by-day over a panel
produces BYTE-IDENTICAL trades + metrics to nq.engine.portfolio.simulate — with the vol-target off AND
on — and it is cron-RESUMABLE (save/load mid-run reproduces a single full run). Hermetic."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.data.features import compute_all_features
from nq.engine.panel import compose_ranked_panel
from nq.engine.portfolio import simulate
from nq.paper.book import PaperBook

CFG = load_frozen_cfg()
VT = {"vol_target_annual": 0.05, "vol_window": 42, "vol_floor": 0.40}   # low target -> engages on synth


def _panel():
    def synth(n, seed, drift):
        rng = np.random.default_rng(seed)
        c = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.02, n)))
        return pd.DataFrame({"Open": c * (1 + rng.normal(0, 0.003, n)), "High": c * 1.004,
                             "Low": c * 0.996, "Close": c,
                             "Volume": rng.integers(3_000_000, 5_000_000, n).astype(float)},
                            index=pd.bdate_range("2015-01-01", periods=n))
    ohlcv = {f"N{i:02d}": synth(600, i + 1, float(d)) for i, d in enumerate(np.linspace(0.0004, 0.0016, 14))}
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [12.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    return compose_ranked_panel(compute_all_features(ohlcv, holidays=set()), ohlcv,
                                fund_store=fund, membership=None)


def _ledger(res):
    return [(t["ticker"], t["entry_date"], t["exit_date"], t["qty"], t["entry"], t["exit"], t["pnl"])
            for t in res["trades"]]


def test_paper_parity_vol_target_off():
    p = _panel()
    bt = simulate(p, CFG)
    book = PaperBook(CFG).run_batch(p)
    assert _ledger(book) == _ledger(bt)                       # byte-identical trade ledger
    assert book["metrics"] == bt["metrics"]                   # and identical metrics


def test_paper_parity_vol_target_on():
    p = _panel()
    bt = simulate(p, CFG, vol_target=VT)
    book = PaperBook(CFG, vol_target=VT).run_batch(p)
    assert _ledger(book) == _ledger(bt)                       # parity holds with the overlay on too


def test_paper_book_is_cron_resumable(tmp_path):
    # a book run in two halves (save/load between) must equal a single full run
    p = _panel().copy()
    p["date"] = pd.to_datetime(p["date"])
    dates = sorted(p["date"].unique())
    mid = dates[len(dates) // 2]
    full = PaperBook(CFG).run_batch(p)

    b1 = PaperBook(CFG)
    for d, g in p[p["date"] <= mid].groupby("date", sort=True):
        b1.step(d, g.set_index("ticker"))
    b1.save(tmp_path)

    b2 = PaperBook(CFG); b2.load(tmp_path)
    for d, g in p[p["date"] > mid].groupby("date", sort=True):
        b2.step(d, g.set_index("ticker"))
    assert _ledger({"trades": b2.trades}) == _ledger(full)    # resumed run == single run
