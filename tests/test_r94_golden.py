"""R94 GOLDEN MASTER — the byte-identical gate for the LIVE weekly-swing engine.

Constitution M1. The momentum engine has ``tests/test_stage2_golden.py``; the live swing engine
(``scripts/run_bhanushali_weekly_rank.py`` + the cron's card builder) had no equivalent — its
"every lever defaults OFF => byte-identical" claims were enforced by comments alone.

Two pinned cells, both run on the hermetic synthetic fixture (``tests/fixtures/r94_golden_*``,
built by ``scripts/build_r94_golden_fixture.py`` — closed-form price paths, no RNG, no network,
no live cache):

  * ``frozen_defaults`` — ``backtest()`` with every lever at its default: the frozen 0094 research
    configuration. **This cell may never change.** A diff means the frozen engine drifted and the
    0094 run of record is no longer reproducible.
  * ``live_config`` — exactly what ``scripts/run_bhanushali_cron.py`` runs: the Grade-A set,
    ``LIVE_DISCIPLINE`` + ``LIVE_EXIT`` (config P), the capped ₹10L paper book, the uncapped signal
    ledger, and the dashboard envelope/cards. This cell changes ONLY with a documented owner
    config change — regenerate the fixture in the SAME commit and state the diff.

The fixture includes a SUSPENSION case (``SUSPX`` stops printing bars mid-hold), so the golden
captures constitution bug **B-1** (absent-bar positions are unmanageable and marked at ENTRY
price in NAV) as behaviour of record. The B-1 fix is cfg-gated: with the gate OFF these
assertions must still hold byte-for-byte; ``test_b1_probe_pins_current_behaviour`` is the
explicit anchor for that diff.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "r94_golden_ohlcv.csv"
EXPECTED_JSON = ROOT / "tests" / "fixtures" / "r94_golden_expected.json"


@pytest.fixture(scope="module")
def expected() -> dict:
    assert EXPECTED_JSON.exists(), f"golden expectations missing: {EXPECTED_JSON}"
    return json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cells():
    """Run all golden cells once (the builder is the single source of the run logic)."""
    assert FIXTURE_CSV.exists(), f"golden fixture missing: {FIXTURE_CSV}"
    from build_r94_golden_fixture import run_cells, synth_universe
    ohlcv, index = synth_universe()
    return run_cells(ohlcv, index)


def test_fixture_csv_unchanged(expected):
    """The input snapshot itself is hash-pinned — a fixture edit must be deliberate."""
    got = hashlib.sha256(FIXTURE_CSV.read_bytes()).hexdigest()[:16]
    assert got == expected["fixture_csv_sha16"], (
        "golden fixture CSV changed; regenerate expectations deliberately "
        "(python scripts/build_r94_golden_fixture.py) and state the diff in the commit")


def test_synth_universe_is_deterministic():
    """No RNG / clock anywhere in the fixture generator: two builds must be identical."""
    from build_r94_golden_fixture import synth_universe
    a_ohlcv, a_idx = synth_universe()
    b_ohlcv, b_idx = synth_universe()
    assert sorted(a_ohlcv) == sorted(b_ohlcv)
    for t in a_ohlcv:
        pd.testing.assert_frame_equal(a_ohlcv[t], b_ohlcv[t])
    pd.testing.assert_series_equal(a_idx, b_idx)


def test_frozen_defaults_cell_byte_identical(cells, expected):
    """FROZEN 0094 configuration — may NEVER change. Any diff = the research engine drifted."""
    got, exp = cells[0], expected["frozen_defaults"]
    for k in sorted(exp):
        assert got[k] == exp[k], (
            f"FROZEN R94 engine drifted on '{k}': got {got[k]!r}, golden {exp[k]!r}. "
            "The 0094 run of record is no longer reproducible — this is not a fixture refresh.")


def test_live_config_cell_byte_identical(cells, expected):
    """The LIVE cron configuration (Grade-A + discipline + config P) — the book, the NAV curve,
    and the dashboard cards. Changes only with a documented owner config change."""
    got, exp = cells[1], expected["live_config"]
    for k in sorted(exp):
        assert got[k] == exp[k], (
            f"LIVE swing config drifted on '{k}': got {got[k]!r}, golden {exp[k]!r}. "
            "If intentional, regenerate the fixture in the same commit and document the diff.")


def test_live_cell_exercises_every_exit_branch(cells):
    """Guard on the GUARD: a golden that only ever exercises the time cap would not detect an
    exit-logic regression. Pin that the live cell really does traverse the stop and runner
    branches, and that a Grade-A card set is produced."""
    live = cells[1]
    # Coverage is asserted on the UNCAPPED ledger: it funds every Grade-A signal, so its exit mix
    # is the full lifecycle. The capped book's mix depends on who won the cash race, so a fixture
    # edit that merely reorders funding must not read as a lost exit branch.
    reasons = set(live["uncapped_exit_reasons"])
    assert {"stop", "sma_break"} <= reasons, f"golden lost exit coverage: {reasons}"
    assert live["paper_n_ledger"] > 20, "golden lost trade volume"
    assert live["n_signals"] > 0, "golden produces no cards — card path unpinned"


def test_b1_probe_pins_current_behaviour(cells, expected):
    """Constitution B-1, pinned as behaviour OF RECORD (a bug the golden deliberately captures).

    A held name whose bars stop mid-hold is never exited (the exit loop skips a missing bar) and
    is carried in NAV at its ENTRY price rather than its last traded close. The cfg-gated fix must
    leave this byte-identical with the gate OFF; with the gate ON, the diff must be isolated to
    exactly these positions."""
    got, exp = cells[1]["b1_absent_bar_positions"], expected["live_config"]["b1_absent_bar_positions"]
    assert got == exp, f"B-1 absent-bar behaviour changed: got {got!r}, golden {exp!r}"
    assert exp, "fixture no longer exercises the absent-bar (suspension) case"
    for tkr, rec in exp.items():
        assert rec["marked_at_entry_not_last_close"] is True
        assert rec["last_bar"] < expected["live_config"]["generated_at"], (
            f"{tkr} is not actually stale in the fixture")


def test_b1_fixed_cell_byte_identical(cells, expected):
    """The live config with the B-1 staleness gate ON — the fix's pinned output."""
    got, exp = cells[2], expected["live_config_b1_fixed"]
    for k in sorted(exp):
        assert got[k] == exp[k], (
            f"B-1-fixed cell drifted on '{k}': got {got[k]!r}, golden {exp[k]!r}")


def test_b1_fix_parameter_mirrors_momentum_engine(cells):
    """The staleness threshold is the momentum engine's constant, not a new invented parameter."""
    from nq.engine.portfolio import STALE_ABSENT_DAYS
    assert cells[2]["stale_absent_days"] == STALE_ABSENT_DAYS == 10


def test_b1_fix_diff_is_isolated_to_the_stale_position(cells):
    """The fix's blast radius: it may ONLY release the bar-less holding.

    Nothing else may move — no other position opens or closes, and every stale exit must be a
    name the fixture actually suspended, priced at its LAST TRADED close (never the entry mark)."""
    base, fixed = cells[1], cells[2]
    diff = fixed["diff_vs_live_config"]
    stale_names = {r["tkr"] for r in fixed["stale_exits"]}
    absent_names = set(base["b1_absent_bar_positions"])

    assert stale_names == absent_names, (
        f"stale exits {stale_names} != the fixture's absent-bar holdings {absent_names}")
    assert diff["positions_added"] == [], "the fix opened a position — out of blast radius"
    assert set(diff["positions_released"]) == absent_names
    assert diff["closed_trades_delta"] == len(stale_names)
    # every other closed trade is untouched: base ledger + the stale exits == fixed ledger
    assert fixed["paper_n_ledger"] == base["paper_n_ledger"] + len(stale_names)
    for r in fixed["stale_exits"]:
        probe = base["b1_absent_bar_positions"][r["tkr"]]
        assert r["exit_px"] == probe["last_close"], (
            "stale exit must fill at the LAST TRADED close, not the entry mark")
        assert r["exit_px"] != r["entry"] or probe["last_close"] == probe["entry"]
        assert r["stale_absent_sessions"] == fixed["stale_absent_days"]


def test_d5_card_parity_receipt(cells):
    """Constitution D5: every FRESH buy card must price off the stop the RECORD will use.

    The fixture carries a wide-candle name whose raw signal-week low sits further than the risk cap
    below entry, so the discipline lift genuinely binds — the case where the old card and the book
    disagreed. Asserting `stop_record == max(raw_low, entry x (1 - max_risk_pct))` per card pins the
    parity relationship itself, not a snapshot."""
    from run_bhanushali_cron import LIVE_DISCIPLINE, TARGET_R
    cards = cells[2]["fresh_cards"]
    assert cards, "fixture produces no fresh buy cards — the card path would be unpinned"
    mrp = LIVE_DISCIPLINE["max_risk_pct"]
    for c in cards:
        expect_stop = max(c["stop_prefix_raw_low"], c["entry"] * (1.0 - mrp))
        assert c["stop_record"] == pytest.approx(expect_stop, abs=0.01), (
            f"{c['ticker']}: card stop {c['stop_record']} != the record's {expect_stop}")
        assert c["target_record"] == pytest.approx(
            c["entry"] + TARGET_R * (c["entry"] - c["stop_record"]), abs=0.01)
        assert c["risk_pct_record"] <= mrp * 100 + 0.01, "card R exceeds the record's risk cap"
        tr = {t[0]: t for t in c["tranche_levels"]}
        assert tr["target"][1] == pytest.approx(c["target_record"], abs=0.01), (
            "the +2R tranche on the card must equal the card's stated target")

    binding = [c for c in cards if c["stop_delta"] > 0]
    assert binding, ("no fixture card has a raw low outside the risk cap — the D5 fix would only "
                     "be exercised in its no-op branch")
    for c in binding:
        assert c["target_delta"] < 0, (
            "lifting the stop must PULL IN the +2R target; a positive delta means the arithmetic "
            "is inverted")
        assert c["risk_pct_prefix"] > c["risk_pct_record"]


def test_b1_gate_off_is_inert(cells, expected):
    """Belt-and-braces: the gate defaults OFF, so the frozen research cell is untouched by the
    fix's mere existence (this is what makes the 0094 run of record still reproducible)."""
    assert cells[0]["ledger_hash"] == expected["frozen_defaults"]["ledger_hash"]
    assert cells[1]["paper_ledger_hash"] == expected["live_config"]["paper_ledger_hash"]
    assert cells[1]["paper_ledger_hash"] != cells[2]["paper_ledger_hash"], (
        "gate ON and OFF produced the same ledger — the fixture no longer proves the fix runs")
