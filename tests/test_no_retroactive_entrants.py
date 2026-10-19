"""prod-fix 2026-10-19: a name added to the live universe must not signal in past weeks.

The weekly history is rebuilt from inception, and Grade A ranks every signal in a week, so a newly
scanned name's past signal displaced HINDZINC (week of 2026-08-31) and the open BANDHANBNK (week of
2026-09-14). `_mask_late_entrants` removes such windows before the A-set is computed.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402


def _P():
    dates = list(pd.bdate_range("2026-08-03", "2026-11-30"))
    idx = {d: i for i, d in enumerate(dates)}
    def wins(*ds):
        return {idx[pd.Timestamp(d)]: ("win",) for d in ds}
    return {"OLD": {"dates": dates, "entry_win": wins("2026-08-31", "2026-10-19")},
            "NEW": {"dates": dates, "entry_win": wins("2026-08-31", "2026-09-14", "2026-10-19")},
            "JAN": {"dates": dates, "entry_win": wins("2026-10-19", "2026-11-23")}}


def test_a_late_name_loses_only_its_past_windows():
    P = _P()
    mem = {"NEW": [(date(2025, 1, 1), date(2030, 12, 31))]}
    dropped = C._mask_late_entrants(P, {"NEW"}, mem, effective="2026-10-16")
    assert dropped == 2
    assert [str(pd.Timestamp(P["NEW"]["dates"][e]).date()) for e in P["NEW"]["entry_win"]] == ["2026-10-19"]
    assert len(P["OLD"]["entry_win"]) == 2, "names in the carried snapshot are untouched"


def test_a_future_index_entrant_cannot_reach_back_before_its_membership():
    P = _P()
    mem = {"JAN": [(date(2026, 11, 2), date(2030, 12, 31))]}
    C._mask_late_entrants(P, {"JAN"}, mem, effective="2026-10-16", today=pd.Timestamp("2026-12-01"))
    assert [str(pd.Timestamp(P["JAN"]["dates"][e]).date()) for e in P["JAN"]["entry_win"]] == ["2026-11-23"]


def test_the_cron_masks_before_the_grade_a_set_is_computed():
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert src.index("_mask_late_entrants(P, _late, mem)") < src.index("a_set = R94.grade_a_entries(P)")
