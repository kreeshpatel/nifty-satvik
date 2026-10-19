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
    d = json.loads((ROOT / "results" / "history_restatements.json").read_text(encoding="utf-8"))
    for k in ("HINDZINC|2026-08-31", "BANDHANBNK|2026-09-14", "ZYDUSWELL|2026-08-31", "ABDL|2026-09-15"):
        assert d[k].strip()
