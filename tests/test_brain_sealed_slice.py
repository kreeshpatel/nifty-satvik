"""The substrate's sealed validation slice (2024-07-01 .. 2026-06-30) is refused in code.

On 2026-09-16 a Brain measurement read the substrate's `split == "holdout"` rows, which contain the sealed
slice, and became the unplanned sealed open S2. `nq.brain.io.assert_unsealed` makes the next one impossible
without a ledger row written first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.brain.io import (  # noqa: E402
    SEALED_SLICE_END, SEALED_SLICE_START, SealedArtifactError, assert_unsealed, recorded_sealed_opens,
)


def test_train_years_pass():
    assert_unsealed(["2019-01-14", "2024-06-30"])


@pytest.mark.parametrize("day", ["2024-07-01", "2025-03-03", "2026-06-30"])
def test_any_row_in_the_slice_is_refused(day):
    with pytest.raises(SealedArtifactError, match="SEALED validation slice"):
        assert_unsealed(["2020-01-01", day])


SUBSTRATE = ROOT / "research" / "substrate" / "trades.parquet"


def test_a_holdout_label_starting_in_2023_is_not_a_safe_filter():
    """The exact trap, hermetic: a split labelled 'holdout' from 2023 reaches into the slice."""
    sub = pd.DataFrame({"entry_date": pd.to_datetime(["2022-06-01", "2023-02-01", "2024-06-28", "2024-07-08"]),
                        "split": ["train", "holdout", "holdout", "holdout"]})
    with pytest.raises(SealedArtifactError):
        assert_unsealed(sub.loc[sub["split"] == "holdout", "entry_date"])
    assert_unsealed(sub.loc[sub["entry_date"] <= "2024-06-30", "entry_date"])


@pytest.mark.skipif(not SUBSTRATE.exists(), reason="research substrate is not committed (local data only)")
def test_the_real_substrate_holdout_split_is_refused():
    """The same trap on the real parquet, where it exists."""
    sub = pd.read_parquet(SUBSTRATE, columns=["entry_date", "split"])
    with pytest.raises(SealedArtifactError):
        assert_unsealed(sub.loc[sub["split"] == "holdout", "entry_date"])
    assert_unsealed(sub.loc[sub["entry_date"] <= "2024-06-30", "entry_date"])


def test_a_declared_open_must_already_be_in_the_ledger(tmp_path):
    ledger = tmp_path / "ledger.md"
    ledger.write_text("| # | date |\n|---|---|\n| S1 | 2026-07-27 |\n", encoding="utf-8")
    assert_unsealed(["2025-01-01"], declared_open="S1", ledger=ledger)
    with pytest.raises(SealedArtifactError, match="BEFORE the read"):
        assert_unsealed(["2025-01-01"], declared_open="S9", ledger=ledger)


def test_the_committed_ledger_records_s2_and_the_boundaries_are_the_registered_ones():
    assert {"S1", "S2"} <= recorded_sealed_opens()
    assert (SEALED_SLICE_START, SEALED_SLICE_END) == ("2024-07-01", "2026-06-30")
