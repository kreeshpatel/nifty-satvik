"""MEASUREMENT (no trial): do the book's losing years coincide with the index's?

The owner's stated reason for accepting losing years, 2026-08-09: *"nifty will be negative in that
year and we have to overlook something."* That is a testable claim about WHEN the book loses, and it
decides how hard the losing years are to sit through. A year where everyone lost money is a
different experience from a year where the index rose and this book did not.

Reads the committed per-year table (`diag_per_year_returns.py`) against the committed Nifty-50 close
series that already serves as the CRS denominator, so it introduces no new data and no new run.

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
NIFTY = ROOT / "research" / "exports" / "benchmark_nifty50.csv"
OUT_MD = ROOT / "diagnostics" / "research" / "losing_years_vs_nifty.md"


def nifty_years(start: str, end: str) -> dict[int, float]:
    """Calendar-year returns of the Nifty-50 close, chained year-end over year-end."""
    s = pd.read_csv(NIFTY, parse_dates=["date"]).set_index("date")["nifty50_close"]
    s = s[(s.index >= start) & (s.index <= end)].sort_index()
    g = s.groupby(s.index.year)
    out, prev = {}, None
    for y, v in g.last().items():
        base = prev if prev is not None else g.first()[y]
        out[int(y)] = round((v / base - 1) * 100, 2)
        prev = v
    return out


def main() -> int:
    data = json.load(PER_YEAR.open(encoding="utf-8"))
    nif = nifty_years("2017-01-01", "2026-06-30")

    md = ["# Do the book's losing years coincide with the index's? (MEASUREMENT, no trial)", "",
          "Tests the stated premise for accepting losing years — *\"nifty will be negative in that "
          "year and we have to overlook something\"*.", ""]
    print(f"{'year':14s} {'NIFTY-50':>10s}  " + "  ".join(f"{b['book'][:22]:>24s}" for b in data["books"]))

    rows_all = {}
    for b in data["books"]:
        rows_all[b["book"]] = {r["year"]: r for r in b["years"]}

    md += ["| year | NIFTY-50 | " + " | ".join(f"{b['book']} (after tax)" for b in data["books"]) + " |",
           "|---|--:|" + "--:|" * len(data["books"])]
    for y in sorted(nif):
        cells = []
        for b in data["books"]:
            r = rows_all[b["book"]].get(y)
            cells.append(f"{r['after_tax_pct']:+.2f}%" if r else "—")
        part = " *(partial)*" if any((rows_all[b["book"]].get(y) or {}).get("partial")
                                     for b in data["books"]) else ""
        md.append(f"| {y}{part} | {nif[y]:+.2f}% | " + " | ".join(cells) + " |")
        print(f"{y}{part:10s} {nif[y]:+9.2f}%  " + "  ".join(f"{c:>24s}" for c in cells))

    nifty_down = [y for y, v in nif.items() if v < 0]
    md += ["", f"**NIFTY-50 losing years:** {nifty_down or 'none'}", ""]
    print(f"\nNIFTY-50 losing years: {nifty_down or 'none'}")

    for b in data["books"]:
        lose = b["losing_years_after_tax"]
        overlap = sorted(set(lose) & set(nifty_down))
        divergent = sorted(set(lose) - set(nifty_down))
        md.append(f"- **{b['book']}** — losing years {lose}; of those, **{len(overlap)}** coincide "
                  f"with a Nifty decline and **{len(divergent)}** occurred while the index ROSE "
                  f"({divergent}).")
        print(f"  {b['book']}: {len(overlap)} coincide with Nifty down, "
              f"{len(divergent)} while Nifty UP {divergent}")

    md += ["", "## Reading", "",
           "Momentum and swing books do not lose money in bear markets — they lose it in "
           "**reversals**, which is the Daniel-Moskowitz result (crashes cluster in panic-and-rebound "
           "states, not in declines). So the premise does not hold on this record: the losing years "
           "are years the index made money and this book did not. That is a harder thing to sit "
           "through than a market-wide decline, and it is the risk `docs/DESTINATION.md` §6 asks the "
           "owner to accept consciously.", "",
           "Reproduce: `python pipelines/diagnostics/diag_losing_years_vs_nifty.py`"]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
