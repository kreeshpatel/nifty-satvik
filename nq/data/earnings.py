"""PIT-clean NSE board-meeting / results-calendar layer (census candidate #2; pre-reg 0120).

Two-layer PIT structure, both encoded from the source's native fields (probe-verified):
  * ann_ts     — when the future meeting became PUBLIC (the broadcast timestamp). FEATURE layer:
                 a decision at time t may use only events with ann_ts <= t.
  * event_date — the meeting/results day itself. LABEL layer: grading a completed trade may use true
                 event dates regardless of announcement (the trade lived through them either way).

`known_events_features` is the pure trailing core: for (symbol, asof) it sees only announcements
<= asof, so truncating the raw table at T leaves every asof <= T output unchanged —
tests/test_earnings_pit.py proves it (0017 is the spec).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import DATA_DIR

EARNINGS_RAW_PATH = DATA_DIR / "_earnings_raw.parquet"

_RESULT_PAT = "result"


def build_event_table(raw: pd.DataFrame, results_only: bool = True) -> pd.DataFrame:
    """Normalize the harvested records -> one row per (symbol, event_date) with the EARLIEST
    announcement timestamp (a meeting may be re-intimated; the FIRST public announcement governs PIT)."""
    t = raw.copy()
    t["event_date"] = pd.to_datetime(t["event_date"], format="%d-%b-%Y", errors="coerce")
    t["ann_ts"] = pd.to_datetime(t["ann_ts"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    t = t.dropna(subset=["symbol", "event_date", "ann_ts"])
    if results_only:
        blob = (t["purpose"].fillna("") + " " + t["desc"].fillna("")).str.lower()
        t = t[blob.str.contains(_RESULT_PAT)]
    out = (t.groupby(["symbol", "event_date"], as_index=False)["ann_ts"].min()
             .sort_values(["symbol", "ann_ts"]))
    return out.reset_index(drop=True)


def known_events_features(events: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """For each (symbol, asof) pair: the nearest FUTURE event KNOWN at asof.

    events: build_event_table output. pairs: columns [symbol, asof]. Returns pairs +
    days_to_known_event (calendar days to the nearest event_date >= asof among rows with
    ann_ts <= asof; NaN if none known) — trailing-only in ann_ts (the truncation property).
    """
    out = pairs.copy()
    out["days_to_known_event"] = np.nan
    ev = {s: g[["ann_ts", "event_date"]].sort_values("ann_ts").to_numpy()
          for s, g in events.groupby("symbol")}
    for i, r in out.iterrows():
        a = ev.get(r["symbol"])
        if a is None:
            continue
        asof = np.datetime64(pd.Timestamp(r["asof"]))
        known = a[a[:, 0] <= asof]                       # announced by asof
        fut = known[known[:, 1] >= asof]                 # event still ahead
        if len(fut):
            nearest = fut[:, 1].min()
            out.at[i, "days_to_known_event"] = float((pd.Timestamp(nearest) - pd.Timestamp(r["asof"])).days)
    return out


def events_in_window(events: pd.DataFrame, symbol: str, start, end) -> int:
    """LABEL-side helper: TRUE event count for symbol in [start, end] (announcement-agnostic —
    grading only, never a selection feature)."""
    g = events[events["symbol"] == symbol]
    if not len(g):
        return 0
    m = (g["event_date"] >= pd.Timestamp(start)) & (g["event_date"] <= pd.Timestamp(end))
    return int(m.sum())
