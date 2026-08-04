"""0127 — HEG-class activation bound. ACTIVATION BOUND (ledger row #14). No trial.

Pre-registration: `diagnostics/research/preregistry/0127-hegclass-activation-bound.md`. Every
definition, the management set, the gate and both branches are frozen there and are not re-opened.

The archetype: a name makes a high, declines for 4+ weeks, and that decline carries it back to the
44-week SMA where the signal fires. Two separate claims are priced separately:

  (a) EXCLUSION            — refusing the cohort. Law III bookend: what do the refused trades earn?
  (b) CONDITIONAL MGMT     — handling the cohort differently. Clairvoyant: what does *conditioning on
                             cohort membership* buy over the best single management for everyone?

Both bounds are deliberately INFLATED (uncapped population; excursion ordering assumed favourable),
because a bound whose purpose is to fail should fail on the friendliest population available.

The 0116/0117 sealed slice (`context_windows.parquet`) is NOT read by this script at all.

Reproduce:
    python scripts/diag_hegclass_bound_0127.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.weekly import build_weekly_panel  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# ---- FROZEN (pre-reg §1). No sweep anywhere in this file. ----
PEAK_LOOKBACK = 13          # completed weeks searched for the pre-signal peak
PRIMARY = (4, 20.0)         # (min descent_duration weeks, min descent_depth %) — THE decision cohort
ROBUSTNESS = [(4, 15.0), (6, 20.0)]     # reported, never used to choose
START = pd.Timestamp("2019-01-01")
FLOOR_R_PER_YR = 10.0       # 0109 / 0117 path-noise floor

OUT_JSON = ROOT / "diagnostics" / "research" / "hegclass_bound_0127.json"
OUT_MD = ROOT / "diagnostics" / "research" / "hegclass_bound_0127.md"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(
            "—" if (r[c] is None or (isinstance(r[c], float) and np.isnan(r[c]))) else str(r[c])
            for c in cols) + " |")
    return "\n".join(out)


def descent_features(panel: pd.DataFrame, tr: pd.DataFrame) -> pd.DataFrame:
    """duration / depth / velocity of the decline that carried the name back to the line.

    PIT by construction: the peak is searched in the 13 COMPLETED weeks before the signal week, and
    the depth is measured to the signal week's own close (the bar the decision is made on).
    """
    rows = []
    for tkr, g in panel.groupby("ticker", sort=False):
        sub = tr[tr["ticker"] == tkr]
        if sub.empty:
            continue
        g = g.sort_values("week_end", kind="mergesort")
        we = g["week_end"].to_numpy()
        hi, cl = g["h"].to_numpy(float), g["c"].to_numpy(float)
        for idx, t in sub.iterrows():
            k = int(np.searchsorted(we, np.datetime64(t["entry_date"])))
            if k < PEAK_LOOKBACK + 1 or k >= len(we):
                continue
            w = hi[k - PEAK_LOOKBACK:k]
            if not np.isfinite(w).any():
                continue
            j = int(np.nanargmax(w))
            peak = float(w[j])
            if not (peak > 0):
                continue
            dur = PEAK_LOOKBACK - j
            dep = 100.0 * (peak - cl[k]) / peak
            rows.append(dict(row=idx, descent_duration=dur, descent_depth=round(dep, 3),
                             descent_velocity=round(dep / dur, 3) if dur else np.nan))
    return pd.DataFrame(rows).set_index("row")


def apply_management(d: pd.DataFrame) -> pd.DataFrame:
    """R under each frozen management. mfe/mae are normalised to R by the trade's own stop distance.

    Approximation stated in the pre-reg: excursion ORDER is unknown, so a modelled take-profit
    assumes the favourable excursion was reachable. This inflates every ceiling — the conservative
    direction for a bound meant to fail.
    """
    risk = d["risk_pct"].replace(0, np.nan)
    mfe_r = d["mfe_pct"] / risk
    mae_r = -(d["mae_pct"].abs() / risk)
    out = pd.DataFrame(index=d.index)
    out["as-is"] = d["R"]
    out["TP@2R"] = np.where(mfe_r >= 2.0, 2.0, d["R"])
    out["TP@3R"] = np.where(mfe_r >= 3.0, 3.0, d["R"])
    out["stop@-0.5R"] = np.where(mae_r <= -0.5, -0.5, d["R"])
    return out


def per_year_sign(d: pd.DataFrame, value: np.ndarray, years: pd.Series) -> dict:
    s = pd.Series(value, index=d.index).groupby(years).sum()
    pos = int((s > 0).sum())
    return dict(by_year={int(k): round(float(v), 2) for k, v in s.items()},
                n_years=int(len(s)), n_positive=pos,
                majority_sign="+" if pos * 2 > len(s) else ("-" if (len(s) - pos) * 2 > len(s) else "tie"),
                majority_share=f"{max(pos, len(s) - pos)}/{len(s)}")


def main() -> None:
    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr = tr[tr["setup"] == "touch44"].copy()
    tr["entry_date"] = pd.to_datetime(tr["entry_date"])
    tr = tr[tr["entry_date"] >= START].copy()

    panel = build_weekly_panel(corrected_universe())
    panel["week_end"] = pd.to_datetime(panel["week_end"])
    feats = descent_features(panel, tr)
    d = tr.join(feats, how="inner").dropna(subset=["descent_depth", "R"]).copy()
    years = d["entry_date"].dt.year
    span = max((d["entry_date"].max() - d["entry_date"].min()).days / 365.25, 1e-9)

    res: dict = {
        "_doc": "0127 HEG-class activation bound (ledger #14; 0 trials; sealed slice not read).",
        "prereg": "diagnostics/research/preregistry/0127-hegclass-activation-bound.md",
        "population": "uncapped Stage-1 substrate, setup=touch44, entry_date>=2019 (INFLATES both bounds)",
        "n_trades": int(len(d)), "span_years": round(span, 2),
        "total_R": round(float(d["R"].sum()), 1),
        "total_R_per_yr": round(float(d["R"].sum()) / span, 1),
    }

    # ---- §5.1 cohort table, recomputed here (reproduce-before-trust) ----
    q = d[["descent_duration", "descent_depth", "descent_velocity"]].quantile([.25, .5, .75])
    res["descent_quartiles"] = {c: [round(float(q.loc[x, c]), 2) for x in (.25, .5, .75)]
                                for c in q.columns}
    cohort_tbl = []
    for dur, dep in [PRIMARY] + ROBUSTNESS:
        m = (d["descent_duration"] >= dur) & (d["descent_depth"] >= dep)
        cohort_tbl.append(dict(threshold=f">={dur}wk & >={dep:.0f}%", N=int(m.sum()),
                               share_pct=round(100.0 * float(m.mean()), 1),
                               primary=(dur, dep) == PRIMARY))
    res["cohort_table"] = cohort_tbl

    # ---- the PRIMARY cohort ----
    hot = (d["descent_duration"] >= PRIMARY[0]) & (d["descent_depth"] >= PRIMARY[1])
    d["hegclass"] = hot
    coh, rest = d[hot], d[~hot]
    res["primary_cohort"] = {
        "definition": f">={PRIMARY[0]}wk descent AND >={PRIMARY[1]:.0f}% depth",
        "N": int(len(coh)), "share_of_trades_pct": round(100.0 * float(hot.mean()), 1),
        "cohort_meanR": round(float(coh["R"].mean()), 3),
        "rest_meanR": round(float(rest["R"].mean()), 3),
        "cohort_total_R": round(float(coh["R"].sum()), 1),
        "share_of_book_R_pct": round(100.0 * float(coh["R"].sum() / d["R"].sum()), 1),
        "cohort_win_pct": round(100.0 * float((coh["R"] > 0).mean()), 1),
        "rest_win_pct": round(100.0 * float((rest["R"] > 0).mean()), 1),
    }

    # ---- BOUND (a): EXCLUSION — the Law III bookend ----
    refused_r_per_yr = float(coh["R"].sum()) / span          # what refusing them costs (if positive)
    losers = coh[coh["R"] < 0]
    clair_excl = -float(losers["R"].sum()) / span            # refuse ONLY the losers, with hindsight
    res["bound_a_exclusion"] = {
        "R_per_yr_refused": round(refused_r_per_yr, 2),
        "interpretation": ("refusing the cohort COSTS this much R/yr (positive-EV cohort)"
                           if refused_r_per_yr > 0 else "refusing the cohort SAVES this much R/yr"),
        "clairvoyant_refuse_only_losers_R_per_yr": round(clair_excl, 2),
        "note": "the clairvoyant leg is an unreachable ceiling (perfect foresight on which lose); "
                "it also ignores redeployment, which 0121 measured as the dominant term",
        "per_year": per_year_sign(coh, coh["R"].to_numpy(float), coh["entry_date"].dt.year),
    }

    # ---- BOUND (b): CONDITIONAL MANAGEMENT — clairvoyant ----
    mgmt = apply_management(d)
    tot_all = mgmt.sum()
    tot_coh = mgmt[hot].sum()
    tot_rest = mgmt[~hot].sum()
    best_all, best_coh, best_rest = tot_all.idxmax(), tot_coh.idxmax(), tot_rest.idxmax()
    cond_gain = float(tot_coh[best_coh] + tot_rest[best_rest] - tot_all[best_all])
    res["bound_b_conditional_management"] = {
        "management_totals_R": {k: round(float(v), 1) for k, v in tot_all.items()},
        "cohort_totals_R": {k: round(float(v), 1) for k, v in tot_coh.items()},
        "rest_totals_R": {k: round(float(v), 1) for k, v in tot_rest.items()},
        "best_single_for_all": best_all,
        "best_for_cohort": best_coh, "best_for_rest": best_rest,
        "clairvoyant_conditional_gain_R": round(cond_gain, 1),
        "clairvoyant_conditional_gain_R_per_yr": round(cond_gain / span, 2),
        "note": "the gain of CONDITIONING on cohort membership, over the best single management "
                "applied to everyone — with perfect hindsight on which management to pick",
    }
    gain_series = (mgmt[best_coh].where(hot, mgmt[best_rest])
                   - mgmt[best_all])
    res["bound_b_conditional_management"]["per_year"] = per_year_sign(
        d, gain_series.to_numpy(float), years)

    # ---- §2 gate ----
    def verdict(v: float, pyr: dict) -> dict:
        mag = abs(v) > FLOOR_R_PER_YR
        maj = pyr["majority_sign"] == ("+" if v > 0 else "-")
        return dict(value_R_per_yr=round(v, 2), clears_floor=bool(mag),
                    majority_year_consistent=bool(maj),
                    PASS=bool(mag and maj and v > 0))

    res["gate"] = {
        "floor_R_per_yr": FLOOR_R_PER_YR,
        "a_exclusion_as_a_saving": verdict(-refused_r_per_yr,
                                           res["bound_a_exclusion"]["per_year"]),
        # The clairvoyant refuse-only-losers leg is POSITIVE BY CONSTRUCTION in every year (removing
        # negatives always helps), so a sign-consistency test on it is a tautology, not evidence.
        # It is therefore judged on magnitude + reachability, and reachability is the binding term:
        # picking the losers in advance is exactly the pre-entry wall, dead five independent ways.
        "a_exclusion_clairvoyant_ceiling": {
            "value_R_per_yr": round(clair_excl, 2),
            "clears_floor": bool(abs(clair_excl) > FLOOR_R_PER_YR),
            "sign_test": "NOT APPLICABLE — positive by construction (tautology, not evidence)",
            "reachable": False,
            "why_unreachable": "requires perfect foresight on which trades lose — the pre-entry "
                               "wall (bar-level ML, loser forensics, path shape, formulas, "
                               "perception); and 0121 showed redeployment dominates anyway",
            "PASS": False,
        },
        "b_conditional_management": verdict(cond_gain / span,
                                            res["bound_b_conditional_management"]["per_year"]),
    }
    res["VERDICT"] = ("PASS — screen #14 may be pre-registered"
                      if any(v.get("PASS") for v in res["gate"].values() if isinstance(v, dict))
                      else "FAIL — no screen #14; thread closed until habit-ledger labels")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    md = [
        "# 0127 — HEG-class activation bound (ledger #14)",
        "",
        "**0 trials. Sealed slice not read. Judge log unread. No engine change.**",
        "**Standing counts: screens 14 · sealed opens 1 · n_trials 138.**",
        "",
        f"Population: **{res['n_trades']} uncapped touch44 trades**, {res['span_years']}y, "
        f"total {res['total_R']}R ({res['total_R_per_yr']} R/yr). "
        "Uncapped and excursion-order-optimistic — **both bounds are inflated on purpose**.",
        "",
        "## Cohort table (recomputed here — reproduce-before-trust)",
        "",
        md_table(pd.DataFrame(res["cohort_table"])),
        "",
        f"Descent quartiles — duration {res['descent_quartiles']['descent_duration']} wk · "
        f"depth {res['descent_quartiles']['descent_depth']}% · "
        f"velocity {res['descent_quartiles']['descent_velocity']} %/wk",
        "",
        "## Bound (a) — EXCLUSION (Law III bookend)",
        "", "```", json.dumps(res["bound_a_exclusion"], indent=2, default=str), "```",
        "",
        "## Bound (b) — CONDITIONAL MANAGEMENT (clairvoyant)",
        "", "```", json.dumps(res["bound_b_conditional_management"], indent=2, default=str), "```",
        "",
        "## Gate (pre-committed: |bound| > 10 R/yr AND majority-year sign)",
        "", "```", json.dumps(res["gate"], indent=2, default=str), "```",
        "", f"## VERDICT: {res['VERDICT']}", "",
        "Reproduce: `python scripts/diag_hegclass_bound_0127.py`", "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write("\n".join(md).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
