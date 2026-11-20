import numpy as np
import pandas as pd
import pytest

from nq.data import risk_features as RF
from nq.research.holdout import HoldoutViolation


def _mkt(n=700, k=12, start="2022-01-03", seed=0):
    idx = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(seed)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (n, k)), axis=0)), index=idx,
                         columns=[f"S{i}" for i in range(k)])
    vol = pd.DataFrame(1e5, index=idx, columns=close.columns)
    mem = pd.DataFrame(True, index=idx, columns=close.columns)
    return close, vol, mem


def test_price_family_pit_truncation():
    c, v, m = _mkt()
    d = RF.fridays(c.index)[60:80]
    full = RF.price_features(c, v, m, d)
    cut = d[10]
    tr = RF.price_features(c.loc[:cut], v.loc[:cut], m.loc[:cut], d[d <= cut])
    pd.testing.assert_frame_equal(full.loc[d[d <= cut]], tr, check_freq=False)


def test_band_family_pit_and_nan_before_source():
    c, _, _ = _mkt()
    sess, syms = c.index, list(c.columns)
    hit = pd.DataFrame({"date": sess[300:310], "symbol": "S1", "series": "EQ", "side": "L"})
    bands = pd.DataFrame({"date": np.repeat(sess[300:400:5], 2), "symbol": ["S1", "S2"] * 20, "series": "EQ",
                          "band_pct": 5.0, "remarks": ["GSM Stage - II", "-"] * 20})
    d = RF.fridays(sess)
    f = RF.band_features(hit, bands, sess, d, syms)
    before = f.loc[d[d < sess[300]]]
    assert before["band_pct"].isna().all() and before["lo_hits63"].isna().all()  # unknown, not zero
    cut = sess[350]
    tr = RF.band_features(hit[hit.date <= cut], bands[bands.date <= cut], sess[sess <= cut], d[d <= cut], syms)
    pd.testing.assert_frame_equal(f.loc[d[d <= cut]], tr, check_freq=False)
    assert f.xs("S1", level="symbol")["gsm_stage"].dropna().max() == 3.0


def test_asm_and_pledge_pit():
    c, _, _ = _mkt()
    d = RF.fridays(c.index)
    syms = ["S1", "S2"]
    ev = pd.DataFrame({"symbol": ["S1", "S1"], "date": [c.index[100], c.index[200]], "stage": [11.0, 0.0]})
    a = RF.asm_features(ev, d, syms)
    cut = c.index[150]
    a2 = RF.asm_features(ev[ev.date <= cut], d[d <= cut], syms)
    pd.testing.assert_frame_equal(a.loc[d[d <= cut]], a2, check_freq=False)
    pl = pd.DataFrame({"symbol": "S1", "broadcast_ts": [c.index[100] + pd.Timedelta(hours=16), c.index[200]],
                       "pledge_pct": [10.0, 25.0]})
    p = RF.pledge_features(pl, d, syms, source_start="2021-01-01")
    s1 = p.xs("S1", level="symbol")
    friday_after_close = s1.index[s1.index >= c.index[100]][0]
    if friday_after_close == c.index[100]:  # broadcast after 15:30 on a Friday is not known at that close
        assert np.isnan(s1.loc[friday_after_close, "pledge_pct"])
    assert s1["pledge_pct"].max() == 25.0 and s1["pledge_chg_1q"].dropna().iloc[-1] == 15.0
    assert p.xs("S2", level="symbol")["pledge_pct"].isna().all()  # NaN, never zero
    assert p.xs("S2", level="symbol")["pledge_declared_none"].isna().all()  # no filing known: unknown, not 0


def test_fundamental_family_validity_window():
    d = RF.fridays(pd.bdate_range("2023-01-02", "2024-12-31"))
    view = pd.DataFrame({"company": "C1", "broadcast_ts": pd.to_datetime(["2023-05-20"]), "ttm_pbt": [100.0],
                         "ttm_finance_costs": [0.0], "ttm_core_pat": [-5.0], "ttm_core_pat_chg4": [1.0], "lag_days": [130]})
    bs = pd.DataFrame({"company": "C1", "period_end": pd.to_datetime(["2023-03-31"]),
                       "broadcast_ts": pd.to_datetime(["2023-05-20"]), "borrowings_current": [50.0],
                       "borrowings_noncurrent": [50.0], "total_equity": [200.0]})
    f = RF.fundamental_features(view, bs, d, {"S1": "C1"}).xs("S1", level="symbol")
    assert np.isnan(f.loc[f.index < "2023-05-20", "de_ratio"]).all()
    assert (f.loc["2023-06-01":"2023-12-31", "de_ratio"] == 0.5).all()
    assert f.loc[f.index > "2024-01-15", "de_ratio"].isna().all()  # past next deadline (Sep + 45d) + 60d
    assert f["int_cover"].isna().all()                              # finance costs 0 -> NaN, not inf/zero
    assert f.loc["2023-06-01":, "late_filer"].eq(1).all() and f.loc["2023-06-01":, "ttm_core_pat_pos"].eq(0).all()


def test_label_never_past_train_end():
    c, _, m = _mkt(n=900, start="2021-06-01")
    d = RF.fridays(c.index)
    beta = pd.DataFrame(1.0, index=d, columns=c.columns)
    lab = RF.crash_label(c, m, beta, d)
    have = lab.dropna().index.get_level_values("date")
    last_exit = c.index[c.index.get_indexer([have.max()])[0] + RF.H_LABEL]
    assert last_exit <= pd.Timestamp("2024-06-30")
    with pytest.raises(HoldoutViolation):
        RF.crash_label(c, m, beta, d, unseal_token="not-a-token")


def test_pledge_missing_field_is_nan_with_reason():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipelines" / "build"))
    import build_risk_features as B
    ctx = ('<xbrli:context id="P"><xbrli:scenario><xbrldi:explicitMember dimension="a:CategoryOfShareholdersAxis">'
           'a:ShareholdingOfPromoterAndPromoterGroupMember</xbrldi:explicitMember></xbrli:scenario></xbrli:context>')
    filed0 = ctx + '<a:NumberOfShares contextRef="P">100</a:NumberOfShares><a:PledgedOrEncumberedNumberOfShares contextRef="P">0</a:PledgedOrEncumberedNumberOfShares>'
    blank = ctx + '<a:NumberOfShares contextRef="P">100</a:NumberOfShares><a:PledgedOrEncumberedNumberOfShares contextRef="P"></a:PledgedOrEncumberedNumberOfShares>'
    flag = ctx + ('<a:NumberOfShares contextRef="P">100</a:NumberOfShares>'
                  '<a:WhetherAnySharesHeldByPromotersArePledgeOrOtherwiseEncumbered contextRef="X">false'
                  '</a:WhetherAnySharesHeldByPromotersArePledgeOrOtherwiseEncumbered>')
    assert B.parse_pledge(filed0) == (0.0, "filed_number")
    new = ctx + ('<a:NumberOfShares contextRef="P">200</a:NumberOfShares>'
                 '<a:NumberOfSharesEncumbered contextRef="P">30</a:NumberOfSharesEncumbered>')
    assert B.parse_pledge(new) == (15.0, "filed_number")
    new_pct = ctx + '<a:EncumberedSharesHeldAsPercentageOfTotalNumberOfShares contextRef="P">0.1553</a:EncumberedSharesHeldAsPercentageOfTotalNumberOfShares>'
    assert B.parse_pledge(new_pct)[0] == pytest.approx(15.53)
    new_flag = ctx + ('<a:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup contextRef="X">'
                      'false</a:WhetherAnySharesHeldByPromotersAreEncumberedUnderPledgedForPromoterAndPromoterGroup>')
    assert B.parse_pledge(new_flag)[1] == "flag_false_no_field" and np.isnan(B.parse_pledge(new_flag)[0])
    for xml, why in ((blank, "blank_field"), (flag, "flag_false_no_field"), (ctx, "missing_field")):
        v, r = B.parse_pledge(xml)
        assert np.isnan(v) and r == why
    c, _, _ = _mkt()
    d = RF.fridays(c.index)
    pl = pd.DataFrame({"symbol": "S1", "broadcast_ts": [c.index[100]], "pledge_pct": [np.nan],
                       "reason": ["flag_false_no_field"]})
    p = RF.pledge_features(pl, d, ["S1"], source_start="2021-01-01").xs("S1", level="symbol")
    after = p[p.index > c.index[100]]
    assert after["pledge_pct"].isna().all() and (after["pledge_reason"] == "flag_false_no_field").all()


def test_asm_known_from_publication_strictly_before_friday():
    d = RF.fridays(pd.bdate_range("2024-01-01", "2024-03-29"))
    f = d[3]
    ev = pd.DataFrame({"symbol": ["S1", "S2"], "date": [f, f - pd.Timedelta(days=1)],
                       "eff_date": [f + pd.Timedelta(days=3), f + pd.Timedelta(days=3)], "stage": [21.0, 11.0]})
    a = RF.asm_features(pd.concat([ev, pd.DataFrame({"symbol": ["S3"], "date": [d[0] - pd.Timedelta(days=7)],
                                                     "eff_date": [d[0]], "stage": [0.0]})]), d, ["S1", "S2"])
    assert a.loc[(f, "S1"), "asm_stage"] == 0.0           # published on the Friday itself: not known at its close
    assert a.loc[(f, "S2"), "asm_stage"] == 11.0          # published Thursday: known, though effective Monday
    assert a.loc[(f, "S2"), "asm_days_in_stage"] == -3.0  # known but not yet in force
    assert a.loc[(d[4], "S1"), "asm_stage"] == 21.0
