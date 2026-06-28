"""The shared long-horizon exit decision — live ≡ backtest, by construction.

``decide_exit`` is the SINGLE source of truth for when a held position closes. Both the backtest
(:func:`nq.engine.portfolio.simulate`) and the live signal tracker call it with the same frozen
cfg, so the two paths cannot drift. The decision is made on the **close** of each session.

Priority (first match wins), all read off the frozen cfg:

  1. **Hard stop** — ``close <= stop`` (the ATR stop ``entry × (1 − stop_atr_mult × atr_pct)`` is
     baked into ``position['stop']`` at entry). Gap-aware fill: if the session OPENED below the
     stop, fill at the open (we could not have cleared at the unreachable stop); never better than
     the stop. The stop is NEVER suppressed by the min-hold floor — risk control comes first.
  2. **Min-hold floor** — below ``min_hold_days`` no profit-taking / time exit fires (only the
     hard stop above). The position gets its minimum window to work.
  3. **Target** — intraday high trades through ``entry × (1 + target_pct/100)``; filled AT the
     target (a resting limit), never higher.
  4. **Hard time cap** — ``days_held >= max_hold_days`` (trading-day aging).
  5. **Trailing stop** — once the close-peak has risen past ``+trailing_activate_pct``, exit when
     the close falls ``trailing_pct`` below the running close-peak.

Pure function — does not mutate ``position``; the caller applies the decision (close, or update
the peak). This is the long-horizon-clean equivalent of the source's shared ``exit_logic`` with
the long-horizon cfg, for which the v1 partial / regime-override / hybrid-re-eval / benchmark
branches are all inert (and so are absent here).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExitDecision:
    """Outcome of evaluating one session against an open position.

    ``close_reason`` is the headline: if non-None, the caller closes the position at
    ``exit_price`` for this reason. ``new_peak`` reports an updated close-peak (None = unchanged)
    so the caller can advance its trailing reference without this function mutating state.
    """

    close_reason: str | None = None        # "stop" | "target" | "time" | "trailing" | None
    exit_price: float = 0.0
    new_peak: float | None = None


def decide_exit(
    position: dict[str, Any], today_ohlc: dict[str, float],
    cfg: dict[str, Any], days_held: int,
) -> ExitDecision:
    """Evaluate one session's OHLC against an open position. See the module docstring for the
    priority order. ``position`` needs ``entry, stop, peak, target``; ``today_ohlc`` needs
    ``close`` (``high``/``open`` optional — ``open`` enables the gap-through stop fill); ``cfg``
    supplies ``min_hold_days, max_hold_days, trailing_activate_pct, trailing_pct``.
    """
    entry = float(position["entry"])
    stop = float(position["stop"])
    peak = float(position["peak"])
    target = float(position.get("target", 0) or 0)
    close = float(today_ohlc["close"])
    high = float(today_ohlc.get("high", close))
    open_raw = today_ohlc.get("open")
    open_ = float(open_raw) if open_raw is not None else None

    d = ExitDecision(exit_price=close)
    if close > peak:
        d.new_peak = close

    past_min_hold = days_held >= int(cfg["min_hold_days"])

    # 1. Hard stop — gap-aware fill, never better than the stop. Not min-hold gated.
    if close <= stop:
        d.close_reason = "stop"
        d.exit_price = min(open_, close) if (open_ is not None and open_ < stop) else close
        return d

    # Min-hold floor: hold below min_hold_days (the hard stop above always fires).
    if not past_min_hold:
        return d

    # 2. Target — intraday touch, conservative fill AT the target.
    if target > 0 and high >= target:
        d.close_reason = "target"
        d.exit_price = target
        return d

    # 3. Hard time cap (trading-day aging).
    if days_held >= int(cfg["max_hold_days"]):
        d.close_reason = "time"
        return d

    # 4. Trailing stop on the running close-peak, once activated.
    effective_peak = d.new_peak if d.new_peak is not None else peak
    if entry > 0 and effective_peak > entry * (1 + float(cfg["trailing_activate_pct"]) / 100.0):
        trail_stop = effective_peak * (1 - float(cfg["trailing_pct"]) / 100.0)
        if close <= trail_stop:
            d.close_reason = "trailing"
            return d

    return d
