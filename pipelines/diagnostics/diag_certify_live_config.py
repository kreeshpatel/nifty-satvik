"""A1 — certify the configuration that actually trades. Pre-registered in forward/prereg_swing_A1.md.

MEASUREMENT, no trial. `n_trials` stays 2. ONE configuration, run ONCE, no variants, no sweep.

The primary headline is read at **2025-12-31**, per §4a, because 28% of final equity at 2026-06-29 is
an unrealised end-of-sample mark. The stop date is applied as a **continuous slice of the one run** —
never a truncated re-run, which would force a liquidation that never happened and charge costs for it.

The DSR gate reads the **certified** count 114, per §4b, so the live config faces the bar base-swing
faced. The live (2) and lifetime (140) counts are reported alongside.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap, after_tax_curve  # noqa: E402
from nq.validation.bootstrap import block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials, lifetime_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

CUT = "2025-12-31"          # PRIMARY, per prereg §4a
FULL = "2026-06-29"         # secondary line only
CERTIFIED_N_TRIALS = R94.CERTIFIED_N_TRIALS
# NOTE the third slice is labelled by its registered name but, at the PRIMARY 2025-12-31 stop, it
# actually spans 2022-2025. The 0.91 recorded for the "2022-26 gate" in docs/decisions/0010 is a
# full-window figure and is NOT this number; comparing them directly would be an end-date error of
# exactly the kind diag_end_of_sample_stub.py measured.
SLICES = [("2017-18", "2017-01-01", "2018-12-31"), ("2019-21", "2019-01-01", "2021-12-31"),
          ("2022-onward (2022-2025 at the primary stop)", "2022-01-01", "2026-12-31")]
OUT = ROOT / "diagnostics" / "research" / "certify_live_config_A1.json"
OUT_MD = ROOT / "diagnostics" / "research" / "certify_live_config_A1.md"


def after_tax_cagr(ec: list[dict], trades: list[dict], stcg: float = 0.20) -> float:
    """After-tax CAGR with the FINAL year charged.

    `after_tax_curve` applies each year's drag at the first session of the next year, so the last
    calendar year in a window is never charged (found by red-team 2026-08-09). Here the final year's
    bill is applied explicitly to the terminal equity.
    """
    at = after_tax_curve({"equity_curve": ec, "trades": trades}, stcg=stcg)
    if not at:
        return float("nan")
    last_year = int(str(ec[-1]["date"])[:4])
    realised_last = sum(float(t["pnl"]) for t in trades if int(str(t["exit_date"])[:4]) == last_year)
    final = float(at[-1]["equity"]) - stcg * max(0.0, realised_last)
    yrs = (pd.Timestamp(ec[-1]["date"]) - pd.Timestamp(ec[0]["date"])).days / 365.25
    return round(((final / EQ0) ** (1 / yrs) - 1) * 100, 3)


def slice_cagr(eq: pd.Series, lo: str, hi: str) -> float | None:
    s = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    if len(s) < 2 or s.iloc[0] <= 0:
        return None
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return round(((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 else None


def slice_sharpe(eq: pd.Series, lo: str, hi: str) -> float | None:
    s = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    r = s.pct_change().dropna()
    return round(float(r.mean() / r.std() * np.sqrt(252)), 3) if len(r) > 60 and r.std() else None


def read_at(curve: pd.Series, ledger: list, upto: str) -> dict:
    eq = curve[curve.index <= pd.Timestamp(upto)].sort_index()
    tr = [{**r, "pnl": float(r["net_pnl"])} for r in ledger
          if r.get("exit_date") is not None and r.get("net_pnl") is not None
          and pd.Timestamp(str(r["exit_date"])[:10]) <= pd.Timestamp(upto)]
    ec = [{"date": str(d)[:10], "equity": float(v)} for d, v in eq.items()]
    r = eq.pct_change().dropna()
    arr = r.to_numpy(float)
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=63, n_samples=5000, seed=12345)
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / EQ0) ** (1 / yrs) - 1) * 100
    dd = float((eq / eq.cummax() - 1).min()) * 100
    R = np.array([float(t.get("R", np.nan)) for t in tr], dtype=float)
    # positions open AT this date: entered on or before, exited after (or never)
    open_now = [r for r in ledger
                if pd.Timestamp(str(r["entry_date"])[:10]) <= pd.Timestamp(upto)
                and (r.get("exit_date") is None
                     or pd.Timestamp(str(r["exit_date"])[:10]) > pd.Timestamp(upto))]
    return {
        "upto": upto, "sessions": int(len(eq)), "years": round(yrs, 3),
        "n_closed": len(tr),
        "sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3),
        "cagr_pct": round(cagr, 3), "maxdd_pct": round(dd, 2),
        "calmar": round(cagr / abs(dd), 3) if dd else None,
        "win_rate_pct": round(float((R > 0).mean()) * 100, 2) if R.size and np.isfinite(R).any() else None,
        "final_equity": round(float(eq.iloc[-1]), 2),
        "after_tax_cagr_pct": after_tax_cagr(ec, tr),
        "bootstrap_sharpe_ci": [round(ci.lower, 3), round(ci.upper, 3)],
        "dsr_at_certified_114": round(_dsr_from_bootstrap(arr, CERTIFIED_N_TRIALS, (ci.lower, ci.upper)), 4),
        "dsr_at_live": round(_dsr_from_bootstrap(arr, cumulative_n_trials(), (ci.lower, ci.upper)), 4),
        "dsr_at_lifetime": round(_dsr_from_bootstrap(arr, lifetime_n_trials(), (ci.lower, ci.upper)), 4),
        "slices": {n: {"cagr_pct": slice_cagr(eq, lo, hi), "sharpe": slice_sharpe(eq, lo, hi)}
                   for n, lo, hi in SLICES},
        "open_positions_at_date": len(open_now),
    }


def main() -> int:
    print("building weekly panel ...", flush=True)
    ohlcv, mem = corrected_universe(), load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)

    print("running the LIVE configuration (once) ...", flush=True)
    led: list = []
    m = R94.backtest(P, mem, ledger=led, start="2017-01-01", eq0=EQ0, a_grade=a,
                     **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)
    curve = m["curve"].sort_index()

    # §7 falsifier: parity against the numbers already committed in mc_year_on_year_P.py
    yrs_f = (curve.index[-1] - curve.index[0]).days / 365.25
    cagr_f = (curve.iloc[-1] / EQ0) ** (1 / yrs_f) - 1
    dd_f = float((curve / curve.cummax() - 1).min())
    assert m["trades"] == 130 and abs(cagr_f - 0.272) < 0.01 and abs(dd_f + 0.395) < 0.01, (
        f"PARITY FAILED — the reconstruction is not the live book: trades={m['trades']} "
        f"cagr={cagr_f:.3f} dd={dd_f:.3f} (expected 130 / 0.272 / -0.395). Run is VOID.")
    print("  parity OK: 130 trades / 27.2% / -39.5%\n", flush=True)

    primary, secondary = read_at(curve, led, CUT), read_at(curve, led, FULL)

    g = {"dsr_gt_0.95_at_114": bool(primary["dsr_at_certified_114"] > 0.95),
         "ci_low_gt_0": bool(primary["bootstrap_sharpe_ci"][0] > 0),
         "all_slices_positive": bool(all((v["cagr_pct"] or -1) > 0 for v in primary["slices"].values()))}
    outcome = "CERTIFIED-EQUIVALENT" if all(g.values()) else "UNCERTIFIED, BOUNDED"

    out = {"_doc": "A1 certification of the live configuration. MEASUREMENT, no trial.",
           "prereg": "forward/prereg_swing_A1.md",
           "reproduce": "python pipelines/diagnostics/diag_certify_live_config.py",
           "n_trials_unchanged": cumulative_n_trials(),
           "config": {"grading": "A-only", **LIVE_DISCIPLINE, **LIVE_STALENESS,
                      "exit": "config P (40%@2R / 40% blow-off@2.5R / 20% runner to 44w SMA)"},
           "primary_at_2025_12_31": primary, "secondary_full_window": secondary,
           "gates": g, "outcome": outcome,
           "slice_2022_26_note": (
               "Pre-declared NOT RESOLVABLE in prereg §6: config P scores 0.91 against a 1.04 bar, a "
               "-0.13 miss that is roughly one fifth of the ±0.59 dSharpe half-width. Recorded, not "
               "litigated."),
           }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    md = ["# A1 — certifying the live configuration (MEASUREMENT, no trial)", "",
          f"Pre-registered: `forward/prereg_swing_A1.md`. `n_trials` unchanged at {cumulative_n_trials()}.",
          "", "| | **PRIMARY 2025-12-31** | secondary (full window) |", "|---|--:|--:|"]
    for k, lab in [("n_closed", "closed trades"), ("sharpe", "Sharpe"), ("cagr_pct", "CAGR %"),
                   ("after_tax_cagr_pct", "after-tax CAGR %"), ("maxdd_pct", "MaxDD %"),
                   ("calmar", "Calmar"), ("dsr_at_certified_114", "DSR @ certified 114"),
                   ("dsr_at_live", "DSR @ live"), ("dsr_at_lifetime", "DSR @ lifetime"),
                   ("open_positions_at_date", "positions still open")]:
        md.append(f"| {lab} | **{primary[k]}** | {secondary[k]} |")
    md += ["", f"Bootstrap 95% Sharpe CI: **{primary['bootstrap_sharpe_ci']}** (primary)", "",
           "| slice | CAGR % | Sharpe |", "|---|--:|--:|"]
    for n, v in primary["slices"].items():
        md.append(f"| {n} | {v['cagr_pct']} | {v['sharpe']} |")
    md += ["", "## Gates (pre-committed §6)", ""]
    for k, v in g.items():
        md.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")
    md += ["", f"## Outcome: **{outcome}**", "", out["slice_2022_26_note"]]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"  PRIMARY (2025-12-31): Sharpe {primary['sharpe']} | CAGR {primary['cagr_pct']}% "
          f"(after tax {primary['after_tax_cagr_pct']}%) | MaxDD {primary['maxdd_pct']}%")
    print(f"    CI {primary['bootstrap_sharpe_ci']} | DSR @114 {primary['dsr_at_certified_114']} "
          f"| @live {primary['dsr_at_live']} | @lifetime {primary['dsr_at_lifetime']}")
    print(f"    slices: " + " | ".join(f"{n} {v['cagr_pct']}%/{v['sharpe']}"
                                       for n, v in primary["slices"].items()))
    print(f"    still open at the cut: {primary['open_positions_at_date']} positions")
    print(f"  gates: {g}")
    print(f"\n  OUTCOME: {outcome}")
    print(f"\nwrote {OUT.relative_to(ROOT)} + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
