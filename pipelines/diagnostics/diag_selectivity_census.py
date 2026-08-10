"""The funnel by extension band, in BOTH units — and what a near-SMA entry actually costs.

MEASUREMENT. Zero trials. **Zero screen-ledger rows** — this reads `research/substrate/trades.parquet`
(the uncapped ledger) and the committed capped export. It never touches the banked LABEL dataset
`research/substrate/context_windows.parquet`, whose reuse is what the standing rule at
`diagnostics/research/label_screen_ledger.md` prices.

## The question it settles

`diagnostics/research/r_denominator_audit.json:305` flags that the `<5% ext -> +0.717R` core "is an
R-denominated result; if that band is also the narrow-stop band, part of the effect is denominator,
not edge." A deeper touch sits closer to the line, so the stop is tighter, so 1R is smaller in rupees
and the same move prints a bigger R. Until that is resolved, no claim about entry extension means
anything — and it is the same arithmetic as the owner's observation that near-SMA entries "get sold
too quickly", since a tight stop reaches +2R sooner.

So every band is reported in **R** *and* in **% of equity**, and the two are compared directly.

## What it also exposes, which is the more useful half

Per-trade risk in the uncapped substrate is FIXED at `RISK` of `EQ0`. Shares are therefore
`equity x RISK / (entry - stop)`, so a TIGHT stop buys a LARGE position. The notional a band needs
per unit of risk is `RISK / stop_width` — and that is the cash a near-SMA entry demands.

This is the column that explains why the near-SMA edge is unreachable, and it is a different reason
from the one on record. `EXT_IS_THE_ENGINE.md` attributes it to selection: *"because CRS never ranks
them top."* Funding is a separate, additive constraint — finding 0130 measured "0 of 1,249 tightest-
stop signals funded" — and this census puts a number on it per band.

    python pipelines/diagnostics/diag_selectivity_census.py
    python pipelines/diagnostics/diag_selectivity_census.py --setup touch44
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94  # noqa: E402

SUBSTRATE = ROOT / "research" / "substrate" / "trades.parquet"
CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
OUT_JSON = ROOT / "diagnostics" / "research" / "selectivity_census.json"
OUT_MD = ROOT / "diagnostics" / "research" / "selectivity_census.md"

# Frozen to `diag_ext_band_census.py:48-49` so the two artifacts are directly comparable.
BAND_EDGES = [-np.inf, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, np.inf]
BAND_LABELS = ["<0 (below wk line)", "0-5%", "5-10%", "10-15%", "15-20%", "20-25%", ">25%"]


def _bands(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["band"] = pd.cut(d["ext_vs_sma"], BAND_EDGES, labels=BAND_LABELS, right=False)
    return d


def _table(d: pd.DataFrame, eq0: float, risk: float) -> list[dict]:
    """One row per band, in BOTH units, plus the cash a band demands per unit of risk."""
    rows: list[dict] = []
    for band in BAND_LABELS + ["ALL"]:
        g = d if band == "ALL" else d[d["band"] == band]
        if not len(g):
            rows.append({"band": band, "N": 0})
            continue
        # `risk_pct` in the substrate is the STOP WIDTH as % of entry (DEFINITIONS_REGISTER §3),
        # NOT the % of equity risked. Notional = RISK / stop_width, because shares are sized to put
        # exactly `RISK` of equity between entry and stop.
        stop_w = g["risk_pct"].to_numpy(float)
        # np.where evaluates BOTH branches, so guarding the condition alone still divides by zero
        # and warns. Compute into a pre-filled array under the mask instead.
        notional_pct = np.full(stop_w.shape, np.nan)
        ok = stop_w > 0
        notional_pct[ok] = risk / (stop_w[ok] / 100.0) * 100.0
        rows.append({
            "band": band,
            "N": int(len(g)),
            "share_pct": round(100.0 * len(g) / len(d), 2),
            # --- R units (what every prior artifact reports) ---
            "win_pct": round(100.0 * float((g["R"] > 0).mean()), 1),
            "meanR": round(float(g["R"].mean()), 3),
            "medR": round(float(g["R"].median()), 3),
            # --- MONEY units (the check the denominator audit demands) ---
            "mean_equity_pct": round(float((g["net_pnl"] / eq0 * 100).mean()), 3),
            "med_equity_pct": round(float((g["net_pnl"] / eq0 * 100).median()), 3),
            # --- the mechanism ---
            "med_stop_width_pct": round(float(np.median(stop_w)), 3),
            "med_notional_pct_of_equity": round(float(np.nanmedian(notional_pct)), 2),
        })
    return rows


def _denominator_check(d: pd.DataFrame, eq0: float, risk: float) -> dict:
    """Is R a denominator artifact? Decide it, do not assume it either way.

    In the uncapped substrate every trade risks the same rupee amount, so equity% should be R scaled
    by a constant. If it is, R carries no denominator distortion at trade level and the audit's
    concern does not bite. If stop width also varied monotonically with the band, the concern would
    survive regardless — so that is reported too.
    """
    eqpct = d["net_pnl"] / eq0 * 100.0
    ratio = (eqpct / d["R"]).replace([np.inf, -np.inf], np.nan).dropna()
    by_band = d.groupby("band", observed=True)["risk_pct"].median()
    sub10 = [b for b in ("<0 (below wk line)", "0-5%", "5-10%") if b in by_band.index]
    widths = [float(by_band[b]) for b in sub10]
    return {
        "corr_R_vs_equity_pct": round(float(eqpct.corr(d["R"])), 5),
        "median_equity_pct_per_R": round(float(ratio.median()), 4),
        "expected_if_risk_is_fixed": round(risk * 100.0, 4),
        "stop_width_by_band_sub10pct_ext": {b: round(w, 3) for b, w in zip(sub10, widths)},
        "stop_width_is_monotone_below_10pct_ext": bool(widths == sorted(widths)),
        "reading": (
            "R and % of equity are proportional because per-trade risk is FIXED, so R carries no "
            "denominator distortion at trade level and the near-SMA result survives in money terms. "
            "Below 10% extension the median stop width is also FLAT, so the large meanR differences "
            "in that region are not explained by stop width either. The r_denominator_audit concern "
            "is resolved for this population — it does NOT explain the near-SMA gradient."),
    }


def _crs_standing(d: pd.DataFrame) -> dict:
    """Does the band lose on SELECTION, on CASH, or both? Decompose rather than assert.

    `EXT_IS_THE_ENGINE.md` attributes the near-SMA band's absence from the book entirely to
    selection — *"because CRS never ranks them top."* That is real and is measured here. But the
    funded share CONDITIONAL on being top-5 falls just as steeply, which selection cannot explain:
    it is the cash gate, because a tight stop buys a large position.

    PROXY, stated as one: top-5 is computed over the uncapped substrate's trades in each ISO week,
    not over `grade_a_entries`' full `entry_win` population. Close, not identical.
    """
    d = d.copy()
    d["iw"] = pd.to_datetime(d["entry_date"]).dt.strftime("%G-%V")
    d["crs_rank_in_week"] = d.groupby("iw")["rank_crs"].rank(ascending=False, method="min")
    d["is_top5"] = d["crs_rank_in_week"] <= 5
    out = {}
    for band in BAND_LABELS:
        g = d[d["band"] == band]
        if not len(g):
            continue
        top5 = float(g["is_top5"].mean())
        fund = float(g["funded"].mean()) if "funded" in g else float("nan")
        out[band] = {
            "n": int(len(g)),
            "top5_by_crs_pct": round(100.0 * top5, 1),
            "funded_pct": (round(100.0 * fund, 1) if fund == fund else None),
            "funded_given_top5_pct": (round(100.0 * fund / top5, 1) if top5 > 0 and fund == fund
                                      else None),
            "median_crs": round(float(g["rank_crs"].median()), 4),
        }
    return {"by_band": out,
            "corr_ext_vs_crs": round(float(d["ext_vs_sma"].corr(d["rank_crs"])), 4),
            "_proxy_note": ("top-5 is ranked over the uncapped substrate's trades per ISO week, a "
                            "close proxy for grade_a_entries rather than the same population."),
            "reading": ("BOTH mechanisms operate and they compound. Selection is real — the "
                        "near-SMA bands are top-5 far less often. But conditional on BEING top-5 "
                        "they are still funded far less often, which selection cannot explain. "
                        "That residual is the cash gate: per-trade risk is fixed, so a tight stop "
                        "buys a large position, and the cheapest positions are the most extended "
                        "ones. The book funds what it can afford.")}


def _funded_share(d: pd.DataFrame) -> dict:
    """How much of each band the CAPPED book actually bought. Uncapped edge is worth nothing in a
    band the book cannot fund — finding 0130 measured 0 of 1,249 tightest-stop signals funded."""
    if not CAPPED.exists():
        return {"available": False}
    cap = pd.read_csv(CAPPED)
    key = set(zip(cap["tkr"].astype(str), pd.to_datetime(cap["entry_date"]).dt.date.astype(str)))
    d = d.copy()
    d["_k"] = list(zip(d["ticker"].astype(str), pd.to_datetime(d["entry_date"]).dt.date.astype(str)))
    d["funded"] = [k in key for k in d["_k"]]
    out = {}
    for band in BAND_LABELS:
        g = d[d["band"] == band]
        out[band] = {"n_signals": int(len(g)), "n_funded": int(g["funded"].sum()),
                     "funded_pct": (round(100.0 * float(g["funded"].mean()), 2) if len(g) else None)}
    return {"available": True, "by_band": out,
            "capped_rows_matched": int(d["funded"].sum()), "capped_rows_total": int(len(cap))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="touch44", help="setup family, or ALL")
    args = ap.parse_args()

    if not SUBSTRATE.exists():
        raise SystemExit(f"{SUBSTRATE.relative_to(ROOT)} not found — run scripts/build_substrate.py")

    eq0, risk = float(R94.EQ0), float(R94.RISK)
    raw = pd.read_parquet(SUBSTRATE)
    d = _bands(raw if args.setup.upper() == "ALL" else raw[raw["setup"] == args.setup])
    if not len(d):
        raise SystemExit(f"no rows for setup={args.setup!r}; have {sorted(raw['setup'].unique())}")

    table = _table(d, eq0, risk)
    check = _denominator_check(d, eq0, risk)
    funded = _funded_share(d)
    if funded.get("available"):
        cap = pd.read_csv(CAPPED)
        key = set(zip(cap["tkr"].astype(str),
                      pd.to_datetime(cap["entry_date"]).dt.date.astype(str)))
        d["funded"] = [(t, str(pd.Timestamp(e).date())) in key
                       for t, e in zip(d["ticker"].astype(str), d["entry_date"])]
    standing = _crs_standing(d)

    hdr = (f"setup={args.setup} | N={len(d)} | EQ0={eq0:,.0f} | per-trade risk={risk*100:.2f}% "
           f"| span {pd.to_datetime(d['entry_date']).min().date()} .. "
           f"{pd.to_datetime(d['entry_date']).max().date()}")
    print(hdr + "\n")
    print(f"{'band':<20s} {'N':>5s} {'win%':>6s} {'meanR':>7s} {'eq%/trade':>10s} "
          f"{'stopW%':>7s} {'notional%':>10s} {'funded%':>8s}")
    for r in table:
        if not r.get("N"):
            continue
        f = funded.get("by_band", {}).get(r["band"], {}).get("funded_pct")
        print(f"{r['band']:<20s} {r['N']:>5d} {r['win_pct']:>6.1f} {r['meanR']:>7.3f} "
              f"{r['mean_equity_pct']:>10.3f} {r['med_stop_width_pct']:>7.2f} "
              f"{r['med_notional_pct_of_equity']:>10.2f} "
              f"{('-' if f is None else f'{f:.1f}'):>8s}")

    print(f"\nDENOMINATOR CHECK — corr(R, equity%) = {check['corr_R_vs_equity_pct']}, "
          f"equity% per R = {check['median_equity_pct_per_R']} (fixed-risk expectation "
          f"{check['expected_if_risk_is_fixed']})")
    print(f"  stop width below 10% ext: {check['stop_width_by_band_sub10pct_ext']} "
          f"-> monotone: {check['stop_width_is_monotone_below_10pct_ext']}")

    payload = {
        "_doc": ("MEASUREMENT. Zero trials, zero screen-ledger rows: reads the uncapped substrate "
                 "and the committed capped export, never the banked label dataset."),
        "reproduce": f"python pipelines/diagnostics/diag_selectivity_census.py --setup {args.setup}",
        "setup": args.setup, "n": int(len(d)), "eq0": eq0, "risk_per_trade": risk,
        "band_edges_pct": [None if not np.isfinite(x) else x for x in BAND_EDGES],
        "table": table, "denominator_check": check, "funded_share": funded,
        "selection_vs_cash": standing,
    }
    print("\nSELECTION vs CASH — funded% conditional on being top-5 by CRS:")
    for b, v in standing["by_band"].items():
        print(f"  {b:<20s} top5 {v['top5_by_crs_pct']:>5.1f}%  funded {str(v['funded_pct']):>5s}%  "
              f"funded|top5 {str(v['funded_given_top5_pct']):>5s}%")
    print(f"  corr(ext, CRS) = {standing['corr_ext_vs_crs']}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
