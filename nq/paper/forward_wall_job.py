"""Forward-wall daily-append JOB — where the wall meets reality (forward/prereg.md §1, §3).

The hash-chain primitive (`forward_wall.py`) proves the log cannot lie about the past; this job is
responsible for writing the RIGHT row in the first place — the operational-correctness half a chain
cannot help with. It holds to three criteria the primitive does not:

1. **One source.** `record_trading_day` takes base and veto metrics that the caller MUST have computed
   from a SINGLE day's panel (one OHLCV pull → one `compose_ranked_panel`). Passing them together in
   one call is the structural enforcement; the shared source is the cron's contract (see module note).
2. **Deterministic double-run & gaps.** A second call for the same date is refused (the primitive's
   date guard). A missed trading day is filled with a hash-chained `gap` marker — never back-dated,
   never silently skipped.
3. **Drift exposure is logged STATE.** The drift book's multiplier is computed from the LOGGED
   (immutable, hash-chained) base returns and written into the row, so a later data revision to the
   trailing window cannot rewrite what exposure was actually applied.

Cron integration (the remaining operational hook — deliberately NOT wired into the live cron here,
because that edit must be verified against the running paper book, not shipped under this bar):

    # in run_paper_cron, AFTER building the single `panel` and stepping the base PaperBook:
    #   base = {"ret":.., "equity":.., "npos":..}          # from the stepped base book, this session
    #   veto = {"ret":.., "equity":.., "npos":..}          # a veto PaperBook stepped on the SAME panel
    #                                                          with trend_rank = residual_ranks(panel)-veto
    #   record_trading_day(session_date, base, veto)       # derives drift, logs one atomic row
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from config import NSE_HOLIDAYS
from nq.paper.forward_wall import DEFAULT_LOG, append_row, gap_row, read_verified

DRIFT_WINDOW = 63          # trailing-63d base return governs the drift exposure (prereg §1)
DRIFT_DEGROSS = 0.5        # ×0.5 when that trailing return is negative, else ×1.0


def _norm_holidays(holidays: Iterable[Any] | None) -> set[str]:
    src = NSE_HOLIDAYS if holidays is None else holidays
    return {pd.Timestamp(h).date().isoformat() for h in src}


def _is_trading_day(d: pd.Timestamp, holidays: set[str]) -> bool:
    return d.weekday() < 5 and d.date().isoformat() not in holidays


def _missing_trading_days(last_iso: str, date_iso: str, holidays: set[str]) -> list[str]:
    """Trading days strictly between the last logged date and `date` (the gap to fill)."""
    out: list[str] = []
    d = pd.Timestamp(last_iso) + pd.Timedelta(days=1)
    end = pd.Timestamp(date_iso)
    while d < end:
        if _is_trading_day(d, holidays):
            out.append(d.date().isoformat())
        d += pd.Timedelta(days=1)
    return out


def _drift_mult(base_rets: list[float]) -> float:
    """Exposure multiplier for today from the trailing-63d LOGGED base return (through the prior
    session — no lookahead). <63 rows of history ⇒ full exposure (documented default)."""
    if len(base_rets) < DRIFT_WINDOW:
        return 1.0
    cum = 1.0
    for r in base_rets[-DRIFT_WINDOW:]:
        cum *= 1.0 + r
    return 1.0 if cum - 1.0 >= 0.0 else DRIFT_DEGROSS


def record_trading_day(
    date: str, base: Mapping[str, Any], veto: Mapping[str, Any], *,
    path: str | Path = DEFAULT_LOG, initial_capital: float = 1_000_000.0,
    holidays: Iterable[Any] | None = None,
) -> str:
    """Fill any missed trading days with gap markers, derive the drift book (multiplier logged as
    state), and atomically append ONE base+veto+drift row through the verified chain. Refuses
    (IntegrityError) on a broken chain or a same-date double-run. Returns the new row_hash.

    `base` / `veto` are ``{ret, equity, npos}`` computed by the caller from a SINGLE day's panel."""
    hol = _norm_holidays(holidays)
    date = str(date)[:10]
    rows = read_verified(path)                                   # verifies the whole chain first
    if rows:
        for gd in _missing_trading_days(rows[-1]["date"], date, hol):
            append_row(gap_row(gd), path)                        # each gap chained; never back-dated
        rows = read_verified(path)

    ok_rows = [r for r in rows if r["status"] == "ok" and r["base_ret"] != ""]
    mult = _drift_mult([float(r["base_ret"]) for r in ok_rows])
    prev_drift_eq = float(ok_rows[-1]["drift_equity"]) if ok_rows else float(initial_capital)
    drift_ret = float(base["ret"]) * mult
    row = {
        "date": date, "status": "ok",
        "base_ret": base["ret"], "base_equity": base["equity"], "base_npos": base["npos"],
        "veto_ret": veto["ret"], "veto_equity": veto["equity"], "veto_npos": veto["npos"],
        "drift_ret": drift_ret, "drift_equity": prev_drift_eq * (1.0 + drift_ret),
        "drift_npos": base["npos"], "drift_mult": mult,
    }
    return append_row(row, path)
