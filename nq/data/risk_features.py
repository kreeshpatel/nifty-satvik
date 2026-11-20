"""L5 crash-risk feature and label panel: one row per (symbol, week-end Friday) for PIT Nifty 500 members.

Data engineering only: no model is fitted, and no feature-label statistic is computed. Every feature is known at
that Friday's close. Each family is a pure function of its inputs, so the PIT truncation tests can rebuild it on
truncated data.

**Dates and universe**
- "Friday" means the last session of each W-FRI week.
- Universe: PIT Nifty 500 members on that session.

**Price**, from the cleaned close and volume:
- `rv63`, `rv126`: annualised standard deviation of daily log returns.
- `dvol126`: downside volatility, sqrt(mean(min(r, 0)²)) × √252.
- `beta126`, `dbeta126`: OLS slope against the equal-weight member return; the downside beta uses only days the
  market fell.
- `mdd252`: worst peak-to-trough of the close over 252 sessions.
- `n_down5_252`: count of daily returns at or below −5%.
- `adv20_cr`, `adv60_cr`: mean traded value, in ₹ crore.

**Bands**, from NSE band files:
- `lo_hits63`, `lo_hits252`, `up_hits63`, `up_hits252`: lower- and upper-band hits in EQ series.
- `band_pct`: the price band in force in the latest band file on or before the Friday.
- NaN before the first band file (2019-12-30); an F&O name with no band is NaN too.

**Surveillance**
- `gsm_stage`: from the band file's Remarks. 0 = not under GSM; GSM stage k (0, I..VI) is coded k + 1.
- `asm_stage`: from the circulars' consolidated lists. 0 = on neither list; 10+k = short-term ASM stage k;
  20+k = long-term ASM stage k (the higher code wins). A circular counts as known at a Friday close only if its
  publication date is strictly before that Friday (NSE gives a date, not a time).
- `asm_days_in_stage`: Friday − the effective (w.e.f.) date of the current stage; negative = known, not yet in force.

**Pledge**, from shareholding XBRL from 2021 onward:
- `pledge_pct`: promoter shares pledged as % of promoter holding.
- `pledge_chg_1q`: change since the previous filing.
- Known from the filing's broadcast timestamp (counts if it is at or before 15:30 on the Friday).
- NaN is never 0. `pledge_reason` says why a value is NaN: "pre_2021_source"; "no_filing_known"; or the filing's
  own code ("flag_true_no_field", "blank_field", "missing_field", "no_promoter_context").
- A filing whose promoter yes/no flags all say "no pledge" and that files no number counts as 0 (an explicit
  declaration, owner decision 2026-11-20); `pledge_declared_none` = 1 marks it.

**Fundamentals**, from the Phase 0 feature view; the latest filing broadcast by the Friday's 15:30 close:
- `de_ratio`: (current + non-current borrowings) ÷ total equity, from half-year and year-end balance sheets.
  - It is valid until the next scheduled balance-sheet filing (the next half-year end + 45 days, or + 60 days for a
    March year end), plus 60 days. After that it is NaN.
- `int_cover`: (TTM PBT + TTM finance costs) ÷ TTM finance costs, where TTM finance costs > 0.
- `ttm_core_pat_pos`: 1 if TTM core PAT is above 0, 0 if it is at or below 0.
- `ttm_core_pat_chg4`: as in the panel.
- `last_lag_days`, `late_filer`: lag of the last filing; late_filer = lag over 120 days.

**Label** (separate column, training window only)
- Over the next 63 sessions after the Friday, the stock-specific path is the cumulative product of
  (1 + r_stock − beta126 × r_EW) − 1.
- `label_crash` = 1 if that path's minimum is at or below −25%.
- A label is computed only when its 63rd session is on or before 2024-06-30; the holdout guard is asserted on
  those exit dates.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from nq.research.holdout import TRAIN_END, assert_pre_holdout

H_LABEL = 63
CRASH = -0.25
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def fridays(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(s.groupby(idx.to_period("W-FRI")).max().values)


def _stack(df: pd.DataFrame, name: str) -> pd.Series:
    s = df.stack(future_stack=True)
    s.index.names = ["date", "symbol"]
    return s.rename(name)


# ------------------------------------------------------------------------------------------------ price
def price_features(close: pd.DataFrame, volume: pd.DataFrame, member: pd.DataFrame,
                   dates: pd.DatetimeIndex) -> pd.DataFrame:
    r = np.log(close).diff()
    rs = close.pct_change(fill_method=None)
    mk = rs.where(member).mean(axis=1)
    out = {}
    for w in (63, 126):
        out[f"rv{w}"] = r.rolling(w, min_periods=int(w * 0.8)).std() * np.sqrt(252)
    out["dvol126"] = np.sqrt((r.clip(upper=0) ** 2).rolling(126, min_periods=100).mean()) * np.sqrt(252)
    mv = mk.rolling(126, min_periods=100).var()
    cov = rs.rolling(126, min_periods=100).cov(mk)
    out["beta126"] = cov.div(mv, axis=0)
    dn = mk.where(mk < 0)
    rd = rs.where(mk < 0, axis=0)
    out["dbeta126"] = rd.rolling(126, min_periods=40).cov(dn).div(dn.rolling(126, min_periods=40).var(), axis=0)
    peak = close.rolling(252, min_periods=200).max()
    dd = close / peak - 1
    out["mdd252"] = dd.rolling(252, min_periods=200).min()
    out["n_down5_252"] = (rs <= -0.05).astype(float).where(rs.notna()).rolling(252, min_periods=200).sum()
    tv = close * volume
    out["adv20_cr"] = tv.rolling(20, min_periods=15).mean() / 1e7
    out["adv60_cr"] = tv.rolling(60, min_periods=45).mean() / 1e7
    mem = member.reindex(dates)
    return pd.concat([_stack(v.reindex(dates).where(mem), k) for k, v in out.items()], axis=1)


# ------------------------------------------------------------------------------------------------ bands + GSM
def gsm_stage_from_remarks(remarks: pd.Series) -> pd.Series:
    m = remarks.fillna("").astype(str).str.upper().str.extract(r"GSM[^A-Z0-9]*(?:STAGE)?[^A-Z0-9]*([IVX]+|\d)")[0]
    st = m.map(lambda x: ROMAN.get(x, int(x) if isinstance(x, str) and x.isdigit() else np.nan))
    has = remarks.fillna("").astype(str).str.upper().str.contains("GSM")
    # 0 = not under GSM; GSM stage k (0..VI) -> k + 1, so GSM stage 0 is distinct from "not listed";
    # GSM named without a parseable stage -> 1
    return (st + 1).where(has, 0.0).where(~(has & st.isna()), 1.0)


def band_features(hitters: pd.DataFrame, bands: pd.DataFrame, sessions: pd.DatetimeIndex,
                  dates: pd.DatetimeIndex, symbols) -> pd.DataFrame:
    """hitters: date, symbol, series, side (H/L). bands: date, symbol, series, band_pct, remarks (optional)."""
    h = hitters[hitters["series"] == "EQ"]
    h_first = hitters["date"].min()
    out = {}
    for side, nm in (("L", "lo"), ("H", "up")):
        x = h[h["side"] == side].assign(v=1.0).pivot_table(index="date", columns="symbol", values="v", aggfunc="sum")
        x = x.reindex(index=sessions, columns=symbols).fillna(0.0)
        x.loc[sessions < h_first] = np.nan          # no hitter file yet: unknown, not zero
        for w in (63, 252):
            out[f"{nm}_hits{w}"] = x.rolling(w, min_periods=w).sum()
    b = bands[bands["series"] == "EQ"]
    files = pd.DatetimeIndex(sorted(b["date"].unique()))
    pos = files.searchsorted(dates, side="right") - 1
    pre = pos < 0
    asof_file = files[np.clip(pos, 0, None)]
    bp = b.pivot_table(index="date", columns="symbol", values="band_pct", aggfunc="last")
    band = bp.reindex(index=files, columns=symbols).reindex(asof_file).set_axis(dates)
    if "remarks" in b:
        g = b.assign(gsm=gsm_stage_from_remarks(b["remarks"])).pivot_table(index="date", columns="symbol",
                                                                           values="gsm", aggfunc="last")
        gsm = g.reindex(index=files, columns=symbols).fillna(0.0).reindex(asof_file).set_axis(dates)
    else:
        gsm = pd.DataFrame(np.nan, index=dates, columns=symbols)
    band.loc[pre] = np.nan
    gsm.loc[pre] = np.nan
    res = [_stack(v.reindex(dates), k) for k, v in out.items()]
    res += [_stack(band, "band_pct"), _stack(gsm, "gsm_stage")]
    return pd.concat(res, axis=1)


# ------------------------------------------------------------------------------------------------ ASM
def asm_features(events: pd.DataFrame, dates: pd.DatetimeIndex, symbols) -> pd.DataFrame:
    """events: symbol, date (publication date: when the stage became known), optional eff_date (when it applies to
    trading; defaults to date), stage (0 = out, >0 = stage).

    - NSE stamps circulars with a date only. A circular dated D may be issued after the 15:30 close, so it counts as
      known at a Friday close only if D is strictly before that Friday.
    - asm_days_in_stage = Friday - eff_date. It is negative when the stage is known but not yet in force.
    - Before the first circular every value is NaN (unknown, not zero).
    """
    out_s = pd.DataFrame(np.nan, index=dates, columns=symbols)
    out_d = pd.DataFrame(np.nan, index=dates, columns=symbols)
    if len(events):
        ev = events.sort_values("date", kind="stable")
        eff_col = "eff_date" if "eff_date" in ev else "date"
        for s, g in ev.groupby("symbol"):
            if s not in out_s.columns:
                continue
            pos = g["date"].searchsorted(dates, side="left") - 1          # strictly before the Friday
            st = np.where(pos >= 0, g["stage"].to_numpy()[np.clip(pos, 0, None)], 0.0)
            start = np.where(pos >= 0, g[eff_col].to_numpy()[np.clip(pos, 0, None)], np.datetime64("NaT"))
            out_s[s] = st
            out_d[s] = (dates.to_numpy() - start) / np.timedelta64(1, "D")
        out_s = out_s.fillna(0.0)
        out_s.loc[dates <= ev["date"].min()] = np.nan
        out_d = out_d.where(out_s > 0)
    return pd.concat([_stack(out_s, "asm_stage"), _stack(out_d, "asm_days_in_stage")], axis=1)


# ------------------------------------------------------------------------------------------------ pledge
def pledge_features(pl: pd.DataFrame, dates: pd.DatetimeIndex, symbols, source_start="2021-01-01") -> pd.DataFrame:
    """pl: symbol, broadcast_ts, pledge_pct (per shareholding filing), optional reason (why a filing's pct is NaN).
    As-of the Friday close. A filing whose pledge field is missing stays NaN (never 0) and its reason is carried."""
    rows = []
    close = dates + pd.Timedelta(hours=15, minutes=30)
    for s, g in pl.sort_values("broadcast_ts").groupby("symbol"):
        if s not in set(symbols):
            continue
        g = g.drop_duplicates("broadcast_ts", keep="last")
        pos = g["broadcast_ts"].searchsorted(close, side="right") - 1
        v = g["pledge_pct"].to_numpy()
        rs = (g["reason"] if "reason" in g else pd.Series(None, index=g.index)).to_numpy(dtype=object)
        cur = np.where(pos >= 0, v[np.clip(pos, 0, None)], np.nan)
        why = np.where(pos >= 0, rs[np.clip(pos, 0, None)], None)
        decl = np.where(pos >= 0, (rs[np.clip(pos, 0, None)] == "declared_none").astype(float), np.nan)
        prv = np.where(pos >= 1, v[np.clip(pos - 1, 0, None)], np.nan)
        rows.append(pd.DataFrame({"date": dates, "symbol": s, "pledge_pct": cur, "pledge_chg_1q": cur - prv,
                                  "_why": why, "_decl": decl}))
    df = pd.concat(rows) if rows else pd.DataFrame(columns=["date", "symbol", "pledge_pct", "pledge_chg_1q", "_why", "_decl"])
    df = df.set_index(["date", "symbol"])
    full = pd.MultiIndex.from_product([dates, list(symbols)], names=["date", "symbol"])
    df = df.reindex(full)
    df["pledge_reason"] = np.where(df.index.get_level_values("date") < pd.Timestamp(source_start), "pre_2021_source",
                                   np.where(df["pledge_pct"].isna(),
                                            df["_why"].where(df["_why"].notna(), "no_filing_known"), None))
    df["pledge_reason"] = df["pledge_reason"].where(df["pledge_reason"] != "declared_none")
    df["pledge_declared_none"] = df["_decl"].astype(float).where(
        df.index.get_level_values("date") >= pd.Timestamp(source_start))   # NaN while no filing is known
    return df.drop(columns=["_why", "_decl"])


# ------------------------------------------------------------------------------------------------ fundamentals
def _next_bs_deadline(pe: pd.Series) -> pd.Series:
    nxt = pe + pd.offsets.MonthEnd(6)
    return nxt + pd.to_timedelta(np.where(nxt.dt.month == 3, 60, 45), unit="D")


def fundamental_features(view: pd.DataFrame, bs: pd.DataFrame, dates: pd.DatetimeIndex,
                         sym2co: dict[str, str]) -> pd.DataFrame:
    """view: Phase 0 feature view (company, broadcast_ts, ttm_*, lag_days...). bs: company, period_end, broadcast_ts,
    borrowings_current, borrowings_noncurrent, total_equity (instant contexts, primary basis)."""
    close = pd.Series(dates + pd.Timedelta(hours=15, minutes=30), index=dates)
    v = view.sort_values("broadcast_ts")
    cols = ["ttm_pbt", "ttm_finance_costs", "ttm_core_pat", "ttm_core_pat_chg4", "lag_days"]
    b = bs.sort_values("broadcast_ts").copy()
    b["de"] = (b["borrowings_current"].fillna(0) + b["borrowings_noncurrent"].fillna(0)).where(
        b[["borrowings_current", "borrowings_noncurrent"]].notna().any(axis=1)) / b["total_equity"].where(b["total_equity"] > 0)
    b["valid_to"] = _next_bs_deadline(b["period_end"]) + pd.Timedelta(days=60)
    out = []
    for sym, co in sym2co.items():
        g = v[v["company"] == co]
        bb = b[b["company"] == co]
        left = pd.DataFrame({"date": dates, "t": close.to_numpy()})
        if len(g):
            m = pd.merge_asof(left, g[["broadcast_ts"] + cols], left_on="t", right_on="broadcast_ts", direction="backward")
        else:
            m = left.assign(**{c: np.nan for c in cols})
        if len(bb):
            mb = pd.merge_asof(left, bb[["broadcast_ts", "de", "valid_to"]].dropna(subset=["de"]), left_on="t",
                               right_on="broadcast_ts", direction="backward")
            de = mb["de"].where(mb["t"] <= mb["valid_to"])
        else:
            de = np.nan
        fc = m["ttm_finance_costs"]
        out.append(pd.DataFrame({
            "date": dates, "symbol": sym, "de_ratio": de,
            "int_cover": ((m["ttm_pbt"] + fc) / fc).where(fc > 0),
            "ttm_core_pat_pos": np.where(m["ttm_core_pat"].isna(), np.nan, (m["ttm_core_pat"] > 0).astype(float)),
            "ttm_core_pat_chg4": m["ttm_core_pat_chg4"], "last_lag_days": m["lag_days"],
            "late_filer": np.where(m["lag_days"].isna(), np.nan, (m["lag_days"] > 120).astype(float))}))
    return pd.concat(out).set_index(["date", "symbol"]) if out else pd.DataFrame()


# ------------------------------------------------------------------------------------------------ label
def crash_label(close: pd.DataFrame, member: pd.DataFrame, beta: pd.DataFrame, dates: pd.DatetimeIndex,
                unseal_token: str | None = None) -> pd.DataFrame:
    """beta: dates x symbols (beta126 at the Friday). Only Fridays whose 63rd forward session is <= TRAIN_END."""
    rs = close.pct_change(fill_method=None)
    mk = rs.where(member).mean(axis=1)
    idx = close.index
    pos = idx.get_indexer(dates)
    ok = (pos >= 0) & (pos + H_LABEL < len(idx))
    exit_dt = pd.DatetimeIndex([idx[p + H_LABEL] if o else pd.NaT for p, o in zip(pos, ok)])
    keep = ok & (np.asarray(exit_dt <= pd.Timestamp(TRAIN_END)) if unseal_token is None else ok)
    assert_pre_holdout(pd.Series(1.0, index=exit_dt[keep]), unseal_token=unseal_token, what="crash-label exit dates")
    R = rs.to_numpy()
    M = mk.to_numpy()
    out = pd.DataFrame(np.nan, index=dates, columns=close.columns)
    for k, (p, kp) in enumerate(zip(pos, keep)):
        if not kp:
            continue
        b = beta.iloc[k].to_numpy()
        seg = R[p + 1:p + 1 + H_LABEL] - b[None, :] * M[p + 1:p + 1 + H_LABEL, None]
        path = np.cumprod(1 + np.nan_to_num(seg, nan=0.0), axis=0) - 1
        valid = np.isfinite(b) & (np.isfinite(R[p + 1:p + 1 + H_LABEL]).sum(axis=0) >= H_LABEL * 0.8)
        mn = path.min(axis=0)
        out.iloc[k] = np.where(valid, (mn <= CRASH).astype(float), np.nan)
    out = out.where(member.reindex(dates))
    return _stack(out, "label_crash").to_frame()
