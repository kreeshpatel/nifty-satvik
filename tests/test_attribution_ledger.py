"""The per-trade attribution ledger — the rebuild must be deterministic, and a gap must read as a gap.

Two defects this pins, both found on the collector's first run:
  * an uncovered market window silently returned **0.0%** instead of "unknown" (`window_pct`);
  * the excursion columns existed only when the price cache happened to be deep enough, so the CSV
    schema depended on the machine it ran on.

Everything else here is the contract the ledger has to keep to be worth having: a rerun is a no-op, a
reconstructed row can never read as forward evidence, and the live book's own closed trades reproduce.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import collect_attribution_ledger as C  # noqa: E402
from nq.brain import ledger as L  # noqa: E402


# --------------------------------------------------------------------------- pure functions
def test_stop_width_is_the_r_denominator():
    assert L.stop_width_pct(100.0, 90.0) == pytest.approx(10.0)
    assert L.stop_width_pct(1133.4, 1116.2) == pytest.approx(1.5176, abs=1e-4)   # the real CCL trade
    assert L.stop_width_pct(100.0, 100.0) is None and L.stop_width_pct(100.0, 110.0) is None
    assert L.stop_width_pct(None, 90.0) is None


def test_decompose_splits_a_loss_into_designed_and_beyond_the_stop():
    assert L.decompose_r(-2.32) == {"designed_r": -1.0, "beyond_stop_r": pytest.approx(-1.32),
                                    "gap_through": True}
    assert L.decompose_r(-0.93) == {"designed_r": pytest.approx(-0.93), "beyond_stop_r": 0.0,
                                    "gap_through": False}
    assert L.decompose_r(3.5)["beyond_stop_r"] == 0.0
    assert L.decompose_r(None)["designed_r"] is None


def test_the_decomposition_adds_back_to_the_realised_r():
    for r in (-4.0, -1.0001, -1.0, -0.5, 0.0, 2.7):
        d = L.decompose_r(r)
        assert d["designed_r"] + d["beyond_stop_r"] == pytest.approx(r, abs=1e-9)


def test_excursions_in_r_units():
    out = L.excursions_r([102.0, 108.0, 104.0], [99.0, 95.0, 97.0], entry=100.0, stop=90.0)
    assert out["mfe_r"] == pytest.approx(0.8) and out["mae_r"] == pytest.approx(-0.5)
    assert L.excursions_r([], [], entry=100, stop=90)["mae_r"] is None
    assert L.excursions_r([101], [99], entry=100, stop=100)["mfe_r"] is None


def test_capture_of_mfe_only_when_the_trade_went_favourable():
    assert L.capture_of_mfe(1.0, 4.0) == pytest.approx(0.25)
    assert L.capture_of_mfe(-1.0, -0.2) is None and L.capture_of_mfe(None, 3.0) is None


# --------------------------------------------------------------------------- the 0.0% bug
def test_an_uncovered_window_is_unknown_not_zero():
    """The first run reported a confident 0.0% index move for all 11 live trades, because the committed
    Nifty CSV ends before the live book starts and `asof` returned the same print at both ends."""
    idx = pd.Series([100.0, 101.0], index=pd.to_datetime(["2026-07-01", "2026-07-03"]))
    assert L.window_pct(idx, "2026-07-13", "2026-07-27") is None       # entirely past the data
    assert L.window_pct(idx, "2026-07-02", "2026-07-20") is None       # end past the data
    assert L.window_pct(idx, "2026-06-01", "2026-07-03") is None       # start before the data


def test_a_covered_window_measures_the_move():
    idx = pd.Series([100.0, 110.0, 99.0],
                    index=pd.to_datetime(["2026-07-01", "2026-07-10", "2026-07-20"]))
    assert L.window_pct(idx, "2026-07-01", "2026-07-10") == pytest.approx(10.0)
    # asof at both ends, inside coverage: 2026-07-02 walks back to the 07-01 print (100.0)
    assert L.window_pct(idx, "2026-07-02", "2026-07-20") == pytest.approx(-1.0)
    assert L.window_pct(idx, "2026-07-02", "2026-07-21") is None, "one day past the data is still uncovered"


# --------------------------------------------------------------------------- episodes
def test_a_redated_signal_is_one_trade():
    """The book re-dates a card as it recomputes; two dates within the episode window are one trade."""
    rows = {("PTCIL", "2026-08-07"): {"ticker": "PTCIL", "signal_date": "2026-08-07", "entry": 100.0,
                                      "stop": None},
            ("PTCIL", "2026-08-10"): {"ticker": "PTCIL", "signal_date": "2026-08-10", "entry": 101.0,
                                      "stop": 90.0},
            ("PTCIL", "2026-12-01"): {"ticker": "PTCIL", "signal_date": "2026-12-01", "entry": 200.0,
                                      "stop": 180.0}}
    out = L.collapse_episodes(rows, ("entry", "stop"))
    assert set(out) == {("PTCIL", "2026-08-07"), ("PTCIL", "2026-12-01")}
    merged = out[("PTCIL", "2026-08-07")]
    assert merged["entry"] == 100.0, "the first-seen entry wins"
    assert merged["stop"] == 90.0, "a later re-date may only FILL a gap"


def test_first_seen_keeps_the_card_as_issued():
    snaps = [("2026-07-04", {"signals": [{"ticker": "A", "signal_date": "2026-07-03", "stop": 90.0}]}),
             ("2026-07-11", {"signals": [{"ticker": "A", "signal_date": "2026-07-03", "stop": 97.0,
                                          "target": 130.0}]})]
    got = L.first_seen(snaps, ("stop", "target"))[("A", "2026-07-03")]
    assert got["stop"] == 90.0, "a trailed stop must not rewrite what the card said at issue"
    assert got["target"] == 130.0 and got["as_of_snapshot"] == "2026-07-04"


# --------------------------------------------------------------------------- the collector
@pytest.fixture(scope="module")
def built():
    return C.build()


def test_the_rebuild_is_deterministic(built, tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    assert C.main(["--out", str(a)]) == 0 and C.main(["--out", str(b)]) == 0
    assert a.read_bytes() == b.read_bytes(), "a rerun must be a no-op"


def test_every_row_is_provenance_labelled_and_none_claims_to_be_forward_yet(built):
    assert set(built["provenance"]) <= {"reconstructed", "forward"}
    early = built[built["as_of_snapshot"] < C.FORWARD_FROM]
    assert (early["provenance"] == "reconstructed").all(), (
        "a row rebuilt from a snapshot written before the collector existed is a record, not forward evidence")


def test_the_schema_does_not_depend_on_how_deep_the_price_cache_is(built):
    for col in ("mae_r", "mfe_r", "capture_of_mfe", "nifty_same_window_pct", "stop_width_pct"):
        assert col in built.columns


def test_the_live_closed_trades_reproduce_their_outcome(built):
    import json
    hist = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    closed = {h["ticker"]: h for h in hist if h.get("exit_reason")}
    rows = built[built["exit_reason"].notna()]
    assert len(rows) == len(closed), f"ledger has {len(rows)} closed trades, history has {len(closed)}"
    for _, r in rows.iterrows():
        h = closed[r["ticker"]]
        assert r["r_multiple"] == pytest.approx(h["r_multiple"])
        assert r["exit_reason"] == h["exit_reason"]


def test_the_decomposition_of_the_live_book_adds_up(built):
    rows = built[built["r_multiple"].notna()]
    assert rows["designed_r"].sum() + rows["beyond_stop_r"].sum() == pytest.approx(
        rows["r_multiple"].sum(), abs=1e-6)


def test_every_trade_has_the_denominator_its_r_is_measured_against(built):
    assert built["stop_width_pct"].notna().all()
    assert (built["stop_width_pct"] > 0).all()


def test_validate_reports_holes_and_declares_the_unfillable_ones():
    assert C.main(["--validate"]) == 0
    assert set(C.DECLARED_HOLES) >= {"judge_*", "owner_action / owner_note"}
    assert all(len(v) > 40 for v in C.DECLARED_HOLES.values()), "a declared hole costs a reason"


def test_holes_flags_a_trade_with_no_denominator():
    df = pd.DataFrame([{"entry": 100.0, "stop": np.nan, "stop_width_pct": np.nan, "exit_reason": "stop",
                        "r_multiple": -1.0}])
    assert any("stop_width_pct" in h for h in C.holes(df))
    assert C.holes(pd.DataFrame()) == ["ledger is empty — no archived signal on or after the inception"]


def test_the_collector_writes_only_under_results_and_is_not_in_the_engine():
    """The ledger reads the book; it must never be imported by anything that decides a trade."""
    src = (ROOT / "scripts" / "run_bhanushali_weekly_rank.py").read_text(encoding="utf-8")
    assert "attribution_ledger" not in src and "nq.brain" not in src
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'.');"
                          "import nq.brain.ledger as m; print(m.__file__)"], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0
