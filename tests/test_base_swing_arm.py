"""The base-swing comparator arm must actually accrue, and must never be surfaced.

`forward/prereg_swing.md §4` decides which grading the live product runs — A-only vs base-swing —
at the 2027-07-01 review, on forward **MaxDD** and **Calmar**, requiring **>=20 forward closed
trades per book**. Its fallback is explicit: *"Insufficient evidence (< 20 forward closed trades per
book…): default to base-swing… A-only does not get the benefit of the doubt."*

§2 registered base-swing as *"reconstructable from the uncapped signal ledger
`results/signals_history_weekly.json` (every signal, all grades)"*. It was not. Both books the cron
wrote passed `a_grade=a_set`, so every logged signal was Grade A and the comparator never accrued a
trade. The §4 fallback would therefore have fired mechanically at every review — retiring the live
product by default rather than by evidence — and the failure was invisible, because the arm that
wasn't there produced no error and no empty file.

It also cannot be repaired retroactively: §3 forbids reconstructed history entering the forward
record, so a week not logged is a week of the comparison permanently gone. That is what makes this
worth a test rather than a note.

Two properties are pinned here:

1. **The arm is genuinely all-grades** — behaviourally, not by reading the call site. An arm that
   silently re-acquired an `a_grade` filter would be identical to the traded book and the §4
   comparison would be a book against itself.
2. **It is never surfaced.** The book contains Grade-B names and the owner rule is that Grade B is
   never shown or bought. Logging it is a research obligation; displaying it would break a standing
   rule, so the artifact must not reach the envelope, the cards, or the memos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CRON = ROOT / "scripts" / "run_bhanushali_cron.py"


def _correlated_universe(n: int = 900, ntk: int = 20, rho: float = 0.93) -> dict[str, pd.DataFrame]:
    """Names driven by a shared factor plus small idiosyncratic noise.

    Independent random walks will not do. The 44-SMA touch funnel is sparse — on uncorrelated
    synthetics fewer than five names ever signal in the same ISO week, so "top-5 by CRS" admits
    everything and the two books come out byte-identical for a reason that has nothing to do with
    grading. Correlating the paths makes signals cluster, which is what real weeks look like and
    what makes the Grade-A cut actually bind.
    """
    rng = np.random.default_rng(5)
    common = rng.normal(0.0016, 0.018, n)
    out: dict[str, pd.DataFrame] = {}
    for i in range(ntk):
        idio = np.random.default_rng(1000 + i).normal(0, 0.010, n)
        c = 100.0 * np.exp(np.cumsum(rho * common + (1.0 - rho) * idio * 3))
        out[f"T{i:02d}"] = pd.DataFrame(
            {"Open": c * 0.999, "High": c * 1.02, "Low": c * 0.98, "Close": c,
             "Volume": np.full(n, 8e5)},
            index=pd.bdate_range("2017-01-02", periods=n),
        )
    return out


# --------------------------------------------------------------- 1. the arm is all-grades, for real
def test_base_swing_is_a_genuinely_different_book_from_a_only():
    """Behavioural. If `a_grade` ever creeps back onto the base-swing call, the two books converge
    and §4 compares A-only against itself — a comparison that cannot fail and cannot inform.

    The assertion is that the NAV curves DIVERGE, not that the trade count grows. Both books run
    the same ₹10L cash gate, so admitting Grade B mostly changes *which* names get funded rather
    than how many — the equity path is what §4 actually reads (MaxDD and Calmar), so that is what
    is pinned.
    """
    import run_bhanushali_weekly_rank as R94

    P = R94.prep_weekly_rank(_correlated_universe())
    a_set = R94.grade_a_entries(P)

    a_only = R94.backtest(P, None, a_grade=a_set)
    all_grades = R94.backtest(P, None)                     # no a_grade => base-swing

    assert a_only["trades"] > 0, "fixture produced no Grade-A trades; it cannot compare the books"
    assert all_grades["trades"] >= a_only["trades"], (
        "the all-grades book took FEWER trades than the Grade-A subset, which is not possible if "
        "a_grade is a filter — check that grade_a_entries still returns a subset"
    )
    assert float(all_grades["curve"].iloc[-1]) != float(a_only["curve"].iloc[-1]), (
        f"base-swing and A-only produced identical NAV ({a_only['curve'].iloc[-1]:,.0f}) on "
        f"{all_grades['trades']} vs {a_only['trades']} trades. Either the arm re-acquired an "
        f"a_grade filter, or the fixture is too sparse for the top-5 cut to bind — in which case "
        f"this test proves nothing and the fixture needs more clustering."
    )


# --------------------------------------------------------------------- 2. wiring and non-surfacing
@pytest.fixture(scope="module")
def cron_src() -> str:
    return CRON.read_text(encoding="utf-8")


def test_the_cron_runs_a_base_swing_arm_without_a_grade(cron_src: str):
    call = cron_src[cron_src.index("out_base = R94.backtest") :]
    call = call[: call.index(")\n") + 1]
    assert "a_grade" not in call, (
        "the base-swing arm passes an a_grade filter, so it is not all-grades:\n" + call
    )
    for required in ("LIVE_DISCIPLINE", "LIVE_EXIT", "LIVE_STALENESS"):
        assert required in call, (
            f"the base-swing arm omits **{required}. It must run the SAME discipline as the traded "
            f"book — §4 compares grading, and any other difference confounds it."
        )
    assert "uncapped" not in call, (
        "base-swing is defined in §2 as running the ₹10L cash gate; an uncapped arm has a different "
        "NAV and its MaxDD/Calmar are not comparable to the traded book's"
    )


def test_the_base_swing_book_is_never_surfaced(cron_src: str):
    """It holds Grade-B names. Logging is required; showing them is forbidden."""
    envelope_call = cron_src[cron_src.index("build_envelopes(") :]
    envelope_call = envelope_call[: envelope_call.index(")")]
    assert "out_base" not in envelope_call and "led_base" not in envelope_call, (
        "the base-swing book reaches build_envelopes, which feeds the signals page and the cards. "
        "It contains Grade-B names and the owner rule is that Grade B is never surfaced."
    )
    assert "base_swing_forward.json" in cron_src, "the watched arm is computed but never written"


# ------------------------------------------------------------------- 3. the record supports §4
def test_the_record_carries_what_the_decision_rule_needs():
    import run_bhanushali_cron as cron

    curve = pd.Series(
        [1_000_000.0, 1_100_000.0, 900_000.0, 1_050_000.0],
        index=pd.to_datetime(["2026-07-06", "2026-07-13", "2026-07-20", "2026-07-27"]),
    )
    out = {"curve": curve, "dd": -0.1818, "cagr": 0.42, "sharpe": 0.55, "trades": 7,
           "wr": 0.571, "expR": 0.31, "reasons": {"stop": 3, "tp": 4}}
    rec = cron._base_swing_record(out, [], "2026-07-04", "2026-07-31")

    # §4 decides on MaxDD and Calmar, with a >=20-closed floor per book.
    for field in ("maxdd_pct", "calmar", "n_closed", "nav"):
        assert rec[field] is not None, f"§4 cannot be evaluated without {field}"
    assert rec["n_closed"] == 7
    assert rec["calmar"] == pytest.approx(0.42 / 0.1818, rel=1e-3)
    assert len(rec["nav"]) == len(curve), (
        "the full NAV curve must be written, not just a summary — at the review the two books have "
        "to be compared over a COMMON window, which a summary cannot support"
    )
    assert rec["status"].startswith("WATCHED")
    assert "prereg_swing.md §4" in rec["authority"]


def test_the_record_labels_the_gross_R_unit():
    """`expR` is computed on raw prices while the NAV metrics are net. Mixing them is the exact
    error the swing scorecard already makes (gross expectancy against a net Sharpe), so the unit is
    stated in the artifact rather than left for a reader to infer."""
    import run_bhanushali_cron as cron

    curve = pd.Series([1e6, 1.1e6], index=pd.to_datetime(["2026-07-06", "2026-07-13"]))
    rec = cron._base_swing_record(
        {"curve": curve, "dd": -0.05, "cagr": 0.2, "sharpe": 0.5, "trades": 1,
         "wr": 1.0, "expR": 0.4, "reasons": {}}, [], "2026-07-04", "2026-07-13")
    assert "expectancy_R_gross" in rec
    assert "GROSS" in rec["_units"] and "NET" in rec["_units"]
