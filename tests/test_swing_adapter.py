"""The swing book's translation into the adjudicable contract.

`adjudicate` is engine-agnostic but the weekly-swing book never reached it: `backtest` returns
`curve` as a Series and `trades` as a COUNT, so six diagnostics each hand-rolled their own `stats()`.
This adapter is the one translation layer, and the tests that matter are the ones that would let a
WRONG translation look right:

* metrics are RE-DERIVED from the curve rather than forwarded, so a parity test against the engine is
  a real check rather than a tautology;
* a ledger row with no `net_pnl` is dropped, not zero-filled — `adjudicate` charges STCG on positive
  pnl, so a phantom zero understates tax on a book whose after-tax CAGR is a promotion gate;
* Calmar on a zero-drawdown curve is NaN, not infinity, because an infinity wins every gate.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from nq.engine.swing_adapter import TURNOVER_UNITS, to_adjudicable


def _curve(vals, start="2019-01-01"):
    return pd.Series(vals, index=pd.bdate_range(start, periods=len(vals)))


def _bt(vals, **kw):
    e = _curve(vals)
    yrs = max((e.index[-1] - e.index[0]).days / 365.25, 1e-9)
    return {"curve": e, "cagr": (vals[-1] / vals[0]) ** (1 / yrs) - 1,
            "dd": float((e / e.cummax() - 1).min()), "trades": kw.pop("trades", 0),
            "sharpe": 1.0, "tpy": 0.0, "skipped_cash": kw.pop("skipped_cash", 0), **kw}


def _led(n, pnl=1000.0, exit_date="2019-03-01"):
    return [{"tkr": f"T{i}", "exit_date": exit_date, "net_pnl": pnl, "R": 1.0, "reason": "targets"}
            for i in range(n)]


# --------------------------------------------------------------------------- the contract
def test_it_emits_exactly_the_three_keys_adjudicate_reads():
    out = to_adjudicable(_bt([1e6, 1.1e6, 1.2e6]), _led(2))
    assert {"equity_curve", "trades", "metrics"} <= set(out)
    assert set(out["equity_curve"][0]) == {"date", "equity"}
    assert {"exit_date", "pnl"} <= set(out["trades"][0])
    assert {"calmar", "turnover_per_year"} <= set(out["metrics"])


def test_the_native_result_is_carried_through_untouched():
    bt = _bt([1e6, 1.2e6])
    out = to_adjudicable(bt, _led(1))
    assert out["native"]["sharpe"] == bt["sharpe"]


def test_an_empty_curve_does_not_raise():
    out = to_adjudicable({"curve": pd.Series(dtype=float), "cagr": 0, "dd": 0, "trades": 0}, [])
    assert out["equity_curve"] == [] and out["trades"] == []
    assert math.isnan(out["metrics"]["sharpe"])


# --------------------------------------------------------------------------- re-derivation
def test_metrics_are_recomputed_from_the_curve_not_forwarded():
    """If the adapter forwarded the engine's own numbers, a parity test would be a tautology."""
    bt = _bt([1e6, 2e6])
    bt["cagr"] = 999.0                      # a value the curve cannot support
    bt["dd"] = -0.99
    out = to_adjudicable(bt, _led(1))
    assert out["metrics"]["cagr"] != pytest.approx(999.0)
    assert out["metrics"]["max_drawdown"] == pytest.approx(0.0), "this curve never drew down"


def test_drawdown_and_calmar_match_a_hand_computation():
    vals = [100.0, 120.0, 60.0, 90.0]        # peak 120 -> trough 60 = -50%
    out = to_adjudicable(_bt(vals), _led(1))
    m = out["metrics"]
    assert m["max_drawdown"] == pytest.approx(-0.5, abs=1e-9)
    assert m["calmar"] == pytest.approx(m["cagr"] / 0.5, rel=1e-9)


def test_calmar_on_a_flat_curve_is_nan_not_infinity():
    """An infinite Calmar wins every gate it is compared on."""
    out = to_adjudicable(_bt([100.0, 101.0, 102.0]), _led(1))
    assert math.isnan(out["metrics"]["calmar"])


# --------------------------------------------------------------------------- trades / tax
def test_a_row_without_net_pnl_is_dropped_rather_than_zero_filled():
    led = _led(2) + [{"tkr": "X", "exit_date": "2019-03-01", "net_pnl": None},
                     {"tkr": "Y", "exit_date": "2019-03-01", "net_pnl": float("nan")}]
    out = to_adjudicable(_bt([1e6, 1.1e6]), led)
    assert len(out["trades"]) == 2, "a phantom zero would understate STCG on the after-tax gate"


def test_n_trades_prefers_the_ledger_and_falls_back_to_the_count():
    assert to_adjudicable(_bt([1e6, 1.1e6], trades=99), _led(3))["metrics"]["n_trades"] == 3
    assert to_adjudicable(_bt([1e6, 1.1e6], trades=99), None)["metrics"]["n_trades"] == 99


def test_exit_dates_are_normalised_to_iso_days():
    out = to_adjudicable(_bt([1e6, 1.1e6]), [
        {"tkr": "A", "exit_date": pd.Timestamp("2019-03-01 15:30"), "net_pnl": 1.0}])
    assert out["trades"][0]["exit_date"] == "2019-03-01"


# --------------------------------------------------------------------------- the unit trap
def test_turnover_is_labelled_as_trades_per_year_not_notional():
    """adjudicate's gate is named `turnover_le_30pct`. On the momentum engine that is NOTIONAL
    turnover; this book cannot compute that, so the payload must disambiguate or a reader compares
    two different quantities across engines and concludes nothing."""
    m = to_adjudicable(_bt([1e6, 1.1e6]), _led(5))["metrics"]
    assert m["turnover_units"] == TURNOVER_UNITS == "trades_per_year"
    assert m["turnover_per_year"] > 0


def test_turnover_per_year_is_trades_over_elapsed_years():
    vals = list(np.linspace(1e6, 1.2e6, 261))          # ~1 business year
    out = to_adjudicable(_bt(vals), _led(10))
    yrs = (pd.to_datetime(out["equity_curve"][-1]["date"])
           - pd.to_datetime(out["equity_curve"][0]["date"])).days / 365.25
    assert out["metrics"]["turnover_per_year"] == pytest.approx(10 / yrs, rel=1e-6)


# --------------------------------------------------------------------------- adjudicate accepts it
def test_adjudicate_consumes_the_adapter_output():
    """The whole point: the swing book reaching the seven-gate bar without a hand-rolled stats()."""
    from nq.runner.research import adjudicate

    rng = np.random.default_rng(0)
    base = 1e6 * np.cumprod(1 + rng.normal(0.0004, 0.01, 400))
    cand = 1e6 * np.cumprod(1 + rng.normal(0.0006, 0.01, 400))
    a = to_adjudicable(_bt(list(base), trades=50), _led(50, exit_date="2019-06-03"))
    b = to_adjudicable(_bt(list(cand), trades=55), _led(55, exit_date="2019-06-03"))
    res = adjudicate(a, b, n_trials=2, n_samples=200)
    assert "verdict" in res and "gates" in res
    assert res["verdict"] in ("PROMOTE-CANDIDATE", "UNDERPOWERED", "KILL")


# --------------------------------------------------------------------------- parity with the record
#
# The load-bearing test. `build_substrate.guard()` pins the frozen 0094 book at Sharpe 1.132 / 255
# trades on the CORRECTED universe (pin + backfill + aliases) — not the live cache, which is a
# different universe and reproduces neither number. Because the adapter RE-DERIVES its metrics from
# the curve rather than forwarding the engine's, agreement here is evidence rather than a tautology.
_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
_NEEDS_DATA = not (_ROOT / "data" / "ohlcv.pkl").exists()


@pytest.mark.skipif(_NEEDS_DATA, reason="pinned OHLCV cache absent (gitignored; not on CI)")
def test_the_adapter_reproduces_the_frozen_0094_run_of_record():
    import sys

    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "scripts"))
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_path1 import corrected_universe

    led: list = []
    bt = R94.backtest(R94.prep_weekly_rank(corrected_universe()), load_membership(),
                      ledger=led, start="2017-01-01")
    out = to_adjudicable(bt, led)
    m = out["metrics"]

    assert m["n_trades"] == 255, "the adapter changed the book's trade count"
    assert m["sharpe"] == pytest.approx(1.132, abs=0.01), "re-derived Sharpe left the record"
    assert m["sharpe"] == pytest.approx(bt["sharpe"], abs=1e-6), "re-derivation disagrees with engine"
    assert len(out["trades"]) == 255, "a trade lost its net_pnl and was dropped from the tax leg"
    assert len(out["equity_curve"]) > 2000 and out["equity_curve"][0]["equity"] > 0
