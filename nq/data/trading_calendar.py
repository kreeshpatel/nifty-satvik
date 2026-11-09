"""The ONE trading calendar for orchestration, as-of stamping and freshness checks.

## Why this exists

Until 2026-11 every script carried its own idea of a "session", "last trading day" and "this week":
``pd.bdate_range`` minus a holiday set here, ``weekday() < 5`` there, ``date.today()`` (runner-local,
i.e. UTC on Actions) beside an IST clock elsewhere. On 2026-11-08 (Sunday) NSE held the Diwali Muhurat
session, Yahoo served a real bar dated 11-08, the scan's as-of became 11-08, the blend logger (which
intersects two NAV streams) stopped at the last REGULAR session 11-06, and the post-commit check went red
because it compared the logger's date with the scan's raw as-of. None of the scripts was wrong by its own
lights; they disagreed about what a "session" is.

## Vocabulary (the contract the rest of the repo should use)

* **regular session**   a weekday that is not in ``config.NSE_HOLIDAYS``. The notion watched books,
                        freshness checks and the forward wall count in.
* **special session**   a session NSE holds outside that rule: a weekend (Budget Saturday/Sunday, Muhurat
                        Sunday) or a holiday-listed day that still trades briefly (Muhurat on a weekday
                        is *listed* as a holiday by NSE and still trades). Known ones are in
                        ``SPECIAL_SESSIONS``; unknown ones are caught by passing ``observed=`` (dates the
                        data actually carries a bar for).
* **session**           regular OR special. ``is_session`` / ``last_session(regular=False)``.

## Rules

* ``last_session(asof)`` is "the most recent session on or before ``asof``". Pass ``regular=True`` when the
  answer will be compared against something that only advances on regular sessions (a watched-book NAV, the
  wall). Pass ``closed=True`` to refuse a same-day session whose close has not happened yet.
* ``week_key(d)`` -> ``(iso_year, iso_week)`` of the Mon-Fri trading week ``d`` belongs to. **A weekend
  SESSION belongs to the FOLLOWING week.** Reasoning: the Friday close is a closed week's close and must
  stay final (a frozen week cannot be re-opened by a one-hour Sunday session); and
  ``Series.resample("W-FRI")``, which breadth-50 uses, already files a Sunday bar in the following week.
  A weekend date that is NOT a session (a Saturday cron stamp) keeps its ISO week, i.e. the week that just
  closed. NOTE the live weekly engine's ISO grouping (``nq.data.weekly._iso_week_groups``) files a Sunday
  bar in the PRECEDING week; that is golden-locked and deliberately not changed here (see the PR).
* **Timezone.** Every "today" is the IST date. A tz-aware datetime is converted to IST; a *naive*
  datetime / Timestamp / date is taken to already be an IST calendar date (the runner clock is UTC, and the
  crons fire 02:00-13:00 UTC, i.e. the same IST date, but ``today_ist()`` is correct at any hour).
* **Calendar run-out never crashes.** ``config.NSE_HOLIDAYS`` is authoritative only through
  ``NSE_HOLIDAYS_COVERED_THROUGH``. Past it the calendar degrades to *weekdays plus data-observed
  sessions* and emits ONE ``RuntimeWarning`` per process. (``config.assert_calendar_covers`` remains the
  deliberate HARD guard for writes to the hash-chained wall, which cannot be retracted.)

Pure stdlib + config: no pandas needed, so tests and cron steps stay cheap. Backtests do not use this
module; how historical sessions are treated in the engine is untouched.
"""
from __future__ import annotations

import warnings
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

import config as _cfg

IST = timezone(timedelta(hours=5, minutes=30))     # IST has no DST

# Sessions NSE held outside the weekday-minus-holiday rule. Sourced from NSE circulars; extend by adding a
# date here OR just let ``observed=`` catch it from the data. Muhurat 2025-10-21 is a Tuesday that NSE's own
# holiday master lists as a holiday (it trades 13:45-14:45), hence "special" even though it is a weekday.
SPECIAL_SESSIONS: frozenset[str] = frozenset({
    "2025-02-01",   # Saturday  - Union Budget
    "2025-10-21",   # Tuesday   - Diwali Muhurat (holiday-listed, trades briefly)
    "2026-02-01",   # Sunday    - Union Budget
    "2026-11-08",   # Sunday    - Diwali Muhurat
})

CLOSE_REGULAR = time(15, 30)      # IST
CLOSE_SPECIAL = time(20, 0)       # Muhurat runs in the evening on the old schedule; generous bound

_LOOKBACK_DAYS = 30               # last_session never needs more than a long holiday cluster
_warned: set[str] = set()


# ── coercion ─────────────────────────────────────────────────────────────────────────────────────
def _has_time(x) -> bool:
    return isinstance(x, datetime)            # pd.Timestamp subclasses datetime


def to_date(x) -> date:
    """date | datetime | pd.Timestamp | 'YYYY-MM-DD...' -> IST calendar date (see module docstring)."""
    if isinstance(x, str):
        return date.fromisoformat(x[:10])
    if isinstance(x, datetime):
        if x.tzinfo is not None:
            return x.astimezone(IST).date()
        return x.date()
    if isinstance(x, date):
        return x
    return to_date(str(x))     # numpy.datetime64 and friends


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> date:
    """Today on the exchange's clock. Use this, not ``date.today()`` (runner-local, UTC on Actions)."""
    return now_ist().date()


def _iso(d: date) -> str:
    return d.isoformat()


def _observed_set(observed: Iterable | None) -> frozenset[str]:
    if not observed:
        return frozenset()
    return frozenset(_iso(to_date(o)) for o in observed)


# ── coverage ─────────────────────────────────────────────────────────────────────────────────────
def covered_through() -> str:
    return _cfg.NSE_HOLIDAYS_COVERED_THROUGH


def is_covered(d) -> bool:
    """True when the holiday list is authoritative for ``d`` (upper bound only; see config)."""
    return _iso(to_date(d)) <= covered_through()


def _warn_if_uncovered(d: date) -> None:
    if _iso(d) > covered_through() and "uncovered" not in _warned:
        _warned.add("uncovered")
        warnings.warn(
            f"trading_calendar: NSE holiday list ends {covered_through()}; asked about {_iso(d)}. Falling "
            f"back to weekdays + data-observed sessions (an unlisted holiday reads as a session). Load the "
            f"next year: `python scripts/build_nse_holidays.py --emit`.", RuntimeWarning, stacklevel=3)


# ── classification ───────────────────────────────────────────────────────────────────────────────
def is_regular_session(d) -> bool:
    """Weekday and not a listed holiday. Past the calendar: any weekday (warns once)."""
    d = to_date(d)
    if d.weekday() >= 5:
        return False
    _warn_if_uncovered(d)
    return _iso(d) not in _cfg.NSE_HOLIDAYS


def is_special_session(d, observed: Iterable | None = None) -> bool:
    """A session outside the regular rule: known (``SPECIAL_SESSIONS``) or seen in the data (``observed``)."""
    d = to_date(d)
    if is_regular_session(d):
        return False
    return _iso(d) in SPECIAL_SESSIONS or _iso(d) in _observed_set(observed)


def is_session(d, observed: Iterable | None = None) -> bool:
    """Did (or will) the exchange trade on ``d``? Regular or special."""
    return is_regular_session(d) or is_special_session(d, observed)


# ── navigation ───────────────────────────────────────────────────────────────────────────────────
def _pred(regular: bool, obs: frozenset[str]):
    return is_regular_session if regular else (lambda d: is_session(d, obs))


def _close_time(d: date) -> time:
    return CLOSE_REGULAR if is_regular_session(d) else CLOSE_SPECIAL


def last_session(asof=None, *, regular: bool = False, observed: Iterable | None = None,
                 closed: bool = False) -> date:
    """The most recent session on or before ``asof`` (default: now, IST).

    ``regular=True`` ignores special sessions. ``closed=True`` skips a same-day session whose close has not
    happened yet, which only matters when ``asof`` carries a time of day (or is None = now).
    """
    obs = _observed_set(observed)
    pred = _pred(regular, obs)
    if asof is None:
        asof = now_ist()
    d = to_date(asof)
    skip_today = False
    if closed and _has_time(asof):
        t = asof.astimezone(IST).time() if asof.tzinfo is not None else asof.time()
        skip_today = pred(d) and t < _close_time(d)
    elif closed and not _has_time(asof):
        skip_today = False        # a bare date means "as of that day's end"
    cur = d - timedelta(days=1) if skip_today else d
    for _ in range(_LOOKBACK_DAYS):
        if pred(cur):
            return cur
        cur -= timedelta(days=1)
    while cur.weekday() >= 5:     # unreachable in practice: a 30-day run with no session
        cur -= timedelta(days=1)
    return cur


def next_session(d, *, regular: bool = False, observed: Iterable | None = None) -> date:
    """The first session strictly after ``d``."""
    pred = _pred(regular, _observed_set(observed))
    cur = to_date(d) + timedelta(days=1)
    for _ in range(_LOOKBACK_DAYS):
        if pred(cur):
            return cur
        cur += timedelta(days=1)
    while cur.weekday() >= 5:
        cur += timedelta(days=1)
    return cur


def sessions_between(start, end, *, regular: bool = False, observed: Iterable | None = None,
                     include_start: bool = False, include_end: bool = True) -> list[date]:
    """Sessions in (start, end] by default - 'how many sessions closed since the last row, up to today'."""
    pred = _pred(regular, _observed_set(observed))
    lo, hi = to_date(start), to_date(end)
    out: list[date] = []
    cur = lo if include_start else lo + timedelta(days=1)
    stop = hi if include_end else hi - timedelta(days=1)
    while cur <= stop:
        if pred(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out


def add_sessions(d, n: int, *, regular: bool = True, observed: Iterable | None = None) -> date:
    """``d`` plus ``n`` sessions (default: regular only, which is what buy-window arithmetic means)."""
    cur = to_date(d)
    for _ in range(max(0, int(n))):
        cur = next_session(cur, regular=regular, observed=observed)
    return cur


# ── ingest guard ─────────────────────────────────────────────────────────────────────────────────
def special_sessions() -> frozenset[str]:
    """The ONE declared special-session source (ISO dates). Other modules (scan watchdog, checks) must read
    this, not keep their own list."""
    return SPECIAL_SESSIONS


def is_ingestible_bar_date(d) -> bool:
    """May a vendor bar dated ``d`` enter the LIVE cache? False only when the calendar is authoritative for
    ``d`` (>= config.NSE_HOLIDAYS_COVERED_FROM) AND ``d`` is a weekend or listed holiday AND not a declared
    special session. Earlier dates are never judged (no holidays are carried before COVERED_FROM, and the
    historical research cache is deliberately left alone); past the run-out only weekends can be judged.
    """
    d = to_date(d)
    if _iso(d) < _cfg.NSE_HOLIDAYS_COVERED_FROM:
        return True
    if _iso(d) in SPECIAL_SESSIONS:
        return True
    if d.weekday() >= 5:
        return False
    return _iso(d) not in _cfg.NSE_HOLIDAYS


def drop_non_session_bars(df, ticker: str = "?"):
    """``(clean_df, dropped_iso_dates)``: remove bars dated on a closed-market day. Pure; df untouched if clean.

    Incident 2026-09-14 (Ganesh Chaturthi): Yahoo carried bars for the holiday, weekly rebuilds entered
    ANGELONE / CHOLAFIN / GESHIP on it, Yahoo later dropped the bar, the rebuild re-dated the entries to
    09-15 and history-drift went red. A closed-market bar never enters the live cache.
    """
    if df is None or len(df) == 0:
        return df, []
    keep = [is_ingestible_bar_date(ts) for ts in df.index]
    if all(keep):
        return df, []
    dropped = [_iso(to_date(ts)) for ts, k in zip(df.index, keep) if not k]
    return df[keep], dropped


def filter_ohlcv_non_session(ohlcv, *, label: str = "ohlcv", warn: bool = True):
    """Apply :func:`drop_non_session_bars` to ``{ticker: DataFrame}``. Returns ``(clean_dict, {date: n_tickers})``.
    LIVE/cron paths only; the research cache and backtests never call this."""
    out, hist = {}, {}
    for t, df in ohlcv.items():
        c, dropped = drop_non_session_bars(df, t)
        out[t] = c
        for d in dropped:
            hist[d] = hist.get(d, 0) + 1
    if hist and warn:
        summary = ", ".join(f"{d} x{n}" for d, n in sorted(hist.items())[:8])
        print(f"::warning::{label}: dropped {sum(hist.values())} vendor bar(s) dated on closed-market days "
              f"(holiday/weekend, not a declared special session): {summary}", flush=True)
    return out, hist


def week_key(d, observed: Iterable | None = None) -> tuple[int, int]:
    """``(iso_year, iso_week)`` of the trading week ``d`` belongs to. A weekend SESSION -> following week."""
    d = to_date(d)
    if d.weekday() >= 5 and is_session(d, observed):
        d = d + timedelta(days=7 - d.weekday())      # the Monday after
    y, w, _ = d.isocalendar()
    return int(y), int(w)


def same_week(a, b, observed: Iterable | None = None) -> bool:
    return week_key(a, observed) == week_key(b, observed)
