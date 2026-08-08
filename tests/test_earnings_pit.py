"""PIT / truncation guard for the earnings-calendar layer (nq.data.earnings) — 0017 as spec.

The two-layer structure must hold: a decision at asof sees only events ANNOUNCED by asof (ann_ts <= asof),
never events whose announcement lies in the future — even when the event date itself is near. Truncating
the raw table at T must leave every asof <= T feature unchanged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.earnings import (
    build_event_table,
    card_event_badge,
    events_in_window,
    known_events_features,
)


def _raw() -> pd.DataFrame:
    rows = [
        # symbol, purpose, desc, event_date, ann_ts
        ("AAA", "Financial Results", "results q4", "20-Mar-2024", "10-Mar-2024 15:00:00"),
        ("AAA", "Financial Results", "results q1", "15-Jun-2024", "05-Jun-2024 18:00:00"),
        ("AAA", "Financial Results", "re-intimation", "15-Jun-2024", "01-Jun-2024 09:00:00"),  # earlier ann
        ("AAA", "Dividend", "interim dividend consideration", "01-May-2024", "20-Apr-2024 10:00:00"),
        ("BBB", "Results/Other", "approve results", "10-Apr-2024", "02-Apr-2024 12:00:00"),
    ]
    return pd.DataFrame(rows, columns=["symbol", "purpose", "desc", "event_date", "ann_ts"])


def test_build_dedup_and_results_filter():
    ev = build_event_table(_raw())
    aaa = ev[ev["symbol"] == "AAA"]
    assert len(aaa) == 2                                   # dividend row filtered out
    jun = aaa[aaa["event_date"] == "2024-06-15"]
    assert jun["ann_ts"].iloc[0] == pd.Timestamp("2024-06-01 09:00:00")   # earliest announcement kept


def test_unannounced_event_is_invisible():
    ev = build_event_table(_raw())
    pairs = pd.DataFrame({"symbol": ["AAA"], "asof": [pd.Timestamp("2024-05-20")]})
    f = known_events_features(ev, pairs)
    # the 15-Jun event was announced 01-Jun — at 20-May it must be INVISIBLE (no known future event)
    assert np.isnan(f["days_to_known_event"].iloc[0])
    pairs2 = pd.DataFrame({"symbol": ["AAA"], "asof": [pd.Timestamp("2024-06-02")]})
    f2 = known_events_features(ev, pairs2)
    assert f2["days_to_known_event"].iloc[0] == 13.0       # now known: 15-Jun minus 02-Jun


def test_truncation_invariance():
    raw = _raw()
    ev_full = build_event_table(raw)
    T = pd.Timestamp("2024-05-31")
    raw_tr = raw[pd.to_datetime(raw["ann_ts"], format="%d-%b-%Y %H:%M:%S") <= T]
    ev_tr = build_event_table(raw_tr)
    pairs = pd.DataFrame({"symbol": ["AAA", "AAA", "BBB"],
                          "asof": [pd.Timestamp("2024-03-12"), pd.Timestamp("2024-05-20"),
                                   pd.Timestamp("2024-04-03")]})
    pd.testing.assert_frame_equal(known_events_features(ev_full, pairs),
                                  known_events_features(ev_tr, pairs))


def test_label_side_uses_true_events():
    ev = build_event_table(_raw())
    assert events_in_window(ev, "AAA", "2024-06-01", "2024-06-30") == 1
    assert events_in_window(ev, "AAA", "2024-01-01", "2024-12-31") == 2


# ── card badge: display-only, but PIT-legal on exactly the 0120 rule ──────────────────────────
def test_card_badge_fires_inside_the_window():
    ev = build_event_table(_raw())
    # signal Friday 2024-06-07 -> entry Monday 2024-06-10 -> window through 2024-06-24.
    # AAA's 15-Jun event was announced 01-Jun, so it IS known at 07-Jun.
    b = card_event_badge(ev, "AAA", "2024-06-07")
    assert b is not None
    assert b["event_date"] == "2024-06-15"
    assert b["days_into_window"] == 5                      # 10-Jun -> 15-Jun
    assert b["announced_on"] == "2024-06-01"
    assert b["cohort_cost_r"] == -0.38 and b["false_touch_enrichment_pp"] == 9.8


def test_card_badge_hides_an_unannounced_event():
    """The 15-Jun event is announced 01-Jun; a 24-May signal Friday must NOT see it."""
    ev = build_event_table(_raw())
    assert card_event_badge(ev, "AAA", "2024-05-24") is None


def test_card_badge_is_silent_outside_the_window_and_for_unknown_symbols():
    ev = build_event_table(_raw())
    assert card_event_badge(ev, "AAA", "2024-04-05") is None      # next event >14cd away
    assert card_event_badge(ev, "ZZZ", "2024-06-07") is None      # symbol not in the calendar


def test_card_badge_truncation_invariance():
    """Truncating the raw feed at T cannot change any badge for a signal Friday <= T."""
    raw = _raw()
    T = pd.Timestamp("2024-06-03")
    raw_tr = raw[pd.to_datetime(raw["ann_ts"], format="%d-%b-%Y %H:%M:%S") <= T]
    a = card_event_badge(build_event_table(raw), "AAA", "2024-06-03")
    b = card_event_badge(build_event_table(raw_tr), "AAA", "2024-06-03")
    assert a == b and a is not None
