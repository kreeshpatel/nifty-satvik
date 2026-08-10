"""Make the weekly-swing book adjudicable — the `{equity_curve, trades, metrics}` contract.

`nq.runner.research.adjudicate` is engine-agnostic by design: *"any simulator returning the
``{equity_curve, trades, metrics}`` contract can be held to the same bar"*. Two engines already
satisfy it — `nq.engine.portfolio.simulate` and `nq.engine.signal_book.simulate_signal_book`.

The book that actually trades does not. `run_bhanushali_weekly_rank.backtest` returns
``dict(curve, ret, trades:int, tpy, cagr, sharpe, dd, ...)``, where `curve` is a Series and `trades`
is a COUNT rather than a list. So every swing diagnostic has hand-rolled its own `stats()` —
`diag_grade_b.py`, `diag_pool_filter.py`, `diag_random_selection.py` and three more, each with its
own arithmetic and its own opportunity to be subtly wrong.

This is the single translation layer. `nq/engine/signal_book.py` documents the same motivation for
its own existence: *"a dozen scripts/diag_*.py explorers each grew their own portfolio loop — and
their own bugs."*

Nothing here runs a backtest, reads a cfg, or decides anything. It reshapes a result.

## The unit that is NOT what its name suggests

`adjudicate`'s turnover gate is `turnover_le_30pct`. On the momentum engine `turnover_per_year` is
**notional** turnover. This book does not compute that, and it cannot be inverted reliably from the
ledger: share count would have to come from `stt_paid`, and for the 34% of trades that booked the
+2R half the position was sold in two legs at different prices, so the inversion is wrong without
`half_px` (see `scripts/diag_unit_resolution.py`).

So this adapter reports **trades per year** and says so, in the payload as well as here. For a
SELECTIVITY study that is arguably the more meaningful constraint anyway — the failure mode of every
killed filter in this family was the freed cash buying *more, weaker* trades (0104: 130 → 161) — but
it is a different quantity from the momentum book's, and a reader comparing the two numbers across
engines would be comparing nothing. `metrics["turnover_units"]` carries the disambiguation.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

__all__ = ["to_adjudicable", "TURNOVER_UNITS"]

TURNOVER_UNITS = "trades_per_year"


def _equity_curve(curve) -> list[dict[str, Any]]:
    """`backtest`'s `curve` Series -> the `[{date, equity}]` rows `adjudicate` reads."""
    if curve is None or not len(curve):
        return []
    s = pd.Series(curve).dropna()
    return [{"date": str(pd.Timestamp(d).date()), "equity": float(v)} for d, v in s.items()]


def _trades(ledger: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Ledger rows -> the `[{exit_date, pnl}]` rows the after-tax leg reads.

    `net_pnl` is the ledger's own realised rupee P&L, already net of costs. A row without one is
    DROPPED rather than defaulted to zero: `adjudicate` charges STCG on positive `pnl`, so inventing
    a zero would silently understate the tax on a book whose after-tax CAGR is a promotion gate.
    """
    out: list[dict[str, Any]] = []
    for r in ledger or []:
        pnl = r.get("net_pnl")
        if pnl is None or (isinstance(pnl, float) and np.isnan(pnl)):
            continue
        out.append({"exit_date": str(pd.Timestamp(r["exit_date"]).date()), "pnl": float(pnl),
                    "ticker": r.get("tkr"), "R": r.get("R"), "reason": r.get("reason")})
    return out


def to_adjudicable(bt: Mapping[str, Any], ledger: Sequence[Mapping[str, Any]] | None = None,
                   *, initial_capital: float = 1_000_000.0) -> dict[str, Any]:
    """Reshape `run_bhanushali_weekly_rank.backtest(...)` into the adjudicable contract.

    ``bt`` is the dict `backtest` returned; ``ledger`` is the list it appended to (pass the same one
    given as ``ledger=``). Returns ``{equity_curve, trades, metrics}`` plus the untouched original
    under ``native`` so nothing is lost in translation.

    Metrics are RE-DERIVED from the curve, not copied, with one exception: `n_trades` comes from the
    ledger when supplied. Re-deriving is deliberate — if the adapter simply forwarded `bt["sharpe"]`
    it would agree with the engine by construction and the parity test below would prove nothing.
    """
    eq = _equity_curve(bt.get("curve"))
    trades = _trades(ledger)

    cagr = float(bt.get("cagr") or 0.0)
    dd = float(bt.get("dd") or 0.0)
    if eq:
        vals = np.array([r["equity"] for r in eq], dtype=float)
        dates = pd.to_datetime([r["date"] for r in eq])
        yrs = max((dates[-1] - dates[0]).days / 365.25, 1e-9)
        cagr = float((vals[-1] / vals[0]) ** (1.0 / yrs) - 1.0) if vals[0] > 0 else 0.0
        dd = float((vals / np.maximum.accumulate(vals) - 1.0).min())
        rets = pd.Series(vals).pct_change().dropna()
        sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() else float("nan")
        tpy = (len(trades) or int(bt.get("trades") or 0)) / yrs
    else:
        sharpe, tpy = float("nan"), 0.0

    metrics = {
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": dd,
        # Calmar is CAGR over the ABSOLUTE drawdown. A zero-drawdown curve has no Calmar rather than
        # an infinite one — `adjudicate` compares Calmars, and an inf would win every gate.
        "calmar": (float(cagr / abs(dd)) if dd else float("nan")),
        "n_trades": len(trades) or int(bt.get("trades") or 0),
        # See the module docstring: this is TRADES per year, not notional turnover.
        "turnover_per_year": float(tpy),
        "turnover_units": TURNOVER_UNITS,
        "initial_capital": float(initial_capital),
        "skipped_cash": int(bt.get("skipped_cash") or 0),
    }
    return {"equity_curve": eq, "trades": trades, "metrics": metrics, "native": dict(bt)}
