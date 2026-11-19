"""PIT / schema / NaN-not-zero guards for nq.data.results_xbrl (style of tests/test_earnings_pit.py).

Fixtures are synthetic: three hand-written XBRL-shaped instances (no NSE data in git).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.results_xbrl import (
    SCHEMA,
    VALUE_FIELDS,
    as_of,
    assign_filing_seq,
    latest_per_period,
    parse_xbrl,
)


def _xbrl(sym, qs, qe, ys, ye, rev, pat, eps, nature="Standalone", rev_text=None, bs=None, with_ctx=True):
    rev_text = rev_text if rev_text is not None else str(rev)
    ctx = ""
    if with_ctx:
        ctx = (f'<xbrli:context id="OneD"><xbrli:entity><xbrli:identifier scheme="x">{sym}</xbrli:identifier>'
               f'</xbrli:entity><xbrli:period><xbrli:startDate>{qs}</xbrli:startDate><xbrli:endDate>{qe}'
               f'</xbrli:endDate></xbrli:period></xbrli:context>'
               f'<xbrli:context id="OneI"><xbrli:entity><xbrli:identifier scheme="x">{sym}</xbrli:identifier>'
               f'</xbrli:entity><xbrli:period><xbrli:instant>{qe}</xbrli:instant></xbrli:period></xbrli:context>')
    bs_xml = f'<f:Equity contextRef="OneI" unitRef="INR" decimals="-5">{bs}</f:Equity>' if bs is not None else ""
    return (f'<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:f="urn:f">{ctx}'
            f'<f:Symbol contextRef="OneD">{sym}</f:Symbol>'
            f'<f:DateOfStartOfReportingPeriod contextRef="OneD">{qs}</f:DateOfStartOfReportingPeriod>'
            f'<f:DateOfEndOfReportingPeriod contextRef="OneD">{qe}</f:DateOfEndOfReportingPeriod>'
            f'<f:NatureOfReportStandaloneConsolidated contextRef="OneD">{nature}</f:NatureOfReportStandaloneConsolidated>'
            f'<f:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-5">{rev_text}</f:RevenueFromOperations>'
            f'<f:ProfitLossForPeriod contextRef="OneD" unitRef="INR" decimals="-5">{pat}</f:ProfitLossForPeriod>'
            f'<f:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="OneD" unitRef="INRPerShare"'
            f' decimals="INF">{eps}</f:BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations>'
            f'<f:DateOfStartOfReportingPeriod contextRef="FourD">{ys}</f:DateOfStartOfReportingPeriod>'
            f'<f:DateOfEndOfReportingPeriod contextRef="FourD">{ye}</f:DateOfEndOfReportingPeriod>'
            f'<f:NatureOfReportStandaloneConsolidated contextRef="FourD">{nature}</f:NatureOfReportStandaloneConsolidated>'
            f'<f:ProfitLossForPeriod contextRef="FourD" unitRef="INR" decimals="-5">{pat * 2}</f:ProfitLossForPeriod>'
            f'{bs_xml}</xbrli:xbrl>').encode()


# three synthetic filings: AAA Q2 original, AAA Q2 revision, BBB Q2 with no <context> elements
FILINGS = [
    ("u1", "2024-11-08 16:05:00", _xbrl("AAA", "2024-07-01", "2024-09-30", "2024-04-01", "2024-09-30",
                                         1_000_000, 100_000, 1.5, bs=9_000_000)),
    ("u2", "2024-11-20 10:00:00", _xbrl("AAA", "2024-07-01", "2024-09-30", "2024-04-01", "2024-09-30",
                                         1_000_000, 110_000, 1.65, bs=9_000_000)),
    ("u3", "2024-11-12 09:00:00", _xbrl("BBB", "2024-07-01", "2024-09-30", "2024-04-01", "2024-09-30",
                                         0, 50, 0.1, nature="Consolidated", rev_text="-", with_ctx=False)),
]


def _build(filings) -> pd.DataFrame:
    rows = []
    for url, ts, x in filings:
        for r in parse_xbrl(x):
            r.update(broadcast_ts=pd.Timestamp(ts), xbrl_url=url, listing="synthetic")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ("period_start", "period_end"):
        df[c] = pd.to_datetime(df[c])
    return assign_filing_seq(df)[SCHEMA]


def test_schema_and_contexts():
    df = _build(FILINGS)
    assert list(df.columns) == SCHEMA
    a = df[(df.symbol == "AAA") & (df.xbrl_url == "u1")].set_index("context_role")
    assert a.loc["current", "period_type"] == "Q" and a.loc["ytd", "period_type"] == "H"
    assert a.loc["current", "eps_basic"] == 1.5
    assert a.loc["current", "revenue_ops"] == 1_000_000          # INR fact is already rupees
    assert a.loc["current", "bs_total_equity"] == 9_000_000      # instant at period end, current row
    assert np.isnan(a.loc["ytd", "bs_total_equity"])             # never copied to the ytd row
    b = df[(df.symbol == "BBB") & (df.context_role == "current")].iloc[0]
    assert bool(b["consolidated"]) is True
    assert b["period_end"] == pd.Timestamp("2024-09-30")          # dates from facts, no <context>


def test_nan_not_zero_with_reason():
    df = _build(FILINGS)
    b = df[(df.symbol == "BBB") & (df.context_role == "current")].iloc[0]
    assert np.isnan(b["revenue_ops"]) and b["revenue_ops__reason"] == "parse"   # "-" text
    assert np.isnan(b["finance_costs"]) and b["finance_costs__reason"] == "absent"
    for f in VALUE_FIELDS:
        assert pd.notna(b[f"{f}__reason"]) == bool(np.isnan(b[f])), f   # NaN iff a reason code


def test_revision_is_a_separate_row():
    df = _build(FILINGS)
    a = df[(df.symbol == "AAA") & (df.context_role == "current")].sort_values("broadcast_ts")
    assert list(a["filing_seq"]) == [0, 1] and list(a["is_revision"]) == [False, True]
    assert list(a["pat"]) == [100_000, 110_000]                   # original not overwritten
    assert latest_per_period(df, "2024-11-15")[lambda d: (d.symbol == "AAA") & (d.context_role == "current")
                                                ]["pat"].item() == 100_000
    assert latest_per_period(df, "2024-11-21")[lambda d: (d.symbol == "AAA") & (d.context_role == "current")
                                                ]["pat"].item() == 110_000


def test_unbroadcast_filing_is_invisible():
    df = _build(FILINGS)
    assert len(as_of(df, "2024-11-08 16:04:59")) == 0
    assert set(as_of(df, "2024-11-08 16:05:00")["xbrl_url"]) == {"u1"}       # inclusive at the second


def test_truncation_invariance():
    full = _build(FILINGS)
    T = pd.Timestamp("2024-11-15")
    trunc = _build([f for f in FILINGS if pd.Timestamp(f[1]) <= T])
    for asof in ["2024-11-01", "2024-11-08 16:05:00", "2024-11-12", T]:
        for fn in (as_of, latest_per_period):
            a = fn(full, asof).sort_values(["xbrl_url", "context_id"]).reset_index(drop=True)
            b = fn(trunc, asof).sort_values(["xbrl_url", "context_id"]).reset_index(drop=True)
            pd.testing.assert_frame_equal(a, b)
