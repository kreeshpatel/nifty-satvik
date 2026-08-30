"""Forward-wall daily writer — the operational glue between the paper cron and the hash-chained log.

`update_wall(base_book, panel, cfg)` writes one atomic 3-book row per new session (forward/prereg.md §1):
- **base** metrics come straight from the operational `base_book.equity_curve` — so the wall's base NAV
  reconciles to the paper NAV *by construction* (one source, not a recomputation).
- **veto-0.1** is a second `PaperBook` stepped on the same panel with the bottom-decile residual names
  vetoed (its own `results/wall_veto/` state, resumable).
- **drift** is derived inside `record_trading_day` from the logged base trailing-63d return.

Isolated on purpose: the daily cron calls this in a try/except so a wall failure never breaks the paper
job. Idempotent + resumable: it appends only sessions after the wall's last logged date; a same-date
re-run is refused by the chain; missed trading days become `gap` markers.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import DATA_DIR, RESULTS_DIR
from nq.paper.book import PaperBook
from nq.paper.forward_wall import _load
from nq.paper.forward_wall_job import record_trading_day
from nq.research.residual import residual_ranks

VETO_Q = 0.10   # veto-0.1: drop the bottom-decile residual-momentum names


class VetoArmUnavailable(RuntimeError):
    """The veto-0.1 arm cannot be computed for the sessions about to be logged."""


def _assert_veto_arm_live(dates: list[str], covered_through: str) -> None:
    """HARD guard, not a warning — the same reasoning as ``assert_calendar_covers`` one layer down.

    `residual_ranks` inner-joins each name's returns to the factor panel, so past the factors' last
    date there is no row, `resid_rank` is NaN, and the veto condition `resid_rank < VETO_Q` is False
    for every name on every session. The veto book then steps the *unmodified* panel and comes out
    **byte-identical to base** — silently, with no error and no empty column to notice.

    That failure is uniquely corrosive here. `forward/prereg.md` registers the wall as a THREE-book
    comparison, and the rows are hash-chained specifically so a later reader can trust that what was
    logged is what was known. An inert arm writes a perfect agreement between base and veto into a
    tamper-evident log — evidence that two independent books concurred, when only one book ran. It
    cannot be retracted afterwards without breaking the chain.

    So refuse to log at all, exactly as the calendar guard does. A wall that stops is a wall you
    fix; a wall that agrees with itself is a wall you believe.

    The check is deliberately a coverage-END comparison, and only that. `resid_rank` is *also*
    legitimately absent during warm-up — the regression needs `REG_WIN` 252 bars of joined history
    before the first monthly score exists — and a warm-up gap resolves itself as history accrues.
    Refusing there would block every honest cold start. The two cases share an observable (no rank)
    and differ in where the gap sits: warm-up is at the head and self-heals; stale factors are at
    the tail and never do. Only the tail is refused.

    What this consciously does NOT catch: an arm inert for a subtler reason inside the covered
    range — an all-NaN factor column, a dtype mismatch that makes the join miss. Those would pass
    this guard. The paired positive in `tests/test_wall_veto_arm_liveness.py` asserts the veto book
    actually diverges from base on a live fixture, which is where that class would surface.
    """
    stale = [d for d in dates if d[:10] > covered_through]
    if not stale:
        return
    raise VetoArmUnavailable(
        f"the veto-0.1 arm has no residual ranks for {len(stale)} of {len(dates)} session(s) about "
        f"to be logged ({stale[0]} … {stale[-1]}), so on those days it is byte-identical to base "
        f"and cannot be logged as an independent observation. Factor panel covers through "
        f"{covered_through}; past that date the inner join in "
        f"nq.research.residual.residual_ranks drops every row. "
        f"Fix: extend data/ff_india_factors.parquet past the sessions being logged, or amend "
        f"forward/prereg.md to retire the veto arm. Refusing to write agreement we did not measure."
    )


def _daily_from_curve(curve: list[dict[str, Any]], initial: float) -> dict[str, dict[str, Any]]:
    """{date_iso -> {ret, equity, npos}} from a PaperBook equity_curve; ret vs the prior NAV
    (first session vs initial capital)."""
    out: dict[str, dict[str, Any]] = {}
    prev = float(initial)
    for e in curve:
        eq = float(e["equity"])
        out[str(e["date"])[:10]] = {"ret": (eq / prev - 1.0) if prev > 0 else 0.0,
                                    "equity": eq, "npos": int(e["n_positions"])}
        prev = eq
    return out


def _step_veto_book(panel: pd.DataFrame, cfg: Mapping[str, Any], factors_path: Path,
                    vol_target: Mapping[str, Any] | None, state_dir: Path, since: str,
                    upto: str) -> tuple[PaperBook, str]:
    """Load/step the veto-0.1 book on the residual-vetoed panel over [since, upto] — the SAME window the
    base book stepped (residual_ranks still sees the full panel history for its 252d regression).

    Returns the book and the factor panel's last date, so `update_wall` can refuse to log sessions
    the arm could not have acted on (see :func:`_assert_veto_arm_live`)."""
    factors = pd.read_parquet(factors_path).set_index("date").sort_index()
    rr = residual_ranks(panel[["date", "ticker", "close"]], factors)   # full history for the regression
    vp = panel.merge(rr, on=["date", "ticker"], how="left").copy()
    vetoed = vp["resid_rank"].notna() & (vp["resid_rank"] < VETO_Q)
    vp["_vetoed"] = vetoed
    vp.loc[vetoed, "trend_rank"] = np.nan
    vp["date"] = pd.to_datetime(vp["date"])
    vp = vp[(vp["date"] >= pd.to_datetime(since)) & (vp["date"] <= pd.to_datetime(upto))]
    vp = vp.dropna(subset=["open", "high", "low", "close"])
    # The last session the arm could possibly have acted on. `update_wall` asserts the dates it is
    # about to append against this, so the check lands on rows entering the log, not on history.
    covered_through = str(factors.index.max())[:10] if len(factors.index) else ""
    vp = vp.drop(columns=["_vetoed"])

    vb = PaperBook(cfg, vol_target=vol_target)
    vdir = state_dir / "wall_veto"
    vb.load(vdir)
    last = pd.to_datetime(vb.equity_curve[-1]["date"]) if vb.equity_curve else None
    for d, g in vp.groupby("date", sort=True):
        if last is not None and d <= last:
            continue
        vb.step(d, g.set_index("ticker"))
    vb.save(vdir)
    return vb, covered_through


def update_wall(base_book: PaperBook, panel: pd.DataFrame, cfg: Mapping[str, Any], *,
                state_dir: str | Path = RESULTS_DIR, vol_target: Mapping[str, Any] | None = None,
                factors_path: str | Path = DATA_DIR / "ff_india_factors.parquet",
                holidays: Iterable[Any] | None = None, wall_start: str | None = None,
                backfill: bool = False) -> int:
    """Append 3-book wall rows for every base session not yet logged. Returns the number appended.

    ``wall_start`` (ISO date) is the wall's REGISTERED START — no session before it is ever written.
    It exists because of a hazard that is invisible until the first scheduled run:

    The paper book steps forward from its own inception, so on a cold start ``base_book.equity_curve``
    already contains every session since then. Without this bound the wall's first firing would append
    one ``ok`` row per past session — a whole stretch of *recomputed* history entering the log as
    forward evidence. Every row would pass the chain (dates strictly increase) and every row would be
    a lie about when it was known. `forward/prereg.md` §3's "never reconstructed" rule is about
    exactly this, and the chain cannot enforce it on its own.

    Default ``None`` preserves the previous behaviour, so existing callers and tests are unaffected;
    the scheduled cron is required to pass one (asserted in `tests/test_wall_schedule.py`).

    ``backfill`` (default False) decides what happens to sessions this job MISSED. Off, only the most
    recent session is logged as an ``ok`` row and the ones before it become hash-chained ``gap``
    markers — `forward/prereg.md` SS3 rule 4, "a missed day is a gap, never reconstructed". On, every
    unlogged session is written as an ``ok`` row, which is an owner override of that rule.
    """
    if not base_book.equity_curve:
        return 0
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])              # normalize (cron may carry string dates)
    state_dir = Path(state_dir)
    first_base = base_book.equity_curve[0]["date"]
    last_base = base_book.equity_curve[-1]["date"]
    vb, veto_covered_through = _step_veto_book(
        panel, cfg, Path(factors_path), vol_target, state_dir, first_base, last_base)

    base_daily = _daily_from_curve(base_book.equity_curve, base_book.initial_capital)
    veto_daily = _daily_from_curve(vb.equity_curve, vb.initial_capital)

    wall_path = state_dir / "forward_wall.csv"
    existing = _load(wall_path)
    last_wall = existing[-1]["date"] if existing else None

    todo: list[str] = []
    for d in sorted(base_daily):
        if wall_start is not None and d < str(wall_start)[:10]:
            continue                                   # before the registered start: never forward evidence
        if last_wall is not None and d <= last_wall:
            continue
        if d not in veto_daily:                       # alignment guard (should not happen)
            continue
        todo.append(d)
    # Assert BEFORE the first append, never inside the loop: a mid-loop raise leaves a partially
    # written wall, and an append-only hash chain has no way to take a row back.
    _assert_veto_arm_live(todo, veto_covered_through)

    # `forward/prereg.md` SS3 rule 4: "No back-dating. A row's date must be strictly after the last;
    # a missed day is a gap, never reconstructed." Only the MOST RECENT session in `todo` is an
    # observation; everything before it is a session this job failed to log on its day, and SS3's
    # missed-day rule says those are `gap` markers.
    #
    # `record_trading_day` already fills the trading days strictly between the last logged date and
    # the date it is given with hash-chained gaps, so writing only the last session produces exactly
    # the shape SS3 asks for. Looping over every date instead wrote one `ok` row per missed session
    # — reconstruction that the chain accepts (dates strictly increase) and that a later reader
    # cannot tell from a row written on the day. That is what would have entered the log after the
    # 2026-08-24..28 stall: five recomputed rows presented as five observations.
    #
    # `backfill=True` is the owner override that restores the old behaviour. It exists because the
    # numbers ARE deterministic EOD values, so someone may reasonably decide a complete comparison
    # is worth more than a truthful provenance — but that is a decision about a pre-registered
    # record, so it has to be typed, not defaulted into.
    to_log = todo if backfill else todo[-1:]
    for d in to_log:
        record_trading_day(d, base_daily[d], veto_daily[d], path=wall_path,
                           initial_capital=base_book.initial_capital, holidays=holidays)
    return len(to_log)
