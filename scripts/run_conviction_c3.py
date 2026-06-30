"""Stage-C / C3 — conviction-weighted SIZING vs flat sizing, through the real promotion harness.

This IS an n_trials trial (a PROMOTE/KILL decision). The candidate scales per-trade risk by conviction
quintile (mean-preserved: multipliers renormalised across each day's new entries to mean 1.0, so
aggregate deployed risk is unchanged — a redistribution, not a size-up; the Kelly/Stage-D charter).
Pre-reg: diagnostics/research/preregistry/0073-conviction-sizing-c3.md (n_trials bumped BEFORE the run).

Reports, alongside the paired ΔSharpe/DSR verdict, the MEAN-PRESERVATION proof (same trade set, equal
total deployed notional) and the governance Kelly-multiple k = realised-ann-vol ÷ Sharpe (ceiling 0.5).

    python scripts/run_conviction_c3.py            # pinned (defaults from baseline_v1.json)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import RESULTS_DIR, load_frozen_cfg  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from scripts.run_cpcv import (_fetch_pinned_release, _recorded_pin,  # noqa: E402
                              build_universe)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="C3 conviction-weighted sizing vs flat (paired harness)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=str(RESULTS_DIR / "conviction_c3.json"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--pinned-release", default=_recorded_pin().get("release_tag"))
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)

    import numpy as np

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, file_sha256, load_ohlcv_cache,
                               save_ohlcv_cache)
    from nq.engine.panel import compose_ranked_panel
    from nq.research.conviction import add_conviction_score
    from nq.runner.research import (NOISE_FLOOR, _daily_returns, _dsr_from_bootstrap, run_backtest)
    from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric, bootstrap_delta
    from nq.validation.dsr import cumulative_n_trials
    from nq.validation.metrics import TRADING_DAYS, sharpe

    cfg = load_frozen_cfg()
    universe = build_universe(args.mode)
    end = args.end or date.today().isoformat()
    cache = Path(args.cache) if args.cache else OHLCV_CACHE

    expect = args.expect_sha256
    if args.pinned_release:
        if expect is None:
            expect = _recorded_pin().get("ohlcv_sha256")
        if not cache.exists():
            print(f"fetching pinned snapshot from release {args.pinned_release!r} -> {cache}", flush=True)
            _fetch_pinned_release(args.pinned_release, cache)

    ohlcv = load_ohlcv_cache(cache)
    if not ohlcv:
        if args.pinned_release or expect:
            print(f"ERROR: pinned run but no OHLCV snapshot at {cache}", flush=True)
            return 2
        ohlcv = download_ohlcv(universe, start=args.start, end=end)
        save_ohlcv_cache(ohlcv, cache)
    ohlcv_sha256 = file_sha256(cache)
    if expect and ohlcv_sha256 != expect:
        print(f"ERROR: OHLCV snapshot sha256 mismatch ({ohlcv_sha256} != {expect})", flush=True)
        return 2

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1
    panel = add_conviction_score(panel, gate_quantile=float(cfg["gate_quantile"]))

    base_cfg = dict(cfg)
    cand_cfg = {**cfg, "conviction_size": True}
    print("running C3: flat vs conviction-weighted sizing (paired bootstrap + DSR) ...", flush=True)
    base_bt = run_backtest(panel, base_cfg, start=args.start, end=end)
    cand_bt = run_backtest(panel, cand_cfg, start=args.start, end=end)

    # paired verdict (same primitives as nq.runner.research.evaluate_overlay)
    bser = _daily_returns(base_bt["equity_curve"])
    cser = _daily_returns(cand_bt["equity_curve"])
    common = bser.index.intersection(cser.index)
    a = cser.loc[common].to_numpy(dtype=float)   # candidate
    b = bser.loc[common].to_numpy(dtype=float)   # base
    nt = cumulative_n_trials()
    n_samples = 1000 if args.quick else 5000
    delta = bootstrap_delta(a, b, sharpe, block_size=DEFAULT_BLOCK, n_samples=n_samples, seed=12345)
    cand_ci = block_bootstrap_metric(a, sharpe, block_size=DEFAULT_BLOCK, n_samples=n_samples, seed=12345)
    dsr = _dsr_from_bootstrap(a, nt, (cand_ci.lower, cand_ci.upper))
    clean = bool(delta.lower > 0 and delta.point > NOISE_FLOOR)
    dsr_ok = bool(np.isfinite(dsr) and dsr > 0.95)
    underpowered = bool(not (clean and dsr_ok) and delta.point > 0 and delta.lower <= 0)
    verdict = ("PROMOTE-CANDIDATE" if (clean and dsr_ok)
               else "UNDERPOWERED" if underpowered else "KILL")

    # mean-preservation proof: same trade SET, equal total deployed notional (only the split differs)
    def _keys(tr): return {f"{t['entry_date']}|{t['ticker']}" for t in tr}
    def _notional(tr): return float(sum(t["qty"] * t["entry"] for t in tr))
    bk, ck = _keys(base_bt["trades"]), _keys(cand_bt["trades"])
    overlap = len(bk & ck) / max(len(bk | ck), 1)
    notional_ratio = (_notional(cand_bt["trades"]) / _notional(base_bt["trades"])
                      if _notional(base_bt["trades"]) else float("nan"))

    # governance Kelly-multiple k = realised-ann-vol / Sharpe (ceiling 0.5)
    ann_vol = float(b.std(ddof=0) * np.sqrt(TRADING_DAYS))
    base_sharpe = float(sharpe(b))
    k = ann_vol / base_sharpe if base_sharpe > 0 else float("nan")

    out = {
        "stage": "C3 — conviction-weighted sizing vs flat (n_trials TRIAL)",
        "prereg": "diagnostics/research/preregistry/0073-conviction-sizing-c3.md",
        "pin": {"ohlcv_sha256": ohlcv_sha256, "release_tag": args.pinned_release},
        "config": {"mode": args.mode, "start": args.start, "end": end},
        "n_trials": nt,
        "result": {
            "base_sharpe": round(base_sharpe, 3), "candidate_sharpe": round(float(sharpe(a)), 3),
            "base_cagr": base_bt["metrics"].get("cagr_pct"), "cand_cagr": cand_bt["metrics"].get("cagr_pct"),
            "base_maxdd": base_bt["metrics"].get("max_drawdown_pct"), "cand_maxdd": cand_bt["metrics"].get("max_drawdown_pct"),
            "dSharpe": round(delta.point, 3), "dSharpe_ci": [round(delta.lower, 3), round(delta.upper, 3)],
            "dsr_candidate": dsr, "verdict": verdict,
        },
        "mean_preservation": {
            "base_n_trades": len(base_bt["trades"]), "cand_n_trades": len(cand_bt["trades"]),
            "trade_set_overlap": round(overlap, 4), "deployed_notional_ratio": round(notional_ratio, 4),
            "note": "overlap~1.0 + notional_ratio~1.0 => same selection, mean-preserved (redistribution not size-up)",
        },
        "governance_kelly_multiple": {
            "k": round(k, 3), "definition": "realised annual vol / Sharpe (full-Kelly vol == Sharpe)",
            "ceiling": 0.5, "within_ceiling": bool(np.isfinite(k) and k <= 0.5),
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    r = out["result"]
    print(f"C3 verdict={verdict} | dSharpe={r['dSharpe']} ci={r['dSharpe_ci']} dsr={dsr:.3f} "
          f"| base_sh={r['base_sharpe']} cand_sh={r['candidate_sharpe']}", flush=True)
    print(f"  mean-preservation: trade_overlap={overlap:.3f} notional_ratio={notional_ratio:.3f} "
          f"(base {len(base_bt['trades'])} / cand {len(cand_bt['trades'])} trades)", flush=True)
    print(f"  governance k={k:.3f} (ceiling 0.5; within={out['governance_kelly_multiple']['within_ceiling']})"
          f" -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
