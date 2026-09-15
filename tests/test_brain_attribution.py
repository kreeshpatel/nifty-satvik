"""Brain attribution — reproduce the figures quoted to the owner, from committed inputs only.

On 2026-09-08 the owner was told the 9 stopped swing trades lost −14.37R, of which −9.00R was the
stop working as designed and −5.37R was the close-only stop filling past its level, with 6 of 9 fills
below the stop. Those numbers came from ad-hoc code. Reproduce-before-trust: they are rebuilt here
from the immutable `results/archive/2026-09-04/` snapshot, offline, every run.

The instrument check matters more than the arithmetic. `R = −1 + (R + 1)` holds by construction, so
the split is only evidence if the engine measured R against the stop that was actually on the card.
`test_recorded_stops_agree_with_the_engines_r` verifies that against the archived cards.

Hermetic — reads committed files, touches no network, and never opens the sealed judge log.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.brain import attribution as A  # noqa: E402
from nq.brain import io as brain_io  # noqa: E402

SNAPSHOT = ROOT / "results" / "archive" / "2026-09-04"


def _snapshot_trades() -> list[A.ClosedTrade]:
    trades = A.closed_trades(brain_io.read_json(SNAPSHOT / "signals_history_weekly.json"))
    envelopes = [brain_io.read_json(p) for p in sorted(
        glob.glob(str(ROOT / "results" / "archive" / "2026-*" / "signals_today_weekly.json")))
        if Path(p).parent.name <= "2026-09-04"]
    return A.with_recorded_stops(trades, A.recorded_stops(envelopes))


# --------------------------------------------------------------------------- the quoted figures
def test_the_quoted_stop_decomposition_reproduces_exactly():
    trades = _snapshot_trades()
    d = A.stop_decomposition(trades)
    assert d["n"] == 9
    assert round(d["realised_r"], 2) == -14.37
    assert d["designed_r"] == -9.0
    assert round(d["beyond_stop_r"], 2) == -5.37
    assert d["n_filled_beyond_stop"] == 6
    assert round(d["share_beyond_stop"], 2) == 0.37


def test_every_closed_trade_was_a_stop_or_line_break():
    """All 9 exits in the snapshot were HIT_STOP; one (NATCOPHARM) exited on the 44w line."""
    trades = _snapshot_trades()
    assert {t.exit_reason for t in trades} <= {"stop", "sma_break"}
    assert [t.ticker for t in trades if t.exit_reason == "sma_break"] == ["NATCOPHARM"]


# --------------------------------------------------------------------------- the instrument check
def test_recorded_stops_agree_with_the_engines_r():
    """Without this the decomposition is an identity with no evidential weight."""
    trades = _snapshot_trades()
    assert all(t.stop_source == "recorded" for t in trades), (
        f"no archived card for: {[t.ticker for t in trades if t.stop_source != 'recorded']}")
    gaps = A.stop_agreement(trades)
    worst = max(gaps, key=gaps.get)
    assert gaps[worst] < 0.005, f"{worst}: recorded stop is {gaps[worst]:.2%} from the stop R implies"


def test_the_split_is_an_identity_so_it_must_hold_exactly():
    trades = _snapshot_trades()
    d = A.stop_decomposition(trades)
    assert d["beyond_stop_r"] == pytest.approx(sum(t.beyond_stop_r for t in trades))
    assert d["designed_r"] + d["beyond_stop_r"] == pytest.approx(d["realised_r"])


# --------------------------------------------------------------------------- matched control
def test_window_excess_places_a_name_against_the_same_window():
    idx = pd.bdate_range("2026-07-01", periods=10)
    name = pd.Series([100.0] * 9 + [90.0], index=idx)                  # −10%
    universe = {f"U{i}": pd.Series([100.0] * 9 + [100.0 + i], index=idx) for i in range(-5, 6)}
    out = A.window_excess(name, universe, idx[0], idx[-1])
    assert out["name_return"] == pytest.approx(-0.10)
    assert out["universe_median"] == pytest.approx(0.0)
    assert out["excess"] == pytest.approx(-0.10)
    assert out["percentile"] == 0.0                                    # nothing did worse


def test_window_excess_refuses_a_window_with_no_bars():
    idx = pd.bdate_range("2026-07-01", periods=5)
    s = pd.Series(1.0, index=idx)
    assert A.window_excess(s, {"U": s}, "2027-01-01", "2027-02-01") is None


@pytest.mark.parametrize("depth, band", [
    (-4.3, "sub-line <0%"), (0.0, "core 0-5%"), (4.99, "core 0-5%"), (5.0, "weak 5-10%"),
    (10.0, "weak 5-10%"), (13.67, "outside >10%"), (None, None), (float("nan"), None),
])
def test_touch_bands_match_the_ext_census_edges(depth, band):
    assert A.touch_band(depth) == band


def test_implied_stop_refuses_a_zero_r():
    t = A.ClosedTrade("X", "2026-07-01", "2026-07-10", 100.0, 100.0, 0.0)
    with pytest.raises(ValueError, match="no stop can be implied"):
        _ = t.implied_stop


# --------------------------------------------------------------------------- incomplete sessions
def test_forensics_refuse_a_window_ending_on_an_unfinished_session():
    """The first run of the market control silently ended at the prior close because the end date's
    bar was still trading. A completed session is the only honest end date."""
    import importlib.util
    from datetime import date
    spec = importlib.util.spec_from_file_location("diag_tf", ROOT / "scripts" / "diag_trade_forensics.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit, match="not a completed session"):
        mod.assert_completed_session("2026-09-09", today=date(2026, 9, 9))
    mod.assert_completed_session("2026-09-08", today=date(2026, 9, 9))   # yesterday is fine


def test_the_committed_record_reproduces_the_quoted_market_control():
    """The price-dependent figures cannot be recomputed offline, so the committed run is the record.
    Pinned to the values quoted to the owner: losers in the bottom decile, open names above the market."""
    s = brain_io.read_json(ROOT / "diagnostics" / "research" / "trade_forensics" / "2026-09-04" / "summary.json")
    assert s["prices"]["end"] == "2026-09-08"
    mc = s["market_control"]
    assert mc["STOPPED"] == {"n": 9, "median_excess_pct": -4.05, "median_percentile": 11.0,
                             "n_underperformed_universe": 8}
    assert mc["OPEN"]["median_excess_pct"] == 3.82 and mc["OPEN"]["median_percentile"] == 68.2


# --------------------------------------------------------------------------- the seal, in code
def test_the_brain_reader_refuses_the_sealed_judge_log_without_opening_it():
    """Crons have no PreToolUse hook, so the refusal must live in the reader itself."""
    from nq.paper.judge_log import DEFAULT_LOG
    with pytest.raises(brain_io.SealedArtifactError, match="sealed 0125 judge log"):
        brain_io.read_json(DEFAULT_LOG)


def test_the_brain_reader_serves_ordinary_artifacts():
    assert isinstance(brain_io.read_json(SNAPSHOT / "signal_analytics_weekly.json"), dict)
