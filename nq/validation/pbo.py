"""Probability of Backtest Overfitting (PBO) — the "is my best config just luck?" test.

Bailey, Borwein, Lopez de Prado & Zhu, *The Probability of Backtest Overfitting* (2015), via
Combinatorially Symmetric Cross-Validation (CSCV).

What it answers, and why it is different from the Deflated Sharpe Ratio
----------------------------------------------------------------------
DSR asks: **given that I tried N configurations, is this Sharpe still significant?** It corrects a
single number for the number of attempts.

PBO asks a sharper question: **when I pick the best configuration in-sample, how often does it land
in the bottom half out-of-sample?** It measures the *selection procedure* rather than the winner.
A strategy family can contain a genuine edge and still have high PBO if the ranking between its
configurations is noise — which is precisely the failure mode where a parameter sweep produces a
confident-looking winner that does not survive.

The two are complements. DSR can pass while PBO says the choice was arbitrary.

How CSCV works
--------------
Take the per-period returns of every configuration as a matrix ``M`` (rows = periods, columns =
configurations). Split the rows into ``S`` contiguous blocks. For each of the ``C(S, S/2)`` ways to
choose half the blocks as the in-sample set:

1. pick the configuration with the best in-sample performance;
2. find that configuration's **rank** among all configurations in the complementary out-of-sample
    half;
3. convert the rank to a relative rank ``w`` in (0, 1), where higher is better;
4. record the logit ``lambda = ln(w / (1 - w))``.

``PBO = P(lambda <= 0)`` — the share of splits where the in-sample winner finished in the bottom
half out-of-sample. Under pure noise the winner is a coin flip and PBO tends to 0.5.

**Reading it:** PBO < 0.5 is the usual bar; the literature treats values approaching 0.5 as
"the selection carries no information". PBO near 1.0 is worse than useless — it means the in-sample
winner is *systematically* the out-of-sample loser, the signature of fitting noise.

Combinatorially symmetric means every split is also evaluated with its halves swapped, so the
estimate does not depend on which half was arbitrarily called "in sample".
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

__all__ = ["PBOResult", "cscv_pbo", "sharpe_of"]


@dataclass(frozen=True)
class PBOResult:
    """PBO plus the diagnostics that explain it."""
    pbo: float                 # P(in-sample winner lands in the bottom half OOS)
    n_splits: int
    n_configs: int
    n_periods: int
    median_logit: float
    oos_ranks: tuple[float, ...]      # relative OOS rank of each in-sample winner, in (0,1)
    winner_counts: dict[int, int]     # how often each config was the in-sample winner

    @property
    def selection_is_informative(self) -> bool:
        """True when picking the in-sample best beats a coin flip out of sample."""
        return self.pbo < 0.5


_DEGENERATE_SD = 1e-12


def sharpe_of(returns: np.ndarray, periods: int = 252) -> float:
    """Annualised Sharpe of a return column; 0.0 when degenerate, so it can never win by accident.

    The floor is a tolerance, not ``sd > 0``. A constant column does NOT have exactly zero sample
    standard deviation in floating point — ``np.full(100, 0.01).std(ddof=1)`` is about 1.7e-18 —
    so a strict ``> 0`` check lets it through and returns a Sharpe near 1e17, which then wins every
    CSCV split and drives PBO to a meaningless value. A real daily return series never has a
    standard deviation below 1e-12; anything that does is numerically constant.
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if r.size < 2:
        return 0.0
    sd = float(r.std(ddof=1))
    if not np.isfinite(sd) or sd < _DEGENERATE_SD:
        return 0.0
    out = float(r.mean() / sd * np.sqrt(periods))
    return out if np.isfinite(out) else 0.0


def cscv_pbo(matrix: np.ndarray, *, n_blocks: int = 16, periods: int = 252,
             metric=None) -> PBOResult:
    """Run CSCV on a ``(n_periods, n_configs)`` matrix of per-period returns.

    ``n_blocks`` must be even; the number of splits is ``C(n_blocks, n_blocks/2)`` (12,870 at the
    default 16, which is the value used in the source paper).

    Raises on fewer than two configurations — PBO is a statement about *choosing between*
    configurations, so a single-config call is a category error rather than an edge case.
    """
    M = np.asarray(matrix, dtype=float)
    if M.ndim != 2:
        raise ValueError("matrix must be 2-D: (n_periods, n_configs)")
    n_periods, n_configs = M.shape
    if n_configs < 2:
        raise ValueError("PBO compares configurations; need at least 2 columns")
    if n_blocks % 2 or n_blocks < 4:
        raise ValueError("n_blocks must be even and >= 4")
    if n_periods < n_blocks * 2:
        raise ValueError(f"need >= {n_blocks * 2} periods for {n_blocks} blocks, got {n_periods}")
    metric = metric or (lambda col: sharpe_of(col, periods))

    bounds = np.linspace(0, n_periods, n_blocks + 1, dtype=int)
    blocks = [np.arange(bounds[i], bounds[i + 1]) for i in range(n_blocks)]

    logits: list[float] = []
    ranks: list[float] = []
    winners: dict[int, int] = {}
    half = n_blocks // 2

    for combo in combinations(range(n_blocks), half):
        is_idx = np.concatenate([blocks[b] for b in combo])
        oos_idx = np.concatenate([blocks[b] for b in range(n_blocks) if b not in combo])
        is_perf = np.array([metric(M[is_idx, j]) for j in range(n_configs)])
        oos_perf = np.array([metric(M[oos_idx, j]) for j in range(n_configs)])
        best = int(np.nanargmax(is_perf))
        winners[best] = winners.get(best, 0) + 1

        order = np.argsort(np.argsort(oos_perf))          # 0 = worst
        w = (order[best] + 1) / (n_configs + 1)           # relative rank in (0,1)
        ranks.append(float(w))
        logits.append(float(np.log(w / (1.0 - w))))

    lg = np.array(logits, dtype=float)
    return PBOResult(
        pbo=float((lg <= 0).mean()),
        n_splits=len(lg), n_configs=n_configs, n_periods=n_periods,
        median_logit=float(np.median(lg)),
        oos_ranks=tuple(ranks), winner_counts=winners,
    )
