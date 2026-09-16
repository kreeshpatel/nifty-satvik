"""Excursions against the random-walk null — is a target "too high", or is it chance?

Layer 5 of the Brain. Pure functions: no network, no clock, no model calls. The diagnostic that feeds
prices in is `scripts/diag_excursions_null.py`; the definitions it implements are fixed in
`diagnostics/research/excursions_null/SPEC.md`, committed before any result existed.

WHY A NULL IS THE WHOLE POINT

A 2:1 target is reached before its stop about a third of the time by a driftless walk, whatever was
bought (optional stopping: P = b/(a+b) in log space). So "the target is rarely hit" is not evidence of
anything until it is compared with that number over the same trades. :func:`null_p_target_first` gives
the null; :func:`first_passage` measures what the path actually did; the gap between them is the only
part the entry can take credit or blame for.

WHAT THIS CANNOT DO

It describes the geometry of past entries. It does not choose a target: a change to the live `tp1_r` is
a change to the book, which needs a pre-registration, a trial, and the quarterly review. And it is not a
feature for choosing entries (program-laws I).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import numpy.typing as npt

HIT, STOPPED, UNRESOLVED = "target", "stop", "unresolved"


def null_p_target_first(entry: float, stop: float, target: float, *,
                        mu: float = 0.0, sigma: float | None = None) -> float:
    """P(target before stop) for geometric Brownian motion with continuous barriers.

    With ``sigma`` None (and ``mu`` 0) this is the driftless-in-log-space null b/(a+b), where
    a = ln(target/entry) and b = ln(entry/stop). With an arithmetic drift ``mu`` and volatility ``sigma``
    (both annualised) the log drift is nu = mu − sigma²/2 and

        P = (1 − e^{2·nu·b/sigma²}) / (e^{−2·nu·a/sigma²} − e^{2·nu·b/sigma²})

    which tends to b/(a+b) as nu → 0. ``sigma`` None means the driftless null (``mu`` must then be 0).
    """
    if not (stop < entry < target):
        raise ValueError(f"need stop < entry < target, got {stop}, {entry}, {target}")
    a = math.log(target / entry)
    b = math.log(entry / stop)
    if sigma is None:
        if mu != 0.0:
            raise ValueError("a drifted null needs sigma")
        return b / (a + b)
    nu = mu - 0.5 * sigma * sigma
    k = 2.0 * nu / (sigma * sigma)
    if abs(k) < 1e-12:
        return b / (a + b)
    num = 1.0 - math.exp(k * b)
    den = math.exp(-k * a) - math.exp(k * b)
    return num / den


@dataclass(frozen=True)
class Passage:
    outcome: str                 # HIT | STOPPED | UNRESOLVED
    sessions: int | None         # sessions from entry to the deciding touch (0 = the entry session)
    mfe_r_before_stop: float     # best High reached before the stop touch (or horizon), in R


def first_passage(high: Sequence[float], low: Sequence[float], *, entry: float, stop: float,
                  target: float) -> Passage:
    """Which barrier the path touched first. Bars start at the entry session.

    Target touch = High ≥ target; stop touch = Low ≤ stop (continuous monitoring, as in the theorem).
    A bar that touches both counts as the STOP first — the conservative convention of the prior barrier
    study and pre-reg 0011.
    """
    if not stop < entry < target:
        raise ValueError(f"need stop < entry < target, got {stop}, {entry}, {target}")
    h = np.asarray(high, dtype=float)
    lo = np.asarray(low, dtype=float)
    if h.shape != lo.shape:
        raise ValueError("high and low must be the same length")
    risk = entry - stop
    stop_hits = np.flatnonzero(lo <= stop)
    tgt_hits = np.flatnonzero(h >= target)
    first_stop = int(stop_hits[0]) if stop_hits.size else None
    first_tgt = int(tgt_hits[0]) if tgt_hits.size else None
    cut = first_stop if first_stop is not None else len(h)
    mfe = float((np.nanmax(h[:cut]) - entry) / risk) if cut > 0 else float("nan")
    if first_stop is not None and (first_tgt is None or first_stop <= first_tgt):
        return Passage(STOPPED, first_stop, mfe)
    if first_tgt is not None:
        return Passage(HIT, first_tgt, mfe)
    return Passage(UNRESOLVED, None, mfe)


def passage_outcomes(high: npt.NDArray[np.float64], low: npt.NDArray[np.float64],
                     close: npt.NDArray[np.float64], week_end: npt.NDArray[np.bool_], *,
                     entry: float, stop: float, ks: Sequence[float], weekly_stop: bool) -> list[str]:
    """Outcome per k for one path, under either stop rule (SPEC A2.2).

    ``weekly_stop=False``: the SPEC's continuous stop (Low <= stop). ``weekly_stop=True``: the live book's
    rule — only a weekly CLOSE <= stop (``week_end`` marks each ISO week's last bar) stops the trade. The
    target is an intraday High >= target either way. A stop and target on the same bar count as the stop
    (conservative, as in :func:`first_passage`).
    """
    stop_mask = (close <= stop) & week_end if weekly_stop else (low <= stop)
    s_hits = np.flatnonzero(stop_mask)
    first_stop = int(s_hits[0]) if s_hits.size else None
    out = []
    for k in ks:
        t_hits = np.flatnonzero(high >= target_at(entry, stop, k))
        first_tgt = int(t_hits[0]) if t_hits.size else None
        if first_stop is not None and (first_tgt is None or first_stop <= first_tgt):
            out.append(STOPPED)
        elif first_tgt is not None:
            out.append(HIT)
        else:
            out.append(UNRESOLVED)
    return out


def target_at(entry: float, stop: float, k: float) -> float:
    """The +kR price: entry + k·(entry − stop)."""
    return entry + k * (entry - stop)


def risk_band(risk_frac: float) -> str:
    """The SPEC's fixed stop-distance bands. The 10% edge is the live `max_risk_pct`.

    Rounded to 6 dp first (SPEC A2.3): a stop capped at exactly entry x 0.90 computes as 0.0999999… or
    0.1000001… by float noise, and must land in `r>=10%` as `[10%, ∞)` says, whichever way it rounds."""
    risk_frac = round(float(risk_frac), 6)
    if risk_frac < 0.05:
        return "r<5%"
    if risk_frac < 0.10:
        return "5%<=r<10%"
    return "r>=10%"


def cluster_bootstrap_diff(obs: Sequence[float], null: Sequence[float], clusters: Sequence[str], *,
                           n_boot: int = 2000, seed: int = 20260916) -> tuple[float, float, float]:
    """(point, lo95, hi95) of mean(obs) − mean(null), resampling whole clusters (tickers).

    Paths of one name overlap in time, so resampling trades independently would understate the spread.
    """
    o = np.asarray(obs, dtype=float)
    nl = np.asarray(null, dtype=float)
    c = np.asarray(clusters)
    if o.size == 0:
        return float("nan"), float("nan"), float("nan")
    point = float(o.mean() - nl.mean())
    keys, inv = np.unique(c, return_inverse=True)
    groups = [np.flatnonzero(inv == g) for g in range(len(keys))]
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[g] for g in pick])
        diffs[i] = o[idx].mean() - nl[idx].mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return point, float(lo), float(hi)
