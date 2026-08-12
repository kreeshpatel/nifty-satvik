"""The activation-bound harness.

The standing law says no usage trial may be pre-registered until a zero-trial clairvoyant bound has
been run against the ±10 R/yr floor. Four scripts each re-implemented that method; this is the fifth
shape, so the method moved into one harness.

A harness that cannot reproduce a KNOWN answer may not be believed on an unknown one, so the
validation against 0119's published -1.29 R/yr is a hard precondition rather than a nicety. The other
tests cover the two ways this class of tool goes quietly wrong: counting activations that could never
have changed a funded decision, and letting a bound be run before its multiplicity is priced.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pipelines" / "diagnostics" / "bound_selectivity.py"
_HAS_SUBSTRATE = (ROOT / "research" / "substrate" / "trades.parquet").exists()


def _mod():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("bound_selectivity", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sub(rows):
    """rows: (iw, ticker, crs, R, ext, funded)"""
    d = pd.DataFrame(rows, columns=["iw", "ticker", "rank_crs", "R", "ext_vs_sma", "funded"])
    d["entry_date"] = pd.Timestamp("2020-06-01")
    return d


# --------------------------------------------------------------------------- frozen constants
def test_the_constants_are_the_family_constants():
    m = _mod()
    assert m.FLOOR_R_PER_YR == 10.0, "the 0109/0117 path-noise floor"
    assert (m.TRAIN_LO, m.TRAIN_HI) == ("2019-01-01", "2024-06-30"), "the pre-reg 0116 split"
    assert m.YRS == 5.5
    assert m.NEAR_SMA_EXT_PCT == 5.0, "frozen to the census band edge, not chosen after the fact"


def test_the_size_grid_is_stated_in_advance_and_is_not_a_sweep():
    m = _mod()
    assert isinstance(m.SIZE_GRID, tuple) and len(m.SIZE_GRID) <= 2, "a grid this wide is a sweep"


# --------------------------------------------------------------------------- the funding margin
def test_only_competitive_weeks_are_activations():
    """A week that funded everything, or funded nothing, offers no decision to change. Counting it
    would inflate the activation rate — the statistic the gate turns on."""
    m = _mod()
    all_funded = _sub([("w1", "A", 0.2, 1.0, 3.0, True), ("w1", "B", 0.1, 2.0, 3.0, True)])
    none_funded = _sub([("w2", "A", 0.2, 1.0, 3.0, False), ("w2", "B", 0.1, 2.0, 3.0, False)])
    assert list(m.marginal_pairs(all_funded)) == []
    assert list(m.marginal_pairs(none_funded)) == []


def test_the_margin_is_lowest_funded_against_highest_unfunded():
    m = _mod()
    d = _sub([("w", "HIF", 0.9, 5.0, 3.0, True), ("w", "LOF", 0.2, 1.0, 3.0, True),
              ("w", "HIU", 0.5, 4.0, 3.0, False), ("w", "LOU", 0.05, 0.0, 3.0, False)])
    (_iw, last_f, best_u, _g), = list(m.marginal_pairs(d))
    assert last_f["ticker"] == "LOF", "the marginal slot is the WEAKEST funded name"
    assert best_u["ticker"] == "HIU", "the contender is the STRONGEST unfunded name"


# --------------------------------------------------------------------------- the arithmetic
def test_a_slot_is_not_free_the_displaced_trade_is_charged():
    """Law III. Admitting a name at the margin displaces one; a bound that only counts the gain is
    the error that made every 'these are bad trades' argument look good."""
    m = _mod()
    d = _sub([("w", "OUT", 0.2, 3.0, 30.0, True), ("w", "IN", 0.5, 4.0, 2.0, False)])
    a = m.band_sizing_bound(d, 0.02, 1.0)
    assert a["activations"] == 1
    assert a["mean_delta_R"] == pytest.approx(4.0 - 3.0), "f*R_in - R_out, not R_in alone"


def test_reduced_size_scales_only_the_admitted_leg():
    m = _mod()
    d = _sub([("w", "OUT", 0.2, 2.0, 30.0, True), ("w", "IN", 0.5, 4.0, 2.0, False)])
    assert m.band_sizing_bound(d, 0.02, 0.50)["mean_delta_R"] == pytest.approx(0.5 * 4.0 - 2.0)


def test_only_near_sma_contenders_activate_the_rule():
    m = _mod()
    far = _sub([("w", "OUT", 0.2, 1.0, 30.0, True), ("w", "IN", 0.5, 4.0, 20.0, False)])
    assert m.band_sizing_bound(far, 0.02, 1.0)["activations"] == 0


def test_the_clairvoyant_arm_is_an_unreachable_ceiling():
    """It admits only the winners. It must never be below the realistic arm, and must be labelled a
    ceiling wherever it is reported."""
    m = _mod()
    d = pd.concat([_sub([("w1", "OUT", 0.2, 5.0, 30.0, True), ("w1", "IN", 0.5, 1.0, 2.0, False)]),
                   _sub([("w2", "OUT", 0.2, 1.0, 30.0, True), ("w2", "IN", 0.5, 5.0, 2.0, False)])])
    a = m.band_sizing_bound(d, 0.02, 1.0)
    assert a["clairvoyant_R_per_yr"] >= a["realistic_R_per_yr"]


# --------------------------------------------------------------------------- the gate
def test_the_gate_needs_both_the_floor_and_sign_consistency():
    m = _mod()
    up = {"majority_sign": "+"}
    assert m.gate(20.0, up)["PASS"] is True
    assert m.gate(2.0, up)["PASS"] is False, "below the floor"
    assert m.gate(20.0, {"majority_sign": "-"})["PASS"] is False, "wrong-signed years"
    assert m.gate(20.0, {"majority_sign": "tie"})["PASS"] is False


def test_per_year_sign_counts_years_not_events():
    m = _mod()
    s = m.per_year_sign([(2020, 1.0), (2020, 1.0), (2021, -5.0)])
    assert s["n_years"] == 2 and s["n_positive"] == 1 and s["n_negative"] == 1
    assert s["majority_sign"] == "tie"


# --------------------------------------------------------------------------- ordering is enforced
def test_the_script_refuses_a_bound_without_a_ledger_row(monkeypatch, capsys):
    """The standing rule appends one row per screen BEFORE the run. The harness must not append it
    itself — a tool that both performs and checks an ordering rule enforces nothing."""
    src = SRC.read_text(encoding="utf-8")
    assert "--ledger-row" in src and "REFUSED" in src
    assert "label_screen_ledger" in src
    # it must never write to the ledger
    assert "LEDGER.write_text" not in src and "open(LEDGER" not in src


@pytest.mark.skipif(not _HAS_SUBSTRATE, reason="substrate parquet absent (gitignored; not on CI)")
def test_the_harness_reproduces_the_published_0119_bound():
    """The hard precondition. -1.29 R/yr, 15 swaps, -7.1R over 5.5y — through THIS harness's own
    marginal_pairs, not the original script."""
    m = _mod()
    sub, _ = m.load_frames()
    val = m.validate_0119(sub)
    assert val["PASS"], val
    assert val["reproduced"]["swaps"] == 15
    assert val["reproduced"]["bound_R_per_yr"] == pytest.approx(-1.29, abs=0.01)
