"""Stage-E block 3 — the daily paper cron: incremental merge + step-forward + resume (hermetic)."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pandas as pd

from nq.data.ohlcv import merge_ohlcv


def test_merge_ohlcv_appends_and_dedupes():
    idx = pd.to_datetime(["2026-06-01", "2026-06-02"])
    old = {"AAA": pd.DataFrame({"Close": [10.0, 11.0]}, index=idx)}
    new = {"AAA": pd.DataFrame({"Close": [11.5, 12.0]},                    # 06-02 overwritten, 06-03 new
                               index=pd.to_datetime(["2026-06-02", "2026-06-03"])),
           "BBB": pd.DataFrame({"Close": [5.0]}, index=pd.to_datetime(["2026-06-03"]))}
    m = merge_ohlcv(old, new)
    assert list(m["AAA"]["Close"]) == [10.0, 11.5, 12.0]                   # dedup keeps the new bar
    assert "BBB" in m and len(m["AAA"]) == 3


def _synth(n, seed, drift):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.02, n)))
    return pd.DataFrame({"Open": c * (1 + rng.normal(0, 0.003, n)), "High": c * 1.004,
                         "Low": c * 0.996, "Close": c,
                         "Volume": rng.integers(3_000_000, 5_000_000, n).astype(float)},
                        index=pd.bdate_range("2015-01-01", periods=n))


def test_paper_cron_steps_and_resumes(tmp_path, monkeypatch):
    tickers = [f"N{i:02d}" for i in range(14)]
    ohlcv = {t: _synth(700, i + 1, float(d)) for i, (t, d) in
             enumerate(zip(tickers, np.linspace(0.0004, 0.0016, 14)))}
    cache = tmp_path / "ohlcv.pkl"
    with open(cache, "wb") as f:
        pickle.dump(ohlcv, f)

    # inject a synthetic PIT fund store + no membership mask so the synthetic names form a valid panel
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [12.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in tickers}
    monkeypatch.setattr("nq.data.fundamentals.load_fund_store", lambda *a, **k: fund)
    monkeypatch.setattr("nq.data.membership.load_membership", lambda *a, **k: None)

    from scripts.run_paper_cron import main
    argv = ["--mode", "current", "--start", "2016-06-01", "--end", "2016-12-31",
            "--cache", str(cache), "--no-download", "--state-dir", str(tmp_path)]
    assert main(argv) == 0

    # state persisted + signals emitted
    port = json.loads((tmp_path / "paper_portfolio.json").read_text())
    hist = pd.read_csv(tmp_path / "portfolio_history.csv")
    sig = json.loads((tmp_path / "signals_today.json").read_text())
    assert len(hist) > 0 and "kill_state" in sig and sig["kill_state"]["mode"] == "observe"
    n_trades_1 = len(json.loads((tmp_path / "paper_trades.json").read_text()))
    n_hist_1 = len(hist)

    # RESUME with an unchanged window: must NOT re-process already-stepped sessions
    assert main(argv) == 0
    n_trades_2 = len(json.loads((tmp_path / "paper_trades.json").read_text()))
    assert len(pd.read_csv(tmp_path / "portfolio_history.csv")) == n_hist_1   # no duplicate sessions
    assert n_trades_2 == n_trades_1


def test_signal_issue_date_memory(tmp_path):
    """A name still pending from a prior run keeps its ORIGINAL issue date instead
    of being re-stamped `end` every run; past the buy window it re-issues fresh."""
    from scripts.run_paper_cron import _issue_date, _load_prev_signal_dates

    # carried while the 3-trading-day buy window is open (Thu 07-02 -> Fri 07-03)
    assert _issue_date({"MCX": "2026-07-02"}, "MCX", "2026-07-03") == "2026-07-02"
    # weekend does not consume the window (Thu 07-02 -> Tue 07-07 = 3 bdays)
    assert _issue_date({"MCX": "2026-07-02"}, "MCX", "2026-07-07") == "2026-07-02"
    # window expired -> re-issued fresh (Thu 07-02 -> Wed 07-08 = 4 bdays)
    assert _issue_date({"MCX": "2026-07-02"}, "MCX", "2026-07-08") == "2026-07-08"
    # not previously issued -> today
    assert _issue_date({}, "MCX", "2026-07-03") == "2026-07-03"
    # unparseable carried date -> today, never a crash
    assert _issue_date({"MCX": "garbage"}, "MCX", "2026-07-03") == "2026-07-03"

    # loader: envelope shape, bare-list shape, missing file
    sp = tmp_path / "signals_today.json"
    sp.write_text(json.dumps({"signals": [{"ticker": "MCX", "signal_date": "2026-07-02"}]}))
    assert _load_prev_signal_dates(tmp_path) == {"MCX": "2026-07-02"}
    sp.write_text(json.dumps([{"ticker": "SYRMA", "signal_date": "2026-07-01"}]))
    assert _load_prev_signal_dates(tmp_path) == {"SYRMA": "2026-07-01"}
    assert _load_prev_signal_dates(tmp_path / "nope") == {}
