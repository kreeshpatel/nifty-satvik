"""Forward records (ADR-0020, Part C): a new week is chained onto the frozen past, and the past never moves."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipelines" / "lifecycle"))
import core as C  # noqa: E402
import update_records as U  # noqa: E402

NO = lambda d, prev: {"holdings": None, "turnover": None}
TRI = pd.Series(dtype=float)


def _nav(vals, start="2026-11-13"):
    return pd.Series(vals, index=pd.bdate_range(start, periods=len(vals)), dtype=float)


def test_first_run_writes_only_the_start_row(tmp_path):
    f = tmp_path / "m.csv"
    assert U.chain(f, _nav([1_000_000.0]), NO, TRI, "paper", dry=False) == 1
    rec = C.read_record(f)
    assert len(rec) == 1 and float(rec.nav[0]) == 1_000_000.0 and pd.isna(rec.weekly_return[0])


def test_a_rebuild_that_changes_the_past_cannot_change_recorded_rows(tmp_path):
    f = tmp_path / "m.csv"
    U.chain(f, _nav([1_000_000.0]), NO, TRI, "paper", dry=False)
    U.chain(f, _nav([1_000_000.0] + [1_010_000.0] * 5), NO, TRI, "paper", dry=False)         # week 2: +1%
    frozen = f.read_text(encoding="utf-8")
    # week 3: the rebuild now says week 2 was +5% (a vendor restated prices). Only the NEW week may be appended,
    # as the rebuilt week-3 / week-2 ratio, chained onto the frozen week-2 NAV.
    rebuilt = _nav([1_000_000.0] + [1_050_000.0] * 5 + [1_071_000.0] * 5)
    assert U.chain(f, rebuilt, NO, TRI, "paper", dry=False) == 1
    text = f.read_text(encoding="utf-8")
    assert text.startswith(frozen)
    rec = C.read_record(f)
    assert abs(float(rec.weekly_return.iloc[-1]) - 0.02) < 1e-6
    assert abs(float(rec.nav.iloc[-1]) - 1_010_000.0 * 1.02) < 0.01


def test_a_rerun_of_the_same_week_appends_nothing(tmp_path):
    f = tmp_path / "m.csv"
    nav = _nav([1_000_000.0] + [1_010_000.0] * 5)
    U.chain(f, nav, NO, TRI, "paper", dry=False)
    before = f.read_text(encoding="utf-8")
    assert U.chain(f, nav, NO, TRI, "paper", dry=False) == 0
    assert f.read_text(encoding="utf-8") == before


def test_dry_run_writes_nothing(tmp_path):
    f = tmp_path / "m.csv"
    U.chain(f, _nav([1_000_000.0] + [1_010_000.0] * 5), NO, TRI, "paper", dry=True)
    assert not f.exists()


def test_the_scan_step_cannot_block_the_scan():
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    i = wf.index("Strategy lifecycle - forward records")
    block = wf[i:i + 300]
    assert "continue-on-error: true" in block
    assert wf.index("Strategy lifecycle - forward records") < wf.index("- name: Commit weekly paper state")
