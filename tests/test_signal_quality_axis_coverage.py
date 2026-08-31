"""The signal-quality wall must not lose axes quietly.

`forward/prereg_signal_quality.md` judges four frozen axes. The producer records them on **FRESH**
cards only — a live envelope carries them on 2/2 FRESH rows and on 0/24 ACTIVE rows — and archives
are written on Saturday. So a signal that goes FRESH → ACTIVE between two Saturdays is first *seen*
as ACTIVE, and its axes are gone before anything durable observed them.

PHOENIXLTD (`signal_date` 2026-08-24) is the first instance, sitting between two complete weeks.

Raw coverage counts already existed and could not surface it: `body_ratio: 15/37` reads identically
whether the nulls are the documented pre-schema rows or a hole that opened last week. Two guards
close that:

  * `axis_holes` — rows on/after `SCHEMA_COMPLETE_FROM` must carry every axis. Known losses are
    DECLARED with a reason; anything else is new, and `--validate` exits non-zero.
  * `_coverage_drops` — the rebuild may add coverage or hold it level, never drop it. Q2 is
    recomputed from the OHLCV cache, so a stale cache silently replaces a complete table with a
    worse one. Measured on a two-month-old cache: 4 of 37 touch-depths against a committed 37.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import collect_signal_quality_forward as C  # noqa: E402

AXES = list(C.QUALITY_AXES)


def _df(rows: list[dict]) -> pd.DataFrame:
    cols = ["ticker", "signal_date", *AXES, "touch_depth_min_ext", "r_multiple"]
    return pd.DataFrame(rows, columns=cols)


def _complete(ticker: str, date: str) -> dict:
    return {"ticker": ticker, "signal_date": date, "body_ratio": 0.55,
            "signal_conviction": "normal", "crs_rank": 0.09,
            "touch_depth_min_ext": 3.1, "r_multiple": None}


# --------------------------------------------------------------------------- axis_holes
def test_a_new_hole_is_caught():
    """A post-schema signal that lost its axes, with no decision on record."""
    holes = C.axis_holes(_df([{**_complete("NEWNAME", "2026-09-14"),
                               "body_ratio": None, "signal_conviction": None}]))
    assert holes == [("NEWNAME", "2026-09-14", ["body_ratio", "signal_conviction"])]


def test_the_declared_loss_does_not_fire():
    """PHOENIXLTD is accepted and reasoned about in KNOWN_INCOMPLETE. A guard that keeps shouting
    about a decision already taken gets muted, and then it protects nothing."""
    assert ("PHOENIXLTD", "2026-08-24") in C.KNOWN_INCOMPLETE
    assert not C.axis_holes(_df([{**_complete("PHOENIXLTD", "2026-08-24"),
                                  "body_ratio": None, "signal_conviction": None,
                                  "crs_rank": None}]))


def test_every_declaration_carries_a_reason():
    """The cost of admitting a signal is permanently unmeasurable is one sentence saying why."""
    for key, why in C.KNOWN_INCOMPLETE.items():
        assert len(why) > 80, f"{key} is declared without a real reason"


def test_pre_schema_rows_are_not_holes():
    """Before SCHEMA_COMPLETE_FROM the producer emitted no axes at all. That is a documented
    start-up condition, and flagging 22 rows of it would bury the one row that matters."""
    assert not C.axis_holes(_df([{**_complete("OLDNAME", "2026-07-06"),
                                  "body_ratio": None, "signal_conviction": None,
                                  "crs_rank": None}]))


def test_a_complete_row_is_never_a_hole():
    assert not C.axis_holes(_df([_complete("JSWSTEEL", "2026-08-21")]))


def test_the_live_table_has_no_undeclared_holes():
    """The committed table, as it stands. This is the assertion that goes red when a new signal
    lands without its axes — the reason the file exists."""
    holes = C.axis_holes(C.build())
    assert not holes, (
        "undeclared axis hole(s): "
        + "; ".join(f"{t} {d} missing {','.join(m)}" for t, d, m in holes))


# --------------------------------------------------------------------------- _coverage_drops
def test_a_rebuild_that_loses_coverage_is_refused(tmp_path, monkeypatch):
    """The stale-cache case, which really happened: 37 touch-depths became 4."""
    out = tmp_path / "signal_quality_forward.csv"
    _df([_complete(f"T{i}", "2026-08-21") for i in range(37)]).to_csv(out, index=False)
    monkeypatch.setattr(C, "OUT", out)

    degraded = _df([{**_complete(f"T{i}", "2026-08-21"), "touch_depth_min_ext": None}
                    for i in range(37)])
    drops = C._coverage_drops(degraded)
    assert ("touch_depth_min_ext", 37, 0) in drops


def test_gaining_coverage_is_allowed(tmp_path, monkeypatch):
    """The normal case as history deepens — Q2 fills in as bars accrue. A guard that blocked
    improvement would be worse than none."""
    out = tmp_path / "signal_quality_forward.csv"
    _df([{**_complete("A", "2026-08-21"), "touch_depth_min_ext": None}]).to_csv(out, index=False)
    monkeypatch.setattr(C, "OUT", out)
    assert not C._coverage_drops(_df([_complete("A", "2026-08-21")]))


def test_level_coverage_is_allowed(tmp_path, monkeypatch):
    out = tmp_path / "signal_quality_forward.csv"
    _df([_complete("A", "2026-08-21")]).to_csv(out, index=False)
    monkeypatch.setattr(C, "OUT", out)
    assert not C._coverage_drops(_df([_complete("A", "2026-08-21")]))


def test_no_prior_table_cannot_veto_a_first_build(tmp_path, monkeypatch):
    """A cold checkout has nothing to compare against and must still be able to build."""
    monkeypatch.setattr(C, "OUT", tmp_path / "absent.csv")
    assert not C._coverage_drops(_df([_complete("A", "2026-08-21")]))


def test_an_unreadable_prior_table_does_not_veto(tmp_path, monkeypatch):
    """A corrupt file is a reason to rebuild, not a reason to refuse to."""
    out = tmp_path / "signal_quality_forward.csv"
    out.write_text("this is not, a valid\x00 csv\n\"unterminated", encoding="utf-8")
    monkeypatch.setattr(C, "OUT", out)
    assert not C._coverage_drops(_df([_complete("A", "2026-08-21")]))


# --------------------------------------------------------------------------- the seal
def test_the_collector_still_reports_no_axis_to_outcome_relationship():
    """The forward seal (prereg_signal_quality.md): this collector reports STRUCTURE only. Neither
    guard may become a back door to reading the wall's answer during accrual.

    Parsed, not grepped. The module docstring *names* `adjudicate_family` in order to say the read
    belongs to the wall and never here, so a substring scan flags the sentence that states the rule.
    Walking the AST asks the question that was actually meant: does the collector CALL any of this?
    """
    import ast
    tree = ast.parse((ROOT / "scripts" / "collect_signal_quality_forward.py")
                     .read_text(encoding="utf-8"))
    called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for banned in ("corr", "adjudicate_family", "qcut", "groupby"):
        assert banned not in called, f"the collector calls {banned}() — that is the wall's job"
