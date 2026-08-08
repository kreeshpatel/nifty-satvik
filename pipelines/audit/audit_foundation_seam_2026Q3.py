"""FOUNDATION AUDIT — layer 2b: where, exactly, does the pinned series change adjustment vintage?

Layer 1 found seven names whose implied adjustment factor ``adj(t) = pickle(t) / raw(t)`` FALLS as
time advances. No correct adjustment can do that: adjustments accumulate backwards, so ``adj`` is
non-decreasing toward the present and reaches 1 at the right edge. A fall means two segments of one
symbol's history are carrying DIFFERENT adjustment vintages, and the boundary between them is a
fabricated price step that no market event produced.

Layer 2 pass B found the same thing from the other direction, but only for steps large enough to
clear a 40% move. A rights-issue vintage seam is an 8% step and is invisible to that scan while
being just as fabricated.

This script localises each seam to the exact session by bisection against the exchange: ``adj`` is
measured on a date, and the interval where it changes is halved until one trading day remains. Each
bisection costs about eight bhavcopy fetches and returns a date that can be checked by hand.

The question it settles is mechanical, not statistical: **if the seams land on a common calendar
boundary, the cause is how the cache was assembled, not what any individual company did.**

Output: ``diagnostics/research/foundation_audit_2026Q3/layer2b_seams.json``.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = OUTDIR / "layer2b_seams.json"

STEP_TOL = 0.005          # 0.5% — below this two adj readings are the same vintage


def main() -> int:
    from audit_foundation_corpactions_2026Q3 import DayStore

    ohlcv = pickle.load(open(ROOT / "data" / "ohlcv.pkl", "rb"))
    store = DayStore(set(ohlcv))
    nd = pd.read_parquet(OUTDIR / "layer1_namedays.parquet").sort_values("date")

    # Candidate names: every symbol whose quarterly adj series falls anywhere. This is the full
    # population of the defect as layer 1 can see it, not a hand-picked list.
    cands = []
    for sym, g in nd.groupby("symbol"):
        r = g["ratio"].to_numpy()
        d = g["date"].to_numpy()
        for i in range(1, len(r)):
            if r[i] < r[i - 1] * (1 - STEP_TOL):
                cands.append({"symbol": sym, "lo": pd.Timestamp(d[i - 1]), "hi": pd.Timestamp(d[i]),
                              "adj_lo": float(r[i - 1]), "adj_hi": float(r[i])})
    print(f"downward adjustment steps to localise: {len(cands)}", flush=True)

    def adj_on(sym: str, d: pd.Timestamp):
        df = ohlcv[sym]
        idx = pd.DatetimeIndex(df.index)
        pos = idx.searchsorted(d, side="right") - 1        # last pinned bar on or before d
        if pos < 0:
            return None, None
        day = pd.Timestamp(idx[pos])
        raw = store.close(sym, day)
        return ((float(df["Close"].iloc[pos]) / raw) if raw else None), day

    out = []
    for c in cands:
        sym, lo, hi = c["symbol"], c["lo"], c["hi"]
        a_lo, a_hi = c["adj_lo"], c["adj_hi"]
        idx = pd.DatetimeIndex(ohlcv[sym].index)
        span = list(idx[(idx > lo) & (idx <= hi)])
        n_probe = 0
        # LOWER BOUND on the new vintage: the smallest session whose adj differs from the old
        # vintage. Written as a standard lower-bound search rather than an interval-shrinking loop —
        # the first version of this used the latter and terminated one session late, because the
        # final single-element span was never probed. Every seam it reported was therefore the day
        # AFTER the real one, and each of those days duly reconciled with the exchange, which would
        # have read as "the seam is benign". An off-by-one in an audit is not a cosmetic bug.
        l, r = 0, len(span) - 1
        while l < r:
            m = (l + r) // 2
            a_mid, _ = adj_on(sym, pd.Timestamp(span[m]))
            n_probe += 1
            if a_mid is None:                               # exchange silent: treat as old vintage
                l = m + 1
            elif abs(a_mid - a_lo) / a_lo <= STEP_TOL:      # still the old vintage
                l = m + 1
            else:                                           # already the new vintage
                r = m
        seam = pd.Timestamp(span[l])
        a_seam, _ = adj_on(sym, seam)
        if a_seam is not None:
            a_hi = a_seam
        pos = idx.get_loc(seam)
        prev = pd.Timestamp(idx[pos - 1])
        c_now, c_pr = float(ohlcv[sym]["Close"].iloc[pos]), float(ohlcv[sym]["Close"].iloc[pos - 1])
        raw_now, raw_pr = store.close(sym, seam), store.close(sym, prev)
        rec = {
            "symbol": sym, "seam_session": str(seam.date()), "prev_session": str(prev.date()),
            "adj_before": round(a_lo, 6), "adj_after": round(a_hi, 6),
            "step_factor": round(a_lo / a_hi, 6), "probes": n_probe,
            "series_return": round(c_now / c_pr - 1.0, 6),
            "exchange_return": None if not (raw_now and raw_pr) else round(raw_now / raw_pr - 1.0, 6),
            "seam_is_jan1": seam.month == 1 and seam.day == 1,
        }
        rec["fabricated_return"] = (None if rec["exchange_return"] is None
                                    else round(rec["series_return"] - rec["exchange_return"], 6))
        out.append(rec)
        print(f"  {sym:<12} seam {rec['seam_session']} (prev {rec['prev_session']}) "
              f"step x{rec['step_factor']:.4f} series {rec['series_return']:+.4f} vs exchange "
              f"{rec['exchange_return']} | jan1={rec['seam_is_jan1']}", flush=True)
    store.flush()

    # ── year-boundary census ───────────────────────────────────────────────────────────────────
    # The quarterly sample can only see a seam that is not cancelled by a real corporate action
    # inside the same inter-sample window, so it is a lower bound on the defect. Because most of the
    # localised seams land on 1 January, that dominant class can be closed COMPLETELY and cheaply:
    # probe adj() on the last session of each year and the first of the next, for every name. Two
    # exchange sessions per year boundary covers all 710 names at once.
    census = []
    for yr in range(2018, 2027):
        nxt = pd.Timestamp(f"{yr}-01-01")
        for sym, df in ohlcv.items():
            idx = pd.DatetimeIndex(df.index)
            pos = idx.searchsorted(nxt, side="left")
            if pos == 0 or pos >= len(idx):
                continue
            d_after, d_before = pd.Timestamp(idx[pos]), pd.Timestamp(idx[pos - 1])
            if (d_after - d_before).days > 10 or d_after.year != yr:
                continue
            a_af = adj_on(sym, d_after)[0]
            a_bf = adj_on(sym, d_before)[0]
            if a_af is None or a_bf is None or a_bf == 0:
                continue
            step = a_bf / a_af
            if step > 1 + STEP_TOL:                 # adj FELL across the boundary: a vintage seam
                c_af = float(df["Close"].iloc[pos])
                c_bf = float(df["Close"].iloc[pos - 1])
                raw_af, raw_bf = store.close(sym, d_after), store.close(sym, d_before)
                census.append({
                    "symbol": sym, "boundary": str(d_after.date()),
                    "prev_session": str(d_before.date()), "step_factor": round(step, 6),
                    "series_return": round(c_af / c_bf - 1.0, 6),
                    "exchange_return": (None if not (raw_af and raw_bf)
                                        else round(raw_af / raw_bf - 1.0, 6)),
                })
                print(f"  YEAR-BOUNDARY {sym:<12}{d_after.date()} x{step:.4f} "
                      f"series {census[-1]['series_return']:+.4f} vs exchange "
                      f"{census[-1]['exchange_return']}", flush=True)
        print(f"  year {yr} boundary scanned", flush=True)
    store.flush()

    jan1 = sum(1 for r in out if r["seam_is_jan1"])
    res = {
        "_class": "VERIFICATION — layer 2b vintage-seam localisation",
        "method": "bisection on adj(t) = pickle(t)/raw(t) against NSE bhavcopy, halving the "
                  "interval between two quarterly samples until one session remains",
        "seams_found": len(out),
        "seams_on_january_1": jan1,
        "seams": sorted(out, key=lambda r: r["seam_session"]),
        "year_boundary_census": {
            "_note": "complete over the pinned universe x every year boundary 2018..2026 — this "
                     "class is closed, not sampled",
            "seams": sorted(census, key=lambda r: (r["boundary"], r["symbol"])),
            "n": len(census),
        },
    }
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"\nseams {len(out)} | on 1 January: {jan1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
