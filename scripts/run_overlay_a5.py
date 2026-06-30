"""A5 harness-trust gate — run the regime-to-cash overlay through the REAL promotion harness on
the PINNED corrected universe and assert it is NOT false-promoted.

The long-horizon rule already cuts losers via ATR stops, so a 200-session market filter classically
adds whipsaw + misses V-recoveries rather than risk-adjusted value — a known §11 KILL. This run
feeds that overlay to ``nq.runner.research.evaluate_overlay`` (paired ΔSharpe CI + DSR) and:

  * writes the verdict to ``results/overlay_a5.json`` (the ledger entry), and
  * EXITS NON-ZERO iff the verdict is PROMOTE-CANDIDATE — i.e. the gate FAILS loud if the harness
    false-promotes a no-edge overlay. Green = the harness can be trusted for Stage-C conviction work.

Pinned by default (reproducible): loads the dataset-pin snapshot via --pinned-release and verifies
its sha256 against research/baseline_v1.json, exactly like scripts/run_cpcv.py. Usage:

    python scripts/run_overlay_a5.py                       # pinned (defaults from baseline_v1.json)
    python scripts/run_overlay_a5.py --pinned-release dataset-pin-20260701
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
    ap = argparse.ArgumentParser(description="A5 harness-trust gate (regime overlay must not promote)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=str(RESULTS_DIR / "overlay_a5.json"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--pinned-release", default=_recorded_pin().get("release_tag"),
                    help="release tag of the pinned ohlcv.pkl (default = the pin in baseline_v1.json)")
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap resamples (smoke)")
    args = ap.parse_args(argv)

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, file_sha256, load_ohlcv_cache,
                               save_ohlcv_cache)
    from nq.engine.panel import compose_ranked_panel
    from nq.research.overlays import add_regime_gate_column
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
            print(f"fetching pinned snapshot from release {args.pinned_release!r} -> {cache}",
                  flush=True)
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
        print(f"ERROR: OHLCV snapshot sha256 mismatch\n  expected {expect}\n"
              f"  got      {ohlcv_sha256}", flush=True)
        return 2

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1
    panel = add_regime_gate_column(panel)

    print("running A5: base vs regime-to-cash overlay (paired bootstrap + DSR) ...", flush=True)
    res = evaluate_overlay(panel, cfg, {**cfg, "regime_gate": True}, start=args.start, end=end,
                           n_samples=(1000 if args.quick else 5000))

    n_risk_off_dates = int(panel.groupby("date")["regime_risk_off"].first().sum())
    out = {
        "gate": "A5 harness-trust — regime-to-cash overlay must NOT be promoted",
        "pin": {"ohlcv_sha256": ohlcv_sha256, "release_tag": args.pinned_release},
        "config": {"mode": args.mode, "start": args.start, "end": end},
        "n_risk_off_dates": n_risk_off_dates,
        "result": res,
        "gate_pass": res.get("verdict") != "PROMOTE-CANDIDATE",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"verdict={res.get('verdict')} dSharpe={res.get('dSharpe')} "
          f"ci={res.get('dSharpe_ci')} dsr={res.get('dsr_candidate')} "
          f"risk_off_dates={n_risk_off_dates} -> {out_path}", flush=True)

    if not out["gate_pass"]:
        print("A5 GATE FAILED: the harness PROMOTED a no-edge overlay — do not trust it.", flush=True)
        return 1
    print(f"A5 GATE PASS: harness returned {res.get('verdict')} (not a promotion).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
