"""Attribution — what a closed trade's result was made of, measured against controls.

Layer 5 of the Brain. Pure functions over committed artifacts: no network, no clock, no model calls.
The scripts that need prices (`scripts/diag_trade_forensics.py`) feed Series in; nothing here fetches.

WHAT THIS ANSWERS, AND WHAT IT CANNOT

* **How much of a loss is the stop working as designed, and how much is the fill past it.** The live
  stop is close-only with gap-fill (`nq/paper/book.py`), so a position can trade well below its level
  before a close breaks it. Every trade's R splits exactly into the designed −1R plus the part beyond
  the stop: `R = −1 + (R + 1)`. That is an accounting identity, and it is only *meaningful* if the stop
  the engine measured R against is the stop that was actually recorded on the card. So the recorded
  stop is read from the archive and compared with the stop implied by R; :func:`stop_agreement` is the
  instrument check, and it is what turns the identity into evidence. On the 2026-09-04 snapshot all 9
  recorded stops agree with the implied ones within 0.5%.

* **Whether a name failed or the market did.** A loser-only list re-discovers extension every time
  (program-laws VIII). :func:`window_excess` measures a name against the median of a universe over the
  *same* window and reports its percentile, which is the matched control that makes the question
  answerable.

* **It cannot say why an entry failed before it failed.** Five instruments found entry quality
  invisible at the decision point on this funnel (program-laws I). These functions describe outcomes;
  they are not features for choosing trades, and nothing here should be read as one.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

OPEN_STATUSES = frozenset({"ACTIVE", "FRESH", ""})

# Touch-depth bands used across the 44-week funnel's research (ext census, 2026-07-31), in order.
TOUCH_BANDS: tuple[str, ...] = ("sub-line <0%", "core 0-5%", "weak 5-10%", "outside >10%")


@dataclass(frozen=True)
class ClosedTrade:
    """One closed trade as the engine recorded it, plus the stop from its last archived card."""

    ticker: str
    signal_date: str
    close_date: str
    entry: float
    close_price: float
    r_multiple: float
    exit_reason: str | None = None
    hold_days: int | None = None
    recorded_stop: float | None = None

    @property
    def implied_stop(self) -> float:
        """The stop that makes the engine's R consistent: R = (close − entry) / (entry − stop)."""
        if self.r_multiple == 0:
            raise ValueError(f"{self.ticker}: r_multiple is 0, so no stop can be implied")
        return self.entry - (self.close_price - self.entry) / self.r_multiple

    @property
    def stop(self) -> float:
        return self.recorded_stop if self.recorded_stop is not None else self.implied_stop

    @property
    def stop_source(self) -> str:
        return "recorded" if self.recorded_stop is not None else "implied"

    @property
    def beyond_stop_r(self) -> float:
        """The part of R past the designed −1R. Negative means the fill landed below the stop."""
        return self.r_multiple + 1.0


def closed_trades(history: Iterable[Mapping[str, Any]] | Mapping[str, Any]) -> list[ClosedTrade]:
    """Closed trades from a `signals_history_weekly.json` payload (list, or {"signals": [...]})."""
    rows = history.get("signals", []) if isinstance(history, Mapping) else history
    out: list[ClosedTrade] = []
    for r in rows:
        if str(r.get("status", "")).upper() in OPEN_STATUSES:
            continue
        out.append(ClosedTrade(
            ticker=str(r["ticker"]), signal_date=str(r.get("signal_date", "")),
            close_date=str(r.get("close_date", "")), entry=float(r["entry"]),
            close_price=float(r["close_price"]), r_multiple=float(r["r_multiple"]),
            exit_reason=r.get("exit_reason"),
            hold_days=int(r["hold_days"]) if r.get("hold_days") is not None else None))
    return sorted(out, key=lambda t: (t.close_date, t.ticker))


def recorded_stops(envelopes: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    """The last stop each ticker carried on a card, walking envelopes in the order given.

    Keyed by ticker, not (ticker, signal_date): a FRESH card is dated to its setup Friday and the same
    signal is re-dated to its entry day once ACTIVE (`run_bhanushali_cron.py:422` vs `:534`), so the
    two dates never match. Pass envelopes oldest-first so the latest card wins.
    """
    stops: dict[str, float] = {}
    for env in envelopes:
        for card in env.get("signals", []):
            if card.get("stop") is not None:
                stops[str(card["ticker"])] = float(card["stop"])
    return stops


def with_recorded_stops(trades: Iterable[ClosedTrade], stops: Mapping[str, float]) -> list[ClosedTrade]:
    return [replace(t, recorded_stop=stops.get(t.ticker)) for t in trades]


def stop_agreement(trades: Iterable[ClosedTrade]) -> dict[str, float]:
    """Relative gap between each recorded stop and the stop implied by the engine's R.

    The instrument check behind :func:`stop_decomposition`. Small gaps are expected — the card's entry
    is the planned fill and the history's entry the realised one — but a large gap means R was not
    measured against the stop on the card, and the decomposition then means nothing.
    """
    return {t.ticker: abs(t.recorded_stop - t.implied_stop) / t.implied_stop
            for t in trades if t.recorded_stop is not None}


def stop_decomposition(trades: Sequence[ClosedTrade]) -> dict[str, float | int]:
    """Split realised R into the stop working as designed and the fill beyond it."""
    realised = sum(t.r_multiple for t in trades)
    designed = -float(len(trades))
    return {
        "n": len(trades),
        "realised_r": realised,
        "designed_r": designed,
        "beyond_stop_r": realised - designed,
        "n_filled_beyond_stop": sum(1 for t in trades if t.beyond_stop_r < 0),
        "share_beyond_stop": (realised - designed) / realised if realised else 0.0,
    }


def touch_band(touch_depth_pct: float | None) -> str | None:
    """The ext band a signal's pullback touched, or None when the depth is unknown."""
    if touch_depth_pct is None or pd.isna(touch_depth_pct):
        return None
    x = float(touch_depth_pct)
    if x < 0:
        return TOUCH_BANDS[0]
    if x < 5:
        return TOUCH_BANDS[1]
    if x <= 10:
        return TOUCH_BANDS[2]
    return TOUCH_BANDS[3]


def window_return(series: pd.Series, start: str | pd.Timestamp, end: str | pd.Timestamp) -> float | None:
    """Close-to-close return over [start, end], or None with fewer than two bars inside it."""
    w = series[(series.index >= pd.Timestamp(start)) & (series.index <= pd.Timestamp(end))].dropna()
    if len(w) < 2:
        return None
    return float(w.iloc[-1]) / float(w.iloc[0]) - 1.0


def window_excess(name: pd.Series, universe: Mapping[str, pd.Series],
                  start: str | pd.Timestamp, end: str | pd.Timestamp) -> dict[str, float] | None:
    """A name's return over a window against the universe median over the SAME window.

    `percentile` is the share of universe names that did worse — 11 means the name sat in the bottom
    decile of the market over its own holding window.
    """
    own = window_return(name, start, end)
    if own is None:
        return None
    peers = [r for r in (window_return(s, start, end) for s in universe.values()) if r is not None]
    if not peers:
        return None
    peer = pd.Series(peers)
    median = float(peer.median())
    return {"name_return": own, "universe_median": median, "excess": own - median,
            "percentile": float((peer < own).mean() * 100.0), "n_universe": float(len(peers))}
