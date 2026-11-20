"""Blind replica of one week of the 60/40 forward record (spec part D), record Friday 2026-11-20 as a first week.

Usage: python benchmark_week_replica.py <dir with 150738.json and 119771.json fetched from api.mfapi.in>
Writes diagnostics/replica/phase0/benchmark_week_replica.json.
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

FRIDAY = date(2026, 11, 20)
CAPITAL = 2_000_000.0
STAMP = 0.00005
STT = 0.00001
STCG, LTCG, LT_EXEMPT, CESS = 0.20, 0.125, 125_000.0, 0.04
OUT = Path(__file__).resolve().parent / "benchmark_week_replica.json"


def nav_asof(path):
    data = json.load(open(path, encoding="utf-8"))["data"]
    best = None
    for r in data:
        d = datetime.strptime(r["date"], "%d-%m-%Y").date()
        if d <= FRIDAY and (best is None or d > best[0]):
            best = (d, float(r["nav"]))
    return best


def main(src):
    di, ni = nav_asof(Path(src) / "150738.json")
    da, na = nav_asof(Path(src) / "119771.json")
    cash = CAPITAL
    lots = {"idx": [], "arb": []}       # FIFO lots: (buy_date, units, cost)
    for k, v, nav in (("idx", 0.6 * CAPITAL, ni), ("arb", 0.4 * CAPITAL, na)):
        cash -= v * (1 + STAMP)
        lots[k].append((FRIDAY, v / nav, v))   # cost basis = traded value (stamp not capitalised)
    navs = {"idx": ni, "arb": na}
    val = {k: sum(u for _, u, _ in lots[k]) * navs[k] for k in lots}
    pre = cash + sum(val.values())
    # liquidate FIFO at this week's NAV
    st_gain = lt_gain = 0.0
    c2 = cash
    for k in lots:
        for bd, u, cost in lots[k]:
            proceeds = u * navs[k] * (1 - STT)
            c2 += proceeds
            g = proceeds - cost
            if (FRIDAY - bd).days <= 365:
                st_gain += g
            else:
                lt_gain += g
    # set-off within FY: ST loss offsets ST then LT; LT loss offsets LT only
    if st_gain < 0:
        lt_gain += st_gain
        st_gain = 0.0
    tax = (max(st_gain, 0) * STCG + max(lt_gain - LT_EXEMPT, 0) * LTCG) * (1 + CESS)
    after = c2 - tax
    out = {"nav_index": ni, "nav_index_date": di.isoformat(), "nav_arbitrage": na,
           "nav_arbitrage_date": da.isoformat(), "pre_tax_nav": round(pre, 6), "after_tax_nav": round(after, 6),
           "index_weight": val["idx"] / pre,
           "status": "STALE" if (FRIDAY - di).days > 3 or (FRIDAY - da).days > 3 else "OK",
           "_detail": {"cash_after_buys": cash, "tax": tax, "st_gain": st_gain, "lt_gain": lt_gain,
                       "index_weight_ex_cash": val["idx"] / sum(val.values())}}
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
