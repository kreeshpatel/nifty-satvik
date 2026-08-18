"""The adjustment-monotonicity guard — the vaccine against a new vintage seam entering the cache.

Both directions are pinned, because a guard that only ever passes is indistinguishable from no
guard, and a guard that only ever fails gets disabled. The 2026Q3 foundation audit's own conclusion
drives the shape of these tests: the defect class is NOT size-bounded (observed steps ×1.04 to
×5.00), so the small end is tested explicitly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.adjustment_guard import (  # noqa: E402
    KNOWN_SEAMS, assert_no_new_seams, check_adjustment_monotonicity, implied_adjustment,
    load_reference,
)

DATES = pd.to_datetime(["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01", "2025-01-01"])


def _ref(sym: str, closes) -> pd.DataFrame:
    return pd.DataFrame({"symbol": sym, "date": DATES, "close": list(closes)})


def _series(closes, dates=DATES) -> pd.DataFrame:
    return pd.DataFrame({"Close": list(closes)}, index=pd.DatetimeIndex(dates))


def test_clean_series_passes():
    """adj rising toward 1 is the normal, correct shape of a dividend-adjusted series."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    cache = {"AAA": _series([96, 97, 98, 99, 100])}
    rep = check_adjustment_monotonicity(cache, ref, known={})
    assert rep.overall == "OK", rep.as_dict()
    assert rep.seams == [] and rep.symbols_checked == 1


def test_flat_factor_passes():
    """A constant factor is monotone; an unadjusted series (factor 1 throughout) is too."""
    for cache in ({"AAA": _series([95, 95, 95, 95, 95])},
                  {"AAA": _series([100, 100, 100, 100, 100])}):
        rep = check_adjustment_monotonicity(cache, _ref("AAA", [100] * 5), known={})
        assert rep.overall == "OK", rep.as_dict()


def test_a_falling_factor_is_caught_and_named():
    """The defect: the cache is on the post-split basis from one date while the history is not."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    cache = {"AAA": _series([100, 100, 25, 25, 100])}          # x4 step down at 2024-07-01
    rep = check_adjustment_monotonicity(cache, ref, known={})
    assert rep.overall == "RED"
    assert len(rep.new_seams) == 1
    s = rep.new_seams[0]
    assert s["symbol"] == "AAA"
    assert s["window_start"] == "2024-04-01" and s["window_end"] == "2024-07-01"
    assert s["step_factor"] == pytest.approx(4.0, rel=1e-6)


def test_the_small_end_is_caught_too():
    """A rights-issue seam is ~4%. Every OTHER corporate-action detector in this repo is a 45-50%
    threshold and cannot see it — being size-free is the whole reason this guard exists."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    cache = {"AAA": _series([100, 100, 100 / 1.0425, 100 / 1.0425, 100])}
    rep = check_adjustment_monotonicity(cache, ref, known={})
    assert rep.overall == "RED" and len(rep.new_seams) == 1
    assert rep.new_seams[0]["step_factor"] == pytest.approx(1.0425, rel=1e-4)


def test_paise_rounding_does_not_trip_it():
    """A 2-dp exchange close against a float cache must not read as a seam."""
    ref = _ref("AAA", [100.0, 100.01, 99.99, 100.02, 100.0])
    cache = {"AAA": _series([96.0, 96.0, 96.0, 96.0, 96.0])}
    rep = check_adjustment_monotonicity(cache, ref, known={})
    assert rep.overall == "OK", rep.as_dict()


def test_a_registered_seam_warns_and_does_not_raise():
    """Known seams are an owner decision (F-1). The guard reports them; it does not halt the book
    over a question it is not entitled to decide."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    cache = {"AAA": _series([100, 100, 25, 25, 100])}
    known = {("AAA", "2024-07-01"): {"factor": 4.0, "cause": "test", "provenance": "test"}}
    rep = assert_no_new_seams(cache, ref, known=known)
    assert rep.overall == "WARN"
    assert len(rep.seams) == 1 and rep.new_seams == []
    assert rep.seams[0]["known"] is True and rep.seams[0]["cause"] == "test"


def test_an_unregistered_seam_raises_with_symbol_and_dates():
    """Fail loudly — the message must carry the symbol and the bracketing sessions, or the next
    session cannot act on it."""
    ref = _ref("ZZZ", [100, 100, 100, 100, 100])
    cache = {"ZZZ": _series([100, 100, 25, 25, 100])}
    with pytest.raises(ValueError) as e:
        assert_no_new_seams(cache, ref, known={})
    msg = str(e.value)
    assert "ZZZ" in msg and "2024-04-01" in msg and "2024-07-01" in msg
    assert "4.0" in msg


# ── benign auto-tolerance (2026-08-18 owner decision) — halt only DANGEROUS new seams ─────────────
# A small seam that is old AND unheld: cache falls x1.05 at 2024-07-01 then recovers. `as_of` far in
# the future puts it outside the trailing 44-week window.
_SMALL = [100, 100, 100 / 1.05, 100 / 1.05, 100]
_LATE = "2025-12-01"          # cutoff = as_of - 44w ≈ 2025-01, so the 2024-07 seam is OUT of window


def test_a_benign_new_seam_is_tolerated_not_halted():
    """Below the dividend scale, outside the live window, not held -> warn + record, never raise."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    rep = assert_no_new_seams({"AAA": _series(_SMALL)}, ref, known={}, positions=[], as_of=_LATE)
    assert rep.overall == "WARN"
    assert len(rep.tolerated_seams) == 1 and rep.new_seams == []
    assert rep.tolerated_seams[0]["symbol"] == "AAA"
    assert rep.tolerated_seams[0]["step_factor"] == pytest.approx(1.05, rel=1e-3)


def test_a_small_seam_INSIDE_the_window_still_halts():
    """Small but recent moves a live gate -> dangerous, halts even with auto-tolerance on."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    with pytest.raises(ValueError, match="MONOTONICITY VIOLATED"):
        # default as_of = 2025-01-01 latest bar -> the 2024-07 seam is inside the 44w window
        assert_no_new_seams({"AAA": _series(_SMALL)}, ref, known={}, positions=[])


def test_a_small_seam_on_a_HELD_name_still_halts():
    """A wrong input behind an open position is a different question -> halts regardless of size/age."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    with pytest.raises(ValueError, match="MONOTONICITY VIOLATED"):
        assert_no_new_seams({"AAA": _series(_SMALL)}, ref, known={}, positions=["AAA"], as_of=_LATE)


def test_a_large_old_unheld_seam_still_halts():
    """Split/bonus-scale step wants a human look even when old and unheld -> not benign."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    with pytest.raises(ValueError, match="MONOTONICITY VIOLATED"):
        assert_no_new_seams({"AAA": _series([100, 100, 25, 25, 100])}, ref, known={},
                            positions=[], as_of=_LATE)


def test_legacy_strict_when_positions_not_passed():
    """positions=None (default) keeps the old behaviour: any unregistered seam halts, benign or not."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    with pytest.raises(ValueError, match="MONOTONICITY VIOLATED"):
        assert_no_new_seams({"AAA": _series(_SMALL)}, ref, known={})   # no positions -> strict


def test_absent_reference_is_indeterminate_never_ok():
    """S2.14: a checker that says OK when it could not look is worse than no checker."""
    rep = check_adjustment_monotonicity({"AAA": _series([1, 2, 3, 4, 5])},
                                        pd.DataFrame(columns=["symbol", "date", "close"]))
    assert rep.overall == "INDETERMINATE"
    assert rep.seams == [] and rep.indeterminate

    # a symbol the reference does not cover is INDETERMINATE for that symbol, not a pass
    rep2 = check_adjustment_monotonicity({"BBB": _series([1, 2, 3, 4, 5])},
                                         _ref("AAA", [1] * 5), known={})
    assert any(r.get("symbol") == "BBB" for r in rep2.indeterminate)
    assert rep2.symbols_checked == 0


def test_missing_cache_bar_is_skipped_not_mis_paired():
    """Comparing cache(t-k) to raw(t) would divide two different sessions and manufacture seams."""
    ref = _ref("AAA", [100, 100, 100, 100, 100])
    partial = _series([96, 99], dates=pd.to_datetime(["2024-01-01", "2025-01-01"]))
    adj = implied_adjustment(partial["Close"], ref)
    assert list(adj.index) == list(pd.to_datetime(["2024-01-01", "2025-01-01"]))
    assert len(adj) == 2


def test_the_shipped_register_is_well_formed():
    """Every entry must carry a cause and a provenance, so the register stays a ledger rather than
    drifting into a list of names someone silenced."""
    assert KNOWN_SEAMS, "an empty register would make the guard raise on the known seams"
    for (sym, date), v in KNOWN_SEAMS.items():
        assert isinstance(sym, str) and sym
        pd.Timestamp(date)                                   # parses, or the lookup can never match
        assert v.get("cause"), f"{sym}@{date} has no cause"
        assert v.get("provenance"), f"{sym}@{date} has no provenance"
        assert float(v["factor"]) > 1.0


def test_live_reference_covers_the_pinned_universe_if_present():
    """The shipped reference must actually be usable — an artifact that exists but covers nothing
    would make every symbol INDETERMINATE and the guard silently inert."""
    ref = load_reference()
    if not len(ref):
        pytest.skip("raw_close_reference.parquet not present in this checkout")
    assert ref["symbol"].nunique() > 500
    assert ref["date"].nunique() > 100
    assert (ref["close"].astype(float) > 0).all()


# ── the ADR-0013 escalation trigger ───────────────────────────────────────────────────────────────
#
# Decision (b) accepted running on ONE known-wrong input until 2026-10-01, on a stated scope: a
# suppressed candidate, no open position. These pin the condition under which that scope stops
# holding, because a pre-commitment nobody evaluates is not a pre-commitment.

from nq.data.adjustment_guard import (  # noqa: E402
    LIVE_WINDOW_WEEKS, assert_no_live_escalation, live_exposure,
)

_ACCEPTED = {("TRENT", "2026-01-01"): {"factor": 1.5, "cause": "bonus 1:2",
                                       "provenance": "F-1",
                                       "owner_status": "ACCEPTED_UNTIL_2026-10-01 (ADR-0013)"}}


def _cache(*syms, end="2026-06-29"):
    idx = pd.date_range(end=pd.Timestamp(end), periods=600, freq="D")
    return {s: pd.DataFrame({"Close": range(len(idx))}, index=idx) for s in syms}


def test_the_accepted_seam_alone_does_not_escalate():
    """The status quo the owner signed off: TRENT in-window, accepted, nothing held."""
    ex = live_exposure(_cache("TRENT"), [], as_of="2026-06-29", known=_ACCEPTED)
    assert [s["symbol"] for s in ex["in_window"]] == ["TRENT"]
    assert ex["accepted_live"] and not ex["escalate"]


def test_an_additional_live_affecting_seam_escalates():
    """The first half of the trigger: another seam inside the 44-week window, unaccepted."""
    known = dict(_ACCEPTED)
    known[("NEWCO", "2026-03-01")] = {"factor": 2.0, "cause": "bonus 1:1", "provenance": "test"}
    with pytest.raises(ValueError) as e:
        assert_no_live_escalation(_cache("TRENT", "NEWCO"), [], as_of="2026-06-29", known=known)
    assert "NEWCO" in str(e.value) and "ADR-0013" in str(e.value)


def test_a_seam_on_an_open_position_escalates_even_when_accepted():
    """The second half: the acceptance was granted for a SUPPRESSED CANDIDATE. A held name is a
    different question and must not inherit that acceptance."""
    with pytest.raises(ValueError) as e:
        assert_no_live_escalation(_cache("TRENT"), ["TRENT"], as_of="2026-06-29", known=_ACCEPTED)
    assert "OPEN POSITION" in str(e.value)


def test_a_seam_outside_the_44_week_window_does_not_escalate():
    """CONCOR/HBLENGINE/UPL have aged out — that is why the live scope is one name, not seven."""
    known = {("OLDCO", "2024-01-01"): {"factor": 4.0, "cause": "split", "provenance": "test"}}
    ex = live_exposure(_cache("OLDCO"), [], as_of="2026-06-29", known=known)
    assert ex["in_window"] == [] and not ex["escalate"]


def test_a_seam_on_a_name_absent_from_the_cache_cannot_bite():
    """MAHLIFE is not in the live 500-name universe; a seam there cannot move a live gate."""
    known = {("MAHLIFE", "2026-05-14"): {"factor": 1.09, "cause": "rights", "provenance": "test"}}
    ex = live_exposure(_cache("TRENT"), [], as_of="2026-06-29", known=known)
    assert not ex["escalate"] and ex["in_window"] == []


def test_the_acceptance_expires_on_its_own_date():
    """The acceptance must not outlive the review. After 2026-10-01 the same seam escalates with no
    edit to the register — nobody has to remember."""
    before = live_exposure(_cache("TRENT"), [], as_of="2026-09-30", known=_ACCEPTED)
    after = live_exposure(_cache("TRENT"), [], as_of="2026-10-02", known=_ACCEPTED)
    assert not before["escalate"], "accepted before the review date"
    assert after["escalate"], "the acceptance must expire on 2026-10-01, not silently persist"


def test_an_unparseable_owner_status_is_not_an_acceptance():
    """Fail closed: a malformed status must escalate rather than silently grant immunity."""
    known = {("TRENT", "2026-01-01"): {"factor": 1.5, "cause": "x", "provenance": "t",
                                       "owner_status": "ACCEPTED_UNTIL_whenever"}}
    assert live_exposure(_cache("TRENT"), [], as_of="2026-06-29", known=known)["escalate"]


def test_the_live_window_matches_the_engine_sma():
    """If these ever diverge the trigger stops meaning 'moves a live gate'."""
    import run_bhanushali_weekly_rank as R94  # noqa: F401  (import guard only)
    assert LIVE_WINDOW_WEEKS == 44


def test_the_shipped_register_has_exactly_one_accepted_seam():
    """ADR-0013 accepted TRENT and nothing else. A second acceptance appearing without an ADR is
    the drift this test exists to catch."""
    accepted = {k: v for k, v in KNOWN_SEAMS.items() if v.get("owner_status", "").startswith(
        "ACCEPTED_UNTIL_")}
    assert list(accepted) == [("TRENT", "2026-01-01")], accepted


# --------------------------------------------------------------------------- ADR-0013 expiry gap
#
# Characterization, added 2026-08-10. ADR-0013 accepted the TRENT seam until 2026-10-01, but its own
# reason 3 is that the defect self-resolves on 2026-11-06 when the seam leaves the 44-week window.
# Those dates are five weeks apart, and in that gap the seam is in-window AND unaccepted -- which is
# the escalation condition, so the weekly scan halts. Five Saturday scans fall inside it.
#
# These pin the gap so it cannot be lost. If the review takes option A and extends the acceptance to
# 2026-11-06, `test_the_acceptance_expires_before_the_seam_leaves_the_window` SHOULD fail and be
# retired with the new ADR -- that failure is the point, not a nuisance.
# See diagnostics/research/review_2026Q4/07_adr0013_seam_expiry.md.
class TestADR0013ExpiryGap:
    SEAM = ("TRENT", "2026-01-01")

    def _entry(self):
        from nq.data.adjustment_guard import KNOWN_SEAMS
        return KNOWN_SEAMS[self.SEAM]

    def test_the_acceptance_expires_before_the_seam_leaves_the_window(self):
        from nq.data.adjustment_guard import ACCEPTED_PREFIX, LIVE_WINDOW_WEEKS

        status = self._entry()["owner_status"]
        assert status.startswith(ACCEPTED_PREFIX)
        until = pd.Timestamp(status[len(ACCEPTED_PREFIX):].split()[0])
        leaves = pd.Timestamp(self.SEAM[1]) + pd.Timedelta(weeks=LIVE_WINDOW_WEEKS)
        assert until < leaves, (
            "the acceptance now outlives the seam -- if this was a deliberate extension, retire this "
            "test with the ADR that made it")
        # 2026-10-01 -> 2026-11-05 inclusive: 35 days, five Saturday scans.
        assert (leaves - until).days == 35, "the halt gap changed; re-read binder item 07"

    def test_the_scan_halts_the_day_after_the_acceptance_lapses(self):
        from nq.data.adjustment_guard import assert_no_live_escalation, live_exposure

        oh = {"TRENT": pd.DataFrame(
            {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1]},
            index=pd.to_datetime(["2026-01-01"]))}
        known = {self.SEAM: self._entry()}

        ok = live_exposure(oh, (), as_of="2026-10-01", known=known)
        assert ok["escalate"] is False, "the acceptance still holds on the review date itself"

        for day in ("2026-10-02", "2026-11-05"):
            with pytest.raises(ValueError, match="ESCALATION TRIGGER FIRED"):
                assert_no_live_escalation(oh, (), as_of=day, known=known)

        after = live_exposure(oh, (), as_of="2026-11-06", known=known)
        assert after["escalate"] is False, "seam has left the 44-week window; it self-resolves"

    def test_only_the_saturday_scanner_is_halted(self):
        """Bounds the blast radius: the weekday monitor does not run the guarded script, so daily
        re-pricing of held positions survives the halt. Five weekly scans do not."""
        root = Path(__file__).resolve().parents[1]
        wf = root / ".github" / "workflows"
        callers = [p.name for p in wf.glob("*.yml")
                   if "run_bhanushali_cron" in p.read_text(encoding="utf-8")]
        assert callers == ["cron-bhanushali-scanner.yml"], f"blast radius changed: {callers}"
        sats = pd.date_range("2026-10-02", "2026-11-05", freq="D")
        assert sum(d.weekday() == 5 for d in sats) == 5
