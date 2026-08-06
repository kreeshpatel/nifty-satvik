"""Adjustment-factor monotonicity guard for the OHLCV cache — the vaccine, not the repair.

## The invariant

For any symbol, write the cached series against the exchange's own unadjusted close as

    adj(t) = cache(t) / raw(t)

`adj` is the cumulative corporate-action adjustment the vendor has applied to bars at `t`.
Adjustments accumulate BACKWARDS — a split divides everything before its ex-date and nothing after —
so `adj` is **non-decreasing in t** and reaches 1 at the right edge. **A factor that decreases as
time advances is impossible.** When it happens, two segments of one symbol's history are carrying
different adjustment states and the boundary between them is a price step no market produced.

That is the whole guard. It has no threshold on move size, which is the point: every other
corporate-action detector in this repo is a threshold on the size of a jump
(``_CORP_ACTION_MOVE = 0.50``, the M6 scan at 50%, ``ADJ_JUMP`` on a 25-day overlap), and the
2026Q3 foundation audit established that this defect class is **not size-bounded** — the observed
steps run from ×1.04 (a rights issue) to ×5.00 (a 1:5 split). A guard bounded by size cannot see
the small end. A monotonicity violation is a violation at any magnitude.

## What this guard does NOT claim

It does not repair anything, and it does not model vendor behaviour. The audit found the seams are
**upstream**: a fresh single-call download from the vendor reproduces them exactly, so they are not
an artifact of how this repo assembles its cache and are not healed by rebuilding it. This module
only detects, names, and refuses to let a NEW one enter silently.

## Absent evidence is not evidence of absence

A probe date with no exchange reference, or a symbol the reference does not cover, yields
``INDETERMINATE`` for that cell — never a pass. This is the S2.14 rule the output-contract checker
was rewritten around: a checker that reports "nothing found" when it could not look is worse than
no checker, because it is trusted.

## Known seams

The seven seams the foundation audit localised are carried in ``KNOWN_SEAMS`` with their dates,
factors and the corporate action each belongs to. They are **reported, not repaired** — the repair
is an owner decision (FOUNDATION_AUDIT.md, item F-1). The guard's hard failure is reserved for a
seam that is *not* on that register, which is exactly the event the guard exists to prevent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REFERENCE = DATA_DIR / "raw_close_reference.parquet"

# A factor may only ever RISE toward the present. This tolerance absorbs the paise-level rounding of
# a 2-dp exchange close against a float cache; it is not a size threshold on the defect — the
# smallest seam on the register (UPL, ×1.0425) is eight times larger than it.
STEP_TOL = 0.005

# THE REGISTER — a ledger of every monotonicity violation known to be in the cache, not a
# suppression list. The guard prints every seam it finds on every run whether or not it is here;
# registration only decides whether the build HALTS. Entries are REMOVED as they are repaired, and
# never edited to silence a failure.
#
# `factor` is the step by which adj falls; `cause` is the corporate action whose adjustment the
# vendor applied to only part of the history, where one is known.
#
# Three provenances, kept distinct because they carry different weight:
#   foundation-audit-F-1  the seven the 2026Q3 audit localised to the exact session; a live owner
#                         decision, repair not authorised
#   known-erratum         already pre-declared in run_bhanushali_sixstep.ERRATUM_BARS
#   pre-2019-head         inside the warm-up head the programme does not trade
#   OPEN-undiagnosed      found BY THIS GUARD on its first run; no corporate action explains them
#                         and neither has been localised. Registered so the guard is usable from
#                         today, flagged so they are not mistaken for settled.
KNOWN_SEAMS: dict[tuple[str, str], dict] = {
    ("CGCL", "2024-01-01"): {"factor": 4.00, "cause": "split+bonus ex 2024-03-05",
                             "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("GPIL", "2024-01-01"): {"factor": 5.00, "cause": "split ex 2024 (factor 5)",
                             "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("MOTILALOFS", "2024-01-01"): {"factor": 4.00, "cause": "bonus/split ex 2024 (factor 4)",
                                   "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("UPL", "2024-11-18"): {"factor": 1.0425, "cause": "rights 1:8 ex 2024-11-26",
                            "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("CONCOR", "2025-01-01"): {"factor": 1.25, "cause": "bonus 1:4 ex 2025-07-04",
                               "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("MAHLIFE", "2025-05-14"): {"factor": 1.0884, "cause": "rights 3:8 ex 2025-05-23",
                                "found": "2026-08-06", "provenance": "foundation-audit-F-1"},
    ("TRENT", "2026-01-01"): {"factor": 1.50, "cause": "bonus 1:2 ex 2026-06-04",
                              "found": "2026-08-06", "provenance": "foundation-audit-F-1"},

    # Pre-declared bad bars: the Diwali Muhurat sessions where the cache carries a doubled bar that
    # reverts two days later. `drop_erratum` is gated OFF by default, so they are in the record.
    ("INDIAMART", "2019-10-27"): {"factor": 2.00, "cause": "Muhurat doubled bar (ERRATUM_BARS)",
                                  "found": "2026-07", "provenance": "known-erratum"},
    ("INDIAMART", "2020-11-14"): {"factor": 2.00, "cause": "Muhurat doubled bar (ERRATUM_BARS)",
                                  "found": "2026-07", "provenance": "known-erratum"},

    # Inside the 2017-2018 warm-up head, which the programme does not trade (trust >=2019 only).
    ("J&KBANK", "2017-02-27"): {"factor": 2.0422, "cause": "face-value split, pre-census",
                                "found": "2026-08-06", "provenance": "pre-2019-head"},
    ("CDSL", "2017-07-03"): {"factor": 2.0011, "cause": "listing week, pre-census",
                             "found": "2026-08-06", "provenance": "pre-2019-head"},

    # FOUND BY THIS GUARD, first run, 2026-08-06. Neither is explained by any corporate action in
    # the NSE record, and neither has been localised to its exact session. HBLENGINE is INSIDE the
    # trusted period: the cache moves -0.65% on a session the exchange moved +2.68%. Registered so
    # the guard is usable from today; carried as OPEN so they are not read as settled.
    ("HBLENGINE", "2024-12-24"): {"factor": 1.0336, "cause": "no corporate action in the NSE record",
                                  "found": "2026-08-06", "provenance": "OPEN-undiagnosed"},
    ("TRENT", "2019-03-18"): {"factor": 1.0214, "cause": "no corporate action in the NSE record",
                              "found": "2026-08-06", "provenance": "OPEN-undiagnosed"},
}


@dataclass
class SeamReport:
    """Structured verdict. Mirrors the output-contract checker's vocabulary deliberately: the two
    guards answer the same shape of question and should not be read with different eyes."""

    overall: str                                    # OK | WARN | RED | INDETERMINATE
    seams: list[dict] = field(default_factory=list)          # every monotonicity violation
    new_seams: list[dict] = field(default_factory=list)      # violations NOT on the register
    indeterminate: list[dict] = field(default_factory=list)  # could not be checked
    symbols_checked: int = 0
    probe_dates: int = 0

    def as_dict(self) -> dict:
        return {"overall": self.overall, "symbols_checked": self.symbols_checked,
                "probe_dates": self.probe_dates, "n_seams": len(self.seams),
                "n_new_seams": len(self.new_seams), "n_indeterminate": len(self.indeterminate),
                "seams": self.seams, "new_seams": self.new_seams,
                "indeterminate": self.indeterminate}


def load_reference(path: Path | None = None) -> pd.DataFrame:
    """Raw (unadjusted) exchange closes on the probe grid: columns symbol, date, close."""
    p = path or REFERENCE
    if not p.exists():
        return pd.DataFrame(columns=["symbol", "date", "close"])
    return pd.read_parquet(p)


def implied_adjustment(series: pd.Series, ref: pd.DataFrame) -> pd.Series:
    """adj(t) = cache(t) / raw(t), using ONLY probe dates where the cache has a bar on that exact
    session.

    The first version took the last cache bar on or before the probe date, to keep coverage on thin
    listings. That is unsound: comparing ``cache(t−k)`` to ``raw(t)`` divides two different
    sessions, so an ordinary price move between them would read as a change in the adjustment
    factor — the false-positive class that makes a guard get ignored. On the current cache and probe
    grid the two forms happen to agree exactly (every probe date has a bar), so no finding rests on
    the change; it is made anyway, because a guard should not depend on luck for its soundness.

    A missing bar yields no observation. It is not silently skipped either — the caller counts
    uncovered symbols as INDETERMINATE.
    """
    if not len(ref) or not len(series):
        return pd.Series(dtype=float)
    idx = pd.DatetimeIndex(series.index)
    have = pd.Series(range(len(idx)), index=idx)
    out = {}
    for d, raw in zip(pd.DatetimeIndex(ref["date"]), ref["close"].astype(float)):
        if raw <= 0 or d not in have.index:
            continue
        out[d] = float(series.iloc[int(have.loc[d])]) / raw
    return pd.Series(out).sort_index()


def check_adjustment_monotonicity(ohlcv: dict, ref: pd.DataFrame | None = None, *,
                                  known: dict | None = None) -> SeamReport:
    """Assert `adj` never decreases, per symbol, across the probe grid.

    Returns a report rather than raising, so callers choose the consequence: the build path raises
    on a NEW seam (``assert_no_new_seams``), while a diagnostic run prints everything.
    """
    ref = load_reference() if ref is None else ref
    known = KNOWN_SEAMS if known is None else known
    rep = SeamReport(overall="OK")
    if not len(ref):
        rep.overall = "INDETERMINATE"
        rep.indeterminate.append({"reason": "no raw-close reference available; the guard could not "
                                            "look, so it reports nothing rather than OK",
                                  "path": str(REFERENCE)})
        return rep

    by_sym = {s: g for s, g in ref.groupby("symbol")}
    rep.probe_dates = int(pd.DatetimeIndex(ref["date"]).nunique())
    for sym, df in sorted(ohlcv.items()):
        if df is None or "Close" not in getattr(df, "columns", []) or not len(df):
            continue
        g = by_sym.get(sym)
        if g is None or not len(g):
            rep.indeterminate.append({"symbol": sym, "reason": "symbol absent from the reference"})
            continue
        adj = implied_adjustment(df["Close"].astype(float), g)
        if len(adj) < 2:
            rep.indeterminate.append({"symbol": sym, "reason": f"only {len(adj)} probe(s) covered"})
            continue
        rep.symbols_checked += 1
        vals, dates = adj.to_numpy(), adj.index
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1] * (1 - STEP_TOL):
                seam = {"symbol": sym,
                        "window_start": str(pd.Timestamp(dates[i - 1]).date()),
                        "window_end": str(pd.Timestamp(dates[i]).date()),
                        "adj_before": round(float(vals[i - 1]), 6),
                        "adj_after": round(float(vals[i]), 6),
                        "step_factor": round(float(vals[i - 1] / vals[i]), 6)}
                hit = next((v for (s, d), v in known.items()
                            if s == sym and seam["window_start"] <= d <= seam["window_end"]), None)
                if hit:
                    seam["known"] = True
                    seam["seam_session"] = next(d for (s, d) in known if s == sym
                                                and seam["window_start"] <= d <= seam["window_end"])
                    seam["cause"] = hit["cause"]
                    seam["provenance"] = hit.get("provenance", "registered")
                else:
                    seam["known"] = False
                    rep.new_seams.append(seam)
                rep.seams.append(seam)

    if rep.new_seams:
        rep.overall = "RED"
    elif rep.seams:
        rep.overall = "WARN"
    elif rep.indeterminate and not rep.symbols_checked:
        rep.overall = "INDETERMINATE"
    return rep


def assert_no_new_seams(ohlcv: dict, ref: pd.DataFrame | None = None, *,
                        known: dict | None = None) -> SeamReport:
    """Build-path gate. Raises on a seam that is not on the register; known seams warn.

    The asymmetry is deliberate and is not a softening. The seven registered seams are a live owner
    decision (FOUNDATION_AUDIT.md F-1); halting the book over them would be this guard deciding that
    question by itself. A seam that is NOT registered is a new, undiagnosed discontinuity entering
    the cache, which is precisely what must never pass silently.
    """
    rep = check_adjustment_monotonicity(ohlcv, ref, known=known)
    if rep.new_seams:
        lines = [f"  {s['symbol']}: adj fell x{s['step_factor']:.4f} between {s['window_start']} "
                 f"and {s['window_end']} ({s['adj_before']:.6f} -> {s['adj_after']:.6f})"
                 for s in rep.new_seams]
        raise ValueError(
            "ADJUSTMENT MONOTONICITY VIOLATED — the cache contains a price step no market "
            f"produced:\n" + "\n".join(lines) +
            "\n\nAn adjustment factor cannot decrease as time advances. Localise the exact session "
            "with scripts/audit_foundation_seam_2026Q3.py, then either repair the series or add the "
            "seam to nq.data.adjustment_guard.KNOWN_SEAMS with its cause. Do NOT widen STEP_TOL.")
    return rep
