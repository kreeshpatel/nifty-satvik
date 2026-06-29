"""F3 gate (hermetic) — the long-horizon scan + runner.

Pins selection (top-quantile non-held, free-slot fill, demerger quarantine), signal coherence
(stop < entry < target, sizing, grades), the live≡backtest indicative-entry math, and the
end-to-end runner writing a coherent signals_today.json. The ≤1pp reproduction of baseline_v0 is
a separate CLOUD gate (the local universe is a degenerate survivor subset)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from config import load_frozen_cfg
from nq.engine.portfolio import leg_slippage
from nq.runner.scan import run_scan
from nq.strategy.long_horizon import _grade, build_signal, scan

CFG = load_frozen_cfg()


def _panel(ranks: dict[str, float], *, as_of="2020-06-01") -> pd.DataFrame:
    """A one-date ranked panel: {ticker -> trend_rank}, with plausible price/atr/adv/slope/D-E."""
    rows = []
    for i, (tkr, rk) in enumerate(ranks.items()):
        rows.append({
            "date": pd.Timestamp(as_of), "ticker": tkr, "close": 100.0 + i,
            "atr_pct_63": 2.5, "adv_rupees_20d": 5e8, "sma200_slope_63": 10.0 * rk,
            "trend_rank": rk, "debt_equity": 0.3, "low_debt": -0.3, "roe": 15.0,
        })
    return pd.DataFrame(rows)


def test_grade_thresholds():
    assert _grade(0.99) == ("A", "HIGH")
    assert _grade(0.95) == ("B", "MEDIUM")
    assert _grade(0.50) == ("C", "LOW")


def test_scan_selects_top_quantile_non_held():
    # gate_quantile 0.5 -> rank >= 0.5 eligible; max_positions 15
    panel = _panel({"AAA": 1.00, "BBB": 0.80, "CCC": 0.60, "DDD": 0.40, "EEE": 0.20})
    sigs = scan(panel, CFG)
    picked = [s["ticker"] for s in sigs]
    assert picked == ["AAA", "BBB", "CCC"]          # rank>=0.5, best first; DDD/EEE below gate


def test_scan_excludes_held_and_fills_free_slots():
    panel = _panel({t: r for t, r in zip("ABCDE", [1.0, 0.9, 0.8, 0.7, 0.6])})
    sigs = scan(panel, {**CFG, "max_positions": 3}, held=["A"])   # 3 slots, 1 held -> 2 free
    picked = [s["ticker"] for s in sigs]
    assert "A" not in picked and picked == ["B", "C"]


def test_scan_quarantines_demerger_suspects():
    panel = _panel({"AAA": 1.00, "VEDL": 0.95, "CCC": 0.90})
    sigs = scan(panel, CFG, suspect=["VEDL"])
    assert "VEDL" not in [s["ticker"] for s in sigs]


def test_signal_levels_coherent_and_live_backtest_parity():
    panel = _panel({"AAA": 0.98})
    sig = scan(panel, CFG)[0]
    close, adv = 100.0, 5e8
    entry = close * (1 + leg_slippage(adv))          # the shared indicative-entry math
    assert sig["entry"] == round(entry, 2)
    assert sig["stop"] < sig["entry"] < sig["target"]
    assert sig["stop_pct"] > 0 and sig["target_pct"] > 0 and sig["rr"] > 0
    assert sig["target_pct"] == pytest.approx(CFG["target_pct"], abs=0.05)   # ~22.52%
    assert sig["grade"] == "A" and sig["max_hold_days"] == 63 and sig["min_hold_days"] == 10
    assert sig["shares"] >= 0 and sig["position_value"] == round(sig["shares"] * sig["entry"], 0)


def test_build_signal_zero_adv_safe():
    row = {"ticker": "X", "close": 100.0, "atr_pct_63": 2.0, "adv_rupees_20d": 0.0,
           "sma200_slope_63": 5.0, "trend_rank": 0.99, "debt_equity": 0.2}
    sig = build_signal(row, CFG, equity=1_000_000.0, signal_date="2020-06-01")
    assert sig["shares"] >= 0 and sig["rr"] > 0          # zero ADV doesn't crash; levels coherent


def _synth_ohlcv(n, seed, drift):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    high, low = close * 1.004, close * 0.996
    open_ = close * (1 + rng.normal(0, 0.003, n))
    vol = rng.integers(3_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": vol},
                        index=pd.bdate_range("2015-01-01", periods=n))


def test_run_scan_end_to_end_writes_signals_json(tmp_path):
    from datetime import date

    ohlcv = {"AAA": _synth_ohlcv(400, 1, 0.0012), "BBB": _synth_ohlcv(400, 2, 0.0004)}
    fund = {t: pd.DataFrame({"debt_equity": [0.3], "roe": [15.0]},
                            index=pd.to_datetime(["2014-06-01"])) for t in ohlcv}
    # a synthetic membership covering the window (the default None loads the real Nifty-500 file,
    # which would correctly drop these never-member synthetic tickers)
    membership = {t: [(date(2014, 1, 1), date(2030, 12, 31))] for t in ohlcv}
    out = tmp_path / "signals_today.json"
    run_scan(ohlcv=ohlcv, membership=membership, fund_store=fund, out_path=out)
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["as_of"] and on_disk["n_signals"] == len(on_disk["signals"]) >= 1
    for s in on_disk["signals"]:
        assert s["strategy"] == "LONG_HORIZON" and s["stop"] < s["entry"] < s["target"]
        assert s["entry_is_indicative"] is True


def test_run_scan_no_ohlcv_is_safe(tmp_path):
    out = tmp_path / "signals_today.json"
    res = run_scan(ohlcv={}, out_path=out)
    assert res["n_signals"] == 0 and out.exists()
