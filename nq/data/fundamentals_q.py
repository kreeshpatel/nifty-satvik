"""Quarterly fundamentals panel from the PIT XBRL results dataset (data/results_xbrl.parquet, PR #217).

One row per (company, fiscal quarter, filing). Each row is available at that filing's ``broadcast_ts``.
Revisions are separate rows (``version`` > 0). Data engineering only: no signal is computed here.

Rules (Phase 0 spec, pre-registration 0153):

* **Company key.** ISIN when present, else symbol. ``symbol`` is carried for display.
* **Basis.**
  * Each company uses consolidated figures if consolidated values exist for at least ``CONSOL_SHARE``
    (80%) of the fiscal quarters it ever reported; otherwise it uses standalone figures.
  * One basis is used for the whole history; bases are never mixed within a company. The choice is
    recorded in ``basis``.
  * The choice reads the company's whole filing history. That is a filing-format fact, not a value, and
    it is disclosed as such in the Phase 0 report.
* **Discrete quarters.**
  * A 3-month context gives the quarter directly.
  * A cumulative context (H1, 9M, FY) gives a discrete quarter by subtracting the latest-known
    cumulative context with the same start that ends one quarter earlier (e.g. Q4 = FY − 9M). Such rows
    have ``derived = True``.
  * A derived row is dropped when a direct row for that quarter was already known at its broadcast.
  * Derived EPS is never computed by subtraction: EPS is not additive, so it is left NaN.
* **Core PAT** = PAT − exceptional items × (1 − ``TAX_RATE``) [assumed, CONFIRM]. ``TAX_RATE`` is
  25.17%, the Section 115BAA corporate rate with surcharge and cess. Reported PAT is kept as ``pat``.
* **Shares.**
  * The share count is paid-up equity capital ÷ face value where both are present; otherwise PAT ÷
    basic EPS. ``shares_source`` records which.
* **Splits and bonuses.**
  * These are detected from the company's own paid-up share count: a quarter-on-quarter step whose
    ratio is within 3% of a standard split/bonus ratio (``SPLIT_RATIOS``, or its inverse for a
    consolidation).
  * ``share_factor`` is the cumulative product of the steps up to and including the row's quarter, so it
    uses only information available by that quarter.
  * ``adj_shares`` = shares ÷ share_factor expresses every quarter on the company's earliest share basis.
  * ``adj_core_eps`` = core PAT ÷ adj_shares.
  * The repo's corporate-action registers list demergers only, with no splits or bonuses. That is why
    detection uses the filings themselves.
* **Financials.**
  * ``is_financial`` is set if the filing uses the banking or insurance taxonomy (no
    RevenueFromOperations tag while total income is tagged, in at least half of the company's current
    rows), or if the company name matches ``FIN_NAME_RE``.
  * Financials are kept, flagged.
* **Trailing twelve months.**
  * TTM is the sum of this quarter and the latest-known versions of the three previous quarters, as of
    this row's broadcast.
  * Values are never forward-filled. Any missing input gives NaN plus a reason code in ``nan_reason``.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

CONSOL_SHARE = 0.80
TAX_RATE = 0.2517
SPLIT_RATIOS = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 10.0, 20.0)
SPLIT_TOL = 0.03
FIN_NAME_RE = re.compile(r"\bBANK\b|FINANC|FINSERV|INSURANCE|ASSURANCE|\bCREDIT\b|LEASING|HOUSING FIN", re.I)
FLOWS = ["revenue_ops", "total_income", "pat", "exceptional_items", "tax_expense", "pbt", "pbeit", "finance_costs"]
TAX_CLIP = (0.0, 0.40)
FEATURES = ["ttm_pat", "ttm_revenue_ops", "ttm_margin", "yoy_core_pat", "ttm_core_pat", "ttm_core_pat_chg4",
            "ttm_pbt", "ttm_finance_costs"]  # tax_rate stays inside its basis (it feeds core_pat)
STOCKS = ["paid_up_equity", "face_value"]
KEYS = ["company", "qn"]


def _qn(ts: pd.Series) -> pd.Series:
    return ts.dt.year * 4 + (ts.dt.month - 1) // 3


def qn_to_end(qn: pd.Series) -> pd.Series:
    y, q = qn // 4, qn % 4
    return pd.to_datetime(pd.DataFrame({"year": y, "month": q * 3 + 3, "day": 1})) + pd.offsets.MonthEnd(0)


def company_key(isin: pd.Series, symbol: pd.Series) -> pd.Series:
    """Issuer + security-type part of the ISIN (first 9 characters, e.g. INE686F01). The last two characters,
    serial and check digit, change when a split or face-value change re-issues the ISIN; keying on the full ISIN
    split one company's history in two. Added 2026-11-21 (Phase 0 close-out, after first look). Falls back to the
    symbol when the ISIN is missing."""
    ok = isin.notna() & (isin.astype(str).str.len() >= 9)
    i9 = isin.astype(str).str[:9].where(ok)
    # a few filings carry a mistyped ISIN (e.g. IN3686F... for INE686F...): use each symbol's most frequent
    # issuer code, so one bad filing cannot split a company
    mode = i9.groupby(symbol).agg(lambda s: s.value_counts().index[0] if s.notna().any() else None)
    key = symbol.map(mode)
    return key.where(key.notna(), i9).where(lambda k: k.notna(), symbol)


def _observations(df: pd.DataFrame) -> pd.DataFrame:
    o = df[df["period_end"].notna() & df["period_start"].notna() & df["consolidated"].notna()].copy()
    for c in FLOWS + STOCKS + ["eps_basic"]:
        if c not in o:
            o[c] = np.nan
    o["company"] = company_key(o["isin"], o["symbol"])
    o["span"] = ((o["period_end"] - o["period_start"]).dt.days / 91.31).round().astype(int)
    o = o[o["span"].between(1, 4)]
    o["qn"] = _qn(o["period_end"])
    o["consolidated"] = o["consolidated"].astype(bool)
    return o


def choose_basis(o: pd.DataFrame) -> pd.Series:
    """company -> 'consolidated' | 'standalone' by the CONSOL_SHARE rule (over fiscal quarters reported)."""
    allq = o.groupby("company")["qn"].nunique()
    conq = o[o["consolidated"]].groupby("company")["qn"].nunique().reindex(allq.index).fillna(0)
    return pd.Series(np.where(conq / allq >= CONSOL_SHARE, "consolidated", "standalone"), index=allq.index)


def _discrete(o: pd.DataFrame) -> pd.DataFrame:
    meta = ["company", "symbol", "isin", "qn", "period_start", "period_end", "broadcast_ts", "xbrl_url",
            "lag_days", "period_flag"]
    o = o.sort_values(["company", "qn", "broadcast_ts", "context_role"])  # 'current' before 'ytd'
    direct = o[o["span"] == 1].drop_duplicates(["company", "qn", "xbrl_url"])
    direct = direct[meta + FLOWS + STOCKS + ["eps_basic"]].assign(derived=False)
    cum = o[o["span"] >= 2].drop_duplicates(["company", "qn", "span", "xbrl_url"])
    if cum.empty:
        out = direct.sort_values(["company", "qn", "broadcast_ts"]).drop_duplicates(["company", "qn", "broadcast_ts"])
        out["version"] = out.groupby(KEYS).cumcount()
        return out.reset_index(drop=True)
    prev = o.drop_duplicates(["company", "qn", "span", "xbrl_url"])[
        ["company", "period_start", "qn", "span", "broadcast_ts"] + FLOWS].copy()
    prev["key"] = prev["company"] + "|" + prev["period_start"].astype(str) + "|" + (prev["qn"] + 1).astype(str) \
        + "|" + (prev["span"] + 1).astype(str)
    cum = cum.assign(key=cum["company"] + "|" + cum["period_start"].astype(str) + "|" + cum["qn"].astype(str)
                     + "|" + cum["span"].astype(str))
    m = pd.merge_asof(cum.sort_values("broadcast_ts"),
                      prev.rename(columns={c: c + "_p" for c in FLOWS + ["broadcast_ts"]})
                      [["key", "broadcast_ts_p"] + [c + "_p" for c in FLOWS]].sort_values("broadcast_ts_p"),
                      left_on="broadcast_ts", right_on="broadcast_ts_p", by="key", direction="backward")
    for c in FLOWS:
        m[c] = m[c] - m[c + "_p"]
    m = m[m["broadcast_ts_p"].notna()]
    der = m[meta + FLOWS + STOCKS].assign(eps_basic=np.nan, derived=True)
    # drop a derived row when a direct row for the same quarter was already known at its broadcast
    first_direct = direct.groupby(KEYS)["broadcast_ts"].min().rename("fd")
    der = der.join(first_direct, on=KEYS)
    der = der[der["fd"].isna() | (der["broadcast_ts"] < der["fd"])].drop(columns="fd")
    out = pd.concat([direct, der], ignore_index=True)
    out = out.sort_values(["company", "qn", "broadcast_ts", "derived"]).drop_duplicates(
        ["company", "qn", "broadcast_ts"])
    out["version"] = out.groupby(KEYS).cumcount()
    return out.reset_index(drop=True)


def _nice_ratio(r: float) -> bool:
    if not np.isfinite(r) or r <= 0:
        return False
    x = r if r >= 1 else 1.0 / r
    return any(abs(x / s - 1) <= SPLIT_TOL for s in SPLIT_RATIOS)


def _shares(p: pd.DataFrame) -> pd.DataFrame:
    pv = p["paid_up_equity"] / p["face_value"]
    pv = pv.where((p["paid_up_equity"] > 0) & (p["face_value"] > 0))
    pe = (p["pat"] / p["eps_basic"]).where(p["eps_basic"].abs() > 0.01)
    p["shares"] = pv.fillna(pe)
    p["shares_source"] = np.where(pv.notna(), "paid_up/face_value", np.where(pe.notna(), "pat/eps", None))
    # split / bonus steps on the paid-up count, one value per (company, quarter): the original filing's
    q = p[pv.notna()].assign(pv=pv).sort_values(["company", "qn", "version"]).drop_duplicates(KEYS)
    q["r"] = q.groupby("company")["pv"].transform(lambda s: s / s.shift(1))
    q["step"] = np.where(q["r"].map(_nice_ratio), q["r"], 1.0)
    q["share_factor"] = q.groupby("company")["step"].cumprod()
    p = p.merge(q[KEYS + ["share_factor", "step"]], on=KEYS, how="left")
    # quarters without a paid-up count inherit the last known factor (a factor, not a value: no NaN masking)
    p = p.sort_values(["company", "qn", "version"])
    p["share_factor"] = p.groupby("company")["share_factor"].ffill().fillna(1.0)
    p["split_event"] = p["step"].fillna(1.0) != 1.0
    p["adj_shares"] = p["shares"] / p["share_factor"]
    return p.drop(columns="step")


def _lagged(p: pd.DataFrame, cols: list[str], k: int) -> pd.DataFrame:
    """Latest-known value (broadcast <= this row's broadcast) of ``cols`` for quarter qn-k of the same company.
    ``p`` holds ONE basis only, so a lagged value never comes from another basis."""
    left = p[["company", "qn", "broadcast_ts"]].assign(qk=p["qn"] - k).reset_index()
    right = p[["company", "qn", "broadcast_ts"] + cols].rename(columns={"qn": "qk", "broadcast_ts": "bk"})
    m = pd.merge_asof(left.sort_values("broadcast_ts"), right.sort_values("bk"), left_on="broadcast_ts",
                      right_on="bk", by=["company", "qk"], direction="backward")
    return m.set_index("index").reindex(p.index)[cols]


def _ttm(p: pd.DataFrame, cols=("pat", "revenue_ops", "tax_expense", "pbt")) -> pd.DataFrame:
    cols = list(cols)
    lags = [_lagged(p, cols, k) for k in (1, 2, 3)]
    for c in cols:
        mat = pd.concat([p[c]] + [lg[c] for lg in lags], axis=1)
        p[f"ttm_{c}"] = mat.sum(axis=1, min_count=4).where(mat.notna().all(axis=1))
        p[f"_miss_{c}"] = mat.isna().any(axis=1)
    p["ttm_margin"] = (p["ttm_pat"] / p["ttm_revenue_ops"]).where(p["ttm_revenue_ops"] > 0)
    return p


def _reasons(p: pd.DataFrame) -> pd.Series:
    r = pd.DataFrame({
        "pat_missing": p["pat"].isna(),
        "shares_missing": p["shares"].isna(),
        "exceptional_missing": p["exceptional_items"].isna() & p["pat"].notna(),
        "ttm_pat_incomplete": p["_miss_pat"],
        "ttm_revenue_incomplete": p["_miss_revenue_ops"],
        "tax_rate_fallback": p["tax_rate_fallback"],
        "yoy_base_missing_or_nonpositive": p["yoy_core_pat"].isna(),
        "revenue_nonpositive": p["ttm_revenue_ops"].notna() & (p["ttm_revenue_ops"] <= 0),
    })
    return r.apply(lambda row: ";".join(c for c, v in row.items() if v) or None, axis=1)


def flag_financials(o: pd.DataFrame, names: pd.Series | None = None) -> pd.Series:
    """company -> bool. Bank/insurer taxonomy (no RevenueFromOperations tag while total income is tagged in
    >= 50% of current rows) or a financial company name."""
    cur = o[o["context_role"] == "current"]
    tax = (cur["revenue_ops__tag"].isna() & cur["total_income"].notna()).groupby(cur["company"]).mean() >= 0.5
    if names is not None:
        nm = names.reindex(tax.index).fillna("").astype(str).str.contains(FIN_NAME_RE)
        tax = tax | nm
    return tax


def _one_basis(o: pd.DataFrame, cons: bool) -> pd.DataFrame:
    """Every derived quantity for ONE basis. Nothing in here can see the other basis."""
    ob = o[o["consolidated"] == cons]
    if ob.empty:
        return ob
    p = _discrete(ob)
    if p.empty:
        return p
    p["basis"] = "consolidated" if cons else "standalone"
    p = _ttm(p)
    # effective tax rate: trailing-4-quarter tax / PBT, same basis, clipped; else the statutory fallback, flagged
    rate = (p["ttm_tax_expense"] / p["ttm_pbt"]).where(p["ttm_pbt"] > 0)
    p["tax_rate_fallback"] = rate.isna()
    p["tax_rate"] = rate.clip(*TAX_CLIP).fillna(TAX_RATE)
    p["core_pat"] = p["pat"] - p["exceptional_items"] * (1 - p["tax_rate"])
    p.loc[p["exceptional_items"].isna(), "core_pat"] = np.nan
    base = _lagged(p, ["core_pat"], 4)["core_pat"]
    p["yoy_core_pat"] = (p["core_pat"] / base - 1).where(base > 0)
    p = _ttm(p, cols=("core_pat", "finance_costs"))
    p["ttm_core_pat_chg4"] = p["ttm_core_pat"] - _lagged(p, ["ttm_core_pat"], 4)["ttm_core_pat"]
    p = _shares(p)
    p["adj_core_eps"] = (p["core_pat"] / p["adj_shares"]).where(p["adj_shares"] > 0)
    p["adj_eps"] = (p["pat"] / p["adj_shares"]).where(p["adj_shares"] > 0)
    return p


def build_panel(df: pd.DataFrame, names: pd.Series | None = None) -> pd.DataFrame:
    """results_xbrl rows -> long quarterly panel holding BOTH bases (``basis``); ``is_primary`` marks the
    company's primary basis (consolidated if it covers >= 80% of the company's quarters, else standalone)."""
    o = _observations(df)
    primary = choose_basis(o)
    fin = flag_financials(o, names)
    p = pd.concat([x for x in (_one_basis(o, True), _one_basis(o, False)) if len(x)], ignore_index=True)
    p["primary_basis"] = p["company"].map(primary)
    p["is_primary"] = p["basis"] == p["primary_basis"]
    p["is_financial"] = p["company"].map(fin).fillna(False).astype(bool)
    p["nan_reason"] = _reasons(p)
    p["is_revision"] = p["version"] > 0
    p["fiscal_quarter_end"] = qn_to_end(p["qn"])
    p["fiscal_year"] = np.where(p["fiscal_quarter_end"].dt.month <= 3, p["fiscal_quarter_end"].dt.year,
                                p["fiscal_quarter_end"].dt.year + 1)
    cols = ["company", "symbol", "isin", "basis", "primary_basis", "is_primary", "is_financial", "fiscal_year",
            "fiscal_quarter_end", "qn", "period_start", "period_end", "broadcast_ts", "version", "is_revision",
            "derived", "xbrl_url", "lag_days", "period_flag", "revenue_ops", "total_income", "pat", "pbt",
            "tax_expense", "pbeit", "exceptional_items", "tax_rate", "tax_rate_fallback", "core_pat", "yoy_core_pat",
            "eps_basic", "paid_up_equity", "face_value", "shares", "shares_source", "share_factor", "split_event",
            "adj_shares", "adj_core_eps", "adj_eps", "ttm_pat", "ttm_revenue_ops", "ttm_tax_expense", "ttm_pbt",
            "ttm_margin", "finance_costs", "ttm_core_pat", "ttm_core_pat_chg4", "ttm_finance_costs", "nan_reason"]
    return p[cols].sort_values(["company", "basis", "qn", "version"]).reset_index(drop=True)


def feature_view(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per primary-basis filing, plus other-basis filings for quarters the primary basis never reported.

    Each feature in FEATURES is taken whole from the primary basis. If that is NaN, the feature is taken whole
    from the other basis: its latest version known at this row's broadcast, for the same quarter. The choice
    is recorded in ``<feature>_basis`` and ``<feature>_basis_fallback``. Values from two bases are never combined in
    one calculation, because every feature was computed inside a single basis by ``build_panel``.
    """
    prim = panel[panel["is_primary"]].reset_index(drop=True)
    oth = panel[~panel["is_primary"]]
    seen = prim[["company", "qn"]].drop_duplicates()
    rec = oth.merge(seen, on=["company", "qn"], how="left", indicator=True)
    rec = rec[rec["_merge"] == "left_only"].drop(columns="_merge").copy()
    look = pd.merge_asof(prim[["company", "qn", "broadcast_ts"]].reset_index().sort_values("broadcast_ts"),
                         oth[["company", "qn", "broadcast_ts", "basis"] + FEATURES].rename(
                             columns={"broadcast_ts": "b_o", "basis": "basis_o"}).sort_values("b_o"),
                         left_on="broadcast_ts", right_on="b_o", by=["company", "qn"],
                         direction="backward").set_index("index").reindex(prim.index)
    v = prim.copy()
    for f in FEATURES:
        use = v[f].isna() & look[f].notna()
        v[f"{f}_basis"] = np.where(use, look["basis_o"], v["basis"])
        v[f"{f}_basis_fallback"] = use.to_numpy()
        v[f] = v[f].where(~use, look[f])
    for f in FEATURES:
        rec[f"{f}_basis"] = rec["basis"]
        rec[f"{f}_basis_fallback"] = rec[f].notna()
    v["row_recovered"] = False
    rec["row_recovered"] = True
    return pd.concat([v, rec], ignore_index=True).sort_values(["company", "qn", "broadcast_ts"]).reset_index(drop=True)


def as_of(panel: pd.DataFrame, ts) -> pd.DataFrame:
    """Latest-known version of every (company, quarter) whose broadcast is <= ts (PIT view)."""
    v = panel[panel["broadcast_ts"] <= pd.Timestamp(ts)]
    k = KEYS + (["basis"] if "basis" in v else [])
    return v.sort_values("broadcast_ts").drop_duplicates(k, keep="last").sort_values(k)


def first_tradable_session(ts: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """First session on which a results broadcast (IST, naive) can be traded.

    The rule:
    * A broadcast on a session day before 15:30 (pre-open or in-session) counts that day.
    * A broadcast at or after 15:30, or on a non-session day, counts the next session.

    ``sessions`` is a sorted DatetimeIndex of session dates (midnight). A broadcast after the last listed
    session gives NaT.
    """
    ts = pd.to_datetime(ts)
    day = ts.dt.normalize()
    after_close = (ts - day) >= pd.Timedelta(hours=15, minutes=30)
    is_sess = day.isin(sessions)
    target = day.where(is_sess & ~after_close, day + pd.Timedelta(days=1))
    pos = sessions.searchsorted(target.to_numpy(), side="left")
    out = pd.Series(pd.NaT, index=ts.index, dtype="datetime64[ns]")
    ok = (pos < len(sessions)) & target.notna().to_numpy()
    out[ok] = sessions[pos[ok]]
    return out
