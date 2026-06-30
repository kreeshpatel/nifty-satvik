"""Rank-IC + matched-permutation null — "is this score's ranking distinguishable from chance?"

Used by Stage-C conviction validation: does conviction-at-entry rank the realised per-trade P&L
better than a random score would? The matched-permutation null (AUD-022 lesson) is the honest
significance test for an IC — a raw IC looks impressive on small samples; the null says how often
chance alone produces an |IC| that large.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def spearman_ic(x, y) -> float:
    """Spearman rank-IC = Pearson correlation of the ranks (ties averaged). NaN-pairs dropped.
    Returns nan if < 3 valid pairs or either side is constant."""
    sx, sy = pd.Series(np.asarray(x, dtype=float)), pd.Series(np.asarray(y, dtype=float))
    m = sx.notna() & sy.notna()
    if int(m.sum()) < 3:
        return float("nan")
    rx, ry = sx[m].rank(), sy[m].rank()
    if rx.std(ddof=0) == 0 or ry.std(ddof=0) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def permutation_ic_pvalue(x, y, *, n_perm: int = 5000, seed: int | None = 12345,
                          block: int | None = None) -> dict:
    """Observed Spearman IC of (x, y) plus a two-sided permutation p-value: scramble ``y`` ``n_perm``
    times and measure how often chance produces an |IC| >= |observed|. p = the fraction of
    permutations whose |IC| >= |observed| — small p => the ranking carries real information.

    ``block``: when set, x/y are assumed **time-ordered** and the null is a BLOCK permutation —
    ``y`` is cut into contiguous blocks of ``block`` observations and the block ORDER is shuffled
    (within-block structure preserved). This is the correct null for OVERLAPPING / autocorrelated
    observations (e.g. 63-day-hold trades whose returns co-move): an IID shuffle (``block=None``)
    treats them as exchangeable and gives an ANTI-CONSERVATIVE (too small) p-value."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    obs = spearman_ic(x, y)
    if not np.isfinite(obs) or x.size < 3:
        return {"ic": obs, "n": int(x.size), "n_perm": 0, "p_value": float("nan"), "block": None,
                "null_mean": float("nan"), "null_std": float("nan"),
                "null_p05": float("nan"), "null_p95": float("nan")}
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    use_block = bool(block) and block > 1 and x.size > 2 * block
    if use_block:
        nb = int(math.ceil(x.size / block))
        bounds = [(i * block, min((i + 1) * block, x.size)) for i in range(nb)]
        for i in range(n_perm):
            order = rng.permutation(nb)
            yp = np.concatenate([y[a:b] for a, b in (bounds[j] for j in order)])
            null[i] = spearman_ic(x, yp)
    else:
        yp = y.copy()
        for i in range(n_perm):
            rng.shuffle(yp)
            null[i] = spearman_ic(x, yp)
    null = null[np.isfinite(null)]
    p = float((np.abs(null) >= abs(obs)).mean()) if null.size else float("nan")
    return {"ic": float(obs), "n": int(x.size), "n_perm": int(null.size), "p_value": p,
            "block": (int(block) if use_block else None),
            "null_mean": float(null.mean()), "null_std": float(null.std()),
            "null_p05": float(np.percentile(null, 5)), "null_p95": float(np.percentile(null, 95))}
