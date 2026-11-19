"""Blind replica of the NSE quarterly-results XBRL parser, written from the spec only.

Does NOT import from nq/ and was written without reading the engine parser.
Usage: python -I replica_parse.py <files.txt> <out.csv> [<ambiguity_log.txt>]

Resolutions of spec ambiguities (see bottom of file / ambiguity log for counts):
  A1 Candidate contexts = every contextRef used by a root-child fact. Dates for a context come
     from its DateOfStart/EndOfReportingPeriod facts; for each date missing there, fall back to
     the declared xbrli:context period. Instant / dateless contexts are not candidates.
  A2 Bank case: a context with an end date but no start date. Only an id starting with "One"
     is given a start (first day of the 3-month quarter ending at end date); others are dropped.
  A3 No-dates case: ReportingQuarter + DateOfStartOfFinancialYear. Quarter index mapping:
     First=1, Second=2, Third=3, Fourth=4, "Half yearly"=2, "Yearly"=4 (inferred: in these files
     "Half yearly" filings have OneD = Jul-Sep and "Yearly" filings have OneD = Jan-Mar).
     Applied only to the "One*" context(s) lacking any dates.
  A4 Tie on shortest duration: prefer id starting "One"; still tied -> context referenced by
     the most facts; still tied -> lexicographically smallest id. (Spec stops at "One".)
  A5 "First matching tag wins" = first tag in the chain that HAS a fact in the current
     context, even if that fact's value is NaN (bad unit / non-numeric). No fall-through.
  A6 Units: money fields require unitRef INR; eps_* and face_value require INRPerShare.
  A7 Duplicate facts (same tag, same context): first in document order.
  A8 symbol / isin / nature-of-report: first fact in document order, any context.
"""
import csv
import datetime as dt
import gzip
import math
import os
import sys
from collections import Counter, defaultdict

from lxml import etree

FIELDS = [
    ("revenue_ops", ["RevenueFromOperations"], "INR"),
    ("total_income", ["Income", "TotalIncome", "Revenue"], "INR"),
    ("pat", ["ProfitLossForPeriod", "ProfitLossForThePeriod",
             "ProfitLossAfterTaxAndExtraordinaryItems", "ProfitLossAfterTax"], "INR"),
    ("eps_basic", ["BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                   "BasicEarningsLossPerShareFromContinuingOperations",
                   "BasicEarningsLossPerShare",
                   "BasicEarningsPerShareAfterExtraordinaryItems"], "INRPerShare"),
    ("eps_diluted", ["DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
                     "DilutedEarningsLossPerShareFromContinuingOperations",
                     "DilutedEarningsLossPerShare",
                     "DilutedEarningsPerShareAfterExtraordinaryItems"], "INRPerShare"),
    ("finance_costs", ["FinanceCosts"], "INR"),
    ("depreciation", ["DepreciationDepletionAndAmortisationExpense"], "INR"),
    ("paid_up_equity", ["PaidUpValueOfEquityShareCapital", "PaidUpEquityShareCapital"], "INR"),
    ("face_value", ["FaceValueOfEquityShareCapital"], "INRPerShare"),
]

QUARTER_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4,
                 "half yearly": 2, "half-yearly": 2, "yearly": 4, "annual": 4}

LOG = []


def ln(tag):
    if not isinstance(tag, str):
        return None
    return etree.QName(tag).localname


def parse_date(s):
    if s is None:
        return None
    s = s.strip()[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    return dt.date(y, m % 12 + 1, 1)


def quarter_start_ending(end):
    # first day of the month two months before end's month
    return add_months(dt.date(end.year, end.month, 1), -2)


def to_num(text):
    if text is None:
        return math.nan
    t = text.strip().replace(",", "")
    if t == "":
        return math.nan
    try:
        return float(t)
    except ValueError:
        return math.nan


def parse_file(path):
    fname = os.path.basename(path)
    root = etree.fromstring(gzip.open(path).read())

    facts = [el for el in root if isinstance(el.tag, str) and el.get("contextRef")]
    # declared contexts (anywhere in doc)
    declared = {}
    for c in root.iter():
        if ln(c.tag) != "context":
            continue
        d = {}
        for e in c.iter():
            n = ln(e.tag)
            if n in ("startDate", "endDate", "instant") and e.text:
                d[n] = parse_date(e.text)
        declared[c.get("id")] = d

    by_ctx = defaultdict(list)          # ctx -> [(tag, el)]
    ref_count = Counter()
    first_any = {}
    for el in facts:
        tag = ln(el.tag)
        ctx = el.get("contextRef")
        by_ctx[ctx].append((tag, el))
        ref_count[ctx] += 1
        first_any.setdefault(tag, (el.text or "").strip())

    # A1: dates per context
    periods = {}
    notes = []
    for ctx in by_ctx:
        s = e = None
        for tag, el in by_ctx[ctx]:
            if tag == "DateOfStartOfReportingPeriod" and s is None:
                s = parse_date(el.text)
            elif tag == "DateOfEndOfReportingPeriod" and e is None:
                e = parse_date(el.text)
        decl = declared.get(ctx, {})
        if s is None and decl.get("startDate"):
            s = decl["startDate"]
        if e is None and decl.get("endDate"):
            e = decl["endDate"]
        if e is not None and s is None:
            # A2 bank case
            if ctx.startswith("One"):
                s = quarter_start_ending(e)
                notes.append(f"A2 bank: {ctx} start derived {s}")
            else:
                continue
        if s is None and e is None and ctx.startswith("One") and "instant" not in decl:
            # A3 no-dates case
            rq = fys = None
            for tag, el in by_ctx[ctx]:
                if tag == "ReportingQuarter" and rq is None:
                    rq = (el.text or "").strip().lower()
                if tag == "DateOfStartOfFinancialYear" and fys is None:
                    fys = parse_date(el.text)
            if rq is not None and fys is not None:
                q = None
                for k, v in QUARTER_WORDS.items():
                    if rq.startswith(k):
                        q = v
                        break
                if q is not None:
                    s = add_months(fys, 3 * (q - 1))
                    e = add_months(s, 3) - dt.timedelta(days=1)
                    notes.append(f"A3 nodates: {ctx} from '{rq}' -> {s}..{e}")
        if s is None or e is None:
            continue
        periods[ctx] = (s, e)

    if not periods:
        raise ValueError("no duration context with resolvable dates")

    shortest = min((e - s).days for s, e in periods.values())
    tied = [c for c, (s, e) in periods.items() if (e - s).days == shortest]
    ones = [c for c in tied if c.startswith("One")]
    pool = ones if ones else tied
    pool_sorted = sorted(pool, key=lambda c: (-ref_count[c], c))
    cur = pool_sorted[0]
    if len(pool) > 1:
        # record what alternative tie-breaks would pick
        doc_order = [c for c in dict.fromkeys(el.get("contextRef") for el in facts) if c in pool]
        notes.append(f"A4 tie among {len(pool)} 'One*' ctx; picked {cur} (most facts={ref_count[cur]}); "
                     f"doc-order would pick {doc_order[0]}; alpha would pick {sorted(pool)[0]}")
    if not ones:
        notes.append(f"A4 no One* among shortest; picked {cur}")

    s, e = periods[cur]
    row = {"file": fname,
           "symbol": first_any.get("Symbol", ""),
           "isin": first_any.get("ISIN", ""),
           "period_start": s.isoformat(), "period_end": e.isoformat(),
           "context_id": cur}
    nat = first_any.get("NatureOfReportStandaloneConsolidated", "").strip().lower()
    row["consolidated"] = True if nat.startswith("consol") else (False if nat.startswith("stand") else "")

    cur_facts = by_ctx[cur]
    for name, chain, unit in FIELDS:
        val = math.nan
        for tag in chain:
            hits = [el for t, el in cur_facts if t == tag]
            if not hits:
                continue
            el = hits[0]
            if len(hits) > 1 and len({(h.text or '').strip() for h in hits}) > 1:
                notes.append(f"A7 dup {tag} differing values in {cur}")
            if el.get("unitRef") == unit:
                val = to_num(el.text)
            else:
                notes.append(f"A6 {name}: {tag} unit={el.get('unitRef')} -> NaN")
            if math.isnan(val):
                # would a later chain tag have given a value? (A5 audit)
                for t2 in chain[chain.index(tag) + 1:]:
                    h2 = [x for t, x in cur_facts if t == t2]
                    if h2 and h2[0].get("unitRef") == unit and not math.isnan(to_num(h2[0].text)):
                        notes.append(f"A5 {name}: {tag} NaN but later {t2} numeric")
                        break
            break
        row[name] = val
    for n in notes:
        LOG.append(f"{fname}: {n}")
    return row


def main():
    files = open(sys.argv[1]).read().split()
    out = sys.argv[2]
    rows, failed = [], []
    for p in files:
        try:
            rows.append(parse_file(p))
        except Exception as exc:  # noqa: BLE001
            failed.append((os.path.basename(p), repr(exc)))
    cols = ["file", "symbol", "isin", "period_start", "period_end", "context_id", "consolidated"] + \
           [f[0] for f in FIELDS]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if isinstance(r[k], float) and math.isnan(r[k]) else
                            (repr(r[k]) if isinstance(r[k], float) else r[k])) for k in cols})
    print(f"rows={len(rows)} failed={len(failed)}")
    for f in failed:
        print("FAILED", f)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w") as fh:
            fh.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
