"""Pre-reg 0076 — uncapped target + ATR-proportionate trailing, through the full promotion bar.

Runs each grid arm (trail_atr_mult in {2.0,2.5,3.0,3.5}, target OFF) against the frozen base via
evaluate_overlay (the authoritative 7-gate verdict on the pinned baseline_v1), plus a paired 63-day
block-bootstrap dSortino CI. Writes research/exports/atr_trail_0076_results.json for the finding.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, evaluate_overlay, run_backtest  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, bootstrap_delta  # noqa: E402
from nq.validation.metrics import sortino  # noqa: E402

START, END, NT = "2017-01-01", "2026-06-30", 86
GRID = [2.0, 2.5, 3.0, 3.5]


def main():
    base = load_frozen_cfg()
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    base_bt = run_backtest(panel, base, start=START, end=END)
    base_r = _daily_returns(base_bt["equity_curve"])

    hdr = (f"{'mult':>5}{'candSh':>8}{'dSharpe [CI]':>22}{'dSortino [CI]':>22}{'DSR':>6}"
           f"{'dCalmar':>8}{'22-26dCAGR':>11}{'fold':>6}{'turn%':>7}{'atxCAGR':>8}  verdict")
    print("\n" + hdr)
    print("-" * len(hdr))
    out = []
    for mult in GRID:
        cand = {**base, "target_pct": 999.0, "trail_atr_mult": mult}
        r = evaluate_overlay(panel, base, cand, start=START, end=END, n_trials=NT, n_samples=5000)
        cand_bt = run_backtest(panel, cand, start=START, end=END)
        cand_r = _daily_returns(cand_bt["equity_curve"])
        common = base_r.index.intersection(cand_r.index)
        a, b = cand_r.loc[common].to_numpy(float), base_r.loc[common].to_numpy(float)
        ds = bootstrap_delta(a, b, sortino, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
        reasons = cand_bt["metrics"].get("exit_reasons", {})
        rec = {"trail_atr_mult": mult, **r,
               "dSortino": round(ds.point, 3), "dSortino_ci": [round(ds.lower, 3), round(ds.upper, 3)],
               "cand_maxdd": cand_bt["metrics"]["max_drawdown_pct"],
               "cand_calmar": cand_bt["metrics"]["calmar"],
               "cand_sortino": cand_bt["metrics"]["sortino"], "exit_reasons": reasons}
        out.append(rec)
        dsh = f"{r['dSharpe']:+.3f} [{r['dSharpe_ci'][0]:+.2f},{r['dSharpe_ci'][1]:+.2f}]"
        dso = f"{ds.point:+.3f} [{ds.lower:+.2f},{ds.upper:+.2f}]"
        dsr = r['dsr_candidate'] if r['dsr_candidate'] == r['dsr_candidate'] else float('nan')
        dcal = r['dCalmar'] if r['dCalmar'] is not None else float('nan')
        dcagr = r['subperiod_2022_dCAGR'] if r['subperiod_2022_dCAGR'] is not None else float('nan')
        fold = r['fold_pass_frac'] if r['fold_pass_frac'] is not None else float('nan')
        turn = r['turnover_delta'] * 100 if r['turnover_delta'] is not None else float('nan')
        atx = r['after_tax_cagr_cand'] if r['after_tax_cagr_cand'] is not None else float('nan')
        print(f"{mult:>5.1f}{r['candidate_sharpe']:>8.3f}{dsh:>22}{dso:>22}{dsr:>6.2f}"
              f"{dcal:>8.3f}{dcagr:>11.2f}{fold:>6.2f}{turn:>7.1f}{atx:>8.2f}  {r['verdict']}",
              flush=True)

    base_m = base_bt["metrics"]
    payload = {"prereg": "0076", "n_trials": NT, "anchor": "baseline_v1 dataset-pin-20260701",
               "base": {"sharpe": base_m["sharpe"], "sortino": base_m["sortino"],
                        "maxdd": base_m["max_drawdown_pct"], "calmar": base_m["calmar"],
                        "cagr": base_m["cagr_pct"], "after_tax_cagr": out[0]["after_tax_cagr_base"]},
               "arms": out}
    p = ROOT / "research" / "exports" / "atr_trail_0076_results.json"
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nbase: Sharpe {base_m['sharpe']} Sortino {base_m['sortino']} DD {base_m['max_drawdown_pct']} "
          f"Calmar {base_m['calmar']}\nwrote {p}")


if __name__ == "__main__":
    main()
