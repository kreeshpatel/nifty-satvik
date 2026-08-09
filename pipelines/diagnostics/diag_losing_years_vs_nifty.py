"""MEASUREMENT (no trial): do the book's losing years coincide with the index's?

The owner's stated reason for accepting losing years, 2026-08-09: *"nifty will be negative in that
year and we have to overlook something."* That is a testable claim about WHEN the book loses, and it
decides how hard the losing years are to sit through. A year where everyone lost money is a
different experience from a year where the index rose and this book did not.

Reads the committed per-year table (`diag_per_year_returns.py`) against the **benchmark of record**
-- NIFTY 500 gross TRI, designated by `research/exports/benchmark_manifest.json` and the series this
book's beta and alpha are computed against. NIFTY-50 price return is reported alongside as a
secondary reference; it is the CRS denominator, not the benchmark, and using it as one is what made
an earlier version of this file report "zero overlap" when the true figure is 1 of 3.

No new data and no new run.

    python pipelines/diagnostics/diag_losing_years_vs_nifty.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PER_YEAR = ROOT / "diagnostics" / "research" / "per_year_returns.json"
# The BENCHMARK OF RECORD, per research/exports/benchmark_manifest.json: NIFTY 500 gross TRI,
# aligned to daily_returns.csv, and the series against which this book's beta (1.116) and alpha
# (2.52%) are computed. An earlier version of this file used benchmark_nifty50.csv -- the CRS
# DENOMINATOR, not the benchmark -- and concluded "zero overlap". That was wrong: against the
# designated index 2018 is -2.14%, a genuine market-down year, and the overlap is 1 of 3.
TRI = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"
NIFTY50 = ROOT / "research" / "exports" / "benchmark_nifty50.csv"
OUT_MD = ROOT / "diagnostics" / "research" / "losing_years_vs_nifty.md"


def _years(path, col, start: str, end: str) -> dict[int, float]:
    """Calendar-year returns of an index series, chained year-end over year-end."""
    s = pd.read_csv(path, parse_dates=["date"]).set_index("date")[col]
    s = s[(s.index >= start) & (s.index <= end)].sort_index()
    g = s.groupby(s.index.year)
    out, prev = {}, None
    for y, v in g.last().items():
        base = prev if prev is not None else g.first()[y]
        out[int(y)] = round((v / base - 1) * 100, 2)
        prev = v
    return out


def nifty_years(start: str, end: str) -> dict[int, float]:
    """The benchmark of record: NIFTY 500 gross TRI."""
    return _years(TRI, "tri_close", start, end)


def main() -> int:
    data = json.load(PER_YEAR.open(encoding="utf-8"))
    nif = nifty_years("2017-01-01", "2026-06-30")
    nif50 = _years(NIFTY50, "nifty50_close", "2017-01-01", "2026-06-30")
    # The TRI series starts 2017-09-14 (manifest strategy_dates), so its 2017 row is a PARTIAL year
    # and is not comparable to a full book year. Flagged, not silently annualised.

    md = ["# Do the book's losing years coincide with the index's? (MEASUREMENT, no trial)", "",
          "Tests the stated premise for accepting losing years — *\"nifty will be negative in that "
          "year and we have to overlook something\"*.", ""]
    print(f"{'year':14s} {'NIFTY 500 TRI':>10s}  " + "  ".join(f"{b['book'][:22]:>24s}" for b in data["books"]))

    rows_all = {}
    for b in data["books"]:
        rows_all[b["book"]] = {r["year"]: r for r in b["years"]}

    md += ["| year | **NIFTY 500 TRI** | NIFTY-50 (px) | "
           + " | ".join(f"{b['book']} (after tax)" for b in data["books"]) + " |",
           "|---|--:|--:|" + "--:|" * len(data["books"])]
    for y in sorted(nif):
        cells = []
        for b in data["books"]:
            r = rows_all[b["book"]].get(y)
            cells.append(f"{r['after_tax_pct']:+.2f}%" if r else "—")
        part = " *(partial)*" if any((rows_all[b["book"]].get(y) or {}).get("partial")
                                     for b in data["books"]) else ""
        md.append(f"| {y}{part} | **{nif[y]:+.2f}%** | {nif50.get(y, float('nan')):+.2f}% | "
                  + " | ".join(cells) + " |")
        print(f"{y}{part:10s} {nif[y]:+9.2f}%  " + "  ".join(f"{c:>24s}" for c in cells))

    nifty_down = [y for y, v in nif.items() if v < 0]
    md += ["", f"**NIFTY 500 TRI losing years:** {nifty_down or 'none'}  (2017 is a PARTIAL TRI year — series starts 2017-09-14)", ""]
    print(f"\nNIFTY 500 TRI losing years: {nifty_down or 'none'}")

    for b in data["books"]:
        lose = b["losing_years_after_tax"]
        overlap = sorted(set(lose) & set(nifty_down))
        divergent = sorted(set(lose) - set(nifty_down))
        md.append(f"- **{b['book']}** — losing years {lose}; of those, **{len(overlap)}** coincide "
                  f"with a TRI decline and **{len(divergent)}** occurred while the index ROSE "
                  f"({divergent}).")
        print(f"  {b['book']}: {len(overlap)} coincide with TRI down, "
              f"{len(divergent)} while the TRI ROSE {divergent}")

    md += ["", "## Reading", "",
           "Against the benchmark of record the premise **partly holds**. 2018 — the book's worst year — "
           "was a genuine market decline (TRI −2.14%), so one of the three losing years is the "
           "market-wide kind the owner said they would overlook. The other two, 2022 and 2025, are "
           "not: the index rose and this book did not.", "",
           "That split is the expected shape. Momentum and swing books do not lose money in bear "
           "markets so much as in **reversals** — the Daniel-Moskowitz result that crashes cluster "
           "in panic-and-rebound states rather than in declines. 2025 in particular was a midcap "
           "reversal inside a rising large-cap year, which is this family's worst regime.", "",
           "Reproduce: `python pipelines/diagnostics/diag_losing_years_vs_nifty.py`"]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
