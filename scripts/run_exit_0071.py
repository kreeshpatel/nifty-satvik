"""LOCK-plan Step 2 / pre-reg 0071 — "let winners run": exit-structure arms vs the production exits,
through the MECHANIZED promotion bar (nq.runner.research.evaluate_overlay).

The last non-foreclosed alpha/expectancy lever and the correct 63d analogue of the v1 0022 KILL we are
forbidden to transfer (memory: trust only long-horizon data). Arms (cfg overrides; 9999 = OFF sentinel,
not a tuned threshold — makes the target/trailing thresholds unreachable, no engine change):
  * B stop_only (PRIMARY) — no target, no trailing: exit only on the ATR stop or the 63d time cap.
  * C no_trailing        — keep target, trailing OFF.
  * D no_target          — target OFF, keep trailing.

A TRIAL (already counted in n_trials — "sunk"; running it spends 0 net). Skeptical prior: 0047 found
trailing-off raised RAW EV but LOWERED risk-adjusted IR — so stop_only must clear the FULL bar
(ΔSharpe CI-low>0, ≥2019 fold-pass≥60%, ΔCalmar, 2022-26, turnover, DSR), not just higher CAGR.

    python scripts/run_exit_0071.py            # pinned (defaults from baseline_v1.json)
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

_OFF = 9999.0   # OFF sentinel: makes a target/trailing threshold unreachable


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="0071 let-winners-run exit arms vs production (mechanized bar)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=str(RESULTS_DIR / "exit_0071.json"))
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
        print(f"ERROR: OHLCV snapshot sha256 mismatch ({ohlcv_sha256} != {expect})", flush=True)
        return 2

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1

    arms = {
        "B_stop_only": {**cfg, "target_pct": _OFF, "trailing_activate_pct": _OFF},   # PRIMARY
        "C_no_trailing": {**cfg, "trailing_activate_pct": _OFF},
        "D_no_target": {**cfg, "target_pct": _OFF},
    }
    n_samples = 1000 if args.quick else 5000
    results = {}
    for name, arm_cfg in arms.items():
        print(f"running 0071 arm {name} vs production ...", flush=True)
        res = evaluate_overlay(panel, cfg, arm_cfg, start=args.start, end=end, n_samples=n_samples)
        results[name] = res
        print(f"  {name}: verdict={res.get('verdict')} gate_pass={res.get('gate_pass')} "
              f"dSharpe={res.get('dSharpe')} ci={res.get('dSharpe_ci')} dCalmar={res.get('dCalmar')} "
              f"sub2022={res.get('subperiod_2022_dCAGR')} fold={res.get('fold_pass_frac')} "
              f"dsr={res.get('dsr_candidate')}", flush=True)

    primary = results["B_stop_only"]
    out = {
        "stage": "LOCK Step 2 / pre-reg 0071 — let-winners-run exit arms (TRIAL, sunk)",
        "prereg": "diagnostics/research/preregistry/0071 (carried) — re-run on baseline_v1, mechanized bar",
        "pin": {"ohlcv_sha256": ohlcv_sha256, "release_tag": args.pinned_release},
        "config": {"mode": args.mode, "start": args.start, "end": end},
        "primary_arm": "B_stop_only",
        "primary_verdict": primary.get("verdict"),
        "arms": results,
        "skeptical_prior": "0047: trailing-off raised raw EV but LOWERED risk-adjusted IR. stop_only "
                           "must clear the full mechanized bar (CI-low>0, fold-pass>=60%, dCalmar, etc).",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"0071 PRIMARY (B_stop_only) verdict={primary.get('verdict')} "
          f"gate_pass={primary.get('gate_pass')} -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
