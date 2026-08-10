"""Point-in-time equity F&O membership from the NSE bhavcopies.

The failure mode this guards is silent. A universe pinned to *today's* F&O list looks complete, runs
without error, and quietly deletes every name that left the segment — survivorship through a
different door than the one the daily store already paid for. So the tests that matter are the ones
about names that LEAVE: `members_on` must not see a joiner early, must not keep a leaver late, and
`membership_spans` must make the leavers findable.
"""
from __future__ import annotations

import pandas as pd
import pytest

from nq.data.fo_universe import (build_membership, members_on, membership_spans, parse_fo_members)


def _old(rows: list[tuple[str, str]]) -> pd.DataFrame:
    """OLD schema: INSTRUMENT / SYMBOL."""
    return pd.DataFrame({"INSTRUMENT": [i for i, _ in rows], "SYMBOL": [s for _, s in rows],
                         "CLOSE": [1.0] * len(rows)})


def _udiff(rows: list[tuple[str, str]]) -> pd.DataFrame:
    """UDiFF schema: FinInstrmTp / TckrSymb."""
    return pd.DataFrame({"FinInstrmTp": [i for i, _ in rows], "TckrSymb": [s for _, s in rows],
                         "ClsPric": [1.0] * len(rows)})


# --------------------------------------------------------------------------- parsing
def test_old_schema_keeps_only_single_stock_futures():
    df = _old([("FUTSTK", "RELIANCE"), ("FUTSTK", "TCS"), ("OPTSTK", "INFY"),
               ("FUTIDX", "NIFTY"), ("OPTIDX", "NIFTY")])
    assert parse_fo_members(df, "2019-06-03") == {"RELIANCE", "TCS"}


def test_udiff_schema_keeps_only_single_stock_futures():
    df = _udiff([("STF", "RELIANCE"), ("STO", "INFY"), ("IDF", "NIFTY"), ("IDO", "NIFTY")])
    assert parse_fo_members(df, "2025-06-03") == {"RELIANCE"}


def test_index_names_never_enter_the_equity_universe():
    """NIFTY is an index, not a tradable equity. Its presence in every bhavcopy makes this the
    easiest way to contaminate the universe."""
    for df in (_old([("FUTIDX", "NIFTY"), ("OPTIDX", "BANKNIFTY")]),
               _udiff([("IDF", "NIFTY"), ("IDO", "BANKNIFTY")])):
        assert parse_fo_members(df, "2020-01-01") == set()


def test_symbols_are_normalised_and_blanks_dropped():
    df = _old([("FUTSTK", " reliance "), ("FUTSTK", "TCS"), ("FUTSTK", "   ")])
    assert parse_fo_members(df, "2019-06-03") == {"RELIANCE", "TCS"}


@pytest.mark.parametrize("df", [None, pd.DataFrame(),
                                pd.DataFrame({"SOMETHING_ELSE": [1]}),
                                pd.DataFrame({"INSTRUMENT": ["FUTSTK"]})])       # no SYMBOL column
def test_unusable_input_is_an_empty_set_not_an_exception(df):
    assert parse_fo_members(df, "2019-06-03") == set()


# --------------------------------------------------------------------------- the panel
def test_build_membership_is_dated_sorted_and_unique():
    panel = build_membership({
        "2019-06-03": _old([("FUTSTK", "A"), ("FUTSTK", "B"), ("FUTSTK", "A")]),   # dup in-file
        "2019-06-04": _old([("FUTSTK", "B")]),
    })
    assert list(panel.columns) == ["date", "symbol"]
    assert len(panel) == 3
    assert panel["date"].is_monotonic_increasing
    assert not panel.duplicated().any()


def test_build_membership_spans_both_vendor_schemas():
    panel = build_membership({"2019-06-03": _old([("FUTSTK", "OLDNAME")]),
                              "2025-06-03": _udiff([("STF", "NEWNAME")])})
    assert set(panel["symbol"]) == {"OLDNAME", "NEWNAME"}


def test_empty_input_yields_an_empty_typed_frame():
    panel = build_membership({})
    assert panel.empty and list(panel.columns) == ["date", "symbol"]
    assert members_on(panel, "2020-01-01") == set()


# --------------------------------------------------------------------------- PIT behaviour
def _panel():
    return build_membership({
        "2019-06-03": _old([("FUTSTK", "STAYER"), ("FUTSTK", "LEAVER")]),
        "2019-06-04": _old([("FUTSTK", "STAYER"), ("FUTSTK", "LEAVER")]),
        "2019-06-05": _old([("FUTSTK", "STAYER")]),                    # LEAVER exits
        "2019-06-06": _old([("FUTSTK", "STAYER"), ("FUTSTK", "JOINER")]),
    })


def test_a_joiner_is_not_visible_before_it_joins():
    assert "JOINER" not in members_on(_panel(), "2019-06-05")
    assert "JOINER" in members_on(_panel(), "2019-06-06")


def test_a_leaver_is_not_carried_forward_past_its_exit():
    p = _panel()
    assert "LEAVER" in members_on(p, "2019-06-04")
    assert "LEAVER" not in members_on(p, "2019-06-05"), "the exit must be visible immediately"


def test_a_non_session_date_sees_the_last_session_in_force():
    """A holiday or a weekend must not empty the universe — it carries the prior session forward."""
    p = _panel()
    assert members_on(p, "2019-06-08") == members_on(p, "2019-06-06") == {"STAYER", "JOINER"}


def test_a_date_before_the_panel_starts_is_empty_not_the_first_session():
    assert members_on(_panel(), "2018-01-01") == set()


# --------------------------------------------------------------------------- leavers are findable
def test_membership_spans_exposes_the_names_that_left():
    spans = membership_spans(_panel()).set_index("symbol")
    assert spans.loc["LEAVER", "last"] == pd.Timestamp("2019-06-04")
    assert spans.loc["STAYER", "last"] == pd.Timestamp("2019-06-06")
    assert spans.loc["LEAVER", "n_sessions"] == 2
    leavers = spans[spans["last"] < spans["last"].max()].index.tolist()
    assert leavers == ["LEAVER"], "a universe pinned to the final session would silently drop these"


def test_membership_spans_of_an_empty_panel_is_an_empty_typed_frame():
    out = membership_spans(pd.DataFrame(columns=["date", "symbol"]))
    assert out.empty and list(out.columns) == ["symbol", "first", "last", "n_sessions"]
