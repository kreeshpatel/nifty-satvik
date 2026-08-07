"""Monte Carlo resampling — the drawdown DISTRIBUTION, not the one path you happened to get.

A backtest reports one realisation. Its max drawdown is a single draw from a distribution, and
reporting "-24% max drawdown" from one path invites planning against a number that had no reason to
be the one observed.

Use :func:`resample_equity_curve` for drawdown questions
-------------------------------------------------------
It bootstraps the equity curve's **daily returns** in time-sized blocks — the series a drawdown is
actually made of. The trade-sequence functions below answer a different and weaker question, and on
pre-reg 0001 they answered it wrongly in two ways at once: the block was 10 *trades* (~10 sessions)
against a drawdown spanning months, and the "observed" figure was a path RECONSTRUCTED from trade
returns at a notional weight, not the book's real curve. The realised drawdown appeared to sit at
the 0th percentile of 5,000 resamples. It was neither unlucky nor real — it was the wrong series
compared against resamples of itself.

Trade-sequence schemes, and what they are actually for
------------------------------------------------------
``iid``    shuffle individual trades. Destroys all ordering, so it answers "what if the same trades
           had arrived in any order?" Understates drawdown whenever losses cluster — and in a
           long-only equity book they do, because names fall together.

``block``  resample contiguous runs of trades. Preserves local clustering, so bad patches stay bad
           patches.

Comparing the two is diagnostic about the TRADE SEQUENCE: a large gap says the strategy's risk is
concentrated in clustered episodes rather than spread across trades. Neither is a drawdown estimate,
because neither knows the calendar — overlapping positions falling together, which is the actual
mechanism of an equity drawdown, is not represented in a trade list at all.

What this does NOT do
---------------------
Resampling adds no information. It re-uses the same realised trades, so it cannot reveal a risk the
sample never contained — a book that never met a 2008 has no 2008 in its bootstrap. It widens the
error bars on what was observed; it does not extend the observation.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["MonteCarloResult", "resample_trades", "trade_returns", "resample_equity_curve",
           "suggest_block_days", "acf"]


@dataclass(frozen=True)
class MonteCarloResult:
    """Distributional summary across resampled paths."""
    n_paths: int
    n_trades: int
    scheme: str
    block: int
    dd_median: float
    dd_p95: float                  # a bad-but-plausible drawdown
    dd_p99: float                  # the planning number
    dd_worst: float
    dd_observed: float             # the actual backtest path, for reference
    dd_observed_pctile: float      # where the realised path sat in the distribution
    terminal_median: float
    terminal_p05: float
    terminal_p95: float
    prob_loss: float               # share of paths ending below the starting capital

    @property
    def observed_was_lucky(self) -> bool:
        """True when the realised drawdown was shallower than the median resampled path."""
        return self.dd_observed > self.dd_median


def acf(x: np.ndarray, max_lag: int = 120) -> np.ndarray:
    """Autocorrelation of ``x`` at lags 1..max_lag."""
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)] - np.mean(v[np.isfinite(v)])
    n = len(v)
    denom = float(v @ v)
    if n < 3 or denom <= 0:
        return np.zeros(max_lag)
    return np.array([float(v[k:] @ v[:-k]) / denom for k in range(1, min(max_lag, n - 1) + 1)])


def suggest_block_days(daily_returns: np.ndarray, *, max_lag: int = 120,
                       floor: int = 21) -> int:
    """Block length for a drawdown bootstrap, read off the data rather than guessed.

    Drawdowns are produced by **volatility clustering**, so the dependence that matters is in
    ``|r|``, not ``r`` — raw returns are close to uncorrelated even when their magnitudes are
    strongly persistent. The block is taken as the first lag at which the ACF of ``|r|`` falls
    below ``2/sqrt(n)`` (the usual white-noise band), floored at one month.

    **Why this matters.** A block shorter than the dependence horizon degenerates toward iid and
    shreds exactly the clustering it exists to preserve, which understates tail drawdown every time.
    On pre-reg 0001 a 10-*trade* block (~10 sessions at that turnover) produced a p99 of −20.6%
    against an observed −29.4% — the realised path sat at the 0th percentile of 5,000 resamples,
    which is the signature of a mis-sized block rather than bad luck.
    """
    r = np.asarray(daily_returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 60:
        return floor
    a = acf(np.abs(r), max_lag=max_lag)
    band = 2.0 / np.sqrt(len(r))
    below = np.flatnonzero(a < band)
    lag = int(below[0] + 1) if below.size else max_lag
    return max(floor, lag)


def resample_equity_curve(
    equity_curve: Sequence[dict[str, Any]], *,
    n_paths: int = 5000, block_days: int | None = None, seed: int = 20260807,
) -> MonteCarloResult:
    """Moving-block bootstrap on the equity curve's DAILY returns — the drawdown distribution.

    Prefer this over :func:`resample_trades` for any drawdown question. Trade-sequence resampling
    answers "what if these trades had arrived in another order", which is a different and weaker
    question: it ignores the calendar, so overlapping positions falling together — the actual
    mechanism of an equity drawdown — is not represented at all.

    ``block_days`` defaults to :func:`suggest_block_days` on the curve itself.
    """
    eq = np.array([float(e["equity"]) for e in equity_curve], dtype=float)
    if len(eq) < 60:
        raise ValueError(f"need >= 60 sessions to resample a curve, got {len(eq)}")
    r = np.diff(eq) / eq[:-1]
    r = r[np.isfinite(r)]
    block = int(block_days or suggest_block_days(r))
    n = len(r)
    rng = np.random.default_rng(seed)
    observed = _max_drawdown(eq)

    n_blocks = int(np.ceil(n / block))
    starts = np.arange(max(n - block + 1, 1))
    dds = np.empty(n_paths)
    terms = np.empty(n_paths)
    for i in range(n_paths):
        picks = rng.choice(starts, n_blocks)
        seq = np.concatenate([r[s:s + block] for s in picks])[:n]
        path = np.cumprod(1.0 + seq)
        dds[i], terms[i] = _max_drawdown(path), path[-1]

    return MonteCarloResult(
        n_paths=n_paths, n_trades=n, scheme="equity_block", block=block,
        dd_median=float(np.percentile(dds, 50)),
        dd_p95=float(np.percentile(dds, 5)),
        dd_p99=float(np.percentile(dds, 1)),
        dd_worst=float(dds.min()),
        dd_observed=observed,
        dd_observed_pctile=float((dds < observed).mean()),
        terminal_median=float(np.percentile(terms, 50)),
        terminal_p05=float(np.percentile(terms, 5)),
        terminal_p95=float(np.percentile(terms, 95)),
        prob_loss=float((terms < 1.0).mean()),
    )


def trade_returns(trades: Sequence[dict[str, Any]], *, key: str = "return_pct") -> np.ndarray:
    """Per-trade fractional returns from an engine's trade list."""
    return np.array([float(t[key]) / 100.0 for t in trades if np.isfinite(float(t.get(key, np.nan)))],
                    dtype=float)


def _max_drawdown(equity: np.ndarray) -> float:
    return float((equity / np.maximum.accumulate(equity) - 1.0).min())


def _path(rets: np.ndarray, weight: float) -> np.ndarray:
    """Compound a sequence of per-trade returns at a fixed fraction of equity."""
    return np.cumprod(1.0 + rets * weight)


def resample_trades(
    trades: Sequence[dict[str, Any]] | np.ndarray, *,
    n_paths: int = 5000, scheme: str = "block", block: int = 10,
    weight: float = 0.10, seed: int = 20260807,
) -> MonteCarloResult:
    """Resample the trade sequence and report the drawdown / terminal-wealth distributions.

    ``weight`` is the fraction of equity a single trade moves — the engine's per-name notional, so
    a +2% trade return on a 10% position moves the book 0.2%. Getting this wrong rescales every
    drawdown, so it is explicit rather than inferred.
    """
    rets = trades if isinstance(trades, np.ndarray) else trade_returns(trades)
    rets = rets[np.isfinite(rets)]
    n = len(rets)
    if n < 20:
        raise ValueError(f"need >= 20 trades to resample, got {n}")
    if scheme not in ("iid", "block"):
        raise ValueError("scheme must be 'iid' or 'block'")

    rng = np.random.default_rng(seed)
    observed_dd = _max_drawdown(_path(rets, weight))

    dds = np.empty(n_paths)
    terms = np.empty(n_paths)
    if scheme == "iid":
        for i in range(n_paths):
            eq = _path(rng.permutation(rets), weight)
            dds[i], terms[i] = _max_drawdown(eq), eq[-1]
    else:
        n_blocks = int(np.ceil(n / block))
        starts = np.arange(max(n - block + 1, 1))
        for i in range(n_paths):
            picks = rng.choice(starts, n_blocks)
            seq = np.concatenate([rets[s:s + block] for s in picks])[:n]
            eq = _path(seq, weight)
            dds[i], terms[i] = _max_drawdown(eq), eq[-1]

    return MonteCarloResult(
        n_paths=n_paths, n_trades=n, scheme=scheme, block=block,
        dd_median=float(np.percentile(dds, 50)),
        dd_p95=float(np.percentile(dds, 5)),        # 5th pctile of a negative series = bad tail
        dd_p99=float(np.percentile(dds, 1)),
        dd_worst=float(dds.min()),
        dd_observed=observed_dd,
        dd_observed_pctile=float((dds < observed_dd).mean()),
        terminal_median=float(np.percentile(terms, 50)),
        terminal_p05=float(np.percentile(terms, 5)),
        terminal_p95=float(np.percentile(terms, 95)),
        prob_loss=float((terms < 1.0).mean()),
    )
