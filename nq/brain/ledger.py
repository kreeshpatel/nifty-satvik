"""The per-trade attribution ledger — what each trade was made of, rebuilt from immutable archives.

Layer 5 of the Brain. Pure functions: no network, no clock, no model calls. The collector that feeds
archives and prices in is `scripts/collect_attribution_ledger.py`.

WHY A LEDGER AND NOT A REPORT

Findings 0141 and 0142 both ended at the same place: the target is not the problem and the market
explains much of the drawdown, so the open question is selection — and selection can only be studied
per trade, with what was knowable at entry sitting beside what happened. Five years of this programme's
research has repeatedly discovered, after the fact, that a question could not be answered because the
field that would have answered it was never written down (`06_habit_ledger_spec.md`). A ledger's whole
value is that it starts existing before the question is asked.

WHAT IS REBUILT AND WHAT IS RECORDED ONCE

Every row here is re-derivable from `results/archive/*/` — the weekly write-once snapshots — so the
ledger is a deterministic rebuild, not an append-only chain. That is the same contract as
`scripts/collect_signal_quality_forward.py`. A hash chain (`nq/paper/model_wall.py`) is for streams
that cannot be re-derived; adding one here would imply a guarantee the sources already give.

WHAT THIS CANNOT DO

It describes trades. It is not a feature store for choosing entries: program-laws I says entry quality
is not visible at the decision point on this funnel, in five independent instruments.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

# The live book RE-DATES a signal as it recomputes (PTCIL appeared on 2026-08-07 and again on
# 2026-08-10 — one economic signal). Same ticker within this many days is one episode. Kept equal to
# `scripts/collect_signal_quality_forward.EPISODE_DAYS` on purpose: two ledgers that disagree about
# what one trade is cannot be joined.
EPISODE_DAYS = 16


def first_seen(snapshots: Iterable[tuple[str, Mapping[str, Any]]], fields: Sequence[str],
               *, key_fields: tuple[str, str] = ("ticker", "signal_date")
               ) -> dict[tuple[str, str], dict[str, Any]]:
    """Each (ticker, signal_date)'s fields as FIRST recorded, oldest snapshot first.

    First non-null wins, and later snapshots only fill gaps: a card's entry context is what the book
    knew when it issued the card, not what it looks like after a trail has moved the stop.
    `snapshots` is (as_of, envelope) pairs; the envelope is an archived `signals_today_weekly.json`.
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for as_of, env in snapshots:
        for s in (env or {}).get("signals", []) or []:
            tkr, sig = s.get(key_fields[0]), s.get(key_fields[1])
            if not tkr or not sig:
                continue
            key = (str(tkr), str(sig)[:10])
            rec = out.setdefault(key, {"ticker": key[0], "signal_date": key[1], "as_of_snapshot": as_of})
            for f in fields:
                if rec.get(f) is None and s.get(f) is not None:
                    rec[f] = s.get(f)
    return out


def collapse_episodes(rows: Mapping[tuple[str, str], Mapping[str, Any]], fields: Sequence[str],
                      *, days: int = EPISODE_DAYS) -> dict[tuple[str, str], dict[str, Any]]:
    """Merge re-dated rows of one ticker into a single episode anchored at its earliest date."""
    by_ticker: dict[str, list[str]] = {}
    for tkr, sig in rows:
        by_ticker.setdefault(tkr, []).append(sig)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for tkr, dates in by_ticker.items():
        anchor: str | None = None
        for sig in sorted(dates):
            row = rows[(tkr, sig)]
            if anchor is not None and (pd.Timestamp(sig) - pd.Timestamp(anchor)).days <= days:
                tgt = out[(tkr, anchor)]
                for f in fields:
                    if tgt.get(f) is None and row.get(f) is not None:
                        tgt[f] = row.get(f)
            else:
                anchor = sig
                out[(tkr, anchor)] = dict(row)
    return out


def stop_width_pct(entry: float | None, stop: float | None) -> float | None:
    """(entry − stop) / entry, in percent — the R denominator, and the thing R hides.

    `FINDING_R_cap`: R-multiples are NOT comparable across stop geometries. A −2R loss on a 3% stop and
    a −2R loss on a 13% stop are different events, and only this column can tell them apart.
    """
    if entry is None or stop is None:
        return None
    e, s = float(entry), float(stop)
    if not e > 0 or not s > 0 or s >= e:
        return None
    return round((e - s) / e * 100.0, 4)


def decompose_r(r_multiple: float | None) -> dict[str, float | None]:
    """A loss splits into the stop working as designed (−1R) and the part filled beyond it.

    An identity, not a measurement — it is only evidence when the recorded stop agrees with the stop
    the engine measured R against (`nq.brain.attribution.stop_agreement`, all 9 agreed to 0.28% on the
    2026-09-04 archive). Positive R has no beyond-stop part.
    """
    if r_multiple is None or (isinstance(r_multiple, float) and np.isnan(r_multiple)):
        return {"designed_r": None, "beyond_stop_r": None, "gap_through": None}
    r = float(r_multiple)
    if r >= -1.0:
        return {"designed_r": round(r, 4), "beyond_stop_r": 0.0, "gap_through": False}
    return {"designed_r": -1.0, "beyond_stop_r": round(r + 1.0, 4), "gap_through": True}


def excursions_r(high: Sequence[float], low: Sequence[float], *, entry: float, stop: float
                 ) -> dict[str, float | None]:
    """MAE and MFE over a held window, in R units, plus how much of the favourable move was kept.

    R = entry − stop. `capture_of_mfe` is left to the caller's realised R (it needs the exit).
    """
    if not (entry > stop > 0):
        return {"mae_r": None, "mfe_r": None}
    h = np.asarray(list(high), dtype=float)
    lo = np.asarray(list(low), dtype=float)
    h, lo = h[np.isfinite(h)], lo[np.isfinite(lo)]
    if h.size == 0 or lo.size == 0:
        return {"mae_r": None, "mfe_r": None}
    risk = entry - stop
    return {"mae_r": round(float((lo.min() - entry) / risk), 4),
            "mfe_r": round(float((h.max() - entry) / risk), 4)}


def capture_of_mfe(r_multiple: float | None, mfe_r: float | None) -> float | None:
    """Realised R as a share of the best R the trade ever showed. None when it never went favourable."""
    if r_multiple is None or mfe_r is None or not mfe_r > 0:
        return None
    return round(float(r_multiple) / float(mfe_r), 4)


def window_pct(series: pd.Series, start: str | pd.Timestamp, end: str | pd.Timestamp) -> float | None:
    """Percent change of a price series between two dates, using the last print on or before each.

    None when the series does not COVER the window. Without that check `asof` walks back to the same
    last print at both ends and returns a confident **0.0%** — which is exactly what the first run of
    this ledger reported for every trade, because the committed index CSV ends before the live book
    starts (the weekly cron refreshes it at runtime). A missing measurement must read as missing.
    """
    s = pd.Series(series, dtype=float).dropna()
    if s.empty:
        return None
    s.index = pd.DatetimeIndex(s.index)
    a_t, b_t = pd.Timestamp(start), pd.Timestamp(end)
    if s.index.min() > a_t or s.index.max() < b_t:
        return None
    a, b = s.asof(a_t), s.asof(b_t)
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or a <= 0:
        return None
    return round(float(b / a - 1.0) * 100.0, 4)
