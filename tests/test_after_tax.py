"""Tests for the STCG drag — :func:`nq.runner.research.after_tax_curve`.

The tax model had exactly one assertion before this file: that the field exists. It did not check
what the number MEANS, which is how it stayed in conflict with pre-registration 0001 §5.4 ("STCG is
applied at 20% inside the compounding") while doing something materially different — netting the
whole bill off the final value, so the tax money kept compounding until the last day.
"""
from __future__ import annotations

import pytest

from nq.engine.portfolio import elapsed_years
from nq.runner.research import _after_tax_cagr, after_tax_curve

CAP = 1_000_000.0


def _bt(rows, trades):
    return {"equity_curve": [{"date": d, "equity": e} for d, e in rows], "trades": trades}


def _trade(exit_date, pnl):
    return {"ticker": "X", "entry_date": "2018-01-01", "exit_date": exit_date, "pnl": pnl}


def test_no_gains_means_no_drag():
    bt = _bt([("2018-01-01", CAP), ("2018-12-31", CAP), ("2019-12-31", CAP)], [])
    assert [e["equity"] for e in after_tax_curve(bt)] == [CAP, CAP, CAP]


def test_a_losing_year_is_not_taxed():
    """Losses must not generate a bill. A tax model that taxes a loss would quietly make every
    drawdown worse and still look plausible in aggregate."""
    bt = _bt([("2018-01-01", CAP), ("2018-12-31", 900_000.0), ("2019-12-31", 900_000.0)],
             [_trade("2018-06-01", -100_000.0)])
    assert after_tax_curve(bt)[-1]["equity"] == pytest.approx(900_000.0)


def test_losses_offset_gains_within_the_same_year():
    bt = _bt([("2018-01-01", CAP), ("2018-12-31", CAP), ("2019-12-31", CAP)],
             [_trade("2018-03-01", 200_000.0), _trade("2018-09-01", -200_000.0)])
    assert after_tax_curve(bt)[-1]["equity"] == pytest.approx(CAP)


def test_the_drag_is_charged_at_the_year_boundary_not_before():
    """Tax on 2018's gains must not touch the 2018 curve — it is paid after the year closes."""
    bt = _bt([("2018-06-01", CAP), ("2018-12-31", 1_200_000.0), ("2019-06-01", 1_200_000.0)],
             [_trade("2018-06-01", 200_000.0)])
    c = after_tax_curve(bt)
    assert c[1]["equity"] == pytest.approx(1_200_000.0), "taxed inside the year it was earned"
    # 40,000 of tax on 1,200,000 = 3.333% drag carried forward
    assert c[2]["equity"] == pytest.approx(1_200_000.0 * (1 - 40_000.0 / 1_200_000.0))


def test_the_drag_compounds_and_this_is_the_whole_point():
    """THE test. Paying tax in year 1 removes capital that would otherwise have earned in years 2+.

    Two identical books, same total gain, same total tax — one realises it early, one late. The
    early realiser must end up POORER, because its tax stopped compounding sooner. A model that nets
    the bill off the final value cannot tell these apart, and reports both as identical.
    """
    curve = [("2018-01-01", CAP), ("2018-12-31", 2_000_000.0),
             ("2019-12-31", 4_000_000.0), ("2020-12-31", 8_000_000.0)]
    early = after_tax_curve(_bt(curve, [_trade("2018-06-01", 1_000_000.0)]))
    late = after_tax_curve(_bt(curve, [_trade("2020-06-01", 1_000_000.0)]))
    assert early[-1]["equity"] < late[-1]["equity"], \
        "realising a gain early cost nothing — the tax drag is not compounding"


def test_cagr_uses_the_compounded_curve_and_the_engine_year_convention():
    """Two things at once. The CAGR must come off the TAXED curve, and it must share a denominator
    with the engine's gross CAGR — otherwise their difference is not a tax cost.

    That denominator is now calendar time (`elapsed_years`), not sessions/252. The two conventions
    differ by 0.43pp on 0001, the same order as the effects being measured, so this asserts the
    shared function rather than a hardcoded rule — a future change to one cannot silently desync it
    from the other.
    """
    rows = [("2018-01-01", CAP), ("2018-12-31", 2_000_000.0), ("2019-12-31", 4_000_000.0)]
    bt = _bt(rows, [_trade("2018-06-01", 1_000_000.0)])
    # after-tax final = 4,000,000 x (1 - 200,000/2,000,000) = 3,600,000
    yrs = elapsed_years(bt["equity_curve"], len(rows))
    assert yrs == pytest.approx(729 / 365.25, rel=1e-9), "not annualising by calendar span"
    expected = ((3_600_000.0 / CAP) ** (1 / yrs) - 1) * 100
    assert _after_tax_cagr(bt, CAP) == round(expected, 3)      # the function's stated precision


def test_a_zero_rate_leaves_the_curve_alone():
    bt = _bt([("2018-01-01", CAP), ("2018-12-31", 2_000_000.0), ("2019-12-31", 3_000_000.0)],
             [_trade("2018-06-01", 1_000_000.0)])
    assert [e["equity"] for e in after_tax_curve(bt, stcg=0.0)] == [CAP, 2_000_000.0, 3_000_000.0]


def test_an_empty_backtest_returns_none_rather_than_a_number():
    assert after_tax_curve({"equity_curve": [], "trades": []}) is None
    assert _after_tax_cagr({"equity_curve": [], "trades": []}, CAP) is None
