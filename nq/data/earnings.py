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


# ── Card badge (DISPLAY ONLY — informational, never a selection or sizing input) ─────────────
# The window and the two measured numbers are FROZEN and imported from the research record. They
# are constants here so the card cannot drift from what was actually measured:
#   * window 14cd + the "announced by the signal Friday" test  -> finding 0120 Q2 (`known_event_within_14cd`)
#   * -0.383R conditional cohort cost                          -> finding 0120 Q2 (raw; -0.294 conditional)
#   * +9.8pp false-touch enrichment                            -> finding 0120 Q1 sub-result [+2.6,+17.2]
# Usage of this signal as a RULE is closed: skip/deferral killed by 0121, sizing killed by 0129.
# The badge exists so the owner sees the risk at decision time, not so the engine acts on it.
EVENT_BADGE_WINDOW_CD = 14
EVENT_BADGE_COHORT_COST_R = -0.38
EVENT_BADGE_FALSE_TOUCH_ENRICHMENT_PP = 9.8


def card_event_badge(events: pd.DataFrame, symbol: str, signal_friday) -> dict | None:
    """PIT-legal display badge for a buy card, or ``None`` when nothing is known.

    Mirrors finding 0120's `known_event_within_14cd` EXACTLY: a results event is shown only if it
    was ANNOUNCED by the signal-week Friday (``ann_ts <= signal_friday``) and falls inside the
    14 calendar days from the entry-week Monday. Trailing-only in ``ann_ts``, so truncating the raw
    table at T leaves every ``signal_friday <= T`` badge unchanged (tests/test_earnings_pit.py).

    Returns ``days_into_window`` = calendar days from the entry-week Monday to the event.
    """
    sf = pd.Timestamp(signal_friday).normalize()
    monday = sf + pd.Timedelta(days=3)
    g = events[events["symbol"] == symbol]
    if not len(g):
        return None
    known = g[g["ann_ts"] <= sf]                                   # announced by the decision moment
    hit = known[(known["event_date"] >= monday) &
                (known["event_date"] <= monday + pd.Timedelta(days=EVENT_BADGE_WINDOW_CD))]
    if not len(hit):
        return None
    row = hit.loc[hit["event_date"].idxmin()]
    return {
        "event_date": str(pd.Timestamp(row["event_date"]).date()),
        "announced_on": str(pd.Timestamp(row["ann_ts"]).date()),
        "days_into_window": int((pd.Timestamp(row["event_date"]) - monday).days),
        "window_days": EVENT_BADGE_WINDOW_CD,
        "cohort_cost_r": EVENT_BADGE_COHORT_COST_R,
        "false_touch_enrichment_pp": EVENT_BADGE_FALSE_TOUCH_ENRICHMENT_PP,
        "informational_only": True,
    }


def events_in_window(events: pd.DataFrame, symbol: str, start, end) -> int:
    """LABEL-side helper: TRUE event count for symbol in [start, end] (announcement-agnostic —
    grading only, never a selection feature)."""
    g = events[events["symbol"] == symbol]
    if not len(g):
        return 0
    m = (g["event_date"] >= pd.Timestamp(start)) & (g["event_date"] <= pd.Timestamp(end))
    return int(m.sum())
