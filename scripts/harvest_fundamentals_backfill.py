"""Phase-3 fundamentals backfill for the recovered-delisted names — approved work order
(diagnostics/research/lh_fundamentals_backfill_work_order.md), owner sign-off 2026-07-29.

Harvests D/E (+ roe, eps_ttm, book_value_ps) for the recovered names that the solvency gate
currently drops for want of data, via the PRODUCTION screener path (same fetch, same parser, same
PIT convention as data/fundamentals_pit_screener.pkl).

PIN UNTOUCHED. Writes a DATED artifact — data/fundamentals_pit_backfill_<stamp>.pkl — plus a
coverage report. Merging it into the pinned store is September's governance call, not this script's.

Gating: scripts/probe_screener_coverage.py must pass first (the failures stop-clause). Run:

    python scripts/harvest_fundamentals_backfill.py --stamp 20260729            # full list
    python scripts/harvest_fundamentals_backfill.py --stamp 20260729 --limit 5  # smoke
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.fundamentals import ANNUAL_REPORTING_LAG_DAYS  # noqa: E402
from scrape_screener import DEFAULT_CACHE, fetch_html, frame_from_html  # noqa: E402

CENSUS = ROOT / "diagnostics" / "research" / "alias_census.json"
# The 4 alias pairs where NEITHER symbol has D/E: harvest the SUCCESSOR symbol (the live page),
# then the alias-aware join reaches it from the old symbol. Census Q3 "alias_needs_harvest".
FAILURES = {"JETAIRWAYS", "DHFL", "MANPASAND", "RNAVAL", "GVKPIL", "SREINFRA", "JPASSOCIAT",
            "RCOM", "8KMILES", "COFFEEDAY", "LAKSHVILAS", "FCONSUMER", "FRETAIL", "HCC"}


def targets() -> tuple[list[str], list[str]]:
    rep = json.loads(CENSUS.read_text(encoding="utf-8"))
    non_alias = list(rep["reachability"]["non_alias_harvest_list"])
    succ = [pair[1] for pair in rep["reachability"]["alias_needs_harvest"]]
    return non_alias, succ


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default="20260729")
    ap.add_argument("--sleep", type=float, default=2.5)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    non_alias, succ = targets()
    syms = non_alias + succ
    if a.limit:
        syms = syms[: a.limit]
    print(f"=== fundamentals backfill harvest (pin untouched) ===")
    print(f"targets: {len(non_alias)} non-alias recovered + {len(succ)} alias successors "
          f"({succ}) = {len(syms)}")

    got: dict[str, pd.DataFrame] = {}
    empty: list[str] = []
    nopage: list[str] = []
    for i, t in enumerate(syms):
        html, src = fetch_html(t, cache_dir=Path(DEFAULT_CACHE), sleep=a.sleep, use_cache=True)
        if html is None:
            nopage.append(t)
        else:
            try:
                fr = frame_from_html(html)
            except Exception as e:                                # noqa: BLE001
                print(f"  parse error {t}: {e!r}", flush=True)
                fr = None
            if fr is not None and not fr.empty:
                got[t] = fr
            else:
                empty.append(t)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(syms)}; {len(got)} with data", flush=True)

    # ---- PIT assertion (the contract, enforced not assumed) ---------------------------
    bad = []
    for t, fr in got.items():
        if "period_end" not in fr.columns:
            bad.append((t, "no period_end"))
            continue
        lag = (pd.to_datetime(pd.Series(fr.index.values))
               - pd.to_datetime(fr["period_end"]).reset_index(drop=True)).dt.days
        if (lag < ANNUAL_REPORTING_LAG_DAYS).any():
            bad.append((t, f"available_date lag < {ANNUAL_REPORTING_LAG_DAYS}d"))
    print(f"\nPIT check: {len(got) - len(bad)}/{len(got)} frames satisfy "
          f"available_date >= period_end + {ANNUAL_REPORTING_LAG_DAYS}d")
    for t, why in bad:
        print(f"  PIT VIOLATION {t}: {why}")
    if bad:
        print("REFUSING to write: a PIT violation would inject look-ahead into the gate.")
        return 1

    out = ROOT / "data" / f"fundamentals_pit_backfill_{a.stamp}.pkl"
    with open(out, "wb") as f:
        pickle.dump(got, f)

    with_de = {t: int(fr["debt_equity"].notna().sum()) for t, fr in got.items()
               if "debt_equity" in fr.columns}
    de_ok = {t: n for t, n in with_de.items() if n > 0}
    fail_in = [t for t in syms if t in FAILURES]
    fail_ok = [t for t in fail_in if t in de_ok]
    print(f"\n=== COVERAGE ===")
    print(f"names harvested with usable rows: {len(got)}/{len(syms)}")
    print(f"names with >=1 D/E period:        {len(de_ok)}/{len(syms)}")
    print(f"total periods recovered:          {sum(len(fr) for fr in got.values())}")
    print(f"FAILURE-class names in list: {len(fail_in)} | with D/E: {len(fail_ok)} "
          f"({100*len(fail_ok)/len(fail_in):.0f}%)" if fail_in else "no failure names in list")
    print(f"vendor has NOTHING (remain gate-excluded): {len(nopage) + len(empty)}")
    print(f"  no page: {sorted(nopage)}")
    print(f"  page but no usable rows: {sorted(empty)}")

    rep = {"stamp": a.stamp, "artifact": out.name, "targets": len(syms),
           "harvested": len(got), "with_de": len(de_ok),
           "periods": int(sum(len(fr) for fr in got.values())),
           "failure_names": fail_in, "failure_with_de": fail_ok,
           "no_page": sorted(nopage), "empty": sorted(empty),
           "de_rows_by_name": de_ok}
    rp = ROOT / "diagnostics" / "research" / f"fundamentals_backfill_coverage_{a.stamp}.json"
    rp.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)} + {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
