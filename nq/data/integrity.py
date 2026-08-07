"""Pre-run data-integrity assertions for research books — detect, report, refuse. Never repair.

Why this module exists
----------------------
``research/substrate/DATA_BUG_unadjusted_splits.md`` (2026-07-16) established that
``scripts/run_bhanushali_path1.corrected_universe()`` returns **raw** OHLCV: the CA cleaner
(:func:`nq.data.ohlcv.clean_ohlcv_for_features`) is wired only into the momentum/feature path, never
the swing path. 19 unadjusted splits therefore sit in the universe every swing study reads — a
−94% "crash" in RNAVAL, −75% in CGCL, and so on. The consequences are documented: a fake SELL card
on the live cron when a split hits a held name, suppressed signals for ~44 weeks afterwards, and
loser-forensics that rank artefacts first (the #1 "worst trade" handed to the owner for chart review
was a 1:4 split).

**This module does not fix that.** Applying the cleaner re-anchors the determinism guard
(1.1319 / 255) and every pinned assert across ``build_substrate.py``, ``build_trade_packets.py`` and
friends, which that document classifies as **quarterly-review / governance class, not a session
action**. So the contract here is: *find the events, refuse to let a study silently trade through
them, and quantify what was excluded* — leaving a measured residual bias rather than an unmeasured
one.

Discipline, inherited from :mod:`nq.data.adjustment_guard`
----------------------------------------------------------
**INDETERMINATE is not OK.** The prescriptive demerger reference covers **4 tickers**
(``data/corporate_actions_demergers.csv``); the 53-row ``corporate_actions_demerger_register.csv``
is explicitly *descriptive, not prescriptive* ("nothing reads this file to decide how to clean a
series") and is therefore NOT consulted here. A large drop in a name absent from the prescriptive
reference is reported as ``split_suspect`` — which may be a genuine demerger. That coverage limit is
returned in the report rather than hidden, because a checker that reports "nothing found" when it
could not look is worse than no checker.

This module complements :mod:`nq.data.adjustment_guard`, which is *size-free* (it checks that the
implied adjustment factor never decreases, catching any magnitude ≥ 0.5%) but needs a raw-price
reference. This one is size-based and needs only the cache, so the two fail differently and are
kept apart deliberately.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .ohlcv import load_demerger_reference

__all__ = ["PriceEvent", "scan_price_events", "split_suspects", "trades_spanning_events",
           "universe_counts", "assert_min_universe", "integrity_report",
           "DROP_THRESHOLD", "REVERT_FRAC", "MIN_UNIVERSE_FLOOR"]

# A single-session move at or below this is not a market move — it is a corporate action or a bad
# tick. Matches the <-45% scan in DATA_BUG_unadjusted_splits.md (24 events / 22 tickers).
DROP_THRESHOLD = -0.45
# A "drop" that recovers at least this fraction on the very next bar is a bad tick, not an event.
REVERT_FRAC = 0.50
# Eligible names below this in any period means the study is running on an unrepresentative slice.
# 2016 ran on ~21 names against ~490 in every other year and the numbers were reported before
# anyone noticed.
MIN_UNIVERSE_FLOOR = 100


@dataclass(frozen=True)
class PriceEvent:
    """A single-session discontinuity, classified."""
    ticker: str
    date: str
    move: float
    kind: str            # "demerger" | "bad_tick" | "split_suspect"
    implied_factor: float

    @property
    def factor_roundness(self) -> float:
        """Distance from the nearest integer split ratio — REPORTED, never used to classify.

        A 1:N split divides price by an exact integer, so its implied factor lands on ~2.00, ~4.00,
        ~5.00. A genuine catastrophic market drop lands anywhere. Compare YESBANK 2020-03-06
        (−56.1%, factor 2.28 — the real moratorium collapse) against CDSL 2017-07-03 (−49.9%,
        factor 2.00 — a bonus issue).

        This is deliberately *not* a classifier. The distinction needs the exchange record, and a
        heuristic that silently reclassified a real crash as a data bug (or vice versa) would be
        worse than reporting the number and letting a human adjudicate.
        """
        f = self.implied_factor
        return float("nan") if not np.isfinite(f) else abs(f - round(f))

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "factor_roundness": round(self.factor_roundness, 4)}


def scan_price_events(
    ohlcv: Mapping[str, pd.DataFrame], *,
    threshold: float = DROP_THRESHOLD,
    revert_frac: float = REVERT_FRAC,
    demergers: Mapping[str, set[str]] | None = None,
) -> list[PriceEvent]:
    """Find and classify every single-session drop at or below ``threshold``.

    Classification, in order:

    ``demerger``       the (ticker, date) is in the **prescriptive** reference — a value-leaving
                       event that is an honest discontinuity and must NOT be back-adjusted (the
                       VEDL bug).
    ``bad_tick``       the next bar recovers ``revert_frac`` or more of the drop — a print error.
    ``split_suspect``  everything else. Most are unadjusted splits; some may be demergers missing
                       from the 4-ticker reference. See the module docstring.

    ``implied_factor`` is ``prev_close / close`` — for a clean 1:N split this lands near N, which is
    what makes a suspect checkable by hand against the exchange record.
    """
    ref = load_demerger_reference() if demergers is None else demergers
    out: list[PriceEvent] = []
    for tkr in sorted(ohlcv):
        df = ohlcv[tkr]
        if df is None or len(df) < 3 or "Close" not in df.columns:
            continue
        c = df["Close"].to_numpy(dtype=float)
        idx = pd.DatetimeIndex(df.index)
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = c[1:] / c[:-1] - 1.0
        for k in np.flatnonzero(np.nan_to_num(ret, nan=0.0) <= threshold):
            i = k + 1                                   # position of the drop bar
            day = str(idx[i])[:10]
            prev, now = c[i - 1], c[i]
            if day in ref.get(tkr, set()):
                kind = "demerger"
            elif i + 1 < len(c) and np.isfinite(c[i + 1]) and (c[i + 1] / now - 1.0) >= revert_frac:
                kind = "bad_tick"
            else:
                kind = "split_suspect"
            out.append(PriceEvent(ticker=tkr, date=day, move=float(ret[k]), kind=kind,
                                  implied_factor=float(prev / now) if now > 0 else float("nan")))
    return out


def split_suspects(ohlcv: Mapping[str, pd.DataFrame], **kw) -> list[PriceEvent]:
    """Just the ``split_suspect`` events — the ones a study must not trade through."""
    return [e for e in scan_price_events(ohlcv, **kw) if e.kind == "split_suspect"]


def trades_spanning_events(
    trades: Iterable[Mapping[str, Any]], events: Iterable[PriceEvent],
) -> list[dict[str, Any]]:
    """Trades that were OPEN across one of ``events`` — i.e. corrupted by it.

    A trade spans an event when ``entry_date <= event_date <= exit_date`` for the same ticker. Those
    are the rows whose R is an artefact of the corporate action rather than a market outcome.
    """
    by_ticker: dict[str, list[PriceEvent]] = {}
    for e in events:
        by_ticker.setdefault(e.ticker, []).append(e)
    hits = []
    for t in trades:
        for e in by_ticker.get(str(t.get("ticker")), ()):
            if str(t.get("entry_date"))[:10] <= e.date <= str(t.get("exit_date"))[:10]:
                hits.append({**dict(t), "event_date": e.date, "event_move": e.move,
                             "implied_factor": e.implied_factor})
                break
    return hits


def universe_counts(panel: pd.DataFrame, *, date_col: str = "date", freq: str = "YE") -> pd.Series:
    """Mean eligible names per period — the shape that exposes a thin slice."""
    per = panel.groupby(pd.to_datetime(panel[date_col]))["ticker"].nunique()
    return per.resample(freq).mean()


def assert_min_universe(panel: pd.DataFrame, *, floor: int = MIN_UNIVERSE_FLOOR,
                        date_col: str = "date", freq: str = "YE", context: str = "") -> pd.Series:
    """Raise when any period's mean eligible-name count falls below ``floor``.

    The 2016 case: ~21.6 eligible names against ~490 in every other year, because the pinned OHLCV
    cache starts 2017-01-02 and the only earlier bars come from the delisted-name backfill. Every
    2016 figure was computed on a ~21-name, mostly-delisted universe — and reported before anyone
    checked. This turns that into a loud failure.
    """
    counts = universe_counts(panel, date_col=date_col, freq=freq)
    thin = counts[counts < floor]
    if len(thin):
        detail = ", ".join(f"{str(k)[:10]}={v:.1f}" for k, v in thin.items())
        raise ValueError(
            f"universe too thin{' in ' + context if context else ''}: {detail} "
            f"(floor {floor}). A study on this slice is not representative — restrict the window "
            f"or lower the floor deliberately.")
    return counts


def integrity_report(
    ohlcv: Mapping[str, pd.DataFrame], *,
    trades: Iterable[Mapping[str, Any]] | None = None,
    panel: pd.DataFrame | None = None,
    floor: int = MIN_UNIVERSE_FLOOR,
) -> dict[str, Any]:
    """Structured verdict. ``overall`` is ``"OK"`` / ``"WARN"`` / ``"RED"``.

    ``RED`` means a trade in ``trades`` spans an unadjusted-split suspect — its R is an artefact.
    ``WARN`` means suspects exist in the universe but no supplied trade touches one.
    """
    events = scan_price_events(ohlcv)
    suspects = [e for e in events if e.kind == "split_suspect"]
    spanning = trades_spanning_events(trades or (), suspects)
    counts = universe_counts(panel) if panel is not None else pd.Series(dtype=float)
    thin = {str(k)[:10]: round(float(v), 1) for k, v in counts.items() if v < floor}

    overall = "RED" if spanning else ("WARN" if suspects else "OK")
    return {
        "overall": overall,
        "n_events": len(events),
        "by_kind": {k: sum(1 for e in events if e.kind == k)
                    for k in ("demerger", "bad_tick", "split_suspect")},
        "suspects": [e.as_dict() for e in suspects],
        "trades_spanning_suspects": len(spanning),
        "pnl_in_spanning_trades": round(sum(float(t.get("pnl", 0.0)) for t in spanning), 2),
        "r_in_spanning_trades": round(sum(float(t.get("r", 0.0) or 0.0) for t in spanning), 3),
        "thin_periods": thin,
        "coverage_caveat": (
            "The prescriptive demerger reference covers 4 tickers; a genuine demerger absent from "
            "it is reported as split_suspect. Classification is INDETERMINATE for such names, not "
            "clean — verify against the exchange record before treating a suspect as a data bug."),
    }
