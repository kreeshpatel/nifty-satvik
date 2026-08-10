"""Intraday bar store — pagination, merge, and the coverage audit.

Why this exists. Every cheap screen on the 2017-2026 daily panel is bounded at n_eff = 37
independent 63-day windows and a dSharpe half-width of ±0.59, permanently. Building a genuinely new
sample is the only action that moves that number rather than re-spending it, and intraday bars for
the F&O universe are the elected direction (`diagnostics/research/n_trials.json` reset rationale).

What this module is, and is not. It owns the **mechanics**: how a multi-year request is split into
vendor-legal pages, how those pages are rejoined without dropping or duplicating a bar, and how the
resulting store is audited for coverage. It owns no strategy, no signal and no decision. The network
call is injected, so everything here is testable without a credential or a socket.

Vendor page limits (Kite Connect v3 historical candles) are **per request**, not ceilings on
available history — the distinction that made this project viable at all after yfinance's hard
60/730-day caps had suggested otherwise. You paginate.

Survivorship, stated rather than assumed. ADR-0015 (owner, 2026-08-10) decided the delisted-name
probe does NOT gate this build: finding 0025 measured that survivorship bias scales with holding
period, and an intraday book sits at the short end where that mechanism is weakest. The waiver is of
the *build gate* only. `coverage_report` is the first deliverable of the store, not the last, and it
measures the delisted tail regardless — so any result computed here can state its survivorship
status instead of implying one.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

__all__ = ["PAGE_DAYS", "date_pages", "merge_pages", "fetch_symbol", "coverage_report",
           "bars_strictly_before", "CoverageReport"]

# Documented maximum lookback PER REQUEST, by interval.
# https://kite.trade/docs/connect/v3/historical/
PAGE_DAYS: dict[str, int] = {
    "minute": 60,
    "3minute": 100, "5minute": 100, "10minute": 100,
    "15minute": 200, "30minute": 200,
    "60minute": 400, "day": 2000,
}

BAR_COLUMNS = ("date", "open", "high", "low", "close", "volume")


def date_pages(start: dt.date | str, end: dt.date | str, interval: str) -> list[tuple[dt.date, dt.date]]:
    """Split ``[start, end]`` into inclusive pages no longer than the interval's vendor limit.

    Pages are contiguous and NON-overlapping: the next page begins the day after the previous one
    ends. Overlapping them would be the safer-looking choice and is deliberately not done — it
    invites double-counted bars at every seam, and `merge_pages` should not be relied on to repair
    a defect the pager could avoid. `merge_pages` still de-duplicates, because the *vendor* may
    return a boundary bar twice.
    """
    if interval not in PAGE_DAYS:
        raise ValueError(f"unknown interval {interval!r}; known: {sorted(PAGE_DAYS)}")
    s = pd.Timestamp(start).date()
    e = pd.Timestamp(end).date()
    if e < s:
        raise ValueError(f"end {e} precedes start {s}")

    span = dt.timedelta(days=PAGE_DAYS[interval] - 1)     # inclusive span => limit-1 of delta
    out: list[tuple[dt.date, dt.date]] = []
    cur = s
    while cur <= e:
        stop = min(cur + span, e)
        out.append((cur, stop))
        cur = stop + dt.timedelta(days=1)
    return out


def merge_pages(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate paginated responses into one strictly-increasing bar series.

    De-duplicates on timestamp keeping the FIRST occurrence, because a vendor that repeats a
    boundary bar across two pages should not silently double its volume. Returns an empty frame with
    the right columns when there is nothing, so callers never branch on None.
    """
    kept = [f for f in frames if f is not None and len(f)]
    if not kept:
        return pd.DataFrame({c: pd.Series(dtype="float64") for c in BAR_COLUMNS})

    df = pd.concat(kept, ignore_index=True)
    missing = set(BAR_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"bar frame missing columns: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], utc=False)
    df = (df.drop_duplicates(subset="date", keep="first")
            .sort_values("date", kind="mergesort")
            .reset_index(drop=True))
    return df


def fetch_symbol(historical: Callable[..., list], token: int, start, end, interval: str,
                 *, on_error: str = "raise") -> pd.DataFrame:
    """Paginate one instrument through ``historical(token, from, to, interval)``.

    ``historical`` is injected — in production it is ``kite.historical_data``; in tests it is a
    function. This module never constructs a client and never reads a credential.

    ``on_error='skip'`` drops a failed page and keeps going, which is how a multi-year backfill
    survives one transient vendor 500. The default raises, because a silent hole in a research store
    is worse than a failed run — the store would look complete and be wrong.
    """
    if on_error not in ("raise", "skip"):
        raise ValueError("on_error must be 'raise' or 'skip'")
    pages = []
    for a, b in date_pages(start, end, interval):
        try:
            rows = historical(token, a, b, interval)
        except Exception:
            if on_error == "raise":
                raise
            continue
        if rows:
            pages.append(pd.DataFrame(rows))
    return merge_pages(pages)


def bars_strictly_before(bars: pd.DataFrame, when) -> pd.DataFrame:
    """Every bar that had CLOSED before ``when``.

    Strict: a bar timestamped exactly at the decision instant is excluded. Kite stamps a candle with
    its OPEN time, so a 14:30 bar is still forming at 14:30 and using it is lookahead — the same
    partial-candle error the 14:30 shadow scan was built around and never escaped.
    """
    if not len(bars):
        return bars
    return bars[pd.to_datetime(bars["date"]) < pd.Timestamp(when)]


@dataclass(frozen=True)
class CoverageReport:
    """Gate-1 coverage of a built store. Descriptive: it measures, it does not pass or fail."""
    interval: str
    n_requested: int
    n_present: int
    by_year: dict[int, int]
    empty_symbols: tuple[str, ...]
    delisted_requested: tuple[str, ...]
    delisted_present: tuple[str, ...]

    @property
    def linkage_pct(self) -> float:
        return 0.0 if not self.n_requested else round(100.0 * self.n_present / self.n_requested, 2)

    @property
    def delisted_pct(self) -> float:
        n = len(self.delisted_requested)
        return 0.0 if not n else round(100.0 * len(self.delisted_present) / n, 2)

    def summary(self) -> str:
        miss = len(self.delisted_requested) - len(self.delisted_present)
        return (f"interval {self.interval} | symbols {self.n_present}/{self.n_requested} "
                f"({self.linkage_pct}%) | delisted {len(self.delisted_present)}/"
                f"{len(self.delisted_requested)} ({self.delisted_pct}%), {miss} absent | "
                f"years {min(self.by_year, default='-')}..{max(self.by_year, default='-')}")


def coverage_report(store: dict[str, pd.DataFrame], requested: Sequence[str], interval: str,
                    *, delisted: Sequence[str] = ()) -> CoverageReport:
    """Audit a built store: linkage, per-year bar counts, and the delisted tail.

    ADR-0015 waived the delisted probe as a *build gate*, not as a measurement. This computes the
    number anyway and at no extra cost, so a result carried on this store can state its
    survivorship status rather than imply one.
    """
    present = {s for s in requested if s in store and len(store[s])}
    by_year: dict[int, int] = {}
    for s in present:
        yrs = pd.to_datetime(store[s]["date"]).dt.year
        for y, n in yrs.value_counts().items():
            by_year[int(y)] = by_year.get(int(y), 0) + int(n)

    return CoverageReport(
        interval=interval,
        n_requested=len(requested),
        n_present=len(present),
        by_year=dict(sorted(by_year.items())),
        empty_symbols=tuple(sorted(s for s in requested if s not in present)),
        delisted_requested=tuple(delisted),
        delisted_present=tuple(sorted(s for s in delisted if s in present)),
    )
