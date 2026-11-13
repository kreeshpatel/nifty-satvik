"""scripts/check_history_drift.py: undeclared history changes fail; declared and `appeared` do not."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_history_drift as T  # noqa: E402

CLEAN = {"as_of": "2026-10-24", "restated": [], "vanished": [], "vanished_open": [], "appeared": [], "clean": True}


def _run(tmp_path, entry, declared=None, older=None):
    log = tmp_path / "drift_log.jsonl"
    rows = ([older] if older else []) + [entry]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    dec = tmp_path / "decl.json"
    dec.write_text(json.dumps(declared or {}), encoding="utf-8")
    return T.main(["--log", str(log), "--declared", str(dec)])


def test_clean_passes(tmp_path):
    assert _run(tmp_path, CLEAN) == 0


def test_undeclared_vanished_open_fails(tmp_path, capsys):
    assert _run(tmp_path, {**CLEAN, "vanished_open": ["ABDL|2026-09-15"], "n_vanished_open": 1}) == 1
    assert "::error::" in capsys.readouterr().out


def test_undeclared_vanished_closed_and_restated_fail(tmp_path):
    assert _run(tmp_path, {**CLEAN, "vanished": ["X|2026-01-05"]}) == 1
    assert _run(tmp_path, {**CLEAN, "restated": [{"trade": "Y|2026-01-05", "changed": {}}]}) == 1


def test_declared_passes(tmp_path):
    e = {**CLEAN, "vanished_open": ["ABDL|2026-09-15"], "vanished": ["HINDZINC|2026-08-31"]}
    assert _run(tmp_path, e, {"ABDL|2026-09-15": "2026-10-19 fix", "HINDZINC|2026-08-31": "2026-10-19 fix"}) == 0


def test_partially_declared_still_fails(tmp_path):
    e = {**CLEAN, "vanished_open": ["ABDL|2026-09-15", "ZZZ|2026-09-15"]}
    assert _run(tmp_path, e, {"ABDL|2026-09-15": "2026-10-19 fix"}) == 1


def test_appeared_alone_passes(tmp_path):
    assert _run(tmp_path, {**CLEAN, "appeared": ["MRPL|2026-07-20"], "n_appeared": 1, "clean": False}) == 0


def test_only_the_last_entry_counts(tmp_path):
    assert _run(tmp_path, CLEAN, older={**CLEAN, "vanished": ["OLD|2026-01-05"]}) == 0


def test_committed_declarations_cover_the_known_restatement():
    """The approvals moved into the forward record's amendments file (ADR-0018), verbatim."""
    d = json.loads((ROOT / "results" / "forward_record" / "amendments.json").read_text(encoding="utf-8"))
    for k in ("HINDZINC|2026-08-31", "BANDHANBNK|2026-09-14", "ZYDUSWELL|2026-08-31", "ABDL|2026-09-15",
              "ANGELONE|2026-09-14", "CHOLAFIN|2026-09-14", "GESHIP|2026-09-14"):
        assert d[k].strip() and d[k][:10] < "2026-11-13", "a migrated approval keeps its original date"


def test_the_amendments_file_is_the_single_place_an_approval_lives():
    import check_history_drift as T
    assert T.DECLARED == ROOT / "results" / "forward_record" / "amendments.json"
    assert not (ROOT / "results" / "history_restatements.json").exists(), "the legacy file was folded in"


def test_a_legacy_file_is_read_for_one_release_then_ignored(tmp_path, capsys):
    import check_history_drift as T
    new, old = tmp_path / "amendments.json", tmp_path / "history_restatements.json"
    new.write_text(json.dumps({"A|2026-01-05": "2026-11-13: new"}), encoding="utf-8")
    old.write_text(json.dumps({"B|2026-01-05": "2026-10-01: old"}), encoding="utf-8")
    assert set(T.load_approvals(new, old, today="2026-11-20")) == {"A|2026-01-05", "B|2026-01-05"}
    assert "retired" in capsys.readouterr().out
    assert set(T.load_approvals(new, old, today=T.LEGACY_UNTIL)) == {"A|2026-01-05"}


def test_dividend_rebasing_is_a_warning_not_a_failure():
    """2026-10-24: MRPL entry and close both re-scaled -1.7% (R unchanged) and OBEROIRLTY's close -0.12%
    (R -1.56 -> -1.58) by dividend back-adjustment. Routine re-basing must not fail the run."""
    import check_history_drift as T
    assert T.is_rebase({"entry": [172.0, 169.03], "close_price": [167.45, 164.56]})
    assert T.is_rebase({"close_price": [1698.0, 1695.91], "r_multiple": [-1.56, -1.58]})


def test_a_real_rewrite_still_fails():
    import check_history_drift as T
    assert not T.is_rebase({"close_price": [100.0, 90.0]}), "a 10% price change is not a dividend"
    assert not T.is_rebase({"r_multiple": [-1.0, 2.0]}), "an R flip is not a re-basing"
    assert not T.is_rebase({"close_date": ["2026-08-01", "2026-08-08"]}), "a date change is not a re-basing"
    entry = {"restated": [{"trade": "X|2026-07-01", "changed": {"close_price": [100.0, 90.0]}}]}
    assert T.undeclared(entry, {}) == [("restated", "X|2026-07-01")]
