"""Block bootstrap — percentile CIs that respect serial correlation.

Equity-curve metrics depend on the SEQUENCE of daily returns (a run of 5 losses compounds worse
than 5 scattered losses). An IID bootstrap destroys that; the **overlapping moving-block**
bootstrap preserves short-range autocorrelation by resampling contiguous blocks. The long-horizon
block is **63 trading days** (one full strategy cycle) — shorter blocks understate autocorrelation
and produce falsely narrow CIs (backtest-rigor §E2). Default ``n_samples = 5000`` resamples.

The paired :func:`bootstrap_delta` is the promotion-bar significance test: resample the SAME blocks
of two arms' returns and report the CI of the metric delta (e.g. ΔSharpe) — PROMOTE requires the
95% CI low > 0. Ported behaviour-faithfully from the validated source ``src/validation/bootstrap.py``.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

DEFAULT_BLOCK = 63
DEFAULT_N_SAMPLES = 5000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_SEED = 12345


@dataclass(frozen=True)
class BootstrapResult:
    point: float
    lower: float
    upper: float
    confidence: float
    n_samples: int
    block_size: int


def _resample_indices(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    """Concatenated moving blocks: ceil(n/block) random starts in [0, n-block], trimmed to n."""
    n_blocks = -(-n // block_size)                       # ceil
    starts = rng.integers(0, n - block_size + 1, size=n_blocks)
    idx = np.concatenate([np.arange(s, s + block_size) for s in starts])
    return idx[:n]


def block_bootstrap_metric(
    returns: np.ndarray, metric_fn: Callable[[np.ndarray], float], *,
    block_size: int = DEFAULT_BLOCK, n_samples: int = DEFAULT_N_SAMPLES,
    confidence: float = DEFAULT_CONFIDENCE, seed: int | None = DEFAULT_SEED,
) -> BootstrapResult:
    """Percentile CI for ``metric_fn`` of a daily-return series via the overlapping moving-block
    bootstrap. Point estimate is ``metric_fn`` on the original series."""
    r = np.asarray(returns, dtype=float)
    n = len(r)
    if n == 0:
        raise ValueError("block_bootstrap_metric: returns cannot be empty")
    if not 1 <= block_size <= n:
        raise ValueError(f"block_size must be in [1, {n}], got {block_size}")
    if n_samples < 1:
        raise ValueError("n_samples must be >= 1")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")

    rng = np.random.default_rng(seed)
    vals = np.array([metric_fn(r[_resample_indices(n, block_size, rng)]) for _ in range(n_samples)])
    vals = vals[np.isfinite(vals)]
    alpha = (1.0 - confidence) / 2.0
    lo, hi = np.percentile(vals, [100 * alpha, 100 * (1 - alpha)]) if vals.size else (np.nan, np.nan)
    return BootstrapResult(
        point=float(metric_fn(r)), lower=float(lo), upper=float(hi),
        confidence=confidence, n_samples=n_samples, block_size=block_size)


def bootstrap_delta(
    returns_a: np.ndarray, returns_b: np.ndarray, metric_fn: Callable[[np.ndarray], float], *,
    block_size: int = DEFAULT_BLOCK, n_samples: int = DEFAULT_N_SAMPLES,
    confidence: float = DEFAULT_CONFIDENCE, seed: int | None = DEFAULT_SEED,
) -> BootstrapResult:
    """Paired block bootstrap of ``metric_fn(a) − metric_fn(b)`` — resamples the SAME block indices
    from both arms each draw, so the delta CI is the promotion-bar significance test (PROMOTE needs
    ``lower > 0``). The two series must be the same length and date-aligned."""
    a = np.asarray(returns_a, dtype=float)
    b = np.asarray(returns_b, dtype=float)
    if len(a) != len(b):
        raise ValueError(f"paired arms must be equal length: {len(a)} vs {len(b)}")
    n = len(a)
    if not 1 <= block_size <= n:
        raise ValueError(f"block_size must be in [1, {n}], got {block_size}")
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_samples):
        idx = _resample_indices(n, block_size, rng)
        deltas.append(metric_fn(a[idx]) - metric_fn(b[idx]))
    vals = np.array(deltas)
    vals = vals[np.isfinite(vals)]
    alpha = (1.0 - confidence) / 2.0
    lo, hi = np.percentile(vals, [100 * alpha, 100 * (1 - alpha)]) if vals.size else (np.nan, np.nan)
    return BootstrapResult(
        point=float(metric_fn(a) - metric_fn(b)), lower=float(lo), upper=float(hi),
        confidence=confidence, n_samples=n_samples, block_size=block_size)
