"""Phase-3 step-1 coverage probe for the approved fundamentals backfill — REPORT ONLY.

Fetches a named sample of recovered symbols through the production screener path and reports what
D/E history the vendor actually has. Writes NOTHING to the fundamentals store; the pin is untouched.

The stop-clause this exists to enforce (work order §3): the sample is deliberately loaded with
FAILURES (JETAIRWAYS, DHFL, MANPASAND, RNAVAL). If the vendor systematically has the healthy names
and not the failed ones, a full harvest would recover only the survivors of the survivors and bias
the corrected anchor UPWARD — the opposite of the correction's purpose. In that case: STOP, report,
do not harvest.

    python scripts/probe_screener_coverage.py
    python scripts/probe_screener_coverage.py --symbols A,B,C
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from scrape_screener import DEFAULT_CACHE, fetch_html, frame_from_html  # noqa: E402

# 10 names spanning the failure / merger / rename mix, per the work order.
FAILURES = ["JETAIRWAYS", "DHFL", "MANPASAND", "RNAVAL"]
OTHERS = ["ALBK", "MINDTREE", "HEXAWARE", "THYROCARE", "RELCAPITAL", "TATAMTRDVR"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="")
    ap.add_argument("--sleep", type=float, default=2.5)
    a = ap.parse_args()
    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()] or (FAILURES + OTHERS)

    print("=== screener coverage probe (report only; store NOT written) ===")
    print(f"sample: {len(syms)} names | failures in sample: "
          f"{[s for s in syms if s in FAILURES]}\n")
    rows = []
    for s in syms:
        html, src = fetch_html(s, cache_dir=Path(DEFAULT_CACHE), sleep=a.sleep, use_cache=True)
        if html is None:
            rows.append((s, src, 0, 0, "-"))
            print(f"  {s:12s} [{src:6s}] NO PAGE")
            continue
        try:
            fr = frame_from_html(html)
        except Exception as e:                                    # noqa: BLE001
            rows.append((s, src, 0, 0, f"parse-error {type(e).__name__}"))
            print(f"  {s:12s} [{src:6s}] PARSE ERROR {type(e).__name__}")
            continue
        if fr is None or len(fr) == 0:
            rows.append((s, src, 0, 0, "empty"))
            print(f"  {s:12s} [{src:6s}] page but NO usable rows")
            continue
        n = len(fr)
        de = int(fr["debt_equity"].notna().sum()) if "debt_equity" in fr.columns else 0
        span = f"{str(fr.index.min())[:10]}..{str(fr.index.max())[:10]}"
        rows.append((s, src, n, de, span))
        print(f"  {s:12s} [{src:6s}] {n:3d} rows | {de:3d} with D/E | {span}")

    fail_rows = [r for r in rows if r[0] in FAILURES]
    ok_fail = [r for r in fail_rows if r[3] > 0]
    other_rows = [r for r in rows if r[0] not in FAILURES]
    ok_other = [r for r in other_rows if r[3] > 0]
    print(f"\n--- VERDICT ---")
    print(f"failures with D/E: {len(ok_fail)}/{len(fail_rows)} | "
          f"others with D/E: {len(ok_other)}/{len(other_rows)}")
    if not fail_rows:
        print("no failure names in the sample — probe inconclusive by construction")
    elif len(ok_fail) == 0:
        print("STOP-CLAUSE TRIGGERED: the vendor has none of the failures. A harvest would recover")
        print("only healthy names and bias the corrected anchor upward. Do NOT harvest; report.")
    elif len(ok_fail) < len(fail_rows) / 2:
        print("STOP-CLAUSE WARNING: failure coverage is under half. Escalate to the owner before")
        print("harvesting — a partial, survivor-skewed backfill is worse than none.")
    else:
        print("PROBE PASSES: failure coverage is comparable to the rest; harvest is defensible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
