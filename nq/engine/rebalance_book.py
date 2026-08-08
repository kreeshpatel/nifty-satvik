"""Periodic-rebalance cross-sectional book — the third engine shape.

Why a third engine
------------------
The two existing simulators both exit on a **price level**:

| engine | selection | exit |
|---|---|---|
| :func:`nq.engine.portfolio.simulate` | rank-gate top-N | ATR stop + fixed target + trail |
| :func:`nq.engine.signal_book.simulate_signal_book` | discrete entry events | per-signal stop + R-multiple target |

The classical cross-sectional momentum book exits on a **ranking**: hold the top N, rebalance on a
cadence, and a name leaves because it fell out of the ranking — not because it hit a price. The
literature is explicit that this is deliberate rather than an omission:

    "in pure systematic momentum, discretionary stops often hurt because the rebalance already
     exits losers; stops add value chiefly for crash control and for circuit-risk names."

So this engine has **no stop and no target**, and that absence is the design, not a gap.

The buffer
----------
Exiting the moment a name drops to rank N+1 and re-buying when it returns to N churns the book for
nothing. ``buffer_mult`` adds hysteresis: enter on rank ≤ N, but keep holding until rank falls past
``N × buffer_mult``. At the default 2.0 a top-30 book tolerates a holding down to rank 60. This
roughly halves turnover for a small tracking difference, and it is the standard construction.

Weights
-------
Targets are equal-weight, capped at ``max_position_pct``. At each rebalance the book trades **to**
those targets, so an oversized winner is trimmed and an undersized laggard is topped up. That
rebalancing turnover is real and is charged in full — it is the price of the equal-weight
construction and should not be hidden.

Contract
--------
Returns ``{equity_curve, trades, metrics}`` — byte-compatible with ``simulate`` — so
:func:`nq.runner.research.adjudicate` holds it to the same bar with no adapter.

Execution
---------
Ranks are read at the rebalance date's **close**; every resulting trade fills at the **next
session's open**. Entry pricing is two-pass — size at the liquidity-tier slippage rate, then
re-price with the 0.5%-of-ADV market-impact term once notional is known — matching ``simulate``.
Costs (``LEG_COST`` = brokerage + STT) are charged on **both** legs.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .portfolio import (LEG_COST, MAX_ADV_PARTICIPATION, STALE_ABSENT_DAYS, _slip,
                        compute_metrics)

__all__ = ["RebalanceConfig", "simulate_rebalance_book", "rebalance_dates", "InvariantError"]

CADENCES = ("W", "2W", "M", "Q")
_EQUITY_TOL = 0.01          # rupees — the equity identity must hold to the paisa
_RECON_TOL = 1.0            # rupees — end-of-run PnL reconciliation


class InvariantError(RuntimeError):
    """An accounting identity broke. The engine refuses to return a result.

    This is deliberately fatal rather than a warning. The accumulation leak fixed on 2026-08-07
    survived three full runs and was eventually caught by a drawdown that contradicted the
    literature — not by a test. Had the position-cap identity been asserted per bar, it would have
    died on the first run, in the first month. An engine that can emit a number while one of its
    own identities is false is an engine whose numbers mean nothing.
    """


@dataclass(frozen=True)
class RebalanceConfig:
    """Book shape. Defaults follow the midcap-momentum compendium's Stage-2 baseline."""
    top_n: int = 30
    buffer_mult: float = 2.0          # hold until rank falls past top_n * buffer_mult
    max_position_pct: float = 5.0     # NSE momentum-index single-name cap
    cadence: str = "M"                # W | 2W | M | Q
    max_adv_participation: float = MAX_ADV_PARTICIPATION
    min_trade_pct: float = 0.25       # skip rebalancing trades smaller than this % of equity
    rebalance_band: float = 0.0       # no-trade band as a FRACTION OF TARGET (0 = off; see ENG-01)
    exposure: float = 1.0             # gross exposure multiplier (the vol-target / regime hook)


@dataclass
class _Pos:
    ticker: str
    qty: int
    cost: float                       # total rupees paid, including entry costs
    entry_date: Any
    mark: float
    bars: int = 0
    absent: int = 0                   # consecutive sessions with no quote
    fills: list = field(default_factory=list)

    @property
    def avg_entry(self) -> float:
        return self.cost / self.qty if self.qty else float("nan")


def rebalance_dates(dates: Sequence[Any], cadence: str = "M") -> list[Any]:
    """The last available session of each period — the dates ranks are read on.

    Derived from the sessions actually present, so holidays and half-days are handled by
    construction rather than by a calendar assumption.
    """
    if cadence not in CADENCES:
        raise ValueError(f"cadence must be one of {CADENCES}, got {cadence!r}")
    idx = pd.DatetimeIndex(sorted(pd.to_datetime(list(dates))))
    if cadence == "W":
        key = idx.to_period("W")
    elif cadence == "2W":
        wk = idx.to_period("W")
        key = pd.Index([f"{p.year}-{p.week // 2}" for p in wk])
    elif cadence == "M":
        key = idx.to_period("M")
    else:
        key = idx.to_period("Q")
    return list(pd.Series(idx).groupby(key, sort=True).last())


def simulate_rebalance_book(
    panel: pd.DataFrame, *,
    cfg: RebalanceConfig | None = None,
    rank_col: str = "rank",
    date_col: str = "date",
    initial_capital: float = 1_000_000.0,
    start: str | None = None,
    end: str | None = None,
    exposure_by_date: Mapping[Any, float] | None = None,
    check_invariants: bool = True,
) -> dict[str, Any]:
    """Run the book. ``panel`` needs ``date, ticker, open, high, low, close`` and ``rank_col``
    (higher = better, NaN = not selectable), optionally ``adv_rupees_20d``.

    ``exposure_by_date`` is the overlay hook: a per-date multiplier in [0, 1] applied to target
    weights, which is how a regime filter or a volatility target attaches without the engine
    knowing anything about either.
    """
    cfg = cfg or RebalanceConfig()
    need = {date_col, "ticker", "open", "high", "low", "close", rank_col}
    missing = need - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")

    p = panel.copy()
    p[date_col] = pd.to_datetime(p[date_col])
    if start:
        p = p[p[date_col] >= pd.Timestamp(start)]
    if end:
        p = p[p[date_col] <= pd.Timestamp(end)]
    if p.empty:
        return {"equity_curve": [], "trades": [], "metrics": {}}
    if "adv_rupees_20d" not in p.columns:
        p["adv_rupees_20d"] = 0.0

    dates = sorted(p[date_col].unique())
    dpos = {d: i for i, d in enumerate(dates)}
    by_date = {d: g.set_index("ticker") for d, g in p.groupby(date_col, sort=True)}
    rebals = set(rebalance_dates(dates, cfg.cadence))
    cap_positions = int(cfg.top_n * cfg.buffer_mult)

    cash = equity = float(initial_capital)
    book: dict[str, _Pos] = {}
    equity_curve: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    # PERSISTENT target weights, not a one-shot queue.
    #
    # An earlier version queued targets into a `pending` dict consumed on the next session and
    # discarded. Any name without a quote that morning hit `continue` and was never revisited, so
    # positions ACCUMULATED without bound: a top-30 book with a 45-name buffer drifted to an average
    # of 67 holdings, which flattered the drawdown to -19.6% against a literature benchmark of
    # -50/-70% and produced 166-day average holds on a monthly book. Keeping targets live until the
    # next rebalance also matches how a book actually works — an order is not abandoned because the
    # stock did not trade that morning.
    targets: dict[str, float] = {}
    armed = False                                 # True between a rebalance and the next

    for t in dates:
        day = by_date[t]

        # ── 1. move toward the live targets at THIS session's open ───────────────────
        #
        # THREE ordered passes: absent, then every sell, then every buy.
        #
        # The first version did all of this in ONE loop over `sorted(set(book) | set(targets))`,
        # under a comment claiming "sells first, so their proceeds fund the buys". It did not: the
        # single pass interleaves sells and buys in ALPHABETICAL order, so on a rotation into
        # alphabetically-earlier names every buy was attempted while its funding sells were still
        # pending. Measured on a synthetic full rotation, the book ended the fill session holding
        # **1 position out of 3** and the rest in cash. Two consequences, both bad: the book
        # under-deploys for a session on every turnover event, and *which* names get filled when
        # cash is short depends on the ticker STRING — a bias with no economic content that would
        # also make the result sensitive to renaming a symbol.
        if armed:
            plans: list[tuple[str, float, float, int, bool]] = []   # tkr, px, adv, delta, exiting
            for tkr in sorted(set(book) | set(targets)):
                pos = book.get(tkr)
                tgt_w = targets.get(tkr, 0.0)
                if tkr not in day.index:
                    if pos is not None:
                        pos.absent += 1
                        if pos.absent >= STALE_ABSENT_DAYS:
                            # delisted or suspended: realise at the last observed mark rather than
                            # holding a dead name forever. Without this, persistent targets alone
                            # would still let a permanently-absent name occupy a slot for ever.
                            proceeds_net = pos.qty * pos.mark * (1 - LEG_COST)
                            basis_ps = pos.cost / pos.qty
                            exit_net_ps = proceeds_net / pos.qty
                            cash += proceeds_net
                            trades.append({
                                "ticker": tkr, "entry_date": str(pos.entry_date)[:10],
                                "exit_date": str(t)[:10], "entry": round(basis_ps, 4),
                                "exit": round(exit_net_ps, 4), "qty": int(pos.qty),
                                "days_held": pos.bars, "reason": "stale",
                                "return_pct": round((exit_net_ps - basis_ps) / basis_ps * 100.0, 4)
                                if basis_ps > 0 else 0.0,
                                "pnl": round(proceeds_net - pos.cost, 4)})
                            del book[tkr]
                    continue                     # no quote today: keep the target, retry tomorrow
                if pos is not None:
                    pos.absent = 0
                bar = day.loc[tkr]
                px, adv = float(bar["open"]), float(bar.get("adv_rupees_20d", 0.0) or 0.0)
                if not np.isfinite(px) or px <= 0:
                    continue
                held_qty = pos.qty if pos else 0
                tgt_val = equity * tgt_w
                tgt_qty = int(tgt_val / px)
                if adv > 0:
                    tgt_qty = min(tgt_qty, int(cfg.max_adv_participation * adv / px))
                delta = tgt_qty - held_qty
                # `min_trade_pct` exists to suppress dust REBALANCING, and it must never suppress a
                # full EXIT. Applied to a zero target it becomes a slot leak: a position that has
                # decayed below the threshold is skipped every session for ever, because the test
                # looks at the size of the trade and a small position implies a small trade. At
                # top_n=30 a name would have to lose ~92% to reach it, but the same book at top_n=60
                # needs only 85%, and the position then occupies a slot it can never leave. Exits are
                # therefore exempt: if the target is zero, sell it, however small.
                exiting = tgt_w <= 0.0 and held_qty > 0
                if delta == 0 or (not exiting
                                  and abs(delta * px) < equity * cfg.min_trade_pct / 100.0):
                    continue

                # NO-TRADE BAND (ENG-01). A drift correction is worth ~4.4% of the notional moved
                # once STCG is counted — 0.70% round-trip friction plus 20% tax on a realised gain
                # averaging 18.6%. Tax dominates friction by more than 5x. The benefit of the
                # correction is the rebalancing premium, which is QUADRATIC in the drift, so below
                # some deviation trimming is strictly value-destroying. The band is that floor.
                #
                # Entries and exits are exempt: those are selection decisions, and suppressing them
                # would change the strategy rather than its execution. `held_qty > 0 and tgt_w > 0`
                # is exactly "an adjustment to a position we are keeping".
                if (cfg.rebalance_band > 0.0 and held_qty > 0 and tgt_w > 0.0
                        and abs(delta) < cfg.rebalance_band * tgt_qty):
                    continue
                plans.append((tkr, px, adv, delta, exiting))

            # ── SELL pass — every reduction, so all proceeds are in cash before any buy ──
            for tkr, px, adv, delta, _ in plans:
                if delta >= 0:
                    continue
                pos = book[tkr]
                # Exact proportional cost-basis accounting.
                #
                # `pos.cost` already carries the ENTRY costs (outlay = qty x fill x (1+LEG_COST)),
                # so `cost/qty` is the true all-in basis per share. An earlier version recorded
                # pnl as `q*(fill-basis) - (q*fill + q*basis)*LEG_COST`, which subtracts the entry
                # leg a SECOND time — the end-of-run reconciliation caught it on the first run
                # after the identity was added. Netting the exit leg off the proceeds and removing
                # the proportional basis reconciles by construction.
                q = min(-delta, pos.qty)
                held_qty = pos.qty
                fill = px * (1 - _slip(adv, q * px))
                proceeds_net = q * fill * (1 - LEG_COST)
                basis_ps = pos.cost / pos.qty
                basis_out = basis_ps * q
                cash += proceeds_net
                exit_net_ps = proceeds_net / q
                trades.append({
                    "ticker": tkr, "entry_date": str(pos.entry_date)[:10],
                    "exit_date": str(t)[:10], "entry": round(basis_ps, 4),
                    "exit": round(exit_net_ps, 4), "qty": int(q), "days_held": pos.bars,
                    "reason": "rebalance_exit" if q == held_qty else "rebalance_trim",
                    "return_pct": round((exit_net_ps - basis_ps) / basis_ps * 100.0, 4)
                    if basis_ps > 0 else 0.0,
                    "pnl": round(proceeds_net - basis_out, 4)})
                pos.cost -= basis_out
                pos.qty -= q
                if pos.qty <= 0:
                    del book[tkr]

            # ── BUY pass — two-pass pricing, funded by the cash the sells just raised ──
            #
            # Cash is rationed PRO RATA, not first-come. Filling buys sequentially out of a shared
            # cash balance hands a full fill to whoever sorts first and the remainder to whoever
            # sorts last, so the result depends on the ticker STRING: relabelling the names moved
            # the curve by 0.02%. Scaling every buy by one common factor removes that — each name's
            # quantity is then a function of its own price, ADV and target alone.
            #
            # The budget is priced with the impact term at the FULL intended size, which
            # over-estimates the cost of the (smaller) scaled order. The over-estimate is
            # deliberate: it guarantees the outlays fit in cash without a sequential clamp, which
            # would smuggle the ordering back in.
            priced = []
            want = 0.0
            for tkr, px, adv, delta, _ in plans:
                if delta <= 0:
                    continue
                fill1 = px * (1 + _slip(adv, 0.0))
                budget_ps = px * (1 + _slip(adv, delta * fill1)) * (1 + LEG_COST)
                priced.append((tkr, px, adv, delta, fill1))
                want += delta * budget_ps
            scale = min(1.0, cash / want) if want > 0 else 0.0
            for tkr, px, adv, delta, fill1 in priced:
                q = int(delta * scale)
                if q <= 0:
                    continue
                fill = px * (1 + _slip(adv, q * fill1))
                outlay = q * fill * (1 + LEG_COST)
                if outlay > cash:                # unreachable by construction; a belt-and-braces
                    continue                     # guard so a pricing change cannot silently borrow
                cash -= outlay
                pos = book.get(tkr)
                if pos is None:
                    book[tkr] = _Pos(tkr, q, outlay, t, fill)
                else:
                    pos.qty += q
                    pos.cost += outlay
            # drop satisfied zero-targets so the dict does not grow without bound
            targets = {k: w for k, w in targets.items() if w > 0.0}

        # ── 2. age + mark ────────────────────────────────────────────────────────────
        mtm = 0.0
        for tkr, pos in book.items():
            pos.bars += 1
            if tkr in day.index:
                c = float(day.loc[tkr, "close"])
                if np.isfinite(c):
                    pos.mark = c
            mtm += pos.qty * pos.mark
        equity = cash + mtm

        # ── INVARIANTS, checked every bar ────────────────────────────────────────────
        if check_invariants:
            # The cap binds on positions the engine COULD have transacted this session.
            #
            # A name that did not quote today cannot be sold at any price. Counting it against the
            # cap asserts something the engine has no power to satisfy, and the first version did
            # exactly that: the pre-reg 0001 PBO sweep died at top_n=30 / buffer=1.0 on 2024-09-03
            # holding 31 — all 454 over-cap sessions traced to ONE name, TATAMTRDVR, which simply
            # stopped quoting (`pipelines/diagnostics/diag_slot_overflow.py`). Interior missing bars
            # run 0.162% of listed name-days, so this is a permanent feature of the data, not an
            # anomaly to assert away.
            #
            # The transient is bounded rather than tolerated: an absent name is force-closed after
            # STALE_ABSENT_DAYS, so every untradeable position must be inside that window. The pair
            # of checks is STRICTER than the original count — it pins both the cap and the escape
            # hatch, instead of leaving "some names are absent sometimes" as an unexamined excuse.
            untradeable = [k for k in book if k not in day.index]
            if len(book) - len(untradeable) > cap_positions:
                raise InvariantError(
                    f"{t}: holding {len(book) - len(untradeable)} tradeable positions against a cap "
                    f"of {cap_positions} (top_n={cfg.top_n} x buffer={cfg.buffer_mult}). "
                    f"Positions are accumulating.")
            for k in untradeable:
                if not 0 < book[k].absent < STALE_ABSENT_DAYS:
                    raise InvariantError(
                        f"{t}: {k} has no quote but its absent run is {book[k].absent}, outside the "
                        f"(0, {STALE_ABSENT_DAYS}) force-close window — it is stuck in a slot.")
            recomputed = cash + sum(p.qty * p.mark for p in book.values())
            if abs(recomputed - equity) > _EQUITY_TOL:
                raise InvariantError(
                    f"{t}: equity identity broken — cash + mark-to-market = {recomputed:.2f} "
                    f"but equity = {equity:.2f}")
            if cash < -_EQUITY_TOL:
                raise InvariantError(f"{t}: cash is negative ({cash:.2f}) — the book borrowed")
            if any(p.qty <= 0 for p in book.values()):
                raise InvariantError(f"{t}: a position with non-positive quantity is still held")

        equity_curve.append({"date": str(t)[:10], "equity": round(equity, 2),
                             "cash": round(cash, 2), "n_positions": len(book)})

        # ── 3. rank at the close, queue targets for the next open ────────────────────
        if t in rebals and dpos[t] + 1 < len(dates):
            ranked = day[rank_col].dropna().sort_values(ascending=False)
            if ranked.empty:
                continue
            entrants = list(ranked.index[:cfg.top_n])
            keep_to = int(cfg.top_n * cfg.buffer_mult)
            tolerated = set(ranked.index[:keep_to])
            target = list(dict.fromkeys(entrants + [k for k in book if k in tolerated]))
            target = target[:keep_to]
            if not target:
                continue
            expo = cfg.exposure
            if exposure_by_date is not None:
                expo = float(exposure_by_date.get(t, exposure_by_date.get(str(t)[:10], expo)))
            expo = max(0.0, min(1.0, expo))
            w = min(1.0 / len(target), cfg.max_position_pct / 100.0) * expo
            # every held name NOT in the target gets an explicit zero, so it is actively sold
            # rather than silently retained
            targets = {tkr: 0.0 for tkr in book}
            targets.update({tkr: w for tkr in target})
            armed = True

    # ── END-OF-RUN PnL RECONCILIATION ────────────────────────────────────────────────
    # Every rupee of return must be attributable to a realised trade or an open position. If
    # realised PnL + unrealised PnL does not close the gap between final equity and starting
    # capital, the engine has created or destroyed money somewhere and no metric derived from it
    # can be trusted.
    if check_invariants and equity_curve:
        realised = sum(float(t["pnl"]) for t in trades)
        unrealised = sum(p.qty * p.mark - p.cost for p in book.values())
        final = float(equity_curve[-1]["equity"])
        drift = final - (initial_capital + realised + unrealised)
        if abs(drift) > max(_RECON_TOL, abs(final) * 1e-6):
            raise InvariantError(
                f"PnL reconciliation failed by {drift:.2f}: final equity {final:.2f} vs "
                f"initial {initial_capital:.2f} + realised {realised:.2f} + unrealised "
                f"{unrealised:.2f}. Return is not fully attributable to trades.")

    return {"equity_curve": equity_curve, "trades": trades,
            "metrics": compute_metrics(equity_curve, trades, initial_capital)}
