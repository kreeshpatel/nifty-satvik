"""The corporate-action HOLD: an unregistered cliff on a held name freezes it for a human.

B′ (tests/test_r94_demerger.py) credits a demerger once it is REGISTERED. Before registration, the book
still reads the re-based price as a crash and stops the position out. This is the second line: a held
position that opens or closes >= CA_HOLD_DROP below the prior close, with nothing registered and no owner
review for that session, is frozen — no fill, no tranche, no exit — until the owner resolves it.

Pinned on the hermetic R94 fixture, with a demerger cliff injected into a real held trade:
  * the hold fires, at the OPEN leg, and freezes the trade (no early stop-out);
  * it fires BEFORE a queued exit can fill on the re-based open;
  * a GENUINE_MOVE review releases it to exactly the no-guard behaviour;
  * a registered demerger releases it to exactly the B′ behaviour;
  * with no deep drop anywhere, the guard changes nothing;
  * a position entered ON the drop session was not held into it.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from build_r94_golden_fixture import START_FIX, synth_universe  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT  # noqa: E402

K = 0.4
HOLD = dict(ca_hold_drop=R94.CA_HOLD_DROP)


@pytest.fixture(scope="module")
def base():
    ohlcv, index = synth_universe()
    led, _ = _run(ohlcv, index)
    return ohlcv, index, led


def _run(ohlcv, index, events=None, **kw):
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    led: list = []
    out = R94.backtest(P, None, ledger=led, start=START_FIX, return_state=True, uncapped=True,
                       **LIVE_DISCIPLINE, **LIVE_EXIT, demerger_events=events, **kw)
    return led, out


def _trade(led, tkr="INDIG", entry="2017-12-18"):
    hits = [r for r in led if r["tkr"] == tkr and str(r["entry_date"])[:10] == entry]
    return hits[0] if hits else None


def _cliff(ohlcv, ex, tkr="INDIG", k=K):
    out = dict(ohlcv)
    df = ohlcv[tkr].copy()
    post = df.index >= ex
    for col in ("Open", "High", "Low", "Close"):
        df.loc[post, col] = df.loc[post, col] * k
    out[tkr] = df
    return out


def _quiet_day(ohlcv, after, before, tkr="INDIG"):
    c = ohlcv[tkr]["Close"]
    mv = (c / c.shift(1) - 1.0).abs()
    w = mv[(mv.index > pd.Timestamp(after)) & (mv.index < pd.Timestamp(before))].dropna()
    return w.idxmin()


def test_the_fixture_has_no_deep_drop_so_the_guard_changes_nothing(base):
    ohlcv, index, led0 = base
    led, out = _run(ohlcv, index, **HOLD)
    assert led == led0
    assert not any("ca_hold" in p for p in out["open_positions"].values())


def test_an_unregistered_cliff_freezes_the_trade_instead_of_stopping_it_out(base):
    ohlcv, index, led0 = base
    orig = _trade(led0)
    ex = _quiet_day(ohlcv, orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, ex)
    stopped = _trade(_run(cl, index)[0])
    assert stopped is not None and "stop" in stopped["reason"] and stopped["R"] < -1.0, "precondition: the defect"

    led, out = _run(cl, index, **HOLD)
    assert _trade(led) is None, "a frozen position must not be closed"
    p = out["open_positions"]["INDIG"]
    assert str(p["rec"]["entry_date"])[:10] == "2017-12-18"
    h = p["ca_hold"]
    assert h["date"] == str(ex.date()) and h["leg"] == "open" and h["move_pct"] <= -50.0


def test_the_hold_fires_before_a_queued_exit_can_fill_on_the_rebased_open(base):
    ohlcv, index, led0 = base
    orig = _trade(led0)
    fill_day = pd.Timestamp(orig["exit_date"])                 # the session a queued exit fills at the open
    led, out = _run(_cliff(ohlcv, fill_day), index, **HOLD)
    assert _trade(led) is None, "the queued exit filled on the re-based open"
    assert out["open_positions"]["INDIG"]["ca_hold"]["date"] == str(fill_day.date())


def test_a_genuine_move_review_releases_it_to_the_unguarded_rules(base):
    ohlcv, index, led0 = base
    orig = _trade(led0)
    ex = _quiet_day(ohlcv, orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, ex)
    unguarded, _ = _run(cl, index)
    reviewed, _ = _run(cl, index, **HOLD, ca_reviewed={("INDIG", str(ex.date()))})
    assert reviewed == unguarded


def test_a_registered_demerger_releases_it_to_bprime(base):
    ohlcv, index, led0 = base
    orig = _trade(led0)
    ex = _quiet_day(ohlcv, orig["entry_date"], orig["half_date"])
    cl = _cliff(ohlcv, ex)
    ev = R94.build_demerger_events(cl, [("INDIG", ex, K)], index_provider=lambda _t: index)
    bprime, _ = _run(cl, index, ev)
    guarded, out = _run(cl, index, ev, **HOLD)
    assert guarded == bprime
    assert not any("ca_hold" in p for p in out["open_positions"].values())


def test_a_position_entered_on_the_drop_session_was_not_held_into_it():
    d = pd.Timestamp("2026-09-07")
    s = {"o": [728.25, 250.0], "c": [728.25, 272.2]}
    p: dict = {}
    R94._ca_hold_check(p, "HEG", s, 1, d, "open", 0.15, frozenset(), {id(p): d})
    assert "ca_hold" not in p
    R94._ca_hold_check(p, "HEG", s, 1, d, "open", 0.15, frozenset(), {id(p): d - pd.Timedelta(days=3)})
    assert p["ca_hold"]["move_pct"] == pytest.approx(-65.67, abs=0.01)


def test_a_drop_just_short_of_the_threshold_does_not_fire():
    d = pd.Timestamp("2026-09-07")
    p: dict = {}
    R94._ca_hold_check(p, "X", {"o": [100.0, 85.5], "c": [100.0, 85.5]}, 1, d, "close", 0.15,
                       frozenset(), {id(p): d - pd.Timedelta(days=7)})
    assert "ca_hold" not in p


# --------------------------------------------------------------------------- the cron
def test_reviews_file_parses_and_refuses_anything_but_genuine_move(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("# c\nsymbol,date,verdict,reviewed_on,note\nABC,2026-10-05,GENUINE_MOVE,2026-10-06,results\n",
                 encoding="utf-8")
    assert C.load_ca_reviews(f) == frozenset({("ABC", "2026-10-05")})
    f.write_text("symbol,date,verdict,reviewed_on,note\nABC,2026-10-05,DEMERGER,2026-10-06,x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="registered in"):
        C.load_ca_reviews(f)
    assert C.load_ca_reviews(tmp_path / "absent.csv") == frozenset()


def test_the_committed_reviews_file_loads():
    assert isinstance(C.load_ca_reviews(), frozenset)


def test_every_book_in_main_runs_with_the_hold():
    assert C.LIVE_CA_HOLD == {"ca_hold_drop": 0.15}
    tree = ast.parse(inspect.getsource(C.main))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "backtest" and getattr(n.func.value, "id", None) == "R94"]
    assert len(calls) == 3
    for c in calls:
        starred = [k.value.id for k in c.keywords if k.arg is None and isinstance(k.value, ast.Name)]
        assert "ca_hold" in starred, f"backtest call on line {c.lineno} runs without the corporate-action hold"


# --------------------------------------------------------------------------- the daily monitor
def _held_card(**kw) -> dict:
    card = {"ticker": "HEGX", "signal_date": "2026-07-24", "bought_date": "2026-07-27", "status": "ACTIVE",
            "entry": 653.0, "stop": 587.7, "target": 783.6, "current_price": 272.2}
    card.update(kw)
    return card


def _bars(close: float) -> dict:
    idx = pd.DatetimeIndex(["2026-09-04", "2026-09-07"])
    df = pd.DataFrame({"Open": [728.25, close], "High": [730.0, close], "Low": [720.0, close],
                       "Close": [728.25, close]}, index=idx)
    return {"HEGX": df}


def test_the_monitor_asks_for_a_review_instead_of_a_stop_breach_on_a_frozen_holding():
    from run_bhanushali_monitor import build_monitor
    hold = {"date": "2026-09-07", "leg": "open", "prior_close": 728.25, "price": 260.0, "move_pct": -64.3}
    frozen = build_monitor({"generated_at": "2026-09-07", "signals": [_held_card(ca_hold=hold)]}, _bars(272.2))
    events = {f["event"] for f in frozen["flags"]}
    assert "CORPORATE_ACTION_REVIEW" in events and "STOP_BREACH" not in events

    plain = build_monitor({"generated_at": "2026-09-07", "signals": [_held_card()]}, _bars(272.2))
    assert "STOP_BREACH" in {f["event"] for f in plain["flags"]}, "precondition: an unfrozen card still breaches"


def test_the_reviews_file_is_tracked_not_ignored():
    """A review the owner commits must reach the CI cron. If git ignores the file, CI reads it as absent,
    load_ca_reviews returns nothing, and every released hold silently freezes again."""
    import subprocess
    rel = C.CORPORATE_ACTION_REVIEWS.relative_to(ROOT).as_posix()
    ignored = subprocess.run(["git", "check-ignore", "-q", rel], cwd=ROOT, check=False).returncode == 0
    assert not ignored, f"{rel} is gitignored — whitelist it in .gitignore"
