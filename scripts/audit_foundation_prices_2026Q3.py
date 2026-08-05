"""FOUNDATION AUDIT — layer 1: is the pinned pickle what the exchange published?

Compares ``data/ohlcv.pkl`` (pin ``dataset-pin-20260701``) against authoritative NSE cash bhavcopy
harvested by ``audit_foundation_bhavcopy_2026Q3.py``, on 30 trading days — one per quarter,
2019Q1..2026Q2 — for every symbol in the pinned universe that the exchange listed that day.

Two questions are deliberately kept apart, because they fail differently:

1. **Price truth.** On a given session, does the pickle report the OHLC the exchange reported? This
   is a per-name-day equality test against raw exchange prices.
2. **Adjustment.** Where the pickle differs from raw, is the difference an *adjustment* — a
   monotone, piecewise-constant rescaling of the history — or is it noise? A vendor-adjusted series
   is SUPPOSED to differ from raw in the past. The audit therefore measures the implied factor
   ``pickle_close / bhav_close`` and asks whether it behaves like an adjustment factor should:
   bounded by 1 at the right edge, non-decreasing as it approaches the present, and constant
   between corporate actions.

The second question is where the real information is, and it has a trap that must be stated up
front: **a series with an UNADJUSTED split agrees perfectly with raw bhavcopy on both sides of the
split.** Price truth passes; the series is still broken, because it is discontinuous. Layer 1 cannot
see that by construction. Layer 2 (``audit_foundation_corpactions_2026Q3.py``) exists for exactly
that blind spot, using the exchange's own re-based PREVCLOSE as the receipt.

Strata are reported separately because a defect concentrated in the names that carry the book's P&L
matters more than the same defect spread over names the book never traded:
  * ``book``      — the five names in the live paper book (results/paper_portfolio_weekly.json)
  * ``top_decile``— the top decile of historical names by summed R (research/substrate/trades.parquet)
  * ``rest``      — everything else in the pinned universe (the random-sample stratum; the sample is
                    every listed name on the sampled dates, so it is a census of the stratum, not a draw)

Output: ``diagnostics/research/foundation_audit_2026Q3/layer1_prices.json``.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
SAMPLE = OUTDIR / "bhavcopy_sample.parquet"
OUT = OUTDIR / "layer1_prices.json"

# Exchange prices are published to 2 dp. A pickle bar "agrees" when every one of O/H/L/C matches to
# the paise — the exchange's own precision. This is an equality test, not a tolerance: anything
# looser would let a real adjustment hide inside the band.
PAISA = 0.005


def _strata() -> dict[str, set[str]]:
    book = set(json.loads((ROOT / "results" / "paper_portfolio_weekly.json")
                          .read_text(encoding="utf-8"))["positions"])
    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr = tr[tr["entry_date"] >= "2019-01-01"]
    by_r = tr.groupby("ticker")["R"].sum().sort_values(ascending=False)
    top = set(by_r.head(max(1, int(round(len(by_r) * 0.10)))).index)
    return {"book": book, "top_decile": top - book}


def main() -> int:
    bhav = pd.read_parquet(SAMPLE)
    ohlcv = pickle.load(open(ROOT / "data" / "ohlcv.pkl", "rb"))
    strata = _strata()

    rows = []
    for sym, grp in bhav.groupby("symbol", sort=True):
        df = ohlcv.get(sym)
        if df is None:
            continue
        idx = pd.DatetimeIndex(df.index)
        stratum = ("book" if sym in strata["book"]
                   else "top_decile" if sym in strata["top_decile"] else "rest")
        for _, b in grp.iterrows():
            d = pd.Timestamp(b["date"])
            if d not in idx:
                rows.append({"symbol": sym, "date": d, "stratum": stratum, "present": False})
                continue
            p = df.loc[d]
            rec = {"symbol": sym, "date": d, "stratum": stratum, "present": True,
                   "series": b["series"]}
            for k, col in (("open", "Open"), ("high", "High"), ("low", "Low"),
                           ("close", "Close")):
                rec[f"pk_{k}"] = float(p[col])
                rec[f"ex_{k}"] = float(b[k])
            rec["pk_vol"] = float(p["Volume"])
            rec["ex_vol"] = float(b["volume"])
            rec["ratio"] = (rec["pk_close"] / rec["ex_close"]) if rec["ex_close"] > 0 else np.nan
            rec["exact"] = all(abs(rec[f"pk_{k}"] - rec[f"ex_{k}"]) < PAISA
                               for k in ("open", "high", "low", "close"))
            rows.append(rec)

    R = pd.DataFrame(rows)
    cmp = R[R["present"]].copy()

    # ── the adjustment-factor reading ──────────────────────────────────────────────────────────
    # A vendor-adjusted series has ratio <= 1 in the past (adjustments only ever remove value going
    # backwards) rising to exactly 1 at the right edge. Deviations ABOVE 1 cannot be an adjustment
    # and are the interesting cell.
    cmp["ratio_dev_bps"] = (cmp["ratio"] - 1.0) * 1e4

    def _agg(g: pd.DataFrame) -> dict:
        return {
            "name_days": int(len(g)),
            "symbols": int(g["symbol"].nunique()),
            "exact_ohlc": int(g["exact"].sum()),
            "exact_pct": round(100.0 * g["exact"].mean(), 4),
            "ratio_median": round(float(g["ratio"].median()), 8),
            "ratio_p01": round(float(g["ratio"].quantile(0.01)), 6),
            "ratio_p99": round(float(g["ratio"].quantile(0.99)), 6),
            "ratio_above_1_plus_1bp": int((g["ratio_dev_bps"] > 1).sum()),
            "ratio_below_1_minus_1bp": int((g["ratio_dev_bps"] < -1).sum()),
            "vol_exact": int((g["pk_vol"] == g["ex_vol"]).sum()),
            "vol_within_0p1pct": int((abs(g["pk_vol"] - g["ex_vol"])
                                      <= 0.001 * g["ex_vol"].clip(lower=1)).sum()),
        }

    by_year = {str(y): _agg(g) for y, g in cmp.groupby(cmp["date"].dt.year)}
    by_stratum = {s: _agg(g) for s, g in cmp.groupby("stratum")}

    # ── per-symbol reconcilability ─────────────────────────────────────────────────────────────
    # A symbol is RECONCILED when its ratio series is a possible adjustment path: never materially
    # ABOVE 1 (an adjustment only ever removes value going backwards) and never FALLING as time
    # advances (adjustments accumulate toward the present).
    #
    # An earlier version also demanded ratio == 1 on the last SAMPLED date and reported 116 names as
    # unreconciled. That criterion was wrong, not strict: the last sample is 2026-05-15 while the pin
    # closes 2026-06-29, so any name that went ex-dividend in between correctly sits below raw on the
    # sampled date. Edge behaviour is now DESCRIBED (`edge_exact`) rather than used to convict.
    per_sym = []
    for sym, g in cmp.sort_values("date").groupby("symbol"):
        last = g.iloc[-1]
        above = int((g["ratio_dev_bps"] > 25).sum())          # >25bp above raw: not an adjustment
        # Monotonicity is asserted only on the ADJUSTED portion; a fully-raw series (ratio==1
        # throughout) is trivially monotone and is classified by its edge behaviour instead.
        r = g["ratio"].to_numpy()
        drops = int((np.diff(r) < -25e-4).sum())              # factor falling as time advances
        per_sym.append({
            "symbol": sym, "stratum": g["stratum"].iloc[0], "n": int(len(g)),
            "exact_pct": round(100.0 * g["exact"].mean(), 2),
            "ratio_first": round(float(r[0]), 6), "ratio_last": round(float(r[-1]), 6),
            "edge_exact": bool(last["exact"]),
            "n_ratio_above_raw": above, "n_ratio_falls_forward": drops,
            "reconciled": bool(above == 0 and drops == 0),
        })
    P = pd.DataFrame(per_sym)
    unrec = P[~P["reconciled"]].sort_values(["n_ratio_above_raw", "n_ratio_falls_forward"],
                                            ascending=False)

    res = {
        "_class": "VERIFICATION — layer 1 price truth vs NSE bhavcopy",
        "sample": {
            "dates": int(cmp["date"].nunique()),
            "date_min": str(cmp["date"].min().date()), "date_max": str(cmp["date"].max().date()),
            "symbols_in_pin": len(ohlcv),
            "symbols_compared": int(cmp["symbol"].nunique()),
            "name_days_compared": int(len(cmp)),
            "name_days_symbol_absent_from_pickle_on_that_date": int((~R["present"]).sum()),
        },
        "overall": _agg(cmp),
        "by_stratum": by_stratum,
        "by_year": by_year,
        "per_symbol_reconciliation": {
            "reconciled": int(P["reconciled"].sum()),
            "not_reconciled": int((~P["reconciled"]).sum()),
            "not_reconciled_names": unrec.head(40).to_dict("records"),
        },
        "adjusted_vs_raw_split": {
            "_note": "how much of the pinned universe is vendor-ADJUSTED at all, measured on the "
                     "oldest sampled date each symbol appears on",
            "symbols_raw_at_first_sample": int((P["ratio_first"] > 0.9999).sum()),
            "symbols_adjusted_at_first_sample": int((P["ratio_first"] <= 0.9999).sum()),
        },
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    cmp.to_parquet(OUTDIR / "layer1_namedays.parquet", index=False)
    print(json.dumps({k: res[k] for k in ("sample", "overall", "by_stratum",
                                          "adjusted_vs_raw_split")}, indent=2, default=str))
    print("\nnot reconciled:", int((~P["reconciled"]).sum()))
    print(unrec.head(25).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
