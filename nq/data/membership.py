"""Point-in-time Nifty-500 index-membership mask — the survivorship-bias fix.

Without this, a backtest uses *today's* index for every historical date: a 2025 entrant is
treated as "in the index" in 2020, and a 2023 removal is treated as present in 2024-25. The
tradeable set is contaminated by look-back winners → inflated CAGR and suppressed drawdown.

Fix: for each ``(ticker, date)`` include the row only if the ticker was a Nifty-500
constituent on that date. This module owns the data contract + the filter.

Active file: ``data/nifty500_membership.csv`` — the survivorship-corrected reconstruction
(~813 tickers, real entry/exit + re-entry periods) from Wayback snapshots of the NSE
constituent CSV. The naive survivor-only file (497 names, all ``to_date=2030``) is preserved
at ``nifty500_membership_naive.csv`` and **must never** be used for backtest construction.

CAVEAT: no pre-2018 Wayback snapshot exists, so 2011-2018 membership is the 2018-10 set
back-extended → trust **only >=2019 folds** as fully survivorship-clean.

Schema (one row per continuous inclusion period)::

    ticker,from_date,to_date
    RELIANCE,2010-01-01,2026-04-22
    SWANENERGY,2020-01-01,2023-07-15      # removed, then possibly re-added on a later row

``load_membership()`` returns ``None`` when the file is missing, so callers no-op gracefully.
Ported verbatim (behaviour-preserving) from the validated source.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from config import DATA_DIR

MEMBERSHIP_PATH = DATA_DIR / "nifty500_membership.csv"


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _days(n: int) -> timedelta:
    return timedelta(days=n)


def load_membership(path: Path | None = None) -> dict[str, list[tuple[date, date]]] | None:
    """Read the membership CSV → ``{ticker: [(from, to), ...]}`` (inclusive periods).

    Returns ``None`` when the file is missing (callers no-op). Returns ``{}`` if the file
    exists but is empty/unparseable (would make the filter drop everything — callers should
    check for non-empty before applying).
    """
    p = path or MEMBERSHIP_PATH
    if not p.exists():
        return None

    by_ticker: dict[str, list[tuple[date, date]]] = {}
    try:
        with open(p, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = (row.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                d_from = _parse_date(row.get("from_date", ""))
                d_to = _parse_date(row.get("to_date", ""))
                if d_from is None or d_to is None or d_to < d_from:
                    continue
                by_ticker.setdefault(ticker, []).append((d_from, d_to))
    except Exception:
        return {}

    for t in by_ticker:
        by_ticker[t].sort(key=lambda pair: pair[0])
    return by_ticker


def ticker_in_index_on(ticker: str, as_of: date,
                       membership: dict[str, list[tuple[date, date]]]) -> bool:
    """True if ``ticker`` was a Nifty-500 member on ``as_of``."""
    periods = membership.get(ticker.upper())
    if not periods:
        return False
    return any(d_from <= as_of <= d_to for d_from, d_to in periods)


def current_members(
    membership: dict[str, list[tuple[date, date]]] | None,
    ref_date: date | None = None, *, grace_days: int = 14,
) -> set[str]:
    """Tickers that are CURRENT index members as of ``ref_date`` (default today): any whose
    inclusion period is active — ``from_date <= ref`` and ``to_date >= ref - grace_days``
    (the grace absorbs a name that exited within the last fortnight; the open-ended 2030
    sentinel for still-active names always passes). Empty set when membership is None/empty.
    """
    if not membership:
        return set()
    ref = ref_date or date.today()
    floor = ref - _days(grace_days)
    out: set[str] = set()
    for ticker, periods in membership.items():
        for d_from, d_to in periods:
            if d_from <= ref and d_to >= floor:
                out.add(ticker)
                break
    return out


def filter_features_dict(
    features: dict[str, pd.DataFrame],
    membership: dict[str, list[tuple[date, date]]] | None,
    verbose: bool = False,
) -> dict[str, pd.DataFrame]:
    """Return a copy of ``features`` with each per-ticker frame masked to only the dates the
    ticker was in the Nifty-500. Tickers never in membership are dropped entirely. If
    ``membership`` is None, returns ``features`` unchanged (no-op)."""
    if membership is None:
        return features

    filtered: dict[str, pd.DataFrame] = {}
    rows_before = sum(len(df) for df in features.values())
    rows_after = 0
    tickers_dropped = 0
    tickers_masked = 0

    for ticker, df in features.items():
        periods = membership.get(ticker.upper())
        if not periods:
            tickers_dropped += 1
            continue
        idx = df.index
        mask = pd.Series(False, index=idx)
        for d_from, d_to in periods:
            mask |= (idx >= pd.Timestamp(d_from)) & (idx <= pd.Timestamp(d_to))
        subset = df[mask]
        if len(subset) == 0:
            tickers_dropped += 1
            continue
        filtered[ticker] = subset
        rows_after += len(subset)
        if len(subset) < len(df):
            tickers_masked += 1

    if verbose:
        kept_pct = 100 * rows_after / rows_before if rows_before else 0.0
        print(f"  Membership filter: {rows_before:,} -> {rows_after:,} rows ({kept_pct:.1f}% kept)")
        print(f"    tickers dropped (no history in index): {tickers_dropped}")
        print(f"    tickers partially masked: {tickers_masked}")
        print(f"    tickers kept whole: {len(filtered) - tickers_masked}")

    return filtered


def membership_stats(membership: dict[str, list[tuple[date, date]]] | None) -> dict:
    """Quick sanity summary for a loaded membership file."""
    if not membership:
        return {"n_tickers": 0}
    all_periods = [p for periods in membership.values() for p in periods]
    all_from = [p[0] for p in all_periods]
    all_to = [p[1] for p in all_periods]
    still_active = sum(1 for periods in membership.values()
                       if any(d_to >= date.today() - _days(7) for _, d_to in periods))
    return {
        "n_tickers": len(membership),
        "n_period_rows": len(all_periods),
        "earliest_from": min(all_from).isoformat() if all_from else None,
        "latest_to": max(all_to).isoformat() if all_to else None,
        "tickers_still_active": still_active,
        "tickers_historical_only": len(membership) - still_active,
    }
