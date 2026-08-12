"""Signal archaeology — why a name was not bought in a given week.

The failure this guards against is a CONFIDENT WRONG ANSWER. The book funds ~2.6% of activated
signals, so "we didn't buy it" has five distinct causes that imply different responses. A tool that
returns "no setup" when the truth is "no data", or "unknown" when the truth is knowable, is worse
than no tool: it would have told the owner the HINDALCO touch never formed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pipelines" / "diagnostics" / "diag_signal_archaeology.py"


def _mod():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("diag_signal_archaeology", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _P(entries):
    """entries: {ticker: [(entry_day, crs, high, sma)]} -> a minimal prep_weekly_rank-shaped dict."""
    P = {}
    for t, rows in entries.items():
        dates = sorted({pd.Timestamp(d) for d, *_ in rows})
        idx = {d: i for i, d in enumerate(dates)}
        P[t] = {"dates": [d.to_numpy() for d in dates], "entry_win": {}}
        for d, crs, hi, sma in rows:
            P[t]["entry_win"][idx[pd.Timestamp(d)]] = ([idx[pd.Timestamp(d)]], 1.0, hi, crs, sma, 0)
    return P


# --------------------------------------------------------------------------- week arithmetic
def test_the_signal_week_is_the_week_before_the_entry_week():
    """entry_win is keyed by the ENTRY week's first day. Reading it as the signal week answers a
    different question by exactly one week — which is the whole subject of the HINDALCO case."""
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 110.0, 100.0)]})     # entry week Mon 3 Aug
    assert [r["ticker"] for r in m._signals_for_week(P, pd.Timestamp("2026-07-31"))] == ["AAA"]
    assert m._signals_for_week(P, pd.Timestamp("2026-08-07")) == []


@pytest.mark.parametrize("entry_day", ["2026-08-03", "2026-08-04", "2026-08-05"])
def test_any_weekday_entry_maps_back_to_the_same_friday(entry_day):
    m = _mod()
    P = _P({"AAA": [(entry_day, 0.5, 110.0, 100.0)]})
    got = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    assert len(got) == 1 and got[0]["signal_week_end"] == "2026-07-31"


# --------------------------------------------------------------------------- ranking
def test_signals_are_ranked_by_crs_and_the_top_five_are_grade_a():
    m = _mod()
    P = _P({f"T{i}": [("2026-08-03", 0.9 - i / 100, 110.0, 100.0)] for i in range(8)})
    rows = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    assert [r["crs_rank"] for r in rows] == list(range(1, 9))
    assert [r["grade"] for r in rows] == ["A"] * 5 + ["B"] * 3
    assert rows[0]["crs_dist"] > rows[-1]["crs_dist"]


def test_extension_is_reported_against_the_signal_week_sma():
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 112.0, 100.0)]})
    assert m._signals_for_week(P, pd.Timestamp("2026-07-31"))[0]["ext_at_high_pct"] == pytest.approx(12.0)


def test_a_zero_sma_does_not_divide_by_zero():
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 112.0, 0.0)]})
    assert m._signals_for_week(P, pd.Timestamp("2026-07-31"))[0]["ext_at_high_pct"] is None


# --------------------------------------------------------------------------- the verdict
def test_every_verdict_names_a_specific_gate_never_unknown():
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 110.0, 100.0)]})
    rows = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    week = pd.Timestamp("2026-07-31")
    cases = [
        ("ZZZ", {}, {}, "NOT IN UNIVERSE"),
        ("AAA", {"AAA": pd.DataFrame({"Close": [1.0]})}, {}, "INSUFFICIENT HISTORY"),
        ("AAA", {"AAA": pd.DataFrame({"Close": [1.0]})}, P, "GRADE A, NOT FUNDED"),
    ]
    for tkr, oh, pp, _ in cases:
        v = m._verdict(tkr, rows, pp, oh, None, week, set())
        assert v["gate"] and v["gate"] != "unknown" and v["detail"]

    iso = "%d-%02d" % m._iso("2026-08-03")          # the ENTRY week, which is how the ledger keys
    funded_key = {("AAA", iso)}
    assert m._verdict("AAA", rows, P, {"AAA": pd.DataFrame({"Close": [1.0]})}, None, week,
                      funded_key)["gate"] == "FUNDED"


def test_a_name_that_signalled_but_ranked_low_is_told_its_rank():
    m = _mod()
    P = _P({f"T{i}": [("2026-08-03", 0.9 - i / 100, 110.0, 100.0)] for i in range(8)})
    rows = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    oh = {t: pd.DataFrame({"Close": [1.0]}) for t in P}
    v = m._verdict("T7", rows, P, oh, None, pd.Timestamp("2026-07-31"), set())
    assert v["gate"] == "NOT GRADE A" and v["crs_rank"] == 8 and "ranked 8 of 8" in v["detail"]


def test_a_grade_a_name_that_was_not_funded_is_distinguished_from_one_that_was():
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 110.0, 100.0)]})
    rows = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    oh = {"AAA": pd.DataFrame({"Close": [1.0]})}
    v = m._verdict("AAA", rows, P, oh, None, pd.Timestamp("2026-07-31"), set())
    assert v["gate"] == "GRADE A, NOT FUNDED"
    assert "cash gate" in v["detail"], "the two remaining causes must be named, not merged"


def test_no_setup_is_distinguished_from_no_signal_row():
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 110.0, 100.0)]})
    oh = {"BBB": pd.DataFrame({"Close": [1.0]}), "AAA": pd.DataFrame({"Close": [1.0]})}
    P["BBB"] = {"dates": [pd.Timestamp("2026-08-03").to_numpy()], "entry_win": {}}
    v = m._verdict("BBB", m._signals_for_week(P, pd.Timestamp("2026-07-31")), P, oh, None,
                   pd.Timestamp("2026-07-31"), set())
    assert v["gate"] == "NO SETUP"


def test_funded_lookup_uses_the_entry_week_not_the_signal_week():
    """The capped ledger records `entry_date`. Keying the lookup on the SIGNAL week misses every
    funded trade by exactly one week — and would report the whole book as never bought."""
    m = _mod()
    P = _P({"AAA": [("2026-08-03", 0.5, 110.0, 100.0)]})
    rows = m._signals_for_week(P, pd.Timestamp("2026-07-31"))
    oh = {"AAA": pd.DataFrame({"Close": [1.0]})}
    entry_iso = "%d-%02d" % m._iso("2026-08-03")
    signal_iso = "%d-%02d" % m._iso("2026-07-31")
    assert entry_iso != signal_iso, "the fixture must straddle a week boundary or it proves nothing"

    hit = m._verdict("AAA", rows, P, oh, None, pd.Timestamp("2026-07-31"), {("AAA", entry_iso)})
    assert hit["gate"] == "FUNDED"
    miss = m._verdict("AAA", rows, P, oh, None, pd.Timestamp("2026-07-31"), {("AAA", signal_iso)})
    assert miss["gate"] == "GRADE A, NOT FUNDED", "signal-week keys must NOT register as funded"
