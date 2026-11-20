"""--no-download crashed with KeyError: 'quarantined' (found 2026-11-17 during the degenerate-stop dry run).

The offline path skips the data guards, so the quarantine record was an empty dict that the restatement step then
indexed. The fix: offline carries no record. These tests hold that the ONLINE path is unchanged - the record the
guards fill is passed through as the very same object, empty or populated - and that offline yields None.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import run_bhanushali_cron as C  # noqa: E402

SRC = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")


def test_online_record_is_passed_through_unchanged_when_populated():
    rec = {"quarantined": [{"ticker": "ABC", "held": False}], "flagged": [], "healed": [], "as_of": "x"}
    snapshot = repr(rec)
    out = C._quarantine_record_for(rec, do_download=True)
    assert out is rec and repr(out) == snapshot


def test_online_record_is_passed_through_unchanged_when_clean():
    rec = {"quarantined": [], "flagged": [], "healed": [], "as_of": "x"}
    assert C._quarantine_record_for(rec, do_download=True) is rec


def test_online_strict_mode_none_stays_none():
    assert C._quarantine_record_for(None, do_download=True) is None


def test_offline_carries_no_record():
    assert C._quarantine_record_for({}, do_download=False) is None


def test_the_helper_is_applied_right_after_the_refresh_and_before_any_use():
    i_refresh = SRC.index("ohlcv = _refresh_ohlcv(args.start, args.history_days, not args.no_download, quarantine_out=qrec)")
    i_fix = SRC.index("qrec = _quarantine_record_for(qrec, not args.no_download)")
    i_first_use = SRC.index('if qrec and qrec.get("quarantined"):')
    assert i_refresh < i_fix < i_first_use
