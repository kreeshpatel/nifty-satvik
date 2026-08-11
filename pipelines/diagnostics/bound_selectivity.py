"""The activation-bound harness, generalised — price a selectivity rule without spending a trial.

The STANDING LAW (`diagnostics/research/label_screen_ledger.md`): no usage trial may be
pre-registered until a zero-trial clairvoyant activation bound has been run — how often would the
rule actually fire on the train years, and what was perfect execution worth, against the ±10 R/yr
path-noise floor (0109). The gate stands at **4/4 FAIL** (0119, 0121, 0127, 0129).

Four scripts have each re-implemented that method. This is the fifth shape, so the method moves here
instead, with the mature `diag_eventsize_bound_0129.py` as the template: frozen constants, no sweep,
PRIMARY + CROSS-CHECK, three arms, a mechanised gate, JSON + MD.

## Validated before it is trusted

`--validate` re-runs the 0119 swap-tiebreak bound through this harness's own `marginal_pairs`. It
must reproduce the published **−1.29 R/yr** (15 swaps, mean −0.471, sum −7.1R over 5.5y). A harness
that cannot reproduce a known answer may not be believed on an unknown one, so `--validate` is not
optional decoration — the new bound refuses to run until it passes.

## The rule this exists to price

The census (`selectivity_census_finding_2026-08-11.md`) established that the near-SMA edge is real in
money (+4.83% of equity per trade below the weekly line vs +0.22% at 5-10%) and that it is
unreachable for TWO compounding reasons, not the one on record: those names are ranked top-5 less
often (28% vs 97%), and — conditional on already being top-5 — they are funded 0-2% of the time
against 57%, because fixed risk over a tight stop demands ~39% of equity per position against ~10%.

Every killed experiment in this family acted on SELECTION: `ext_cap` tightening (0104), near-SMA fill
priority (−0.802), pool pre-filtering (CRS 1.29 → 0.47), the rank floor (0110). None acted on price.
0130 priced GLOBAL stop-width-independent sizing at −10.83% equity/yr. The band-conditional version —
admit a near-SMA entry at REDUCED notional rather than full risk-based size — is unpriced.

## Ordering is enforced, not performed

A bound that informs a PROMOTE/KILL decision costs a screen-ledger row, appended BEFORE the run
(0119 is row #8, 0129 is row #15). This script will not run a new bound without `--ledger-row N`
asserting that the row already exists. It does not append the row itself: that is a governance act,
and a tool that both performs and checks an ordering rule enforces nothing.

    python pipelines/diagnostics/bound_selectivity.py --validate
    python pipelines/diagnostics/bound_selectivity.py --rule band_sizing --ledger-row 20
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

SUB = ROOT / "research" / "substrate" / "trades.parquet"
CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
LEDGER = ROOT / "diagnostics" / "research" / "label_screen_ledger.md"
OUT_JSON = ROOT / "diagnostics" / "research" / "bound_selectivity.json"

# ---- FROZEN. No sweep anywhere in this file. (0129 §1 convention.) ----
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"   # pre-reg 0116 split; the SEALED set stays shut
YRS = 5.5                                          # the train window, as every bound in the family
FLOOR_R_PER_YR = 10.0                              # 0109 / 0117 path-noise floor
NEAR_SMA_EXT_PCT = 5.0                             # "near-SMA" = below this extension, frozen to the
                                                   # census band edge, NOT chosen after seeing results
SIZE_GRID = (0.50,)                                # the reduced notional a near-SMA entry is admitted
                                                   # at, as a fraction of its risk-based size

# The 0119 numbers this harness must reproduce before it may be trusted.
VALIDATION_0119 = {"swaps": 15, "sum_R": -7.1, "bound_R_per_yr": -1.29, "mean_delta": -0.471}


def _iso_col(s: pd.Series) -> pd.Series:
    iso = s.dt.isocalendar()
    return iso.year.astype(str) + "-" + iso.week.astype(str).str.zfill(2)


def load_frames() -> tuple[pd.DataFrame, set]:
    """Uncapped substrate restricted to TRAIN, plus the capped book's funded (ticker, iso-week) set.

    Both sides read the SAME uncapped R, so a swapped-in and a swapped-out trade are compared on
    identical exit rules — that apples-to-apples property is what makes the bound meaningful.
    """
    sub = pd.read_parquet(SUB)
    sub["entry_date"] = pd.to_datetime(sub["entry_date"])
    sub = sub[(sub["entry_date"] >= TRAIN_LO) & (sub["entry_date"] <= TRAIN_HI)].copy()
    sub["iw"] = _iso_col(sub["entry_date"])

    cap = pd.read_csv(CAPPED)
    cap["entry_date"] = pd.to_datetime(cap["entry_date"])
    cap = cap[(cap["entry_date"] >= TRAIN_LO) & (cap["entry_date"] <= TRAIN_HI)]
    funded = set(zip(cap["tkr"], _iso_col(cap["entry_date"])))
    sub["funded"] = [(t, w) in funded for t, w in zip(sub["ticker"], sub["iw"])]
    return sub, funded


def marginal_pairs(sub: pd.DataFrame):
    """Per competitive week: (last funded by CRS, best unfunded by CRS) — the funding margin.

    A week is COMPETITIVE when it funded at least one name and left at least one unfunded. That is
    the only place a selection rule can change anything, and it is far rarer than the raw signal
    count suggests — 53 of 279 train weeks in the 0119 run.
    """
    for iw, g in sub.groupby("iw"):
        f, u = g[g["funded"]], g[~g["funded"]]
        if not len(f) or not len(u):
            continue
        yield iw, f.loc[f["rank_crs"].idxmin()], u.loc[u["rank_crs"].idxmax()], g


def per_year_sign(rows: list[tuple[int, float]]) -> dict:
    """Majority-year sign consistency — the second limb of the gate, as in 0129."""
    by: dict[int, float] = {}
    for y, v in rows:
        by[y] = by.get(y, 0.0) + v
    pos = sum(1 for v in by.values() if v > 0)
    neg = sum(1 for v in by.values() if v < 0)
    return {"by_year": {int(k): round(v, 3) for k, v in sorted(by.items())},
            "n_years": len(by), "n_positive": pos, "n_negative": neg,
            "majority_sign": "+" if pos > neg else "-" if neg > pos else "tie"}


def gate(bound_r_per_yr: float, signs: dict) -> dict:
    """Pre-committed: clear the floor AND be sign-consistent across a majority of years."""
    clears = bound_r_per_yr >= FLOOR_R_PER_YR
    consistent = signs["majority_sign"] == "+"
    return {"floor_R_per_yr": FLOOR_R_PER_YR, "bound_R_per_yr": round(bound_r_per_yr, 3),
            "clears_floor": bool(clears), "sign_consistent": bool(consistent),
            "PASS": bool(clears and consistent),
            "verdict": ("PASS — a trial may be pre-registered" if clears and consistent
                        else "FAIL — no trial; record the bound, bank it, stop")}


# --------------------------------------------------------------------------- validation
def validate_0119(sub: pd.DataFrame) -> dict:
    """Reproduce the published 0119 tiebreak bound through THIS harness's marginal_pairs."""
    from nq.data.delivery import DELIVERY_RAW_PATH, apply_alias_map, derive_delivery_features

    raw = apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH))
    raw["date"] = pd.to_datetime(raw["date"]).astype("datetime64[ns]")
    feats = derive_delivery_features(raw)[["symbol", "date", "dlv_med21"]]
    fa = {s: (g["date"].to_numpy(), g["dlv_med21"].to_numpy()) for s, g in feats.groupby("symbol")}

    d = sub.copy()
    d["sig_fri"] = (d["entry_date"]
                    - pd.to_timedelta(d["entry_date"].dt.weekday + 3, unit="D")).astype("datetime64[ns]")
    dlv = []
    for _, r in d.iterrows():
        a = fa.get(r["ticker"])
        if a is None:
            dlv.append(np.nan); continue
        i = np.searchsorted(a[0], np.datetime64(r["sig_fri"]), "right") - 1
        dlv.append(float(a[1][i]) if i >= 0 and (r["sig_fri"] - pd.Timestamp(a[0][i])).days <= 10
                   else np.nan)
    d["dlv"] = dlv

    deltas, comp = [], 0
    for _iw, last_f, best_u, _g in marginal_pairs(d):
        comp += 1
        if not (np.isfinite(last_f["dlv"]) and np.isfinite(best_u["dlv"])):
            continue
        if best_u["dlv"] > last_f["dlv"]:
            deltas.append(float(best_u["R"]) - float(last_f["R"]))
    tot = float(np.sum(deltas)) if deltas else 0.0
    got = {"competitive_weeks": comp, "swaps": len(deltas), "sum_R": round(tot, 1),
           "mean_delta": round(float(np.mean(deltas)), 3) if deltas else None,
           "bound_R_per_yr": round(tot / YRS, 2)}
    ok = (got["swaps"] == VALIDATION_0119["swaps"]
          and abs(got["bound_R_per_yr"] - VALIDATION_0119["bound_R_per_yr"]) < 0.01
          and abs(got["sum_R"] - VALIDATION_0119["sum_R"]) < 0.15)
    return {"published": VALIDATION_0119, "reproduced": got, "PASS": bool(ok)}


# --------------------------------------------------------------------------- the band-sizing bound
def band_sizing_bound(sub: pd.DataFrame, risk: float, f: float) -> dict:
    """What is a near-SMA entry worth if it is admitted at REDUCED size instead of refused?

    ACTIVATION. A week counts when, at the funding margin, the best UNFUNDED name is near-SMA
    (ext < NEAR_SMA_EXT_PCT). Those are the decisions the rule would change; nothing else moves.

    THE TRADE. Admitting it at fraction `f` of risk-based size earns `f x R_in`. It has to come from
    somewhere: the marginal funded name is displaced, costing `R_out`. So the realistic delta is
    `f x R_in - R_out`, which is the honest version — a slot is not free, which is Law III.

    THE CEILING. Clairvoyant admits it only when that delta is positive. Unreachable by construction
    and reported as an upper bound, exactly as 0121 and 0129 do.
    """
    real, clair, years_real, n_act = [], [], [], 0
    for _iw, last_f, best_u, _g in marginal_pairs(sub):
        if not np.isfinite(best_u["ext_vs_sma"]) or best_u["ext_vs_sma"] >= NEAR_SMA_EXT_PCT:
            continue
        n_act += 1
        d = f * float(best_u["R"]) - float(last_f["R"])
        real.append(d)
        clair.append(max(d, 0.0))
        years_real.append((int(pd.Timestamp(best_u["entry_date"]).year), d))

    tot_real = float(np.sum(real)) if real else 0.0
    tot_clair = float(np.sum(clair)) if clair else 0.0
    signs = per_year_sign(years_real)
    return {
        "size_fraction": f,
        "activations": n_act,
        "activations_per_year": round(n_act / YRS, 2),
        "mean_delta_R": round(float(np.mean(real)), 3) if real else None,
        "median_delta_R": round(float(np.median(real)), 3) if real else None,
        "realistic_R_per_yr": round(tot_real / YRS, 3),
        "clairvoyant_R_per_yr": round(tot_clair / YRS, 3),
        "per_year": signs,
        "gate_realistic": gate(tot_real / YRS, signs),
        "gate_clairvoyant": gate(tot_clair / YRS, signs),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="reproduce 0119 and stop")
    ap.add_argument("--rule", choices=("band_sizing",), default=None)
    ap.add_argument("--ledger-row", type=int, default=None,
                    help="the screen-ledger row appended BEFORE this run (required for --rule)")
    args = ap.parse_args()

    sub, _funded = load_frames()
    print(f"train {TRAIN_LO}..{TRAIN_HI} ({YRS}y) | substrate rows {len(sub)} | "
          f"floor ±{FLOOR_R_PER_YR} R/yr")

    val = validate_0119(sub)
    v = val["reproduced"]
    print(f"\nVALIDATION vs published 0119: swaps {v['swaps']} (want {VALIDATION_0119['swaps']}) | "
          f"sum {v['sum_R']}R (want {VALIDATION_0119['sum_R']}) | bound {v['bound_R_per_yr']} R/yr "
          f"(want {VALIDATION_0119['bound_R_per_yr']}) -> {'PASS' if val['PASS'] else 'FAIL'}")
    if not val["PASS"]:
        raise SystemExit("harness does not reproduce a known answer; it may not be trusted on a new one")
    if args.validate:
        return 0

    if args.rule is None:
        print("\nnothing else requested (--rule band_sizing --ledger-row N)")
        return 0
    if args.ledger_row is None:
        raise SystemExit(
            "REFUSED: --ledger-row N is required. The standing rule appends one row per screen "
            "BEFORE it runs (0119 is #8, 0129 is #15). Append the row to "
            "diagnostics/research/label_screen_ledger.md first, then pass its number. This script "
            "will not append it for you — a tool that both performs and checks an ordering rule "
            "enforces nothing.")

    risk = float(R94.RISK)
    arms = [band_sizing_bound(sub, risk, f) for f in SIZE_GRID]
    print(f"\nBAND-CONDITIONAL SIZING — admit an unfunded near-SMA (<{NEAR_SMA_EXT_PCT}% ext) name at "
          f"the margin, at reduced size, displacing the marginal funded pick")
    for a in arms:
        print(f"  f={a['size_fraction']:.2f} | activations {a['activations']} "
              f"({a['activations_per_year']}/yr) | realistic {a['realistic_R_per_yr']:+.2f} R/yr | "
              f"clairvoyant {a['clairvoyant_R_per_yr']:+.2f} R/yr | "
              f"years {a['per_year']['n_positive']}+/{a['per_year']['n_negative']}- | "
              f"{a['gate_realistic']['verdict'].split(' — ')[0]}")

    payload = {
        "_doc": ("MEASUREMENT. Zero trials. Clairvoyant activation bound under the standing law; "
                 "the clairvoyant arm is an UNREACHABLE ceiling, not an expectation."),
        "reproduce": (f"python pipelines/diagnostics/bound_selectivity.py --rule {args.rule} "
                      f"--ledger-row {args.ledger_row}"),
        "screen_ledger_row": args.ledger_row,
        "frozen": {"train": [TRAIN_LO, TRAIN_HI], "years": YRS, "floor_R_per_yr": FLOOR_R_PER_YR,
                   "near_sma_ext_pct": NEAR_SMA_EXT_PCT, "size_grid": list(SIZE_GRID)},
        "validation_0119": val, "rule": args.rule, "arms": arms,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
