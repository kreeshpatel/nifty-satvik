"""Closed-form correctness tests for :mod:`nq.engine.signal_book`.

Pattern copied from ``scripts/build_r94_golden_fixture.py``: a hermetic synthetic universe with
**no RNG, no clock, no network**, whose correct answer is derivable by hand. Five trade archetypes
are constructed deliberately so the fixture exercises every exit branch — a fixture that only ever
hits the time cap would not detect an exit-logic regression (``test_r94_golden`` learned this).

The cost arithmetic is **recomputed independently in the test** rather than read back from the
engine, so an error in the engine's fill/cost path shows up as a mismatch instead of agreeing with
itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.engine.portfolio import LEG_COST, _slip, base_risk_qty
from nq.engine.signal_book import SignalBookConfig, signals_from_arrays, simulate_signal_book

DATES = pd.bdate_range("2024-01-01", periods=40)
ADV = 1e9          # ₹100cr -> LARGE_CAP tier, and 0.5%-of-ADV impact never trips at these sizes
SLIP = _slip(ADV, 0.0)


def _flat(price: float, n: int = len(DATES)) -> dict[str, np.ndarray]:
    a = np.full(n, float(price))
    return {"open": a.copy(), "high": a.copy(), "low": a.copy(), "close": a.copy()}


def _panel() -> pd.DataFrame:
    """Five instruments, one per archetype. Entry signal on bar 5 -> fill at bar 6 open = 100."""
    book: dict[str, dict[str, np.ndarray]] = {}

    # WINNER — rises after entry; target (+2R on a 10-wide stop => 120) touched on bar 12.
    w = _flat(100.0)
    w["high"][12] = 125.0                  # high pierces the 120 target
    w["close"][12:] = 122.0
    book["WINNER"] = w

    # STOPPER — clean -1R: bar 9 trades through a 95 stop but OPENS above it, so fill == stop.
    s = _flat(100.0)
    s["open"][9], s["high"][9], s["low"][9], s["close"][9] = 96.0, 96.0, 94.0, 94.5
    book["STOPPER"] = s

    # GAPPER — same 95 stop, but bar 9 GAPS to 90: fill = min(open, stop) = 90 => worse than -1R.
    g = _flat(100.0)
    g["open"][9], g["high"][9], g["low"][9], g["close"][9] = 90.0, 90.5, 88.0, 89.0
    book["GAPPER"] = g

    # TIMER — never moves; exits on the max_hold backstop at the close.
    book["TIMER"] = _flat(100.0)

    # ABSENT — stops printing after bar 8 (delisted mid-trade); must force-close as "stale".
    book["ABSENT"] = _flat(100.0)

    rows = []
    for tkr, arr in book.items():
        n = len(DATES) if tkr != "ABSENT" else 9
        rows.append(pd.DataFrame({
            "date": DATES[:n], "ticker": tkr,
            "open": arr["open"][:n], "high": arr["high"][:n],
            "low": arr["low"][:n], "close": arr["close"][:n],
            "adv_rupees_20d": ADV,
        }))
    return pd.concat(rows, ignore_index=True)


def _signals() -> pd.DataFrame:
    spec = {"WINNER": (90.0, 2.0, 252), "STOPPER": (95.0, 2.0, 252), "GAPPER": (95.0, 2.0, 252),
            "TIMER": (90.0, 2.0, 5), "ABSENT": (90.0, 2.0, 252)}
    return pd.DataFrame([
        {"date": DATES[5], "ticker": t, "stop": st, "target_r": tr, "max_hold": mh, "priority": 0.0}
        for t, (st, tr, mh) in spec.items()])


def _run(**kw):
    cfg = SignalBookConfig(max_positions=10, risk_pct=2.0, max_position_pct=10.0, **kw)
    return simulate_signal_book(_panel(), _signals(), cfg=cfg, initial_capital=1_000_000.0)


@pytest.fixture(scope="module")
def result():
    return _run()


@pytest.fixture(scope="module")
def by_ticker(result):
    return {t["ticker"]: t for t in result["trades"]}


# --------------------------------------------------------------------------- the five archetypes
def test_every_exit_branch_is_exercised(by_ticker):
    """Guard the guard: the fixture must reach stop, target, time and stale, or it proves nothing."""
    assert {t["reason"] for t in by_ticker.values()} == {"target", "stop", "time", "stale"}


def test_entry_is_the_next_bar_never_the_signal_bar(by_ticker):
    """Lookahead check: a signal on bar 5 fills on bar 6."""
    for rec in by_ticker.values():
        assert rec["entry_date"] == str(DATES[6])[:10]


def test_winner_hits_target_at_exactly_two_r(by_ticker):
    rec = by_ticker["WINNER"]
    fill = 100.0 * (1 + SLIP)
    assert rec["reason"] == "target"
    assert rec["entry"] == pytest.approx(round(fill, 2))
    # target = fill + 2*(fill-90); bar high 125 exceeds it, so we fill AT the target
    assert rec["r"] == pytest.approx(2.0 * (1 - SLIP) - SLIP * (fill / (fill - 90.0)), abs=0.02)
    assert rec["r"] > 1.9


def test_stopper_is_a_clean_minus_one_r_before_costs(by_ticker):
    """Bar 9 opens ABOVE the stop, so the fill is the stop itself: gross R == -1."""
    rec = by_ticker["STOPPER"]
    assert rec["reason"] == "stop"
    fill = 100.0 * (1 + SLIP)
    gross_r = (95.0 - fill) / (fill - 95.0)
    assert gross_r == pytest.approx(-1.0)
    assert rec["r"] == pytest.approx(-1.0, abs=0.02)   # slippage on exit makes it a shade worse


def test_gapper_loses_more_than_one_r(by_ticker):
    """A gap through the stop fills at the open, not the stop — losses exceed 1R, as in life."""
    rec = by_ticker["GAPPER"]
    assert rec["reason"] == "stop"
    assert rec["r"] < -1.5, "gap-through fill must be worse than -1R"
    assert rec["exit"] == pytest.approx(round(90.0 * (1 - SLIP), 2))


def test_timer_exits_on_the_backstop_at_the_close(by_ticker):
    rec = by_ticker["TIMER"]
    assert rec["reason"] == "time"
    assert rec["days_held"] == 5


def test_absent_name_is_force_closed_not_held_forever(by_ticker):
    """B-1: a delisted name must not hold a slot indefinitely."""
    rec = by_ticker["ABSENT"]
    assert rec["reason"] == "stale"
    assert rec["exit_date"] > rec["entry_date"]


# --------------------------------------------------------------------------- cost / sizing arithmetic
def test_sizing_matches_base_risk_qty_independently(by_ticker):
    """Recompute the share count from the shared sizing kernel; the engine must agree."""
    fill = 100.0 * (1 + SLIP)
    expected = base_risk_qty(1_000_000.0, fill, fill - 90.0, ADV, 2.0,
                             max_position_pct=10.0)
    assert by_ticker["WINNER"]["qty"] == expected


def test_notional_cap_binds_not_the_risk_budget(by_ticker):
    """With a 10%-wide stop and a 2% risk budget the risk term wants 20% of equity, so the 10%
    notional cap decides the size. Pinned because it makes 'risk_pct' effectively inert."""
    fill = 100.0 * (1 + SLIP)
    risk_term = int(2.0 / 100.0 * 1_000_000.0 / (fill - 90.0))
    cap_term = int(10.0 / 100.0 * 1_000_000.0 / fill)
    assert cap_term < risk_term
    assert by_ticker["WINNER"]["qty"] == cap_term


def test_pnl_arithmetic_recomputed_by_hand(by_ticker):
    """P&L recomputes from the record to within the price-rounding bound — and no closer.

    ``entry``/``exit`` are stored rounded to 2dp (inherited from ``portfolio._book_exit``) while
    ``pnl`` is computed from the UNROUNDED fills. So hand-auditing a trade row reproduces its P&L
    only to about ``qty x 0.01``, not exactly. Pinned deliberately: someone recomputing a trade
    from an exported ledger will find a few-rupee gap and should know it is rounding, not a bug.
    """
    rec = by_ticker["STOPPER"]
    entry, exit_, qty = rec["entry"], rec["exit"], rec["qty"]
    expected = round(qty * (exit_ - entry) - (qty * exit_ + qty * entry) * LEG_COST, 2)
    bound = qty * 0.01 + 0.05          # half a paise per side per share, both legs
    assert rec["pnl"] == pytest.approx(expected, abs=bound)
    assert abs(rec["pnl"] - expected) > 0, "if this is exact, the record stopped rounding"


def test_impact_term_fires_on_a_large_position():
    """A position above 0.5% of ADV pays the extra 0.1% impact on BOTH legs.

    ``simulate`` prices entries in two passes — size at the tier rate, then re-price with impact
    once the notional is known. The parity fixture deliberately sizes below this threshold so its
    portfolio-free reference stays valid, so the term is exercised here instead.
    """
    thin = _panel().assign(adv_rupees_20d=1e6)      # Rs 1cr ADV -> 0.5% = Rs 5 lakh
    out = simulate_signal_book(thin, _signals(),
                               cfg=SignalBookConfig(max_positions=10, risk_pct=2.0,
                                                    max_position_pct=10.0,
                                                    max_adv_participation=1e9),
                               initial_capital=1_000_000.0)
    rec = {t["ticker"]: t for t in out["trades"]}["TIMER"]
    notional = rec["qty"] * rec["entry"]
    assert notional > 0.005 * 1e6, "fixture must exceed the impact threshold"
    # SMALL_CAP tier (0.40%) + impact (0.10%) = 0.50% per leg on a flat 100 price
    assert rec["entry"] == pytest.approx(100.0 * 1.005, rel=1e-4)


def test_both_legs_are_charged(by_ticker):
    """A round trip at an unchanged price must LOSE money — two legs of slippage + LEG_COST."""
    rec = by_ticker["TIMER"]
    assert rec["pnl"] < 0
    assert rec["return_pct"] < 0


# --------------------------------------------------------------------------- contract / structure
def test_returns_the_simulate_contract(result):
    """This is the whole point: evaluate_overlay only reads these three keys."""
    assert set(result) == {"equity_curve", "trades", "metrics"}
    assert {"date", "equity", "cash", "n_positions"} <= set(result["equity_curve"][0])
    m = result["metrics"]
    for k in ("cagr_pct", "sharpe", "max_drawdown_pct", "calmar", "turnover_per_year", "n_trades"):
        assert k in m, f"metrics missing {k} — evaluate_overlay's gates read it"


def test_equity_curve_is_continuous_and_cash_never_negative(result):
    eq = [e["equity"] for e in result["equity_curve"]]
    assert len(eq) == len(DATES)
    assert all(e["cash"] >= -1e-6 for e in result["equity_curve"]), "book must never borrow"


def test_slot_cap_binds():
    """With one slot, only the highest-priority signal fills."""
    sig = _signals().assign(priority=[5.0, 4.0, 3.0, 2.0, 1.0])
    out = simulate_signal_book(_panel(), sig, cfg=SignalBookConfig(max_positions=1),
                               initial_capital=1_000_000.0)
    assert max(e["n_positions"] for e in out["equity_curve"]) == 1


def test_signals_from_arrays_adapter():
    entry = np.zeros(len(DATES), dtype=bool)
    entry[[5, 20]] = True
    stop = np.full(len(DATES), 90.0)
    out = signals_from_arrays(DATES, "WINNER", entry, stop, target_r=2.0, max_hold=30)
    assert len(out) == 2
    assert list(out["date"]) == [DATES[5], DATES[20]]
    assert (out["max_hold"] == 30).all()


def test_empty_signals_is_a_flat_book():
    out = simulate_signal_book(_panel(), _signals().iloc[0:0], initial_capital=1_000_000.0)
    assert out["trades"] == []
    assert {e["equity"] for e in out["equity_curve"]} == {1_000_000.0}


def test_missing_panel_columns_raise():
    with pytest.raises(ValueError, match="missing columns"):
        simulate_signal_book(_panel().drop(columns=["high"]), _signals())
