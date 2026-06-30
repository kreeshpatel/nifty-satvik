"""Combinatorial Purged Cross-Validation (CPCV) — overfit-resistant splits.

López de Prado, *Advances in Financial Machine Learning*, Ch. 12. A single walk-forward gives ONE
out-of-sample path and is easy to overfit to. CPCV partitions the timeline into ``N`` contiguous
groups, forms every ``C(N, k)`` combination of ``k`` groups as the TEST set, and for each applies:

  * **Purge** — drop training observations whose forward label window ``[j, j + horizon]`` overlaps
    a test block (the label would peek into the test period).
  * **Embargo** — drop the ``embargo`` observations immediately AFTER each test block
    (serial-correlation leak across the boundary). Use ``embargo >= horizon`` for full two-sided
    purging (the 63-day long-horizon label → embargo 63).

The ``C(N, k)`` splits recombine into ``C(N, k) · k / N`` distinct backtest PATHS — a *distribution*
of OOS outcomes that feeds PBO / the Deflated Sharpe Ratio (:mod:`nq.validation.dsr`).

Pure stdlib (integer-index math only) so it unit-tests without the heavy data stack — the caller
maps the returned index tuples onto its own time-ordered observation frame. Ported verbatim from
the validated source ``src/validation/cpcv.py``.
"""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class CPCVSplit:
    """One combinatorial split. ``test_groups`` are the held-out group ids; ``train_idx`` /
    ``test_idx`` are sorted, disjoint 0-based observation indices."""

    test_groups: tuple[int, ...]
    train_idx: tuple[int, ...]
    test_idx: tuple[int, ...]


def _validate(n_groups: int, n_test_groups: int) -> None:
    if n_groups < 2:
        raise ValueError(f"n_groups must be >= 2, got {n_groups}")
    if not 1 <= n_test_groups < n_groups:
        raise ValueError(f"n_test_groups must be in [1, n_groups-1], got {n_test_groups}")


def n_splits(n_groups: int, n_test_groups: int) -> int:
    """Number of combinatorial splits = ``C(n_groups, n_test_groups)``."""
    _validate(n_groups, n_test_groups)
    return math.comb(n_groups, n_test_groups)


def n_backtest_paths(n_groups: int, n_test_groups: int) -> int:
    """Distinct OOS paths CPCV reconstructs = ``C(N, k) · k / N``."""
    _validate(n_groups, n_test_groups)
    return math.comb(n_groups, n_test_groups) * n_test_groups // n_groups


def make_groups(n_obs: int, n_groups: int) -> list[tuple[int, int]]:
    """Partition ``range(n_obs)`` into ``n_groups`` contiguous ``[start, end)`` spans, as balanced
    as possible (earlier groups take the remainder)."""
    if n_obs < n_groups:
        raise ValueError(f"n_obs ({n_obs}) must be >= n_groups ({n_groups})")
    base, rem = divmod(n_obs, n_groups)
    spans: list[tuple[int, int]] = []
    start = 0
    for g in range(n_groups):
        size = base + (1 if g < rem else 0)
        spans.append((start, start + size))
        start += size
    return spans


def contiguous_blocks(indices: Sequence[int]) -> list[tuple[int, int]]:
    """Collapse observation indices into INCLUSIVE contiguous runs, e.g.
    ``[3,4,5, 8,9] -> [(3,5), (8,9)]``. A period backtester runs one (start, end) per block."""
    xs = sorted({int(i) for i in indices})
    if not xs:
        return []
    blocks: list[tuple[int, int]] = []
    run_start = prev = xs[0]
    for i in xs[1:]:
        if i == prev + 1:
            prev = i
            continue
        blocks.append((run_start, prev))
        run_start = prev = i
    blocks.append((run_start, prev))
    return blocks


def cpcv_splits(
    n_obs: int, n_groups: int = 10, n_test_groups: int = 2, *,
    horizon: int = 0, embargo: int = 0,
) -> list[CPCVSplit]:
    """Generate the ``C(n_groups, n_test_groups)`` purged + embargoed splits. A training obs ``j``
    whose label ``[j, j+horizon]`` reaches into a test block is purged; ``embargo`` obs right after
    each test block are also dropped. Pass ``embargo >= horizon`` for full two-sided purging."""
    _validate(n_groups, n_test_groups)
    if horizon < 0 or embargo < 0:
        raise ValueError("horizon and embargo must be >= 0")
    if horizon > 0 and embargo < horizon:
        warnings.warn(
            f"cpcv_splits: embargo ({embargo}) < horizon ({horizon}) — labels can leak across the "
            f"test boundary; pass embargo >= horizon for full purging.",
            stacklevel=2,
        )

    spans = make_groups(n_obs, n_groups)
    splits: list[CPCVSplit] = []
    for combo in combinations(range(n_groups), n_test_groups):
        test_blocks = [spans[g] for g in combo]
        test_idx = [i for (s, e) in test_blocks for i in range(s, e)]
        excluded: set[int] = set(test_idx)
        for s, e in test_blocks:
            for j in range(max(0, s - horizon), e):     # purge: labels reaching into [s, e)
                excluded.add(j)
            for j in range(e, min(n_obs, e + embargo)):  # embargo: obs right after the block
                excluded.add(j)
        train_idx = tuple(i for i in range(n_obs) if i not in excluded)
        splits.append(CPCVSplit(test_groups=combo, train_idx=train_idx, test_idx=tuple(test_idx)))
    return splits


def cpcv_paths(splits: Sequence[CPCVSplit], n_groups: int) -> list[dict[int, int]]:
    """Reconstruct the ``C(N,k)·k/N`` full-length OOS PATHS from the splits. Each group is a test
    group in exactly ``C(N-1,k-1)`` splits; its i-th occurrence feeds path i. Returns one dict per
    path mapping ``group_index -> split_index``. Raises if group coverage is uneven."""
    per_group: dict[int, list[int]] = {g: [] for g in range(n_groups)}
    for si, s in enumerate(splits):
        for g in s.test_groups:
            if g in per_group:
                per_group[g].append(si)
    counts = {len(v) for v in per_group.values()}
    if len(counts) != 1:
        raise ValueError(
            f"uneven group coverage {sorted(counts)} — cpcv_paths needs the full C(N,k) split "
            "enumeration (every group tested the same number of times)")
    n_paths = counts.pop()
    return [{g: per_group[g][p] for g in range(n_groups)} for p in range(n_paths)]
