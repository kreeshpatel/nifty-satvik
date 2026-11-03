"""Card stop = the engine's stop under the scaled exit, and the shadow-exit forward record (2026-11-03).

Hermetic: the synthetic fixture the R94 golden master uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402


def test_active_stop_reads_the_engine_stop_after_the_2r_tranche():
    # half_done is set by the 2R tranche; the trail stays at the original stop; a ratchet raised p["stop"].
    p = {"stop": 105.0, "trail": 95.0, "half_done": True}
    assert C.LIVE_EXIT.get("scaled_exit")
    assert C._active_stop(p) == 105.0


def test_active_stop_is_unchanged_before_any_tranche():
    assert C._active_stop({"stop": 95.0, "trail": 95.0, "half_done": False}) == 95.0


def test_shadow_kwargs_do_not_touch_live_exit():
    before = dict(C.LIVE_EXIT["scaled_exit"])
    kw = C._shadow_exit_kwargs()
    assert C.LIVE_EXIT["scaled_exit"] == before
    assert kw["scaled_exit"]["lockin_mfe"] == 1.0 and kw["scaled_exit"]["lockin_at"] == 0.0


@pytest.fixture(scope="module")
def books():
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import START_FIX, synth_universe
    ohlcv, index = synth_universe()
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    a = R94.grade_a_entries(P)

    def run(exit_kw, uncapped):
        led: list = []
        out = R94.backtest(P, None, ledger=led, start=START_FIX, return_state=True, uncapped=uncapped, a_grade=a,
                           **C.LIVE_DISCIPLINE, **exit_kw)
        return out, led
    return P, run(C.LIVE_EXIT, True), run(C._shadow_exit_kwargs(), True), run(C.LIVE_EXIT, False)[0], \
        run(C._shadow_exit_kwargs(), False)[0]


def test_shadow_record_shape_and_sums(books):
    P, live, shadow, lp, sp = books
    rec = C._shadow_exit_record(P, live, shadow, lp, sp, "2026-11-07")
    assert rec["effective"] == C.SHADOW_EXIT_EFFECTIVE
    assert rec["trades"], "the fixture produces trades"
    for t in rec["trades"]:
        assert t["forward"] == (t["entry_date"] >= C.SHADOW_EXIT_EFFECTIVE)
    both = [t for t in rec["trades"] if not t["forward"] and t["live"] and t["shadow"]]
    s = rec["reconstructed_before_effective"]
    assert s["n_trades"] == len(both)
    assert s["shadow_minus_live_R"] == pytest.approx(s["shadow_sum_R"] - s["live_sum_R"], abs=0.02)
    assert set(rec["paper_book"]) == {"live", "shadow"}


def test_live_trades_in_shadow_record_match_the_live_ledger(books):
    P, live, shadow, lp, sp = books
    rec = C._shadow_exit_record(P, live, shadow, lp, sp, "2026-11-07")
    closed = {(r["tkr"], str(r["entry_date"])[:10]): round(float(r["R"]), 3) for r in live[1]}
    for t in rec["trades"]:
        if t["live"] and t["live"]["status"] == "closed":
            assert t["live"]["R"] == closed[(t["ticker"], t["entry_date"])]
