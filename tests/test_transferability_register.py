"""The transferability register is regenerable, internally consistent, and states its own limits.

The register's product is four counts, so the counts must be recomputable rather than asserted.
These tests pin the properties that make them trustworthy — not the values themselves, which are a
classification and will move as the corpus grows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_transferability_register import (  # noqa: E402
    BAND, CONFIG_P, CORRECTED_UNIVERSE, OUT, band_bookmatch, counts, in_band, render, rows,
    universe_of,
)

RS = rows()
C = counts(RS)
BINDS = {"YES", "NO", "ARGUED"}


class TestTheClassificationIsWellFormed:
    def test_every_id_is_unique(self):
        ids = [r["id"] for r in RS]
        assert len(ids) == len(set(ids))

    def test_every_binds_column_uses_the_closed_vocabulary(self):
        for r in RS:
            for k in ("swing", "frozen", "breadth50"):
                assert r[k] in BINDS, f"{r['id']}.{k} = {r[k]!r}"

    def test_every_book_and_exit_regime_is_from_the_documented_set(self):
        for r in RS:
            assert r["book"] in {"LH", "SWING", "SUBSTRATE", "SLEEVE", "EXTERNAL", "AUDIT"}
            assert r["exit_regime"] in {"ladder-LH", "ladder-0094", "P2", "configP", "own"}
            assert r["unit"] in {"R", "Sharpe", "eq%", "net%", "IC"}

    def test_every_row_carries_a_note(self):
        """A classification without a stated reason is an assertion, which is what this file exists
        to stop. ARGUED rows especially: the whole point is that the argument is written down."""
        for r in RS:
            assert len(r["note"]) >= 20, r["id"]

    def test_every_ARGUED_row_explains_the_mechanism_at_length(self):
        for r in RS:
            if "ARGUED" in (r["swing"], r["frozen"], r["breadth50"]):
                assert len(r["note"]) >= 60, (
                    f"{r['id']} claims ARGUED but its note is too short to carry an argument")

    def test_dates_are_iso_and_within_the_programme(self):
        for r in RS:
            assert len(r["date"]) == 10 and r["date"][4] == "-"
            assert "2026-06-01" <= r["date"] <= "2026-12-31", r["id"]


class TestTheDerivationsAreRight:
    def test_universe_splits_on_the_backfill_date(self):
        assert universe_of("2026-07-02") == "survivor-pin"
        assert universe_of(CORRECTED_UNIVERSE) == "corrected"

    def test_in_band_is_none_when_no_margin_was_published(self):
        assert in_band({"margin": None}) is None

    def test_in_band_is_symmetric_and_strict(self):
        assert in_band({"margin": 0.30}) is True
        assert in_band({"margin": -0.30}) is True
        assert in_band({"margin": -0.40}) is False

    def test_the_band_only_claims_book_match_where_it_was_measured(self):
        """±0.302 came off the swing book. Claiming it describes an LH row is the exact error this
        register is about, so the flag must not quietly include LH/EXTERNAL rows."""
        assert band_bookmatch({"book": "SWING"}) and band_bookmatch({"book": "SUBSTRATE"})
        for b in ("LH", "SLEEVE", "EXTERNAL", "AUDIT"):
            assert not band_bookmatch({"book": b}), b

    def test_counts_partition_the_corpus(self):
        assert (len(C["binds_swing_yes"]) + len(C["binds_swing_argued"])
                + len(C["binds_swing_no"])) == C["total"]

    def test_the_in_band_subset_is_bounded_by_the_rows_that_publish_a_margin(self):
        assert len(C["in_band"]) <= len(C["margin_known"]) <= C["total"]
        assert len(C["in_band_bookmatched"]) <= len(C["in_band"])

    def test_cross_book_never_includes_a_row_that_binds_on_its_own_measurement(self):
        assert not [r for r in C["cross_book"] if r["swing"] == "YES"]

    def test_untested_here_is_a_subset_of_does_not_bind_swing(self):
        assert set(r["id"] for r in C["untested_here"]) <= set(
            r["id"] for r in C["binds_swing_no"])


class TestTheDocumentSaysWhatItMustSay:
    def test_it_regenerates_byte_identically(self):
        assert OUT.exists(), "run scripts/build_transferability_register.py"
        assert OUT.read_text(encoding="utf-8") == render(RS, C), (
            "TRANSFERABILITY_REGISTER.md is stale — regenerate it from the script")

    def test_the_counts_are_frozen_at_16_1_138(self):
        t = OUT.read_text(encoding="utf-8")
        assert "screens 16" in t and "sealed opens 1" in t and "n_trials 138" in t

    def test_it_declares_itself_verification_class_with_zero_trials(self):
        t = OUT.read_text(encoding="utf-8")
        assert "Zero trials, zero screens" in t

    def test_the_guard_forbids_reviving_anything(self):
        """A transferability failure is UNTESTED-HERE, never OPEN-FOR-RETEST."""
        t = OUT.read_text(encoding="utf-8")
        assert "UNTESTED-HERE" in t
        assert "not* OPEN-FOR-RETEST" in t or "not OPEN-FOR-RETEST" in t
        assert "n_trials` pricing" in t or "n_trials pricing" in t

    def test_it_reports_the_band_count_as_a_range_not_a_point(self):
        t = OUT.read_text(encoding="utf-8")
        assert f"{len(C['in_band_bookmatched'])}–{len(C['in_band'])}" in t

    def test_it_names_the_measured_non_transfer(self):
        """O-009 PROMOTED on LH and KILLED on swing is the register's existence proof; without it
        this is an argument from theory."""
        t = OUT.read_text(encoding="utf-8")
        assert "O-009" in t and "0095" in t and "PROMOTED" in t and "KILLED" in t

    def test_the_two_pivot_dates_appear(self):
        t = OUT.read_text(encoding="utf-8")
        assert CORRECTED_UNIVERSE in t and CONFIG_P in t and str(BAND) in t


@pytest.mark.parametrize("row_id,expected_book", [
    ("O-009 vol-target de-gross", "LH"),
    ("0095 vol-target de-gross", "SWING"),
])
def test_the_same_lever_is_classified_to_two_different_books(row_id, expected_book):
    """The pair that proves the register is measuring something real."""
    got = next(r for r in RS if r["id"] == row_id)
    assert got["book"] == expected_book
