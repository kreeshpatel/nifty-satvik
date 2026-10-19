"""The run manifest labels a run LIVE BOOK / NOT LIVE BOOK against the cron's own LIVE_* blocks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.runner import manifest as M  # noqa: E402


def _live():
    return M.live_engine_kwargs()


def test_live_kwargs_with_pit_is_the_live_book():
    m = M.build_manifest(_live(), membership="pit")
    assert m["is_live_book"] and m["label"] == "LIVE BOOK"
    assert m["live_fingerprint"] == M.live_config_fingerprint()


def test_no_membership_is_not_the_live_book_and_names_membership():
    m = M.build_manifest(_live(), membership="none")
    assert not m["is_live_book"]
    assert m["label"] == "NOT LIVE BOOK: membership"


def test_changed_ext_cap_names_ext_cap():
    kw = {**_live(), "ext_cap": 0.30}
    m = M.build_manifest(kw, membership="pit")
    assert not m["is_live_book"] and m["label"] == "NOT LIVE BOOK: ext_cap"
    assert M.diff_from_live(kw, "pit") == ["ext_cap"]


def test_start_is_ignored_but_uncapped_is_not():
    assert M.build_manifest({**_live(), "start": "2019-01-01"}, membership="pit")["is_live_book"]
    assert M.diff_from_live({**_live(), "uncapped": True}, "pit") == ["uncapped"]


def test_fingerprint_is_deterministic_and_sha256():
    a, b = M.live_config_fingerprint(), M.live_config_fingerprint()
    assert a == b and len(a) == 64
    assert M.build_manifest(_live(), membership="pit")["config_hash"] == \
        M.build_manifest(_live(), membership="pit")["config_hash"]
    assert M.build_manifest(_live(), membership="pit")["config_hash"] != \
        M.build_manifest(_live(), membership="none")["config_hash"]


def test_replay_helper_flags_default_config_as_live():
    from nq.lab import runs as L
    assert L._manifest(L.normalize_config(None), "2024-06-28")["label"] == "LIVE BOOK"
    assert L._manifest(L.normalize_config({"pit_membership": False}), None)["label"] == "NOT LIVE BOOK: membership"
    assert L._manifest(L.normalize_config({"grade_gate": False}), None)["label"] == "NOT LIVE BOOK: grade_gate"
