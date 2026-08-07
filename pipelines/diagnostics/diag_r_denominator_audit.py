"""R-DENOMINATOR AUDIT — is R a comparable unit across this book?

**VERIFICATION CLASS. Free. No ledger row, no trial, no rule proposal.** This is a measurement
audit of our own instrument, not a hypothesis test: it computes no feature->outcome screen and
makes no PROMOTE/KILL decision. Anything it suggests routes to the owner's door.

The concern (owner, 2026-08-06): stop width varies from ~2% to >30% across this book, so R -- which
is (price outcome) / (stop width) -- may not be a comparable unit, and any statistic that SUMS or
AVERAGES R across trades may be reporting denominator variation rather than price outcome.

Six legs:
  1. distribution of `stop_width_pct` (the substrate's `risk_pct` = (entry-stop)/entry)
  2. distribution of `stop_width / ATR(weekly)` at entry
  3. correlation of stop width with realized R and with stop-hit frequency
  4. the decisive split: of trades whose stop was NARROWER than 1x weekly ATR, what fraction
     stopped out and then closed ABOVE entry within 4 weeks (the LINDEINDIA signature)
  5. how much of the book's aggregate R is driven by the denominator rather than by price outcome
  6. the sizing-regime consequence: what one R is actually WORTH in rupees, uncapped vs LIVE

Reproduce:
    python scripts/diag_r_denominator_audit.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_bhanushali_path1 import corrected_universe  # noqa: E402

START = pd.Timestamp("2019-01-01")          # the programme trusts >=2019 only
RECOVER_WEEKS = 4                            # the LINDEINDIA signature window
RECOVER_SESSIONS = 20                        # ~4 weeks of trading days

# Engine sizing constants, read from the committed code (not re-derived here):
RISK = 0.02                                  # run_bhanushali_sixstep.RISK
LIVE_MAX_NOTIONAL = 0.20                     # run_bhanushali_cron.LIVE_DISCIPLINE
LIVE_MAX_RISK = 0.10                         # run_bhanushali_cron.LIVE_DISCIPLINE

OUT_JSON = ROOT / "diagnostics" / "research" / "r_denominator_audit.json"
OUT_MD = ROOT / "diagnostics" / "research" / "r_denominator_audit.md"


def dist(s: pd.Series) -> dict:
    s = s.dropna()
    q = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    return {"n": int(len(s)), "mean": round(float(s.mean()), 3),
            "pctiles": {f"p{p}": round(float(s.quantile(p / 100)), 3) for p in q},
            "min": round(float(s.min()), 3), "max": round(float(s.max()), 3),
            "p90_over_p10": round(float(s.quantile(.9) / max(s.quantile(.1), 1e-9)), 2)}


def corr(a: pd.Series, b: pd.Series) -> dict:
    m = a.notna() & b.notna()
    a, b = a[m], b[m]
    return {"n": int(len(a)),
            "pearson": round(float(pearsonr(a, b)[0]), 4),
            "spearman": round(float(spearmanr(a, b)[0]), 4),
            "spearman_p": round(float(spearmanr(a, b)[1]), 5)}


def main() -> None:
    print("VERIFICATION CLASS — free. No ledger row. No trial. No rule proposed.")
    tr = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    tr["entry_date"] = pd.to_datetime(tr["entry_date"])
    tr["exit_date"] = pd.to_datetime(tr["exit_date"])
    d = tr[tr["entry_date"] >= START].dropna(subset=["risk_pct", "R"]).copy()
    d["stopped"] = d["reason"].astype(str).str.startswith("stop")
    d["sw_over_atr"] = d["risk_pct"] / d["atr_pct"]
    d["pnl_pct"] = d["R"] * d["risk_pct"]          # the actual PRICE outcome, denominator removed
    span = max((d["entry_date"].max() - d["entry_date"].min()).days / 365.25, 1e-9)

    res: dict = {
        "_doc": "R-denominator audit — VERIFICATION CLASS (free; no ledger row; no rule proposed).",
        "population": f"uncapped Stage-1 substrate, entry_date>={START.date()}, all setups",
        "n_trades": int(len(d)), "span_years": round(span, 2),
        "book_total_R": round(float(d["R"].sum()), 1),
        "standing_counts": {"screens": 15, "sealed_opens": 1, "n_trials": 138},
    }

    # ---- LEG 1/2: the denominators themselves ----
    res["leg1_stop_width_pct"] = dist(d["risk_pct"])
    res["leg1_by_setup"] = {
        s: {"n": int(len(g)), "median_stop_width_pct": round(float(g["risk_pct"].median()), 2),
            "mean_R": round(float(g["R"].mean()), 3)}
        for s, g in d.groupby("setup") if len(g) >= 25}
    res["leg2_stop_width_over_weekly_ATR"] = dist(d["sw_over_atr"])
    res["leg2_share_below_1x_ATR_pct"] = round(100.0 * float((d["sw_over_atr"] < 1.0).mean()), 1)
    res["leg2_share_below_0p5x_ATR_pct"] = round(100.0 * float((d["sw_over_atr"] < 0.5).mean()), 1)

    # ---- LEG 3: does the denominator drive the numerator? ----
    res["leg3_correlations"] = {
        "stop_width_vs_R": corr(d["risk_pct"], d["R"]),
        "stop_width_vs_stop_hit": corr(d["risk_pct"], d["stopped"].astype(float)),
        "sw_over_atr_vs_R": corr(d["sw_over_atr"], d["R"]),
        "sw_over_atr_vs_stop_hit": corr(d["sw_over_atr"], d["stopped"].astype(float)),
        "stop_width_vs_abs_R": corr(d["risk_pct"], d["R"].abs()),
        "stop_width_vs_price_outcome_pnl_pct": corr(d["risk_pct"], d["pnl_pct"]),
    }
    dec = d.assign(bin=pd.qcut(d["risk_pct"], 10, labels=False, duplicates="drop"))
    res["leg3_by_stop_width_decile"] = [
        {"decile": int(k) + 1, "n": int(len(g)),
         "median_stop_width_pct": round(float(g["risk_pct"].median()), 2),
         "median_sw_over_atr": round(float(g["sw_over_atr"].median()), 2),
         "mean_R": round(float(g["R"].mean()), 3),
         "mean_price_outcome_pct": round(float(g["pnl_pct"].mean()), 2),
         "stop_hit_pct": round(100.0 * float(g["stopped"].mean()), 1),
         "share_of_book_R_pct": round(100.0 * float(g["R"].sum() / d["R"].sum()), 1)}
        for k, g in dec.groupby("bin")]

    # ---- LEG 4: the LINDEINDIA signature ----
    ohlcv = corrected_universe()
    narrow = d[(d["sw_over_atr"] < 1.0) & d["stopped"]].copy()
    wide = d[(d["sw_over_atr"] >= 1.0) & d["stopped"]].copy()

    def recovery_rate(sub: pd.DataFrame) -> dict:
        rec = miss = 0
        for _, r in sub.iterrows():
            px = ohlcv.get(r["ticker"])
            if px is None or r["exit_date"] is pd.NaT:
                miss += 1
                continue
            fwd = px[px.index > r["exit_date"]].head(RECOVER_SESSIONS)
            if not len(fwd):
                miss += 1
                continue
            rec += int(bool((fwd["Close"] > r["entry"]).any()))
        n = max(len(sub) - miss, 1)
        return {"n_stopped": int(len(sub)), "n_evaluable": int(len(sub) - miss),
                "n_closed_above_entry_within_4wk": int(rec),
                "recovery_pct": round(100.0 * rec / n, 1)}

    res["leg4_lindeindia_signature"] = {
        "definition": f"stopped out, then a daily CLOSE above the original entry within "
                      f"{RECOVER_WEEKS} weeks ({RECOVER_SESSIONS} sessions) of the exit",
        "narrow_stop_below_1x_weekly_ATR": recovery_rate(narrow),
        "wide_stop_at_or_above_1x_weekly_ATR": recovery_rate(wide),
    }
    a, b = res["leg4_lindeindia_signature"]["narrow_stop_below_1x_weekly_ATR"], \
        res["leg4_lindeindia_signature"]["wide_stop_at_or_above_1x_weekly_ATR"]
    res["leg4_lindeindia_signature"]["gap_pp"] = round(a["recovery_pct"] - b["recovery_pct"], 1)
    res["leg4_lindeindia_signature"]["mechanical_caveat"] = (
        "PART OF THIS GAP IS DEFINITIONAL and must not be read as pure discovery: a narrow stop is "
        "breached by a smaller adverse move, so recovering back above entry requires a smaller "
        "favourable move. The gap is reported because of what it says about the UNIT, not because "
        "it is a surprise: a -1R booked on a sub-ATR stop and a -1R booked on a 3x-ATR stop are "
        "not the same event, yet the book records both as -1R and averages them together.")

    # ---- LEG 5: how much of aggregate R is denominator, not outcome? ----
    med = float(d["risk_pct"].median())
    d["R_common"] = d["pnl_pct"] / med              # every trade re-expressed at ONE denominator
    narrow_t = d["risk_pct"] <= d["risk_pct"].quantile(1 / 3)
    res["leg5_denominator_decomposition"] = {
        "common_denominator_used_pct": round(med, 3),
        "book_total_R_as_reported": round(float(d["R"].sum()), 1),
        "book_total_R_at_common_denominator": round(float(d["R_common"].sum()), 1),
        "ratio": round(float(d["R_common"].sum() / d["R"].sum()), 3),
        "mean_R_as_reported": round(float(d["R"].mean()), 3),
        "mean_R_at_common_denominator": round(float(d["R_common"].mean()), 3),
        "spearman_R_vs_R_common": round(float(spearmanr(d["R"], d["R_common"])[0]), 3),
        "narrowest_stop_tercile_share_of_book_R_pct": round(
            100.0 * float(d.loc[narrow_t, "R"].sum() / d["R"].sum()), 1),
        "narrowest_stop_tercile_share_at_common_denominator_pct": round(
            100.0 * float(d.loc[narrow_t, "R_common"].sum() / d["R_common"].sum()), 1),
        "log_abs_R_on_log_stop_width_slope": round(float(np.polyfit(
            np.log(d.loc[d["R"].abs() > 1e-9, "risk_pct"]),
            np.log(d.loc[d["R"].abs() > 1e-9, "R"].abs()), 1)[0]), 3),
        "interpretation": "a slope near -1 means |R| is very nearly the reciprocal of the stop "
                          "width — i.e. R is measuring the denominator, not the price outcome",
    }

    # ---- LEG 6: what one R is WORTH, uncapped vs LIVE ----
    rf = (d["risk_pct"] / 100.0).clip(upper=LIVE_MAX_RISK)      # LIVE also caps the stop at 10%
    eff_live = np.minimum(RISK, LIVE_MAX_NOTIONAL * rf)          # effective equity risked per trade
    res["leg6_sizing_regime"] = {
        "run_of_record_and_substrate": "UNCAPPED — sh = eq*2%/(entry-stop); 1R == 2% of equity for "
                                       "EVERY trade, so R IS rupee-comparable there",
        "live_book": f"LIVE_DISCIPLINE (max_risk_pct={LIVE_MAX_RISK}, "
                     f"max_notional_pct={LIVE_MAX_NOTIONAL}) — sh = min(risk-sizing, notional cap)",
        "live_binding_threshold_stop_width_pct": round(100.0 * RISK / LIVE_MAX_NOTIONAL, 2),
        "share_of_trades_where_live_cap_binds_pct": round(
            100.0 * float((eff_live < RISK - 1e-12).mean()), 1),
        "live_effective_equity_risk_pct": dist(pd.Series(100.0 * eff_live)),
        "live_rupee_value_of_1R_vs_nominal": dist(pd.Series(eff_live / RISK)),
        "citation": "already carried structurally as constitution H1/H3 ('Off in run of record') "
                    "and divergence D3 — this leg quantifies the UNIT consequence, it does not "
                    "claim a new divergence",
    }
    # the money question: the same book, weighted by what each R is actually WORTH live
    w = (eff_live / RISK).to_numpy(float)
    res["leg6_sizing_regime"]["book_R_uncapped_weighting"] = round(float(d["R"].sum()), 1)
    res["leg6_sizing_regime"]["book_R_live_rupee_weighting"] = round(float((d["R"] * w).sum()), 1)
    res["leg6_sizing_regime"]["live_translation_ratio"] = round(
        float((d["R"] * w).sum() / d["R"].sum()), 3)
    res["leg6_sizing_regime"]["what_this_means"] = (
        "the SAME trades, re-weighted by the rupees the live cap actually puts behind each R. "
        "A ratio < 1 means the live book converts reported R into proportionally fewer rupees, "
        "because the cap binds hardest exactly on the narrow-stop trades that carry the most R.")

    # ---- exposure check: does the extension band ride on the denominator? ----
    if "ext_vs_sma" in d.columns:
        e = d.dropna(subset=["ext_vs_sma"])
        lo = e[e["ext_vs_sma"] < 5.0]
        res["exposure_check_ext_band"] = {
            "why": "the <5% extension band's +0.717R core (ext_band_census) is an R-denominated "
                   "result; if that band is also the narrow-stop band, part of the effect is "
                   "denominator, not edge",
            "corr_ext_vs_stop_width": corr(e["ext_vs_sma"], e["risk_pct"]),
            "median_stop_width_pct_ext_below_5": round(float(lo["risk_pct"].median()), 2),
            "median_stop_width_pct_ext_at_or_above_5": round(
                float(e[e["ext_vs_sma"] >= 5.0]["risk_pct"].median()), 2),
            "mean_R_ext_below_5": round(float(lo["R"].mean()), 3),
            "mean_R_at_common_denominator_ext_below_5": round(float(lo["R_common"].mean()), 3),
            "mean_R_ext_at_or_above_5": round(float(e[e["ext_vs_sma"] >= 5.0]["R"].mean()), 3),
            "mean_R_at_common_denominator_ext_at_or_above_5": round(
                float(e[e["ext_vs_sma"] >= 5.0]["R_common"].mean()), 3),
            "verdict_is_owner_door": "FLAG ONLY — this audit proposes nothing; the reading is the "
                                     "owner's to make",
        }
        # which yardstick is right depends on the SIZING REGIME — so price the live one explicitly.
        wser = pd.Series(w, index=d.index)
        for tag, mask in (("ext_below_5", e["ext_vs_sma"] < 5.0),
                          ("ext_at_or_above_5", e["ext_vs_sma"] >= 5.0)):
            idx = e.index[mask]
            res["exposure_check_ext_band"][f"live_rupee_weight_{tag}"] = round(
                float(wser.loc[idx].mean()), 3)
            res["exposure_check_ext_band"][f"live_rupee_weighted_meanR_{tag}"] = round(
                float((d.loc[idx, "R"] * wser.loc[idx]).mean()), 3)
        res["exposure_check_ext_band"]["how_to_read"] = (
            "THREE yardsticks, and which is correct depends on how the book sizes. "
            "(1) fixed-RISK sizing (the uncapped run of record): R as reported is already the "
            "rupee truth — the low-ext edge is real there. "
            "(2) fixed-NOTIONAL sizing: the common-denominator column is the truth, and the "
            "ordering reverses. "
            "(3) the LIVE book is neither — it is min(risk-sizing, 20% notional), so it sits "
            "BETWEEN them, and the live-rupee-weighted column is the one that governs live "
            "capital. The exposure is that low-ext trades carry narrow stops, so the live cap "
            "binds hardest on precisely the cohort the research calls the core edge.")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    md = ["# R-denominator audit — is R a comparable unit?", "",
          "**VERIFICATION CLASS — free. No ledger row. No trial. No rule proposed.**",
          "**Standing counts: screens 15 · sealed opens 1 · n_trials 138.**", "",
          "```", json.dumps(res, indent=2, default=str), "```", "",
          "Reproduce: `python scripts/diag_r_denominator_audit.py`", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(json.dumps(res, indent=2, default=str).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
