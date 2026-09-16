"""The read access the Brain is allowed — and the one artifact it may never open.

The 0125 informed-judge verdicts are sealed until the first quarterly review read. The PreToolUse hook
guards interactive sessions, but the Brain runs as code in crons, where no hook exists. A module that
reads `results/` wholesale is exactly the reader the seal is for, so refusal lives here, in code.

The sealed path is taken from the writer's own constant (`nq.paper.judge_log.DEFAULT_LOG`), never typed.
Until 2026-09-15 the hook sealed a path that did not exist while its test asserted the same wrong
literal; deriving the path from the writer is what stops that happening twice.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from nq.paper.judge_log import DEFAULT_LOG

SEALED: frozenset[Path] = frozenset({Path(DEFAULT_LOG).resolve()})


class SealedArtifactError(PermissionError):
    """Raised instead of opening a sealed artifact."""


def assert_not_sealed(path: str | Path) -> Path:
    """Return the resolved path, or raise if it is sealed. Never opens the file."""
    p = Path(path).resolve()
    if p in SEALED:
        raise SealedArtifactError(
            f"{p.name} is the sealed 0125 judge log. It may not be read before the first review read "
            f"(>= 2 quarters from 2026-08-01). Verify it by row count and hash chain only.")
    return p


def read_json(path: str | Path) -> Any:
    """Parse a JSON artifact, refusing sealed ones before any byte is read."""
    p = assert_not_sealed(path)
    return json.loads(p.read_text(encoding="utf-8"))


# ── THE SEALED VALIDATION SLICE ──────────────────────────────────────────────────────────────────────
# The research substrate (`research/substrate/trades.parquet`, `context_windows.parquet`) reserves entries
# from 2024-07-01 to 2026-06-30 as a SEALED validation slice. Each read is a "sealed open", recorded as an
# S-row in the screen ledger BEFORE the read, with a frozen rule to validate.
#
# The trap this guards: the parquet's own `split == "holdout"` label (2023 onward) CONTAINS the slice, so
# a reader that trusts the label opens the seal without knowing. That happened on 2026-09-16 — the
# excursions-null measurement read the holdout split and became the unplanned sealed open S2. Refusal lives
# in the reader, in code, for the same reason the judge-log seal does: no hook runs inside a cron.
SEALED_SLICE_START = "2024-07-01"
SEALED_SLICE_END = "2026-06-30"
SCREEN_LEDGER = Path(__file__).resolve().parents[2] / "diagnostics" / "research" / "label_screen_ledger.md"


def recorded_sealed_opens(ledger: str | Path = SCREEN_LEDGER) -> frozenset[str]:
    """The S-row ids (`S1`, `S2`, …) the screen ledger records."""
    text = Path(ledger).read_text(encoding="utf-8")
    return frozenset(f"S{m}" for m in re.findall(r"^\|\s*S(\d+)\s*\|", text, re.M))


def assert_unsealed(entry_dates: Any, *, declared_open: str | None = None,
                    ledger: str | Path = SCREEN_LEDGER) -> None:
    """Refuse a substrate selection that reaches into the sealed slice, unless the open is on record.

    ``entry_dates`` is any iterable of dates. ``declared_open`` names the ledger S-row that authorises the
    read; it must already exist in the ledger, so the record is written before the data is touched.
    """
    dates = pd.to_datetime(pd.Series(list(entry_dates)), errors="coerce")
    inside = dates[(dates >= pd.Timestamp(SEALED_SLICE_START)) & (dates <= pd.Timestamp(SEALED_SLICE_END))]
    if inside.empty:
        return
    if declared_open is None:
        raise SealedArtifactError(
            f"{len(inside)} rows fall in the SEALED validation slice ({SEALED_SLICE_START}..{SEALED_SLICE_END}). "
            f"The substrate's 'holdout' split contains it — filter entry_date <= 2024-06-30, or record a sealed "
            f"open in {Path(ledger).name} first and pass its S-row id as declared_open.")
    if declared_open not in recorded_sealed_opens(ledger):
        raise SealedArtifactError(
            f"declared_open={declared_open!r} is not an S-row in {Path(ledger).name}. A sealed open is recorded "
            f"BEFORE the read, never after.")
