"""The three legs added to the stop forensics on 2026-09-26, and the join bugs they cost.

Synthetic where the logic lives, structural where the live artifacts are load-bearing. The two join
mistakes this study actually made are pinned as regressions, because both produced a confident wrong
number rather than an error:

  * keying the ledger cross-check on TICKER alone finds a later, still-open re-entry row and reports a
    false MISSING (GESHIP);
  * keying it on (ticker, signal_date) fails for trades whose signal date was RESTATED between
    snapshots (3MINDIA, GESHIP, CCL), which looks like absent data and is not.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import diag_trade_forensics as F  # noqa: E402


@dataclass
class _Trade:
    ticker: str
    r_multiple: float
    signal_date: str
    close_date: str
    exit_reason: str = "stop"
    stop_source: str = "recorded"

    @property
    def beyond_stop_r(self) -> float:
        return self.r_multiple + 1.0


# ------------------------------------------------------------------ the two conventions
def test_the_two_conventions_are_reported_side_by_side_and_differ():
    """A loss shallower than the stop is credited by one convention and ignored by the other."""
    trades = [_Trade("DEEP", -2.0, "2026-07-06", "2026-08-17"),
              _Trade("SHALLOW", -0.5, "2026-07-06", "2026-08-17")]
    out = F.convention_divergence(trades)
    # attribution: designed -1 each = -2.0; beyond = (-1.0) + (+0.5) = -0.5
    assert out["attribution_nets_favourable_fills"]["designed_r"] == pytest.approx(-2.0)
    assert out["attribution_nets_favourable_fills"]["beyond_stop_r"] == pytest.approx(-0.5)
    # ledger: designed -1 + -0.5 = -1.5; beyond counts only the adverse -1.0
    assert out["ledger_counts_adverse_overshoot_only"]["designed_r"] == pytest.approx(-1.5)
    assert out["ledger_counts_adverse_overshoot_only"]["beyond_stop_r"] == pytest.approx(-1.0)
    assert out["difference_r"] == pytest.approx(0.5)


def test_with_no_favourable_fills_the_conventions_agree():
    trades = [_Trade("A", -2.0, "2026-07-06", "2026-08-17"),
              _Trade("B", -1.5, "2026-07-06", "2026-08-17")]
    out = F.convention_divergence(trades)
    assert out["difference_r"] == pytest.approx(0.0)


# ------------------------------------------------------------------ the funded split
def _write_snapshot(tmp: Path, as_of: str, names: list[str]) -> None:
    import json
    d = tmp / "results" / "archive" / as_of
    d.mkdir(parents=True, exist_ok=True)
    (d / "paper_portfolio_weekly.json").write_text(
        json.dumps({"positions": {n: {"shares": 1} for n in names}}), encoding="utf-8")


def test_funded_split_uses_a_half_open_window(tmp_path, monkeypatch):
    """A name absent only at its own close date was still funded — the 0146 boundary trap."""
    monkeypatch.setattr(F, "ROOT", tmp_path)
    _write_snapshot(tmp_path, "2026-07-24", ["HELD"])
    _write_snapshot(tmp_path, "2026-08-17", [])            # gone on its close date
    out = F.funded_split([_Trade("HELD", -1.05, "2026-07-06", "2026-08-17")], "2026-09-04")
    assert out["funded"]["n"] == 1
    assert out["never_funded"]["n"] == 0


def test_the_only_in_window_snapshot_being_the_close_date_is_undetermined(tmp_path, monkeypatch):
    """THE discriminating case for the half-open window, and the one the first test missed.

    The earlier `test_funded_split_uses_a_half_open_window` also held the name in an EARLIER snapshot,
    so it read as funded under a closed window too — it passed under both implementations and did not
    re-break when the boundary was mutated (red-team, 2026-09-27). Here the close-date snapshot is the
    only one in range: half-open must return `undetermined` (no evidence either way), while a closed
    window would see an absent name and wrongly call it `never_funded`, moving its R to the wrong
    cohort.
    """
    monkeypatch.setattr(F, "ROOT", tmp_path)
    _write_snapshot(tmp_path, "2026-08-17", [])            # the close date, and nothing earlier
    out = F.funded_split([_Trade("ONLYCLOSE", -2.0, "2026-08-10", "2026-08-17")], "2026-09-04")
    assert out["undetermined"]["n"] == 1, "a closed window would call this never_funded"
    assert out["never_funded"]["n"] == 0
    assert out["funded"]["n"] == 0


def test_a_name_never_in_a_snapshot_is_never_funded(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "ROOT", tmp_path)
    _write_snapshot(tmp_path, "2026-07-24", ["OTHER"])
    out = F.funded_split([_Trade("ABSENT", -2.0, "2026-07-06", "2026-08-17")], "2026-09-04")
    assert out["never_funded"] == {"n": 1, "tickers": ["ABSENT"], "realised_r": -2.0,
                                  "beyond_stop_r": -1.0}


def test_reruns_and_later_snapshots_are_excluded(tmp_path, monkeypatch):
    """A `__rerun` repeats its parent's as-of, and a snapshot after the as-of is not evidence for it."""
    monkeypatch.setattr(F, "ROOT", tmp_path)
    _write_snapshot(tmp_path, "2026-07-24", ["X"])
    _write_snapshot(tmp_path, "2026-07-24__rerun-20260804T215840Z", ["X"])
    _write_snapshot(tmp_path, "2026-09-18", ["X"])          # after the as-of
    out = F.funded_split([_Trade("X", -1.0, "2026-07-06", "2026-08-17")], "2026-09-04")
    assert out["n_snapshots_used"] == 1


def test_a_trade_with_no_snapshot_in_its_window_is_undetermined_not_unfunded(tmp_path, monkeypatch):
    """Silence is not evidence of absence — it must not be counted as never-funded."""
    monkeypatch.setattr(F, "ROOT", tmp_path)
    _write_snapshot(tmp_path, "2026-09-04", ["ANY"])
    out = F.funded_split([_Trade("EARLY", -1.0, "2026-07-06", "2026-07-20")], "2026-09-04")
    assert out["undetermined"]["n"] == 1
    assert out["never_funded"]["n"] == 0


# ------------------------------------------------------------------ the ledger cross-check, live
def test_the_ledger_crosscheck_leaves_nothing_unexplained():
    """Every per-trade disagreement must be either exact agreement or the documented convention."""
    import glob
    from nq.brain import attribution as A
    from nq.brain import io as brain_io
    as_of = "2026-09-04"
    snap = ROOT / "results" / "archive" / as_of
    if not (snap / "signals_history_weekly.json").is_file():
        pytest.skip("archived snapshot absent")
    env = [brain_io.read_json(p) for p in sorted(glob.glob(
        str(ROOT / "results" / "archive" / "2026-*" / "signals_today_weekly.json")))
        if Path(p).parent.name <= as_of]
    trades = A.with_recorded_stops(
        A.closed_trades(brain_io.read_json(snap / "signals_history_weekly.json")),
        A.recorded_stops(env))
    out = F.ledger_crosscheck(trades)
    if not out.get("available"):
        pytest.skip("attribution ledger absent")
    assert out["n_unexplained"] == 0, out["rows"]
    assert not out["absent"], (
        f"a closed trade did not join to exactly one closed ledger row: {out['absent']}. "
        f"Ticker-only and (ticker, signal_date) joins both fail here — see this file's docstring.")
