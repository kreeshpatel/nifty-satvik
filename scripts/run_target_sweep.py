"""Dig into the 0071 let-winners-run SHADOW lead — map the GIVE-BACK CURVE.

0071 found removing the +22.52% target improves the 63d strategy but UNDERPOWERED. Question (external
#6: momentum alpha decays hyperbolically → there IS an optimal give-back point, not "hold forever"): is
a HIGHER FINITE target better than pure no-target? Sweep target_pct ∈ {15, 22.52(base), 30, 40, OFF},
trailing kept ON (0071 C showed trailing is doing useful work). EXPLORATORY (understand the curve) —
not a new promote-trial; if a finite target Pareto-dominates the base it becomes a candidate.

    python scripts/run_target_sweep.py     # pinned
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

_OFF = 9999.0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="target_pct give-back sweep (0071 follow-up)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=str(RESULTS_DIR / "target_sweep.json"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--pinned-release", default=_recorded_pin().get("release_tag"))
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(argv)

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, file_sha256, load_ohlcv_cache,
                               save_ohlcv_cache)
    from nq.engine.panel import compose_ranked_panel
    from nq.runner.research import evaluate_overlay

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
        print(f"ERROR: sha256 mismatch ({ohlcv_sha256} != {expect})", flush=True)
        return 2

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1

    n_samples = 1000 if args.quick else 5000
    results = {}
    for tgt in (15.0, 30.0, 40.0, _OFF):                       # base target_pct = 22.52
        label = "OFF" if tgt == _OFF else str(tgt)
        res = evaluate_overlay(panel, cfg, {**cfg, "target_pct": tgt},
                               start=args.start, end=end, n_samples=n_samples)
        results[label] = res
        print(f"  target={label}: verdict={res.get('verdict')} dSharpe={res.get('dSharpe')} "
              f"ci={res.get('dSharpe_ci')} cand_sh={res.get('candidate_sharpe')} "
              f"dCalmar={res.get('dCalmar')} sub2022={res.get('subperiod_2022_dCAGR')} "
              f"fold={res.get('fold_pass_frac')} dsr={round(res.get('dsr_candidate',0),3)} "
              f"afterTax_cand={res.get('after_tax_cagr_cand')}", flush=True)

    out = {
        "stage": "0071 follow-up — target_pct give-back sweep (exploratory, base target=22.52)",
        "pin": {"ohlcv_sha256": ohlcv_sha256, "release_tag": args.pinned_release},
        "config": {"mode": args.mode, "start": args.start, "end": end},
        "base_after_tax_cagr": next(iter(results.values())).get("after_tax_cagr_base"),
        "arms": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"target sweep done -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
