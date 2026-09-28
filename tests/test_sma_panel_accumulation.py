"""The SMA panel must ACCUMULATE, because its population cannot be rebuilt after the fact.

Regression test for the prod-fix that added the dated write (2026-09-27). The panel is the only artifact
recording the names that did NOT fire — the rejection and near-miss set — and it depends on the 44-week
SMA and the CRS ranking as they stood in that week on that price vintage. Overwriting it weekly meant the
file held one `as_of` and 494 rows, and every week that passed was permanently lost.

Two properties are asserted, and the second is the one that matters:

  1. the flat `weekly_sma_panel.csv` keeps its old behaviour, because the dashboard and the output
     contract read it;
  2. `results/sma_panel/<as_of>.csv` is append-only — a new week never removes an earlier one, while a
     re-run of the SAME week legitimately restates it (the price vintage may have been corrected).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402


def _panel_input(close: float = 100.0, sma: float = 95.0, fired: bool = True) -> dict:
    """The smallest P a panel row needs: one weekly bar, a 44w SMA, and an optional fire."""
    return {
        "AAA": {
            "wk_hlc": {3: (close * 1.02, close * 0.98, close)},
            "dates": {3: pd.Timestamp("2026-10-02")},
            "wsma_at": {3: sma},
            "entry_win": [3] if fired else [],
            "last_signal": {"rank": 0.1234} if fired else None,
        }
    }


def _write(tmp: Path, as_of: str, **kw) -> pd.DataFrame:
    C._write_sma_panel(_panel_input(**kw), {("AAA", 3)}, as_of, tmp)
    return pd.read_csv(tmp / "sma_panel" / f"{as_of}.csv")


def test_the_flat_snapshot_still_overwrites(tmp_path):
    """Unchanged behaviour: the dashboard and the contract read this file and it stays one week."""
    _write(tmp_path, "2026-10-03")
    _write(tmp_path, "2026-10-10")
    flat = pd.read_csv(tmp_path / "weekly_sma_panel.csv")
    assert list(flat["as_of"].unique()) == ["2026-10-10"], "the flat file must hold the latest week only"


def test_the_dated_copy_accumulates_and_never_drops_a_week(tmp_path):
    _write(tmp_path, "2026-10-03")
    _write(tmp_path, "2026-10-10")
    _write(tmp_path, "2026-10-17")
    weeks = sorted(p.stem for p in (tmp_path / "sma_panel").glob("*.csv"))
    assert weeks == ["2026-10-03", "2026-10-10", "2026-10-17"]
    # and the union is what a counterfactual study would read
    union = pd.concat([pd.read_csv(p) for p in (tmp_path / "sma_panel").glob("*.csv")])
    assert len(union) == 3
    assert set(union["as_of"]) == set(weeks)


def test_a_rerun_of_the_same_week_restates_it_rather_than_duplicating(tmp_path):
    """A re-run legitimately corrects a week's price vintage; it must not append a second copy."""
    first = _write(tmp_path, "2026-10-03", close=100.0)
    second = _write(tmp_path, "2026-10-03", close=123.0)
    assert len(list((tmp_path / "sma_panel").glob("*.csv"))) == 1
    assert first["weekly_close"].iloc[0] == 100.0
    assert second["weekly_close"].iloc[0] == 123.0


def test_the_dated_row_carries_the_non_firing_population(tmp_path):
    """The whole point: a name that did NOT fire must still be recorded, with its distance to the line."""
    row = _write(tmp_path, "2026-10-03", fired=False).iloc[0]
    assert bool(row["is_signal"]) is False
    assert bool(row["is_grade_a"]) is False
    assert row["dist_to_sma_pct"] == pytest.approx((100.0 / 95.0 - 1) * 100, abs=0.01)
    assert bool(row["close_above_sma"]) is True


def test_an_empty_panel_writes_nothing_rather_than_an_empty_week(tmp_path):
    """A week with no rows is a failure, not a week of 'no names' — it must not be recorded as data."""
    C._write_sma_panel({}, set(), "2026-10-03", tmp_path)
    assert not (tmp_path / "sma_panel").exists()
    assert not (tmp_path / "weekly_sma_panel.csv").exists()


def test_the_accumulation_path_is_contracted_and_not_gitignored():
    """The ignore trap this repo has been bitten by seven times: an unwhitelisted path is silently
    dropped by `git add`, so the accumulation would never reach the repo and the cron would stay green."""
    import json
    import subprocess
    contracts = json.loads((ROOT / "results" / "output_contracts.json").read_text(encoding="utf-8"))
    scanner = next(c for c in contracts["contracts"] if c["job"] == "weekly-scanner")
    assert "results/sma_panel" in scanner["must_update"], (
        "a week that does not land is lost, so this is must_update, not conditional")
    for path in ("results/sma_panel", "results/sma_panel/2026-10-03.csv"):
        out = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True, text=True)
        assert out.returncode != 0, f"{path} is gitignored — the weekly add would silently no-op"
