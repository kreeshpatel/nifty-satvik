"""Point-in-time quarterly results from NSE XBRL filings (data layer only — no signal).

Source: the XBRL instance attached to each NSE financial-results filing (legacy
corporates-financial-results listing and the integrated-filing listing), harvested by
pipelines/build/harvest_results_xbrl.py and built by pipelines/build/build_results_xbrl.py.

Row grain: one row per (filing, duration context). A results filing carries the reported quarter
(context_role="current", e.g. OneD) and a year-to-date context (context_role="ytd", e.g. FourD:
H1 in a Q2 filing, 9M in Q3, the full year in a March filing). The current-quarter rows are
what most callers want: ``load_results(asof, role="current")``.

PIT rules:
  * availability = broadcast_ts (from the NSE listing, IST, to the second). A decision at asof may
    use only rows with broadcast_ts <= asof.
  * a revision is its own row with its own broadcast_ts (filing_seq >= 1); originals are never
    overwritten. ``latest_per_period`` picks, per period, the newest filing known at asof.

Value rules:
  * a fact with unit INR is already in rupees (XBRL ``decimals`` is precision, not scale);
    INRPerShare is rupees per share. Any other unit -> NaN with reason "unit".
  * an absent tag -> NaN with reason "absent"; a non-numeric text -> NaN with reason "parse".
    Never 0. Balance-sheet facts only where the filing carries an instant context; never filled.
"""
from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd

from config import DATA_DIR

RESULTS_XBRL_PATH = DATA_DIR / "results_xbrl.parquet"

# output field -> ordered list of accepted XBRL local names (first hit wins; raw tag kept)
DURATION_FIELDS: dict[str, list[str]] = {
    "revenue_ops": ["RevenueFromOperations"],
    "total_income": ["Income", "TotalIncome", "Revenue"],
    "pat": ["ProfitLossForPeriod", "ProfitLossForThePeriod",
            "ProfitLossAfterTaxAndExtraordinaryItems", "ProfitLossAfterTax"],          # last two: insurers
    "eps_basic": ["BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                  "BasicEarningsLossPerShareFromContinuingOperations", "BasicEarningsLossPerShare",
                  "BasicEarningsPerShareAfterExtraordinaryItems"],
    "eps_diluted": ["DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                    "DilutedEarningsLossPerShareFromContinuingOperations", "DilutedEarningsLossPerShare",
                    "DilutedEarningsPerShareAfterExtraordinaryItems"],
    "finance_costs": ["FinanceCosts"],
    "depreciation": ["DepreciationDepletionAndAmortisationExpense"],
    "exceptional_items": ["ExceptionalItemsBeforeTax", "ExceptionalItems"],
    "paid_up_equity": ["PaidUpValueOfEquityShareCapital", "PaidUpEquityShareCapital"],
    "face_value": ["FaceValueOfEquityShareCapital"],
}
INSTANT_FIELDS: dict[str, list[str]] = {
    "bs_equity_share_capital": ["EquityShareCapital"],
    "bs_total_equity": ["Equity", "EquityAttributableToOwnersOfParent"],
    "bs_total_assets": ["Assets"],
    "bs_borrowings_current": ["BorrowingsCurrent", "CurrentBorrowings"],
    "bs_borrowings_noncurrent": ["BorrowingsNoncurrent", "NoncurrentBorrowings"],
}
VALUE_FIELDS = list(DURATION_FIELDS) + list(INSTANT_FIELDS)
UNIT_OK = {"face_value": {"INRPerShare"}, "eps_basic": {"INRPerShare"}, "eps_diluted": {"INRPerShare"}}
DEFAULT_UNIT = {"INR"}

META_COLS = ["symbol", "isin", "period_start", "period_end", "period_type", "context_role", "consolidated",
             "broadcast_ts", "filing_seq", "is_revision", "xbrl_url", "listing", "context_id", "period_source",
             "period_reason", "n_current_candidates", "current_rule"]
SCHEMA = (META_COLS + VALUE_FIELDS + [f"{f}__tag" for f in VALUE_FIELDS] + [f"{f}__unit" for f in VALUE_FIELDS]
          + [f"{f}__reason" for f in VALUE_FIELDS])

_XBRLI = "http://www.xbrl.org/2003/instance"


def _period_type(start: date | None, end: date | None) -> str | None:
    if start is None or end is None:
        return None
    d = (end - start).days + 1
    if 80 <= d <= 100:
        return "Q"
    if 170 <= d <= 190:
        return "H"
    if 260 <= d <= 280:
        return "9M"
    if 350 <= d <= 380:
        return "FY"
    return f"D{d}"


def _num(text: str | None) -> float | None:
    if text is None:
        return None
    t = text.strip().replace(",", "")
    if not re.fullmatch(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", t):
        return None
    return float(t)


def parse_xbrl(content: bytes, hint: dict | None = None) -> list[dict]:
    """Parse one XBRL instance -> one dict per duration context that carries a reporting period.

    Period dates come from DateOfStart/EndOfReportingPeriod facts in that context (present in every
    NSE results instance seen, including 2019 files whose <context> elements are missing), falling
    back to the <context> period.

    ``hint`` is the filing's NSE listing row: {"period_start", "period_end" (dates or None),
    "consolidated" (bool or None)}. It is used only (1) for label-only instances, which carry a
    ReportingQuarter text but no period dates, and (2) to choose the current context when several
    tie (``_rank_current``). Without a hint the parser is a pure function of the file."""
    from lxml import etree

    hint = hint or {}
    root = etree.fromstring(content, parser=etree.XMLParser(recover=True, huge_tree=True))
    ctx_period: dict[str, tuple] = {}
    for c in root.iter(f"{{{_XBRLI}}}context"):
        per = c.find(f"{{{_XBRLI}}}period")
        if per is None:
            continue
        vals = {etree.QName(x).localname: (x.text or "").strip() for x in per}
        ctx_period[c.get("id")] = (vals.get("startDate"), vals.get("endDate") or vals.get("instant"))

    facts: dict[str, dict[str, list]] = {}   # context -> localname -> [(text, unit)]
    for el in root:
        if not isinstance(el.tag, str):
            continue
        cref = el.get("contextRef")
        if not cref:
            continue
        facts.setdefault(cref, {}).setdefault(etree.QName(el).localname, []).append(
            ((el.text or "").strip(), el.get("unitRef")))

    def first(cref, name):
        v = facts.get(cref, {}).get(name)
        return v[0][0] if v else None

    def to_date(s):
        try:
            return pd.Timestamp(s).date() if s else None
        except (ValueError, TypeError):
            return None

    fy_start = next((to_date(first(c, "DateOfStartOfFinancialYear")) for c in facts
                     if first(c, "DateOfStartOfFinancialYear")), None)
    # duration contexts = those carrying a reporting-period end
    dur, src = {}, {}
    for cref, f in facts.items():
        if "DateOfEndOfReportingPeriod" in f:
            s = to_date(first(cref, "DateOfStartOfReportingPeriod"))
            e = to_date(first(cref, "DateOfEndOfReportingPeriod"))
            src[cref] = "facts"
            if (s is None or e is None) and cref in ctx_period:
                s = s or to_date(ctx_period[cref][0])
                e = e or to_date(ctx_period[cref][1])
                src[cref] = "context"
            # banking instances omit start dates: the "One*" context is the quarter ending at e,
            # the other duration context runs from the financial-year start
            if s is None and e is not None and cref.startswith("One"):
                s, src[cref] = _quarter_start(e), "quarter_from_end"
            elif s is None and fy_start is not None:
                s, src[cref] = fy_start, "fy_start"
            if e is not None:
                dur[cref] = (s, e)
    reason = None
    if not dur:
        # label-only instances (ReportingQuarter text, no period dates). Order: the listing's period ->
        # an unambiguous "<n> quarter" label + FY start -> keep the rows with NaN dates and
        # reason "period_label_only" (never dropped).
        qn = {"first": 1, "second": 2, "third": 3, "fourth": 4}
        rq = (first("OneD", "ReportingQuarter") or "").strip().lower()
        h_end = hint.get("period_end")
        for cref in ("OneD", "FourD"):
            if cref not in facts:
                continue
            if h_end is not None:
                if cref == "OneD":
                    # OneD is the quarter. The listing's start is used only when it spans a quarter:
                    # "Yearly" filings list the cumulative FY (Apr..Mar), whose OneD is still Jan..Mar.
                    h_start = hint.get("period_start")
                    if h_start is None or _period_type(h_start, h_end) != "Q":
                        h_start = _quarter_start(h_end)
                    dur[cref], src[cref] = (h_start, h_end), "listing"
                elif fy_start is not None:
                    dur[cref], src[cref] = (fy_start, h_end), "listing_fy_start"
            elif fy_start is not None and rq.endswith("quarter") and rq.split(" ")[0] in qn:
                qe = (pd.Timestamp(fy_start) + pd.offsets.MonthEnd(3 * qn[rq.split(" ")[0]])).date()
                dur[cref] = (_quarter_start(qe) if cref == "OneD" else fy_start, qe)
                src[cref] = "derived_quarter"
        if not dur:
            valued = [c for c, f in facts.items() if any(t in f for tags in DURATION_FIELDS.values() for t in tags)]
            if not valued:
                return []
            dur = {c: (None, None) for c in valued}
            src = {c: "none" for c in valued}
            reason = "period_label_only"
    # instant contexts: those whose context period is an instant
    instants = {c: to_date(p[1]) for c, p in ctx_period.items() if p[0] is None and p[1]}

    any_ctx = next(iter(dur))
    symbol = first(any_ctx, "Symbol")
    isin = first(any_ctx, "ISIN")
    nature = {c: (first(c, "NatureOfReportStandaloneConsolidated") or "").lower() for c in dur}
    cons = {c: True if n.startswith("consol") else (False if n.startswith("stand") else None) for c, n in nature.items()}
    n_values = {c: sum(len(v) for v in facts.get(c, {}).values()) for c in dur}
    shortest, n_cand, rule = _rank_current(dur, cons, n_values, hint)

    rows = []
    for cref, (s, e) in sorted(dur.items()):
        row = {"symbol": symbol, "isin": isin, "period_start": s, "period_end": e,
               "period_type": _period_type(s, e), "context_id": cref, "period_source": src[cref],
               "period_reason": reason, "n_current_candidates": n_cand, "current_rule": rule,
               "context_role": "current" if cref == shortest else "ytd", "consolidated": cons[cref]}
        _fill(row, facts.get(cref, {}), DURATION_FIELDS)
        # balance sheet: only from an instant context dated at this row's period end, current row only
        inst = [c for c, d in instants.items() if e is not None and d == e] if cref == shortest else []
        merged: dict[str, list] = {}
        for c in sorted(inst):
            for k, v in facts.get(c, {}).items():
                merged.setdefault(k, []).extend(v)
        _fill(row, merged, INSTANT_FIELDS)
        rows.append(row)
    return rows


def _quarter_start(end: date) -> date:
    return (pd.Timestamp(end) - pd.offsets.MonthBegin(3)).date()


def _rank_current(dur: dict, cons: dict, n_values: dict, hint: dict) -> tuple[str, int, str]:
    """Choose the current-period context.

    Candidates = duration contexts in the same length class (Q/H/9M/FY) as the shortest one (every
    context when no length is known). Rules, applied in order:
      (a) end date equals the listing's period end;
      (b) consolidated flag equals the listing's flag;
      (c) most tagged values (fact count in the context);
      then id starting "One", then id (deterministic tie-break only).
    A rule whose listing field is missing does not separate candidates.
    Returns (context id, number of candidates, deciding rule: single / a / b / c / tiebreak)."""
    lens = {c: (e - s).days for c, (s, e) in dur.items() if s is not None and e is not None}
    if lens:
        # same length class as the shortest (Q/H/9M/FY), so a 90-day and a 91-day quarter both compete
        kind = _period_type(*dur[min(lens, key=lens.get)])
        cands = [c for c in lens if _period_type(*dur[c]) == kind]
    else:
        cands = list(dur)
    if len(cands) == 1:
        return cands[0], 1, "single"
    h_end, h_cons = hint.get("period_end"), hint.get("consolidated")
    keys = {c: (0 if h_end is None or dur[c][1] == h_end else 1,
                0 if h_cons is None or cons[c] == h_cons else 1,
                -n_values[c],
                0 if c.startswith("One") else 1,
                c) for c in cands}
    order = sorted(cands, key=keys.get)
    top, nxt = keys[order[0]], keys[order[1]]
    rule = ["a", "b", "c", "tiebreak", "tiebreak"][next(i for i in range(5) if top[i] != nxt[i])]
    return order[0], len(cands), rule


def _fill(row: dict, f: dict, spec: dict[str, list[str]]) -> None:
    for field, tags in spec.items():
        row[field], row[f"{field}__tag"], row[f"{field}__unit"], row[f"{field}__reason"] = np.nan, None, None, "absent"
        for t in tags:
            if t not in f:
                continue
            text, unit = f[t][0]
            row[f"{field}__tag"], row[f"{field}__unit"] = t, unit
            ok_units = UNIT_OK.get(field, DEFAULT_UNIT)
            v = _num(text)
            if unit not in ok_units:
                row[f"{field}__reason"] = "unit"
            elif v is None:
                row[f"{field}__reason"] = "parse"
            else:
                vals = {_num(x) for x, u in f[t]}
                if len(vals) > 1:
                    row[f"{field}__reason"] = "conflict"
                else:
                    row[field], row[f"{field}__reason"] = v, None
            break


def assign_filing_seq(df: pd.DataFrame) -> pd.DataFrame:
    """filing_seq = 0 for the first broadcast of a (symbol, period_start, period_end, consolidated,
    context_role) and 1, 2, … for later filings of the same period (revisions). Ties broken by url."""
    out = df.sort_values(["broadcast_ts", "xbrl_url"]).copy()
    key = ["symbol", "period_start", "period_end", "consolidated", "context_role"]
    out["filing_seq"] = out.groupby(key, dropna=False).cumcount()
    out["is_revision"] = out["filing_seq"] > 0
    return out.sort_values(["symbol", "period_end", "broadcast_ts"]).reset_index(drop=True)


def as_of(df: pd.DataFrame, asof) -> pd.DataFrame:
    """Pure PIT filter: rows whose broadcast_ts <= asof (inclusive)."""
    return df[df["broadcast_ts"] <= pd.Timestamp(asof)]


def latest_per_period(df: pd.DataFrame, asof) -> pd.DataFrame:
    """Per (symbol, period, consolidated, context_role): the newest filing known at asof."""
    k = as_of(df, asof).sort_values(["broadcast_ts", "xbrl_url"])
    key = ["symbol", "period_start", "period_end", "consolidated", "context_role"]
    return k.groupby(key, dropna=False, as_index=False).tail(1).reset_index(drop=True)


def load_results(asof, role: str | None = "current", path=RESULTS_XBRL_PATH) -> pd.DataFrame:
    """Rows of the built parquet available at asof (broadcast_ts <= asof). role=None keeps all."""
    df = pd.read_parquet(path)
    if role is not None:
        df = df[df["context_role"] == role]
    return as_of(df, asof).reset_index(drop=True)
