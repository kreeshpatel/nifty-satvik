"""The Saturday post-mortem: pinned by a golden file, and forbidden from touching the sealed log.

Two properties, and the second is non-negotiable:

  1. the page is DETERMINISTIC — `render()` is pure, so a fixed input renders a fixed page, pinned here
     against a golden string rather than against whatever the live book happens to say this week;
  2. the renderer NEVER opens `results/judge_log.jsonl`. A reporting page is exactly the sort of
     convenience that breaches a seal by accident, so the refusal is asserted, not trusted.

Also pinned: the selector bug this page shipped with. `_latest` sorted diagnostics directories by NAME,
so a re-run directory dated after a newer snapshot won, and the first render showed 9 closed trades when
13 had closed. A run date is not a data date.
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

import render_weekly_postmortem as P  # noqa: E402


SCORECARD = {
    "generated_ist": "2026-10-03 18:12",
    "headline": "14/40 closed, 1/4 quarters -> not yet evaluable",
    "forward": {"n_closed": 14, "expectancy_R": -1.40, "win_rate_pct": 0.0,
                "nav": 990000.0, "sharpe": -0.5, "maxdd_pct": -8.0},
    "gates": {
        "readiness": {"n_closed": 14, "quarters_elapsed": 1, "ready": False,
                      "convention": {"book": "uncapped A-only signal tracker"}},
        "promote": {"expectancy_R": -1.40, "maxdd_pct": -8.0, "pass": False,
                    "convention": {"maxdd_book": "capped Rs.10L A-only paper book",
                                   "cagr_years": "calendar", "maxdd_grid": "daily"}},
        "kill": {"sharpe": -0.5, "triggered": True,
                 "convention": {"book": "capped Rs.10L A-only paper book"}},
        "halt": {"maxdd_pct": -8.0, "triggered": False,
                 "convention": {"book": "capped Rs.10L A-only paper book", "grid": "daily"}},
    },
    "swing_grading": {"verdict": "INSUFFICIENT EVIDENCE", "a_only_closed": 14,
                      "base_swing_closed": 2, "floor_per_book": 20,
                      "convention": {"same_quantity": False}},
}
BOOK_IDENTITY = {
    "as_of": "2026-10-03",
    "capped_closures": {"capped_closures": 2, "exact": True},
    "realisation_events": {"n_events": 6},
    "nav_reconciliation": {"implied_realised_pnl": -6101.84, "sum_unrealised_pnl": -367.51},
    "curve_identity": {"identical": True, "n_common": 60},
}
FORENSICS = {
    "as_of": "2026-10-03",
    "stop_decomposition": {"n": 14, "realised_r": -19.0, "designed_r": -13.5,
                           "beyond_stop_r": -5.5, "n_filled_beyond_stop": 9},
    "funded_split": {"funded": {"n": 2, "realised_r": -2.25, "beyond_stop_r": -0.25},
                     "never_funded": {"n": 12, "realised_r": -16.75, "beyond_stop_r": -5.25}},
    "convention_divergence": {"difference_r": 1.26,
                              "attribution_nets_favourable_fills": {"beyond_stop_r": -5.5},
                              "ledger_counts_adverse_overshoot_only": {"beyond_stop_r": -6.76}},
}
LEDGER = pd.DataFrame([
    {"ticker": "AAA", "exit_reason": "stop", "r_multiple": -1.05, "mae_r": -1.05,
     "mfe_r": 0.0, "capture_of_mfe": None, "excursion_basis": "weekly_marks"},
    {"ticker": "BBB", "exit_reason": "stop", "r_multiple": -1.20, "mae_r": -1.20,
     "mfe_r": 1.19, "capture_of_mfe": -1.005, "excursion_basis": "weekly_marks"},
    {"ticker": "CCC", "exit_reason": "stop", "r_multiple": -2.0, "mae_r": None,
     "mfe_r": None, "capture_of_mfe": None, "excursion_basis": None},
])
PORTFOLIO = {"n_positions": 6, "cash": 83005.41, "total_value": 990000.0}


@pytest.fixture(scope="module")
def page() -> str:
    return P.render(SCORECARD, BOOK_IDENTITY, FORENSICS, LEDGER, PORTFOLIO)


def test_the_page_is_deterministic(page):
    """Pure render: same input, same bytes. Without this a golden file is meaningless."""
    again = P.render(SCORECARD, BOOK_IDENTITY, FORENSICS, LEDGER, PORTFOLIO)
    assert page == again


def test_every_headline_number_carries_its_book(page):
    """0146's whole point. A number without its book is not interpretable."""
    assert "| closed trades (the readiness count) | 14 | uncapped tracker |" in page
    assert "| NAV | Rs.990,000.00 | capped Rs.10L book |" in page
    assert "| Sharpe (the kill trigger) | -0.5000 | capped Rs.10L book |" in page


def test_the_capital_books_own_numbers_are_separated_from_the_trackers(page):
    assert "2 closed (exact)" in page
    assert "6 realisation event(s)" in page
    assert "closure count is not the number of times money was realised" in page
    assert "(derived, not sourced)" in page


def test_the_gates_say_whether_they_fired_and_that_they_are_not_applied(page):
    assert "surfaced, not applied" in page
    assert "| kill | -0.5000 | YES |" in page.replace(" | raw-return", " |").replace(
        "-0.5000 | YES | raw-return", "-0.5000 | YES")  # the kill row fired
    assert "below cash, not below the risk-free rate" in page


def test_the_section_4_floor_mismatch_is_stated(page):
    assert "not the same quantity" in page
    assert "Recorded, not repaired" in page


def test_the_funded_split_leads_and_the_tracker_row_is_labelled(page):
    assert "| **funded — the book that holds money** | 2 | -2.25R | -0.25R |" in page
    assert "| never funded — tracker only | 12 | -16.75R | -5.25R |" in page
    assert "must not be quoted as the book's" in page


def test_unmeasurable_excursions_are_explained_not_omitted(page):
    """2 of 3 closed rows have a basis; the third must be accounted for, not silently dropped."""
    assert "2 of 3 closed trades carry an excursion measurement" in page
    assert "no committed price basis" in page
    assert "UNDERSTATEMENTS" in page


def test_the_page_states_what_it_deliberately_lacks(page):
    assert "Owner overrides" in page
    assert "A declared hole, not a zero" in page


# ------------------------------------------------------------------ the seal
def test_the_renderer_never_opens_the_sealed_judge_log(page, monkeypatch):
    """Asserted, not trusted: a reporting page is how a seal gets breached by accident."""
    assert "judge_log.jsonl" in page, "the page should SAY it does not read the log"
    src = (ROOT / "scripts" / "render_weekly_postmortem.py").read_text(encoding="utf-8")
    # the only occurrences may be the constant and prose — never an open/read of it
    for bad in ("read_text", "open(", "read_json"):
        for line in src.splitlines():
            if "judge_log" in line and bad in line:
                pytest.fail(f"the renderer touches the sealed log: {line.strip()}")


def test_a_real_render_does_not_touch_the_sealed_file(tmp_path, monkeypatch):
    """Belt and braces: trip a real open() of the sealed path during a full main() run."""
    import builtins
    real_open = builtins.open
    touched: list[str] = []

    def guard(file, *a, **kw):
        if "judge_log" in str(file):
            touched.append(str(file))
        return real_open(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", guard)
    monkeypatch.setattr(P, "OUT_DIR", tmp_path)
    if not (P.RESULTS / "weekly_review_scorecard.json").is_file():
        pytest.skip("no scorecard generated yet")
    assert P.main(["--out-date", "2026-10-03"]) == 0
    assert not touched, f"the sealed log was opened: {touched}"


# ------------------------------------------------------------------ the selector bug
def test_the_newest_DATA_wins_not_the_newest_directory(tmp_path):
    """The bug this page shipped with: a re-run directory dated after a newer snapshot won, and the
    first render reported 9 closed trades when 13 had closed."""
    base = tmp_path / "diag"
    for dirname, as_of, n in (("2026-09-25", "2026-09-25", 13), ("2026-09-26", "2026-09-04", 9)):
        d = base / dirname
        d.mkdir(parents=True)
        (d / "summary.json").write_text(json.dumps({"as_of": as_of, "n": n}), encoding="utf-8")
    picked = P._latest(base)
    assert picked["as_of"] == "2026-09-25" and picked["n"] == 13, (
        "the selector chose the newest RUN date over the newest DATA date")


def test_a_missing_diagnostics_directory_renders_a_shorter_page_rather_than_crashing():
    page = P.render(SCORECARD, None, None, None, None)
    assert "Saturday post-mortem" in page
    assert "Which book each headline number is about" in page
