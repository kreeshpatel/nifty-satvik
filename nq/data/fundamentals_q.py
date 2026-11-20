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
FLOWS = ["revenue_ops", "total_income", "pat", "exceptional_items"]
STOCKS = ["paid_up_equity", "face_value"]
KEYS = ["company", "qn"]


def _qn(ts: pd.Series) -> pd.Series:
    return ts.dt.year * 4 + (ts.dt.month - 1) // 3


def qn_to_end(qn: pd.Series) -> pd.Series:
    y, q = qn // 4, qn % 4
    return pd.to_datetime(pd.DataFrame({"year": y, "month": q * 3 + 3, "day": 1})) + pd.offsets.MonthEnd(0)


def _observations(df: pd.DataFrame) -> pd.DataFrame:
    o = df[df["period_end"].notna() & df["period_start"].notna() & df["consolidated"].notna()].copy()
    o["company"] = o["isin"].where(o["isin"].notna() & (o["isin"].astype(str) != ""), o["symbol"])
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


def _ttm(p: pd.DataFrame) -> pd.DataFrame:
    base = p[["company", "qn", "broadcast_ts", "pat", "revenue_ops"]].sort_values("broadcast_ts")
    p = p.sort_values("broadcast_ts")
    parts = {"pat": [p["pat"]], "revenue_ops": [p["revenue_ops"]]}
    for k in (1, 2, 3):
        left = p[["company", "qn", "broadcast_ts"]].assign(qk=p["qn"] - k).reset_index()
        right = base.rename(columns={"qn": "qk", "broadcast_ts": "bk"}).sort_values("bk")
        m = pd.merge_asof(left.sort_values("broadcast_ts"), right, left_on="broadcast_ts", right_on="bk",
                          by=["company", "qk"], direction="backward").set_index("index").reindex(p.index)
        for c in parts:
            parts[c].append(m[c])
    for c, cols in parts.items():
        mat = pd.concat(cols, axis=1)
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


def build_panel(df: pd.DataFrame, names: pd.Series | None = None) -> pd.DataFrame:
    """results_xbrl rows -> quarterly fundamentals panel. ``names``: company key -> company name (optional)."""
    o = _observations(df)
    basis = choose_basis(o)
    fin = flag_financials(o, names)
    o = o[o["consolidated"] == (o["company"].map(basis) == "consolidated")]
    p = _discrete(o)
    p["basis"] = p["company"].map(basis)
    p["is_financial"] = p["company"].map(fin).fillna(False).astype(bool)
    p["core_pat"] = p["pat"] - p["exceptional_items"] * (1 - TAX_RATE)
    p.loc[p["exceptional_items"].isna(), "core_pat"] = np.nan
    p = _shares(p)
    p["adj_core_eps"] = (p["core_pat"] / p["adj_shares"]).where(p["adj_shares"] > 0)
    p["adj_eps"] = (p["pat"] / p["adj_shares"]).where(p["adj_shares"] > 0)
    p = _ttm(p)
    p["nan_reason"] = _reasons(p)
    p["is_revision"] = p["version"] > 0
    p["fiscal_quarter_end"] = qn_to_end(p["qn"])
    p["fiscal_year"] = np.where(p["fiscal_quarter_end"].dt.month <= 3, p["fiscal_quarter_end"].dt.year,
                                p["fiscal_quarter_end"].dt.year + 1)
    cols = ["company", "symbol", "isin", "basis", "is_financial", "fiscal_year", "fiscal_quarter_end", "qn",
            "period_start", "period_end", "broadcast_ts", "version", "is_revision", "derived", "xbrl_url",
            "lag_days", "period_flag", "revenue_ops", "total_income", "pat", "exceptional_items", "core_pat",
            "eps_basic", "paid_up_equity", "face_value", "shares", "shares_source", "share_factor", "split_event",
            "adj_shares", "adj_core_eps", "adj_eps", "ttm_pat", "ttm_revenue_ops", "ttm_margin", "nan_reason"]
    return p[cols].sort_values(["company", "qn", "version"]).reset_index(drop=True)


def as_of(panel: pd.DataFrame, ts) -> pd.DataFrame:
    """Latest-known version of every (company, quarter) whose broadcast is <= ts (PIT view)."""
    v = panel[panel["broadcast_ts"] <= pd.Timestamp(ts)]
    return v.sort_values("broadcast_ts").drop_duplicates(KEYS, keep="last").sort_values(KEYS)


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
