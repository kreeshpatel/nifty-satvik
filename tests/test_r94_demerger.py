"""B′ — a demerger on a held position (owner decision 2026-09-15, standing rule).

The live book prices positions on RAW closes. On 2026-09-07 HEG demerged (728.25 -> 272.20), and the book
compared the post-demerger price with its pre-demerger stop: a pending full stop exit, −6.55R and
−₹1,30,831 on the paper book, for value that had in fact been handed to the holder as new shares.

B′ realises the carved-out slice at its market-implied value on the ex-date and carries the remaining
shares re-based. These tests pin it on the engine that actually runs, using the hermetic R94 golden
fixture (closed-form prices, no network):

  * THE DEFECT — inject a demerger cliff into a real held trade: without B′ it stops out early below −1R.
  * EXACTNESS — with B′ the trade is, to machine precision, the original trade with (1 − k) of its
    remaining exposure closed at the prior close: same exit date, same exit reason, and
    R = realised_before + f·(1 − k)·R_prior + k·(R_original − realised_before).
    Mutation-checked on 2026-09-15, and the result corrected this docstring: it is the BEFORE-tranche
    case (INDIG, whose tranches fire after the ex-date) that proves the tranche weighting; removing it
    fails only that test. The after-tranche case (HOTEL) proves exactness on a partly-booked position
    (realised_before > 0, f < 1). Removing the adjusted view fails both; disabling the hook fails both.
  * INTEGRITY — a series the vendor already back-adjusted is left alone; a ratio that matches neither
    the registered cliff nor a continuous series is refused.
  * HEG — `_apply_demerger` reproduces the figures the owner approved.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from build_r94_golden_fixture import START_FIX, synth_universe  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT  # noqa: E402

K = 0.4   # value retained by the listed entity in the synthetic demerger


# --------------------------------------------------------------------------- harness
@pytest.fixture(scope="module")
def base():
    ohlcv, index = synth_universe()
    led = _run(ohlcv, index)
    return ohlcv, index, led


def _run(ohlcv, index, events=None):
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    led: list[dict] = []
    R94.backtest(P, None, ledger=led, start=START_FIX, return_state=True, uncapped=True,
                 **LIVE_DISCIPLINE, **LIVE_EXIT, demerger_events=events)
    return led


def _trade(led, tkr, entry_date):
    hits = [r for r in led if r["tkr"] == tkr and pd.Timestamp(r["entry_date"]) == pd.Timestamp(entry_date)]
    assert len(hits) == 1, f"expected one {tkr} trade entered {entry_date}, found {len(hits)}"
    return hits[0]


def _cliff(ohlcv, tkr, ex, k=K):
    out = dict(ohlcv)
    df = ohlcv[tkr].copy()
    post = df.index >= ex
    for col in ("Open", "High", "Low", "Close"):
        df.loc[post, col] = df.loc[post, col] * k
    out[tkr] = df
    return out


def _quiet_day(ohlcv, tkr, after, before):
    """A session strictly inside (after, before) whose own close-to-close move is smallest, so the
    registered ratio can equal the true factor k without tripping the integrity tolerance."""
    c = ohlcv[tkr]["Close"]
    moves = (c / c.shift(1) - 1.0).abs()
    window = moves[(moves.index > pd.Timestamp(after)) & (moves.index < pd.Timestamp(before))].dropna()
    assert len(window), f"no session inside ({after}, {before}) for {tkr}"
    day = window.idxmin()
    assert window[day] < 0.005, f"quietest session still moved {window[day]:.3%}"
    return day


def _events(ohlcv, index, tkr, ex, retained=K):
    return R94.build_demerger_events(ohlcv, [(tkr, ex, retained)], index_provider=lambda _t: index)


# --------------------------------------------------------------------------- the defect
def test_without_bprime_a_demerger_stops_a_held_trade_out(base):
    ohlcv, index, led0 = base
    orig = _trade(led0, "INDIG", "2017-12-18")
    ex = _quiet_day(ohlcv, "INDIG", orig["entry_date"], orig["half_date"])
    hit = _trade(_run(_cliff(ohlcv, "INDIG", ex), index), "INDIG", "2017-12-18")
    assert pd.Timestamp(hit["exit_date"]) < pd.Timestamp(orig["exit_date"]), "the cliff did not end the trade early"
    assert "stop" in hit["reason"], f"expected a stop exit, got {hit['reason']}"
    assert hit["R"] < -1.0, f"the demerger should read as a loss beyond the stop, got R {hit['R']}"


# --------------------------------------------------------------------------- exactness
def test_bprime_before_any_tranche_is_the_original_trade_minus_a_slice(base):
    ohlcv, index, led0 = base
    orig = _trade(led0, "INDIG", "2017-12-18")
    ex = _quiet_day(ohlcv, "INDIG", orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, "INDIG", ex)
    got = _trade(_run(cl, index, _events(cl, index, "INDIG", ex)), "INDIG", "2017-12-18")

    assert got["exit_date"] == orig["exit_date"] and got["reason"] == orig["reason"]
    prior = float(ohlcv["INDIG"]["Close"][ohlcv["INDIG"].index < ex].iloc[-1])
    r_prior = (prior - orig["entry"]) / (orig["entry"] - orig["stop0"])
    want = (1 - K) * r_prior + K * orig["R"]
    assert got["R"] == pytest.approx(want, abs=2e-3)          # rec R is rounded to 3 dp
    note = got["corporate_actions"][0]
    assert note["kind"] == "demerger" and note["retained"] == pytest.approx(K)
    assert note["credit"] == pytest.approx(note["shares"] * prior * (1 - K), rel=1e-6)


def test_bprime_on_a_partly_booked_position_keeps_what_was_already_banked(base, monkeypatch):
    """HOTEL booked its first tranche before the ex-date, so realised R is already non-zero and less
    than the whole position remains. B′ must slice only what is still held and leave the banked part
    untouched. (The tranche-weighting fix is proven by the INDIG test above — see the module docstring.)"""
    ohlcv, index, led0 = base
    orig = _trade(led0, "HOTEL", "2017-11-13")
    ex = _quiet_day(ohlcv, "HOTEL", orig["half_date"], orig["exit_date"])
    cl = _cliff(ohlcv, "HOTEL", ex)

    seen: dict = {}
    real = R94._apply_demerger

    def spy(p, s, i, d, ev):
        seen.update(rb=p["realized_r"], f=p["frac_left"], en=p["en"], risk0=p["risk0"], prior=float(s["c"][i - 1]))
        return real(p, s, i, d, ev)

    monkeypatch.setattr(R94, "_apply_demerger", spy)
    got = _trade(_run(cl, index, _events(cl, index, "HOTEL", ex)), "HOTEL", "2017-11-13")
    assert seen, "the demerger hook never fired on a position held into the ex-date"
    assert got["exit_date"] == orig["exit_date"] and got["reason"] == orig["reason"]
    r_prior = (seen["prior"] - seen["en"]) / seen["risk0"]
    want = seen["rb"] + seen["f"] * (1 - K) * r_prior + K * (orig["R"] - seen["rb"])
    assert got["R"] == pytest.approx(want, abs=2e-3)


# --------------------------------------------------------------------------- integrity
def test_a_series_the_vendor_already_rebased_is_left_alone(base):
    """Registered event, but no cliff in the prices: applying B′ would double-count."""
    ohlcv, index, led0 = base
    orig = _trade(led0, "INDIG", "2017-12-18")
    ex = _quiet_day(ohlcv, "INDIG", orig["entry_date"], orig["half_date"])
    got = _trade(_run(ohlcv, index, _events(ohlcv, index, "INDIG", ex)), "INDIG", "2017-12-18")
    assert got["R"] == orig["R"] and got["exit_date"] == orig["exit_date"]
    assert "corporate_actions" not in got


def test_a_position_entered_after_the_ex_date_is_not_rebased(base):
    """Only a position held INTO the ex-date received the new shares. A later entry already buys at the
    post-demerger price, and re-basing it would invent a credit."""
    ohlcv, index, led0 = base
    orig = _trade(led0, "INDIG", "2017-12-18")
    ex = _quiet_day(ohlcv, "INDIG", orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, "INDIG", ex)
    led = _run(cl, index, _events(cl, index, "INDIG", ex))
    later = [r for r in led if r["tkr"] == "INDIG" and pd.Timestamp(r["entry_date"]) >= ex]
    assert later, "fixture has no INDIG entry after the ex-date — this test cannot prove anything"
    assert all("corporate_actions" not in r for r in later), [r["entry_date"] for r in later]


def test_a_ratio_matching_neither_cliff_nor_continuity_is_refused(base):
    ohlcv, index, led0 = base
    orig = _trade(led0, "INDIG", "2017-12-18")
    ex = _quiet_day(ohlcv, "INDIG", orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, "INDIG", ex)
    with pytest.raises(R94.DemergerCliffMismatch, match="refusing to re-base"):
        _run(cl, index, _events(cl, index, "INDIG", ex, retained=0.6))


def test_no_events_is_byte_identical_to_the_live_run(base):
    ohlcv, index, led0 = base
    assert _run(ohlcv, index, events={}) == led0


def test_an_unregistered_ticker_builds_no_event(base):
    ohlcv, index, _ = base
    assert R94.build_demerger_events(ohlcv, [("NOTHERE", "2018-01-01", 0.5)],
                                     index_provider=lambda _t: index) == {}


# --------------------------------------------------------------------------- HEG, the approved numbers
def test_heg_reproduces_the_figures_the_owner_approved():
    """Paper book, ex 2026-09-07: entry 653.00, stop 587.70, 305.93 shares, prior close 728.25,
    ex close 272.20, registered retained ratio 0.373773 (= 1 − 0.626227)."""
    r = 1 - 0.626227
    p = dict(en=653.0, stop=587.7, risk0=653.0 - 587.7, tp2=653.0 + 2 * 65.3, trail=587.7, sh=305.93,
             frac_left=1.0, realized_r=0.0, proceeds=0.0, last_mark=728.25)
    dates = pd.DatetimeIndex(["2026-09-04", "2026-09-07"])
    s = {"c": [728.25, 272.20], "dates": dates}
    credit = R94._apply_demerger(p, s, 1, dates[1], {"retained": r, "view": {"dates": dates}})
    assert credit == pytest.approx(305.93 * 456.05, abs=5.0)               # ≈ ₹1,39,519 spun-off value
    assert p["en"] == pytest.approx(244.07, abs=0.01)
    assert p["stop"] == pytest.approx(219.67, abs=0.01)
    assert p["frac_left"] == pytest.approx(r)
    assert p["realized_r"] == pytest.approx((1 - r) * (728.25 - 653.0) / 65.3)
    assert 225.35 > p["stop"], "the 09-15 open must clear the re-based stop (2.6% headroom)"
