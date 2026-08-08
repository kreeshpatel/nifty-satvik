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
    """The input snapshot itself is hash-pinned — a fixture edit must be deliberate.

    The digest is taken over NEWLINE-NORMALISED bytes. Hashing raw bytes made this check
    platform-dependent: with core.autocrlf=true the Windows working tree holds CRLF while git
    stores (and Linux CI checks out) LF, so the identical committed file hashed two ways and CI
    went red while local was green. Normalising removes the platform artifact, not the check —
    any real content edit still changes the digest."""
    from build_r94_golden_fixture import fixture_csv_sha16
    got = fixture_csv_sha16(FIXTURE_CSV)
    assert got == expected["fixture_csv_sha16"], (
        "golden fixture CSV changed; regenerate expectations deliberately "
        "(python scripts/build_r94_golden_fixture.py) and state the diff in the commit")


def test_fixture_hash_is_line_ending_invariant(tmp_path):
    """The regression guard for the CI-red cause: CRLF and LF renderings of the same content must
    hash identically, while a genuine content change must not."""
    from build_r94_golden_fixture import fixture_csv_sha16
    body = b"ticker,date,Close\nAAA,2020-01-01,100.0\nAAA,2020-01-02,101.0\n"
    lf, crlf = tmp_path / "lf.csv", tmp_path / "crlf.csv"
    lf.write_bytes(body)
    crlf.write_bytes(body.replace(b"\n", b"\r\n"))
    assert fixture_csv_sha16(lf) == fixture_csv_sha16(crlf)

    changed = tmp_path / "changed.csv"
    changed.write_bytes(body.replace(b"101.0", b"101.5"))
    assert fixture_csv_sha16(changed) != fixture_csv_sha16(lf), "the check must still catch edits"


def test_synth_universe_is_deterministic():
    """No RNG / clock anywhere in the fixture generator: two builds must be identical."""
    from build_r94_golden_fixture import synth_universe
    a_ohlcv, a_idx = synth_universe()
    b_ohlcv, b_idx = synth_universe()
    assert sorted(a_ohlcv) == sorted(b_ohlcv)
    for t in a_ohlcv:
        pd.testing.assert_frame_equal(a_ohlcv[t], b_ohlcv[t])
    pd.testing.assert_series_equal(a_idx, b_idx)


def _drift_report(got: dict, exp: dict, label: str) -> str:
    """Full mismatch report for a golden cell.

    Why this exists (constitution S2-F5): this assertion used to fail on the FIRST differing key in
    alphabetical order. When `curve_hash` drifted on CI in a run that never reproduced (40 clean CI
    runs afterwards; the threading and hash-seed hypotheses both falsified), the failure told us
    only that `curve_hash` differed — not whether `trades`, `sharpe` or `final_equity` also moved.
    Those are different root causes: identical trades with a different curve hash means numeric
    noise in the curve path, while differing trades means selection-level divergence.

    A flake that cannot be reproduced can still be diagnosed if its ONE sighting is informative, so
    every key is now reported together. This does not widen the comparison — every key is still
    compared exactly and any single mismatch still fails.
    """
    diffs = [k for k in sorted(exp) if got.get(k) != exp[k]]
    lines = [f"{label} drifted on {len(diffs)} key(s): {diffs}",
             "The 0094 run of record is no longer reproducible — this is not a fixture refresh.",
             "--- full cell comparison (got vs golden) ---"]
    for k in sorted(exp):
        mark = "DIFF" if k in diffs else "ok  "
        lines.append(f"  [{mark}] {k}: got={got.get(k)!r} golden={exp[k]!r}")
    lines.append("--- interpreting this (S2-F5) ---")
    scalar_same = all(got.get(k) == exp[k] for k in ("trades", "n_ledger", "final_equity")
                      if k in exp)
    if scalar_same and diffs:
        lines.append("  trades/n_ledger/final_equity MATCH -> divergence is in the curve/ledger "
                     "hash path only, i.e. numeric or ordering noise, NOT trade selection.")
    elif diffs:
        lines.append("  trade-level values differ -> selection-level divergence, not numeric noise.")
    return "\n".join(lines)


def test_curve_key_is_pinned_above_float_noise_and_below_real_drift(cells):
    """Constitution S2-F5, resolved. The curve pin must survive float64 accumulation noise and
    still catch any drift the engine can physically produce.

    The original key rounded to an ABSOLUTE 1e-4 on a series running to ₹1.08e8, where one ULP is
    ~1.9e-9 — a tie boundary only ~5e4 ULP away, with 111 of 1458 points inside 1000 ULP of one.
    Cross-platform summation order moves an accumulated 1e8 by more than that, so the hash flipped
    on Linux CI (54deb7e30a293cb9) while every economically meaningful field — trades, ledger_hash,
    final_equity, sharpe, cagr, max_dd, exit_reasons — stayed byte-identical, and Windows reproduced
    the pinned value at the same commit AND at a558c73, the last commit CI passed. The engine did
    not drift; the check was pinned below the precision the computation reproduces.

    Both directions are asserted, because a repin that only bought robustness would be a muzzle.
    """
    from build_r94_golden_fixture import _curve_key, synth_universe, START_FIX
    import numpy as np
    import run_bhanushali_weekly_rank as R94

    ohlcv, index = synth_universe()
    curve = R94.backtest(R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index), None,
                         ledger=[], start=START_FIX)["curve"]
    base = _curve_key(curve)

    # (a) ROBUST: perturbing every point by 4096 ULP — far beyond any observed cross-platform
    #     divergence, and ~4e-13 relative — must not move the key.
    ulp = np.array([np.spacing(float(v)) for v in curve.values])
    for sign in (+1, -1):
        jittered = pd.Series(curve.values + sign * 4096 * ulp, index=curve.index)
        assert _curve_key(jittered) == base, (
            f"curve key moved under {sign:+d}4096 ULP of float noise — it is pinned below the "
            "precision this computation reproduces, which is what made CI flake")

    # (b) STILL A CHECK: a drift of 1e-6 relative (₹108 on ₹1.08e8) — three orders of magnitude
    #     SMALLER than one different trade, fill or exit day — must still be caught.
    drifted = pd.Series(curve.values * (1 + 1e-6), index=curve.index)
    assert _curve_key(drifted) != base, "curve key no longer detects a 1e-6 relative drift"

    # (c) The path's SHAPE stays pinned byte-for-byte: dates are exact strings, length is the list.
    assert [d for d, _ in base] == [str(d.date()) for d in curve.index]
    dropped = pd.Series(curve.values[:-1], index=curve.index[:-1])
    assert _curve_key(dropped) != base, "curve key no longer detects a truncated path"


def test_frozen_defaults_cell_byte_identical(cells, expected):
    """FROZEN 0094 configuration — may NEVER change. Any diff = the research engine drifted."""
    got, exp = cells[0], expected["frozen_defaults"]
    assert all(got.get(k) == exp[k] for k in exp), _drift_report(got, exp, "FROZEN R94 engine")


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


def test_event_badge_cannot_perturb_the_golden():
    """The event-proximity badge (display-only, added 2026-08-06) reads the REAL PIT results
    calendar from disk, so it is the one card field that is not hermetic by construction.

    It stays inert here only because no synthetic fixture ticker is a real NSE symbol. That is an
    accident waiting to break: rename a fixture ticker onto a real one and the envelope hash moves
    for a reason nobody would look for. Pin it.
    """
    from build_r94_golden_fixture import synth_universe
    try:
        from nq.data.delivery import apply_alias_map
        from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table
    except ImportError:                                     # layer absent -> badge can never fire
        return
    if not EARNINGS_RAW_PATH.exists():                      # no feed in CI -> badge degrades to off
        return
    ohlcv, _ = synth_universe()
    calendar = set(build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))["symbol"])
    collisions = sorted(set(ohlcv) & calendar)
    assert not collisions, (
        f"fixture ticker(s) {collisions} exist in the real results calendar, so the event badge "
        "can fire inside the hermetic golden and move envelope_hash — rename the fixture ticker")


def test_b1_gate_off_is_inert(cells, expected):
    """Belt-and-braces: the gate defaults OFF, so the frozen research cell is untouched by the
    fix's mere existence (this is what makes the 0094 run of record still reproducible)."""
    assert cells[0]["ledger_hash"] == expected["frozen_defaults"]["ledger_hash"]
    assert cells[1]["paper_ledger_hash"] == expected["live_config"]["paper_ledger_hash"]
    assert cells[1]["paper_ledger_hash"] != cells[2]["paper_ledger_hash"], (
        "gate ON and OFF produced the same ledger — the fixture no longer proves the fix runs")
