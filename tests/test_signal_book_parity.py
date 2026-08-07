"""Two-engine parity — the strongest bug detector available to us.

The repo already holds this standard: ``tests/test_stagee_paper_parity.py`` requires ``PaperBook``,
stepped day-by-day, to be BYTE-IDENTICAL to ``simulate``. The same discipline is applied here.

The reference implementation below is written **deliberately differently** from
:func:`nq.engine.signal_book.simulate_signal_book`:

  * the engine walks a **calendar day loop** holding a portfolio of open positions;
  * the reference walks **one trade at a time**, scanning forward from each entry until an exit
    condition fires, with no portfolio state at all.

Two algorithms, one answer. Agreement is meaningful precisely because a shared bug is unlikely to
survive that difference in structure — which is what a single-engine test can never tell you.

**What is compared, and why not everything.** Entry/exit dates, fill prices, exit reason, hold
length and R are fully determined by the price path, the signal and the rules — they do not depend
on position size. Share counts and P&L additionally depend on equity at entry, which is inherently
a portfolio-loop quantity; those are pinned separately against the shared sizing kernel in
``tests/test_signal_book.py::test_sizing_matches_base_risk_qty_independently``. Comparing the
path-determined fields is therefore the sharpest available test of the entry/exit logic, which is
where the bugs actually live.

The fixture deliberately leaves slots and cash non-binding so the two engines are comparable; a
separate test asserts that they DIVERGE once the slot cap binds, proving the comparison is live
rather than vacuously true.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nq.engine.portfolio import _slip
from nq.engine.signal_book import SignalBookConfig, simulate_signal_book

N_BARS = 220
# Deliberately enormous ADV (Rs 1000cr). The 0.5%-of-ADV market-impact term then never fires at
# these position sizes, so per-leg slippage is the flat tier rate and the reference can price a
# fill WITHOUT knowing the share count — which is what keeps it portfolio-free. The impact term is
# a portfolio-dependent quantity and is tested separately, in
# tests/test_signal_book.py::test_impact_term_fires_on_a_large_position.
ADV = 1e11
COMPARED = ("ticker", "entry_date", "exit_date", "entry", "exit", "reason", "days_held", "r")


def _paths() -> dict[str, pd.DataFrame]:
    """Twelve deterministic instruments — trend x sine x sawtooth, phase-shifted per name.

    No RNG, no clock, no network. The phase spread guarantees a mix of stops, targets and time
    exits across the book rather than one archetype repeated.
    """
    idx = pd.bdate_range("2024-01-02", periods=N_BARS)
    out = {}
    for k in range(12):
        t = np.arange(N_BARS, dtype=float)
        drift = 0.0009 * (1 if k % 3 else -1) * (1 + k % 4)
        c = 100.0 * np.exp(drift * t) * (1 + 0.05 * np.sin(2 * np.pi * (t + 7 * k) / (31 + k)))
        hi = c * (1 + 0.012 + 0.004 * np.cos((t + k) / 6.0))
        lo = c * (1 - 0.012 - 0.004 * np.sin((t + k) / 8.0))
        op = np.concatenate([[c[0]], c[:-1] * (1 + 0.002 * np.cos((t[:-1] + k) / 4.0))])
        op = np.clip(op, lo, hi)                       # keep OHLC internally consistent
        out[f"SYN{k:02d}"] = pd.DataFrame(
            {"open": op, "high": hi, "low": lo, "close": c, "adv_rupees_20d": ADV}, index=idx)
    return out


def _panel(paths) -> pd.DataFrame:
    return pd.concat(
        [df.reset_index(names="date").assign(ticker=t) for t, df in paths.items()],
        ignore_index=True)[["date", "ticker", "open", "high", "low", "close", "adv_rupees_20d"]]


MAX_HOLD = 40
SIGNAL_EVERY = 45          # > MAX_HOLD, so two signals on one name can never overlap


def _signals(paths, every: int = SIGNAL_EVERY) -> pd.DataFrame:
    """A signal every `every` bars per name; stop 8% below the signal close; 2R target.

    ``every > MAX_HOLD`` is load-bearing: the engine enforces one position per ticker while the
    reference has no portfolio at all, so overlapping same-name signals would diverge for a reason
    that is a book rule rather than an exit-logic bug. Spacing them apart keeps the reference
    genuinely portfolio-free instead of teaching it engine state.
    ``test_signals_cannot_overlap`` enforces this premise rather than trusting it.
    """
    rows = []
    for t, df in paths.items():
        for i in range(60, N_BARS - 2, every):
            rows.append({"date": df.index[i], "ticker": t,
                         "stop": float(df["close"].iloc[i]) * 0.92,
                         "target_r": 2.0, "max_hold": MAX_HOLD, "priority": float(i)})
    return pd.DataFrame(rows)


def _reference_trades(paths, signals, cfg: SignalBookConfig) -> list[dict]:
    """INDEPENDENT implementation: per-trade forward scan, no portfolio, no calendar loop.

    Mirrors the documented rules only — signal fires at bar i, entry at bar i+1's open plus one
    leg of slippage; then scan forward taking, in order: stop (gap-aware, fill at min(open, stop)),
    target (fill at max(open, target)), then the max-hold backstop at the close.

    **The entry bar is not an exit candidate.** The engine's management pass runs before its fill
    pass, so a position opened at bar j is first evaluated at j+1 and ``days_held`` counts ELAPSED
    sessions. That is ``simulate``'s convention ("positions filled today are skipped; aging is one
    elapsed session"), so the reference scans from j+1 with ``held = k - j``. Getting this wrong
    was the first thing this parity test caught.
    """
    slip = _slip(ADV, 0.0)
    recs = []
    for _, s in signals.iterrows():
        df = paths[s["ticker"]]
        loc = df.index.get_loc(s["date"])
        j = loc + 1
        if j >= len(df):
            continue
        entry = float(df["open"].iloc[j]) * (1 + slip)
        stop = float(s["stop"])
        if entry <= stop:
            continue
        r_unit = entry - stop
        target = entry + float(s["target_r"]) * r_unit
        for k in range(j + 1, min(len(df), j + int(s["max_hold"]) + 1)):
            held = k - j
            lo, hi, op, cl = (float(df[c].iloc[k]) for c in ("low", "high", "open", "close"))
            if lo <= stop:
                px, reason = min(op, stop), "stop"
            elif hi >= target:
                px, reason = max(op, target), "target"
            elif held >= int(s["max_hold"]):
                px, reason = cl, "time"
            else:
                continue
            fill = px * (1 - slip)
            recs.append({"ticker": s["ticker"], "entry_date": str(df.index[j])[:10],
                         "exit_date": str(df.index[k])[:10], "entry": round(entry, 2),
                         "exit": round(fill, 2), "reason": reason, "days_held": held,
                         "r": round((fill - entry) / r_unit, 4)})
            break
    return recs


@pytest.fixture(scope="module")
def fixture():
    paths = _paths()
    return paths, _panel(paths), _signals(paths)


def test_two_engines_agree_trade_for_trade(fixture):
    """The parity gate. Different algorithms, identical path-determined outcomes."""
    paths, panel, signals = fixture
    cfg = SignalBookConfig(max_positions=99, risk_pct=0.05, max_position_pct=0.5)
    engine = simulate_signal_book(panel, signals, cfg=cfg, initial_capital=5_000_000_000.0)
    ref = _reference_trades(paths, signals, cfg)

    a = pd.DataFrame(engine["trades"])[list(COMPARED)].sort_values(
        ["ticker", "entry_date"]).reset_index(drop=True)
    b = pd.DataFrame(ref)[list(COMPARED)].sort_values(
        ["ticker", "entry_date"]).reset_index(drop=True)
    assert len(a) >= 40, "fixture must generate a meaningful number of trades"
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_signals_cannot_overlap(fixture):
    """Enforce the premise that makes the portfolio-free reference valid."""
    _, _, signals = fixture
    assert SIGNAL_EVERY > MAX_HOLD
    for t, g in signals.groupby("ticker"):
        gaps = g["date"].sort_values().diff().dropna().dt.days
        assert (gaps > MAX_HOLD).all(), f"{t} has signals closer together than max_hold"


def test_the_fixture_exercises_every_branch(fixture):
    """Guard the guard: parity over a fixture that only ever stops out proves little."""
    paths, panel, signals = fixture
    cfg = SignalBookConfig(max_positions=99, risk_pct=0.05, max_position_pct=0.5)
    reasons = {t["reason"] for t in simulate_signal_book(
        panel, signals, cfg=cfg, initial_capital=5_000_000_000.0)["trades"]}
    assert {"stop", "target", "time"} <= reasons, f"fixture too tame: only {reasons}"


def test_slots_cash_and_impact_do_not_bind_in_the_parity_fixture(fixture):
    """The reference has no portfolio, so parity is only meaningful when constraints are slack.

    All three premises are asserted, not assumed: free slots, positive cash, and every position's
    notional below the 0.5%-of-ADV impact threshold.
    """
    _, panel, signals = fixture
    cfg = SignalBookConfig(max_positions=99, risk_pct=0.05, max_position_pct=0.5)
    out = simulate_signal_book(panel, signals, cfg=cfg, initial_capital=5_000_000_000.0)
    assert max(e["n_positions"] for e in out["equity_curve"]) < 99
    assert min(e["cash"] for e in out["equity_curve"]) > 0
    biggest = max(t["qty"] * t["entry"] for t in out["trades"])
    assert biggest < 0.005 * ADV, "impact term would fire — reference could not price the fill"


def test_entry_bar_is_never_an_exit_candidate():
    """Pin the elapsed-session convention: a stop breached ON the entry bar does not fire.

    The engine manages positions before it fills them, matching ``simulate``. So a name that opens
    at 100 and craters to 80 the same day is NOT stopped that day — it is stopped at the next bar.
    This is a real optimism in the model and it is inherited deliberately from the engine of
    record; pinned here so it stays a decision rather than becoming an accident.
    """
    idx = pd.bdate_range("2024-01-02", periods=6)
    df = pd.DataFrame({"open": [100.0] * 6, "high": [101.0] * 6,
                       "low": [100.0, 100.0, 80.0, 80.0, 80.0, 80.0],
                       "close": [100.0, 100.0, 85.0, 85.0, 85.0, 85.0],
                       "adv_rupees_20d": ADV}, index=idx)
    panel = df.reset_index(names="date").assign(ticker="X")[
        ["date", "ticker", "open", "high", "low", "close", "adv_rupees_20d"]]
    # signal on bar 1 -> entry bar 2, whose OWN low (80) is already below the 90 stop
    sig = pd.DataFrame([{"date": idx[1], "ticker": "X", "stop": 90.0,
                         "target_r": np.nan, "max_hold": 10, "priority": 0.0}])
    out = simulate_signal_book(panel, sig, cfg=SignalBookConfig(max_positions=1),
                               initial_capital=1_000_000.0)
    rec = out["trades"][0]
    assert rec["entry_date"] == str(idx[2])[:10]
    assert rec["exit_date"] == str(idx[3])[:10], "exit must be the bar AFTER entry, not entry itself"
    assert rec["days_held"] == 1


def test_parity_breaks_when_the_slot_cap_binds(fixture):
    """Proves the comparison is LIVE — a capped book must NOT match the uncapped reference.

    Without this, a parity test that always passes is indistinguishable from one that compares
    nothing.
    """
    paths, panel, signals = fixture
    capped = simulate_signal_book(panel, signals, cfg=SignalBookConfig(max_positions=2),
                                  initial_capital=1_000_000.0)
    ref = _reference_trades(paths, signals, SignalBookConfig())
    assert len(capped["trades"]) < len(ref), "slot cap must refuse fills the reference takes"
