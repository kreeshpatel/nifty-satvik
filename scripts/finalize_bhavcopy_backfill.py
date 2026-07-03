"""Finalize backfill step 2: turn the harvested RAW bhavcopy rows (data/_backfill_bhav_raw.pkl) into
usable series, run the corporate-action screen, merge everything into data/ohlcv_backfill.pkl, and update
the manifest + the scope CSV classification.

CA policy (leakage-audit §2 / W-01):
- RAW bhavcopy prices are unadjusted. Every |1d close move| > 40% is a cliff. A cliff whose ratio is a
  clean split/bonus factor (2, 2.5, 4, 5, 10 or inverses) AND is not in the demerger reference is treated
  as a SPLIT: prices before the cliff are back-adjusted by the factor (volume inversely). Any other cliff
  (demerger, relist, resolution-plan) is NOT adjusted — it is recorded in the manifest as
  `cliff_unadjusted` and left for the consumer to quarantine (back-adjusting a demerger fabricates trend).
- Bhavcopy series carry NO dividend adjustment (price-return only) — recorded per-series as
  `src=bhavcopy_raw`; the pinned cache is auto_adjust=True. Known, documented convention mismatch.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CLEAN_FACTORS = [2.0, 2.5, 4.0, 5.0, 10.0, 0.5, 0.4, 0.25, 0.2, 0.1]
DEMERGERS = pd.read_csv(ROOT / "data" / "corporate_actions_demergers.csv", comment="#")

# W-01 review overrides (owner-audited cliff classifications the heuristic gets wrong):
# - HSIL 2019-08-19: the SHIL/Brilloca DEMERGER (consumer business left) — ratio ~4.0 coincidentally clean;
#   back-adjusting would fabricate pre-2019 trend. Leave RAW.
# - INFIBEAM 2021-03-18: 1:1 bonus (true factor 2.0) + a same-day market move pushed the observed ratio to
#   ~2.33, outside the clean-factor tolerance. Adjust by exactly 2.0.
CA_OVERRIDES = {("HSIL", "2019-08-19"): "demerger_no_adjust",
                ("INFIBEAM", "2021-03-18"): 2.0}


def assemble(rows):
    df = pd.DataFrame(rows, columns=["date", "Open", "High", "Low", "Close", "Volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates("date").set_index("date").sort_index().astype(float)
    return df


def ca_screen(tkr, df):
    """Split-adjust clean-factor cliffs; record everything else. Returns (df, notes)."""
    notes = []
    changed = True
    while changed:                                       # handle multiple splits, latest first
        changed = False
        r = df["Close"].pct_change()
        cliffs = np.flatnonzero(np.abs(r.to_numpy()) > 0.40)
        for i in cliffs[::-1]:
            d = df.index[i]
            ratio = df["Close"].iloc[i - 1] / df["Close"].iloc[i]
            ov = CA_OVERRIDES.get((tkr, str(d.date())))
            demerged = ov == "demerger_no_adjust" or ((DEMERGERS["ticker"] == tkr)
                        & (pd.to_datetime(DEMERGERS["date"]) - d).abs().le(pd.Timedelta(days=7))).any()
            fac = ov if isinstance(ov, float) else next(
                (f for f in CLEAN_FACTORS if abs(ratio / f - 1) < 0.06), None)
            if fac and fac > 1 and not demerged:
                df.loc[:df.index[i - 1], ["Open", "High", "Low", "Close"]] /= fac
                df.loc[:df.index[i - 1], "Volume"] *= fac
                notes.append(f"split x{fac} adjusted at {d.date()}")
                changed = True
                break
            notes.append(f"cliff_unadjusted {d.date()} ratio {1/ratio:.2f}"
                         + (" (known demerger)" if demerged else ""))
    return df, notes


def main() -> int:
    raw = pickle.load(open(ROOT / "data" / "_backfill_bhav_raw.pkl", "rb"))
    bf = pickle.load(open(ROOT / "data" / "ohlcv_backfill.pkl", "rb"))
    man_p = ROOT / "data" / "ohlcv_backfill_manifest.json"
    man = json.load(open(man_p))
    man = {k: (v if isinstance(v, dict) else {}) for k, v in man.items()}
    for k in list(man):
        man[k].setdefault("src", "yfinance_live")
    # (1) old-symbol yfinance recoveries (stage2)
    stage2 = pickle.load(open(ROOT / "data" / "_backfill_stage2_raw.pkl", "rb"))
    for t, (suf, df) in stage2.items():
        bf[t] = df
        man[t] = dict(rows=len(df), first=str(df.index.min().date()), last=str(df.index.max().date()),
                      src=f"yfinance_oldsymbol{suf}")
    # (2) alias successors not in the pinned cache
    alias_fetch = pickle.load(open(ROOT / "data" / "_backfill_stage2_alias_fetch.pkl", "rb"))
    for t in ("LMW",):
        if t in alias_fetch:
            bf[t] = alias_fetch[t]
            man[t] = dict(rows=len(bf[t]), first=str(bf[t].index.min().date()),
                          last=str(bf[t].index.max().date()), src="yfinance_alias_successor")
    # (3) bhavcopy series (CA-screened). NSE-side GSPL/SPICEJET replace the .BO fallbacks.
    for t, rows in sorted(raw.items()):
        df = assemble(rows)
        if len(df) < 100:
            print(f"  {t:<12} only {len(df)} rows — SKIPPED (recorded unresolved)")
            continue
        df, notes = ca_screen(t, df)
        bf[t] = df
        man[t] = dict(rows=len(df), first=str(df.index.min().date()), last=str(df.index.max().date()),
                      src="bhavcopy_raw", ca_notes=notes)
        flag = " | ".join(n for n in notes) if notes else "clean"
        print(f"  {t:<12} {df.index.min().date()} -> {df.index.max().date()} rows {len(df):>5} | {flag}")
    pickle.dump(bf, open(ROOT / "data" / "ohlcv_backfill.pkl", "wb"))
    json.dump(man, open(man_p, "w"), indent=1)
    # (4) scope CSV classification + recovery accounting
    scope = pd.read_csv(ROOT / "diagnostics" / "research" / "delisted_backfill_scope.csv")
    alias = json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
    def classify(t):
        if t in alias:
            return "rename_alias", f"alias->{alias[t]['to']}", True
        if t in man and man[t]["src"].startswith("yfinance_live"):
            return "index_dropped_still_trading", "yfinance", True
        if t in man and man[t]["src"].startswith("yfinance_oldsymbol"):
            return "delisted_yf_retained", man[t]["src"], True
        if t in man and man[t]["src"] == "bhavcopy_raw":
            return "merged_or_delisted", "nse_bhavcopy", True
        return "unresolved", "", False
    scope[["class", "source", "resolved"]] = scope["ticker"].apply(lambda t: pd.Series(classify(t)))
    # coverage-weighted recovery: only the overlap of the recovered series with the membership window counts
    from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
    cache = load_ohlcv_cache(OHLCV_CACHE)
    def covered_days(r):
        t = r["ticker"]
        w0, w1 = pd.Timestamp(r["first"]), pd.Timestamp(r["last"])
        if t in alias:
            src = bf.get(alias[t]["to"]) if alias[t]["to"] in bf else cache.get(alias[t]["to"])
            s0, s1 = src.index.min(), src.index.max()
            if "valid_until" in alias[t]:
                s1 = min(s1, pd.Timestamp(alias[t]["valid_until"]))
        elif t in bf:
            s0, s1 = bf[t].index.min(), bf[t].index.max()
        else:
            return 0
        return max(0, (min(w1, s1) - max(w0, s0)).days)
    scope["covered_days"] = scope.apply(covered_days, axis=1)
    scope.to_csv(ROOT / "diagnostics" / "research" / "delisted_backfill_scope.csv", index=False)
    rec = scope["covered_days"].sum()
    tot = scope["member_days_in_window"].sum()
    print(f"\nresolved {int(scope['resolved'].sum())}/103 names | coverage-weighted member-days recovered "
          f"{rec:,}/{tot:,} = {100*rec/tot:.1f}%")
    worst = scope[scope["covered_days"] < 0.9 * scope["member_days_in_window"]]
    print("partial/missing coverage:")
    for _, r in worst.sort_values("member_days_in_window", ascending=False).head(15).iterrows():
        print(f"  {r['ticker']:<12} window {r['member_days_in_window']:>5}d covered {r['covered_days']:>5}d ({r['class']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
