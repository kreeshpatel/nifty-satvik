"""The complete demerger register — the enforceability prerequisite for binder §10.

The pinned data applies BOTH demerger conventions: 22 events back-adjusted (total-return), 15 left
as cliffs (listed-entity). Either is defensible; both is not. The October decision cannot be
enforced while the committed reference names only 4 of 37 events, so the register enumerates them.

These tests exist to keep the register **descriptive**. The temptation it must survive is someone
filling in the `convention` column — which would be the owner's decision taken by a data edit.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "corporate_actions_demerger_register.csv"
PRESCRIPTIVE = ROOT / "data" / "corporate_actions_demergers.csv"

VALID_TREATMENTS = {"BACK_ADJUSTED", "LEFT_AS_CLIFF", "UNRESOLVED"}


def _rows() -> list[dict]:
    if not REGISTER.exists():
        pytest.skip("demerger register not present in this checkout")
    lines = [ln for ln in REGISTER.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def test_register_is_complete_and_shaped():
    rows = _rows()
    assert len(rows) == 37, f"the audit found 37 demergers; the register has {len(rows)}"
    assert len({r["ticker"] for r in rows}) == 35
    for r in rows:
        assert r["ticker"] and r["ex_date"]
        assert r["vendor_treatment"] in VALID_TREATMENTS, r


def test_convention_is_undecided_everywhere():
    """The whole point. Populating this column IS the binder §10 decision; it may not arrive by
    data entry, by a helpful default, or by a build step."""
    rows = _rows()
    values = {r["convention"] for r in rows}
    assert values == {"UNDECIDED"}, (
        f"convention column carries {sorted(values)} — a convention has been applied to the data "
        "without an owner decision. Binder section 10 is the only thing that may change this.")


def test_both_conventions_are_present_which_is_the_finding():
    """If this ever passes with one treatment, the data changed and the binder item is stale."""
    rows = _rows()
    treatments = [r["vendor_treatment"] for r in rows]
    assert treatments.count("BACK_ADJUSTED") == 22
    assert treatments.count("LEFT_AS_CLIFF") == 15


def test_a_single_name_carries_both_treatments():
    """AARTIIND has two demergers handled two ways — the cleanest demonstration that the pin is not
    merely inconsistent across names but within one series."""
    rows = _rows()
    by_name: dict[str, set] = {}
    for r in rows:
        by_name.setdefault(r["ticker"], set()).add(r["vendor_treatment"])
    both = sorted(n for n, t in by_name.items() if len(t) > 1)
    assert both == ["AARTIIND"], both


def test_the_prescriptive_file_is_untouched():
    """`nq.data.ohlcv` reads the OTHER file to decide cleaning. Extending it would apply the
    listed-entity convention to all 37 events — i.e. decide §10 by editing a data file."""
    body = [ln for ln in PRESCRIPTIVE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    assert body[0].startswith("ticker,date")
    assert len(body) - 1 == 4, (
        f"the prescriptive demerger reference has {len(body) - 1} rows, expected 4. If this grew, a "
        "convention was applied to the live cleaner without an ADR.")


def test_the_two_files_are_not_confused_for_each_other():
    """A reader must be able to tell which one drives behaviour."""
    head = REGISTER.read_text(encoding="utf-8")[:1200]
    assert "DESCRIPTIVE, NOT PRESCRIPTIVE" in head
    assert "corporate_actions_demergers.csv" in head, "must point at the file that IS read"
