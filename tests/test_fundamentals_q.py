import numpy as np
import pandas as pd

from nq.data.fundamentals_q import build_panel


def _row(sym, qend, bcast, cons=True, pat=100.0, eps=1.0, pue=1000.0, fv=10.0, span=1, role="current", url=None,
         exc=0.0, rev=1000.0):
    end = pd.Timestamp(qend)
    start = (end - pd.offsets.QuarterEnd(span)) + pd.Timedelta(days=1)
    return {"symbol": sym, "isin": "IN" + sym, "period_start": start, "period_end": end, "consolidated": cons,
            "context_role": role, "broadcast_ts": pd.Timestamp(bcast), "xbrl_url": url or f"{sym}{qend}{bcast}{cons}",
            "lag_days": 40, "period_flag": None, "revenue_ops": rev, "total_income": rev, "pat": pat,
            "exceptional_items": exc, "paid_up_equity": pue, "face_value": fv, "eps_basic": eps,
            "revenue_ops__tag": "RevenueFromOperations"}


def _co(sym="AAA", n=8, cons=True, **kw):
    q = pd.date_range("2020-06-30", periods=n, freq="QE")
    return [_row(sym, e.date(), (e + pd.Timedelta(days=45)).date(), cons=cons, **kw) for e in q]


def test_truncation_pit():
    df = pd.DataFrame(_co(n=8) + _co("BBB", n=8))
    full = build_panel(df)
    cut = pd.Timestamp("2021-06-01")
    trunc = build_panel(df[df.broadcast_ts <= cut])
    a = full[full.broadcast_ts <= cut].drop(columns="nan_reason").reset_index(drop=True)
    b = trunc.drop(columns="nan_reason").reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def test_basis_never_mixed():
    rows = _co(n=10, cons=False) + _co(n=10, cons=True)[:9]  # consolidated in 9/10 quarters -> consolidated
    rows += _co("SSS", n=10, cons=False) + _co("SSS", n=10, cons=True)[:5]  # 5/10 -> standalone
    p = build_panel(pd.DataFrame(rows))
    assert p.groupby("company")["basis"].nunique().max() == 1
    assert p.loc[p.symbol == "AAA", "basis"].iat[0] == "consolidated"
    assert p.loc[p.symbol == "SSS", "basis"].iat[0] == "standalone"


def test_bonus_adjustment_synthetic():
    rows = _co(n=8)
    for r in rows[4:]:  # 1:1 bonus: paid-up shares double, PAT unchanged
        r["paid_up_equity"] = 2000.0
        r["eps_basic"] = 0.5
    p = build_panel(pd.DataFrame(rows))
    assert p["split_event"].sum() == 1
    assert np.allclose(p["adj_core_eps"], p["adj_core_eps"].iat[0])  # continuous across the bonus
    assert p["share_factor"].iloc[:4].eq(1).all() and p["share_factor"].iloc[4:].eq(2).all()


def test_rights_issue_not_adjusted():
    rows = _co(n=6)
    for r in rows[3:]:
        r["paid_up_equity"] = 1170.0  # 17% dilution: real, not a split
    p = build_panel(pd.DataFrame(rows))
    assert p["split_event"].sum() == 0


def test_nan_not_zero():
    rows = _co(n=6)
    rows[2]["pat"] = np.nan
    p = build_panel(pd.DataFrame(rows))
    assert p["pat"].isna().sum() == 1 and (p["pat"] == 0).sum() == 0
    assert p["ttm_pat"].isna().all()  # every TTM window touching the missing quarter, plus the first 3
    assert p["nan_reason"].iat[2].startswith("pat_missing")


def test_q4_derived_from_fy_minus_9m():
    rows = [_row("AAA", "2021-06-30", "2021-08-10"), _row("AAA", "2021-09-30", "2021-11-10"),
            _row("AAA", "2021-12-31", "2022-02-10")]
    rows.append(_row("AAA", "2021-12-31", "2022-02-10", span=3, role="ytd", pat=300.0, url=rows[-1]["xbrl_url"]))
    rows.append(_row("AAA", "2022-03-31", "2022-05-20", span=4, role="current", pat=450.0))  # FY only
    p = build_panel(pd.DataFrame(rows))
    q4 = p[p.fiscal_quarter_end == "2022-03-31"].iloc[0]
    assert q4["derived"] and q4["pat"] == 150.0 and np.isnan(q4["eps_basic"])


def test_first_tradable_session_rule():
    from nq.data.fundamentals_q import first_tradable_session
    sess = pd.DatetimeIndex(["2024-01-05", "2024-01-08", "2024-01-09"])  # Fri, Mon, Tue
    ts = pd.Series(pd.to_datetime(["2024-01-05 08:00", "2024-01-05 12:00", "2024-01-05 15:30",
                                   "2024-01-06 10:00", "2024-01-09 16:00"]))
    got = first_tradable_session(ts, sess).dt.strftime("%Y-%m-%d").fillna("NaT").tolist()
    assert got == ["2024-01-05", "2024-01-05", "2024-01-08", "2024-01-08", "NaT"]
