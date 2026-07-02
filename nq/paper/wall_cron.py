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
                    vol_target: Mapping[str, Any] | None, state_dir: Path, since: str, upto: str) -> PaperBook:
    """Load/step the veto-0.1 book on the residual-vetoed panel over [since, upto] — the SAME window the
    base book stepped (residual_ranks still sees the full panel history for its 252d regression)."""
    factors = pd.read_parquet(factors_path).set_index("date").sort_index()
    rr = residual_ranks(panel[["date", "ticker", "close"]], factors)   # full history for the regression
    vp = panel.merge(rr, on=["date", "ticker"], how="left").copy()
    vp.loc[vp["resid_rank"].notna() & (vp["resid_rank"] < VETO_Q), "trend_rank"] = np.nan
    vp["date"] = pd.to_datetime(vp["date"])
    vp = vp[(vp["date"] >= pd.to_datetime(since)) & (vp["date"] <= pd.to_datetime(upto))]
    vp = vp.dropna(subset=["open", "high", "low", "close"])

    vb = PaperBook(cfg, vol_target=vol_target)
    vdir = state_dir / "wall_veto"
    vb.load(vdir)
    last = pd.to_datetime(vb.equity_curve[-1]["date"]) if vb.equity_curve else None
    for d, g in vp.groupby("date", sort=True):
        if last is not None and d <= last:
            continue
        vb.step(d, g.set_index("ticker"))
    vb.save(vdir)
    return vb


def update_wall(base_book: PaperBook, panel: pd.DataFrame, cfg: Mapping[str, Any], *,
                state_dir: str | Path = RESULTS_DIR, vol_target: Mapping[str, Any] | None = None,
                factors_path: str | Path = DATA_DIR / "ff_india_factors.parquet",
                holidays: Iterable[Any] | None = None) -> int:
    """Append 3-book wall rows for every base session not yet logged. Returns the number appended."""
    if not base_book.equity_curve:
        return 0
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])              # normalize (cron may carry string dates)
    state_dir = Path(state_dir)
    first_base = base_book.equity_curve[0]["date"]
    last_base = base_book.equity_curve[-1]["date"]
    vb = _step_veto_book(panel, cfg, Path(factors_path), vol_target, state_dir, first_base, last_base)

    base_daily = _daily_from_curve(base_book.equity_curve, base_book.initial_capital)
    veto_daily = _daily_from_curve(vb.equity_curve, vb.initial_capital)

    wall_path = state_dir / "forward_wall.csv"
    existing = _load(wall_path)
    last_wall = existing[-1]["date"] if existing else None

    n = 0
    for d in sorted(base_daily):
        if last_wall is not None and d <= last_wall:
            continue
        if d not in veto_daily:                       # alignment guard (should not happen)
            continue
        record_trading_day(d, base_daily[d], veto_daily[d], path=wall_path,
                           initial_capital=base_book.initial_capital, holidays=holidays)
        n += 1
    return n
