"""Alias census for the corrected universe — Phase-1 detection + the fundamentals-reachability
readout. READ-ONLY: writes a report, mutates no artifact, touches no wall log.

Three questions, each answered from the committed pipeline:

  Q1 DETECTION  Is there an 18th alias pair hiding? Scan every symbol pair in the corrected
                universe for byte-identical or near-identical OVERLAPPING close series (ratio
                constant within tol across the overlap catches split/bonus back-adjustment, the
                same signature the 2026-07-03 alias validation used). The 17 known aliases are the
                seed; anything else the scan surfaces is new.

  Q2 CONCURRENCY Can an alias pair be held in two slots at once? Compares PIT membership windows
                per pair. Disjoint windows => the duplicate series can never compete with itself,
                and the materialization in corrected_universe() (old symbol -> successor series)
                is correct rather than double-counting.

  Q3 REACHABILITY Where does the solvency gate actually lose its data? value_quality_series()
                looks up the RAW ticker, so an alias old-symbol reads NaN even when the SAME
                company has full fundamentals under its successor symbol. Reports, per alias,
                whether the successor carries D/E — i.e. which names need an alias-aware lookup
                rather than a vendor harvest.

    python scripts/diag_alias_census.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

MIN_OVERLAP = 60        # trading days of shared history before a pair is judged
RATIO_TOL = 0.005       # constant-ratio tolerance (split/bonus back-adjustment signature)


def _compare(sa: pd.Series, sb: pd.Series) -> dict | None:
    """Constant-ratio test on the shared dates (a split/bonus back-adjustment shows up as a clean
    constant factor, which is exactly how the 2026-07-03 alias validation confirmed each pair)."""
    idx = sa.index.intersection(sb.index)
    if len(idx) < MIN_OVERLAP:
        return None
    ra = sa.loc[idx].to_numpy(float); rb = sb.loc[idx].to_numpy(float)
    m = (ra > 0) & (rb > 0)
    if m.sum() < MIN_OVERLAP:
        return None
    ratio = ra[m] / rb[m]
    med = float(np.median(ratio))
    if med <= 0:
        return None
    spread = float(np.max(np.abs(ratio / med - 1.0)))
    if spread > RATIO_TOL:
        return None
    return {"overlap_days": int(m.sum()), "ratio": round(med, 4), "max_dev": round(spread, 5)}


def detect_pairs(uni: dict) -> list[dict]:
    """Every symbol pair whose overlapping closes are a constant multiple of each other.

    A materialized alias IS the successor's series (optionally truncated by valid_until), so the two
    symbols share their first date, their last date, or both. Bucketing on those two keys turns an
    intractable 330k-pair sweep into a few small buckets while still covering every pair that the
    alias mechanism can produce. Documented bound: a pair sharing NEITHER endpoint (i.e. truncated at
    both ends relative to its twin) would not be compared — no such construction exists in
    corrected_universe(), which only ever truncates the tail.
    """
    ser = {t: df["Close"].dropna() for t, df in uni.items()
           if df is not None and len(df) and "Close" in df.columns}
    buckets: dict[tuple, list[str]] = {}
    for t, s in ser.items():
        buckets.setdefault(("first", s.index[0]), []).append(t)
        buckets.setdefault(("last", s.index[-1]), []).append(t)
    seen: set[frozenset] = set()
    out = []
    for names in buckets.values():
        if len(names) < 2:
            continue
        for i, a in enumerate(sorted(names)):
            for b in sorted(names)[i + 1:]:
                key = frozenset((a, b))
                if key in seen:
                    continue
                seen.add(key)
                r = _compare(ser[a], ser[b])
                if r:
                    out.append({"a": a, "b": b, **r})
    return sorted(out, key=lambda d: (d["a"], d["b"]))


def main() -> int:
    print("=== alias census (read-only) ===")
    uni = corrected_universe()
    pinned = load_ohlcv_cache(OHLCV_CACHE)
    mem = load_membership()
    fs = load_fund_store()
    amap = json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
    known = {frozenset((old, spec["to"])) for old, spec in amap.items()}
    print(f"universe {len(uni)} names | alias map {len(amap)} entries | recovered "
          f"{len(set(uni) - set(pinned))}")

    # ---- Q1 detection -----------------------------------------------------------------
    print(f"\n--- Q1 DETECTION (overlap >= {MIN_OVERLAP}d, constant ratio within {RATIO_TOL}) ---")
    pairs = detect_pairs(uni)
    novel = [p for p in pairs if frozenset((p["a"], p["b"])) not in known]
    print(f"constant-ratio pairs found: {len(pairs)} | already in the alias map: "
          f"{len(pairs) - len(novel)} | NOVEL: {len(novel)}")
    for p in pairs:
        tag = "NOVEL" if frozenset((p["a"], p["b"])) not in known else "known"
        print(f"  [{tag}] {p['a']:12s} {p['b']:12s} overlap {p['overlap_days']:5d}d  "
              f"ratio {p['ratio']:>8.4f}  max_dev {p['max_dev']:.5f}")
    # aliases the scan could NOT confirm (truncated by valid_until, or overlap too short)
    seen = {frozenset((p["a"], p["b"])) for p in pairs}
    unconfirmed = [sorted(k) for k in known if k not in seen]
    if unconfirmed:
        print(f"  alias pairs not surfaced by the scan (expected when valid_until truncates the "
              f"overlap): {[f'{a}/{b}' for a, b in unconfirmed]}")

    # ---- Q2 concurrency ---------------------------------------------------------------
    print("\n--- Q2 CONCURRENCY (PIT membership-window overlap per alias pair) ---")
    overlapping = []
    for old, spec in amap.items():
        new = spec["to"]
        ov = 0
        for a1, a2 in mem.get(old, []):
            for b1, b2 in mem.get(new, []):
                s, e = max(a1, b1), min(a2, b2)
                if e > s:
                    ov = max(ov, (e - s).days)
        if ov:
            overlapping.append((old, new, ov))
    print(f"alias pairs whose membership windows OVERLAP: {len(overlapping)} of {len(amap)}")
    for old, new, ov in overlapping:
        print(f"  OVERLAP {old} / {new}: {ov}d — concurrent holding POSSIBLE")
    if not overlapping:
        print("  -> every pair is disjoint in PIT time; one company can never occupy two slots,")
        print("     so the old-symbol materialization is correct, not double-counting.")

    # ---- Q3 reachability ---------------------------------------------------------------
    print("\n--- Q3 FUNDAMENTALS REACHABILITY (why the solvency gate loses these names) ---")

    def de_rows(t: str) -> int:
        d = fs.get(t)
        if d is None or len(d) == 0 or "debt_equity" not in d.columns:
            return 0
        return int(d["debt_equity"].notna().sum())

    fixable, harvest = [], []
    for old, spec in amap.items():
        new = spec["to"]
        o, n = de_rows(old), de_rows(new)
        (fixable if (o == 0 and n > 0) else harvest).append((old, new, o, n))
    print(f"alias names the gate loses purely to a NON-ALIAS-AWARE LOOKUP (successor has D/E): "
          f"{len(fixable)} — these need NO harvest, only an alias-aware fundamentals join")
    for old, new, o, n in fixable:
        print(f"  FIXABLE  {old:12s} (D/E rows {o}) <- {new:12s} (D/E rows {n})")
    print(f"alias names where NEITHER symbol has D/E (genuine harvest targets): {len(harvest)}")
    for old, new, o, n in harvest:
        print(f"  HARVEST  {old:12s} (D/E rows {o}) / {new:12s} (D/E rows {n})")

    recovered = sorted(set(uni) - set(pinned))
    alias_old = set(amap)
    genuine = [t for t in recovered if t not in alias_old]
    genuine_no_de = [t for t in genuine if de_rows(t) == 0]
    print(f"\nrecovered {len(recovered)} = alias old-symbols {len(recovered) - len(genuine)} + "
          f"non-alias {len(genuine)}")
    print(f"non-alias recovered names with NO D/E (the harvest list): {len(genuine_no_de)}")

    rep = {"universe": len(uni), "alias_entries": len(amap), "recovered": len(recovered),
           "detection": {"constant_ratio_pairs": pairs, "novel": novel,
                         "unconfirmed_aliases": [list(x) for x in unconfirmed]},
           "concurrency": {"overlapping_pairs": overlapping},
           "reachability": {"alias_fixable_by_lookup": [list(x) for x in fixable],
                            "alias_needs_harvest": [list(x) for x in harvest],
                            "non_alias_harvest_list": genuine_no_de}}
    out = ROOT / "diagnostics" / "research" / "alias_census.json"
    out.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nreport -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
