"""GOLDEN MASTER for ``nq.engine.rebalance_book`` — the engine behind pre-registration 0001.

Why this file exists. Golden masters covered `portfolio.simulate` (`test_stage2_golden`), the feature
layer (`test_stage1_golden`) and the live weekly-swing engine (`test_r94_golden`). `rebalance_book`
had none. Its 33 tests in `test_rebalance_book.py` are synthetic-panel unit and property tests on
twelve hand-built names — excellent at pinning *invariants*, incapable of noticing that the engine
now produces a different book on real data. That engine produced **six defects in a single session**
(2026-08-07) and carries the PROMOTE-CANDIDATE verdict for 0001, which made it simultaneously the
least proven engine in the repo and the only one with no pinned real-data output.

What a golden master is, and is not. Following Feathers, this is a CHARACTERIZATION test: it asserts
that behaviour is *unchanged*, not that behaviour is *correct*. It pins whatever the engine does
today, bugs included. It is a safety net for refactoring and nothing else, and it must never be cited
as evidence that a result is right.

**The fixture is a losing book (CAGR -9.1%) and that is deliberate — it is a slice chosen for path
coverage, not for performance. No number in this file is a research result.**

What is pinned:
  * the input CSV, by sha256 of its newline-normalised bytes, so a fixture edit must be deliberate;
  * every headline metric, compared exactly;
  * the trade ledger, hashed over (ticker, dates, reason, qty, return) — catches drift that nets out
    in the aggregates;
  * the full equity path, hashed over (date, equity, n_positions) — two very different paths can
    share a final value, and the drawdown lives in the path.

Regenerate deliberately with ``python scripts/build_rebalance_golden_fixture.py``, in the SAME commit
as the change that moved it, stating the diff.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book  # noqa: E402

FIXTURE_CSV = ROOT / "tests" / "fixtures" / "rebalance_golden_panel.csv"
EXPECTED_JSON = ROOT / "tests" / "fixtures" / "rebalance_golden_expected.json"


@pytest.fixture(scope="module")
def expected() -> dict:
    assert EXPECTED_JSON.exists(), f"golden expectations missing: {EXPECTED_JSON}"
    return json.loads(EXPECTED_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def golden(expected) -> dict:
    assert FIXTURE_CSV.exists(), f"golden fixture missing: {FIXTURE_CSV}"
    from build_rebalance_golden_fixture import run_golden
    return run_golden(pd.read_csv(FIXTURE_CSV))


def test_fixture_csv_unchanged(expected):
    """The input snapshot is hash-pinned. A golden whose input can drift proves nothing about the
    engine — the output would move for a reason the test could not distinguish from a code change."""
    from build_rebalance_golden_fixture import fixture_csv_sha16
    got = fixture_csv_sha16(FIXTURE_CSV)
    assert got == expected["fixture_csv_sha16"], (
        "golden fixture CSV changed; regenerate expectations deliberately "
        "(python scripts/build_rebalance_golden_fixture.py) and state the diff in the commit")


def test_fixture_hash_is_line_ending_invariant(tmp_path):
    """CRLF and LF renderings of identical content must hash the same; a real edit must not.

    Without this, `core.autocrlf=true` on the Windows dev machine stores LF but checks out CRLF,
    while Linux CI checks out LF — so the same committed file hashes two ways and the golden goes
    red on CI only. `test_r94_golden.py` was reddened by exactly that.
    """
    from build_rebalance_golden_fixture import fixture_csv_sha16
    body = b"date,ticker,close\n2020-01-01,AAA,100.0\n2020-01-02,AAA,101.0\n"
    lf, crlf, changed = tmp_path / "lf.csv", tmp_path / "crlf.csv", tmp_path / "ch.csv"
    lf.write_bytes(body)
    crlf.write_bytes(body.replace(b"\n", b"\r\n"))
    changed.write_bytes(body.replace(b"101.0", b"101.5"))
    assert fixture_csv_sha16(lf) == fixture_csv_sha16(crlf)
    assert fixture_csv_sha16(changed) != fixture_csv_sha16(lf), "the check must still catch edits"


def _drift_report(got: dict, exp: dict) -> str:
    diffs = [k for k in sorted(exp) if got.get(k) != exp[k]]
    lines = [f"rebalance_book golden drifted on {len(diffs)} key(s): {diffs}",
             "This is NOT a fixture refresh — the engine produces a different book than the pin.",
             "--- full comparison (got vs golden) ---"]
    for k in sorted(exp):
        lines.append(f"  [{'DIFF' if k in diffs else 'ok  '}] {k}: "
                     f"got={got.get(k)!r} golden={exp[k]!r}")
    # The same diagnostic split test_r94_golden earned the hard way: identical trades with a moved
    # curve hash is numeric/ordering noise; moved trades is selection-level divergence. They have
    # completely different causes and the failure should say which it is.
    scalar_same = all(got.get(k) == exp[k] for k in ("n_trades", "final_equity", "ledger_hash")
                      if k in exp)
    lines.append("  -> trades and ledger MATCH: divergence is in the curve path only "
                 "(numeric or ordering noise), NOT trade selection."
                 if scalar_same and diffs else
                 "  -> trade-level values differ: selection-level divergence, not numeric noise.")
    return "\n".join(lines)


def test_golden_cell_is_byte_identical(golden, expected):
    """THE gate. Every pinned key at once, so one run reports the whole picture."""
    exp = expected["cells"]["frozen_0001_engine"]
    assert golden == exp, _drift_report(golden, exp)


def test_the_pinned_book_matches_the_expectations_header(expected):
    """The config the golden was built under is recorded alongside it, so a silent change to BOOK
    in the builder cannot quietly re-point the golden at a different strategy."""
    from build_rebalance_golden_fixture import BOOK, CAPITAL, END, START
    assert expected["book"] == BOOK
    assert expected["window"] == [START, END]
    assert expected["initial_capital"] == CAPITAL


def test_the_fixture_actually_exercises_the_engine(golden, expected):
    """A golden can pass while pinning almost nothing. This asserts the run is worth pinning.

    The first build of this fixture filtered ROWS by size band instead of gating the RANK — the very
    defect pre-registration 0001 had to learn — which left ~5 quotable names a day against a 15-slot
    book, 28 stale force-closes out of 317 trades, and a golden that pinned the bug rather than the
    engine. These floors would have caught it.
    """
    assert golden["n_trades"] >= 100, "too few trades to pin meaningful behaviour"
    assert golden["avg_positions_held"] >= 5.0, "book is starved — slot logic barely exercised"
    assert golden["exit_reasons"].get("rebalance_trim", 0) > 0, "no trims: weighting path untested"
    assert golden["exit_reasons"].get("rebalance_exit", 0) > 0, "no exits: ranking path untested"
    assert golden["exit_reasons"].get("stale", 0) == 0, (
        "stale force-closes present — the panel has holes, which means rows are being filtered "
        "somewhere they should not be")
    assert expected["n_names"] >= 20


def test_the_engine_is_reproducible_on_the_fixture(golden):
    """Two runs of the same fixture must agree exactly — otherwise the golden's green is luck."""
    from build_rebalance_golden_fixture import run_golden
    assert run_golden(pd.read_csv(FIXTURE_CSV)) == golden


def test_a_cfg_gated_overlay_leaves_the_golden_untouched():
    """The engine invariant, checked against REAL data rather than a synthetic panel.

    `rebalance_band` defaults to 0.0. The claim that an overlay is inert when off is exactly the kind
    of claim that holds on twelve hand-built names and fails on a real one.
    """
    from build_rebalance_golden_fixture import BOOK, CAPITAL, END, START
    panel = pd.read_csv(FIXTURE_CSV)
    a = simulate_rebalance_book(panel, cfg=RebalanceConfig(**BOOK), start=START, end=END,
                                initial_capital=CAPITAL)
    b = simulate_rebalance_book(panel, cfg=RebalanceConfig(**BOOK, rebalance_band=0.0),
                                start=START, end=END, initial_capital=CAPITAL)
    assert a["equity_curve"] == b["equity_curve"]
    assert a["trades"] == b["trades"]
