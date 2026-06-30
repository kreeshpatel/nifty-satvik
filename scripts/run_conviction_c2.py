"""Stage-C / C2 — is the conviction score real? Conviction-at-entry IC vs realised per-trade P&L,
with a matched-permutation null.

A MEASUREMENT (no trade/PROMOTE decision → NOT an n_trials trial per diagnostics/research/n_trials.json).
It runs the frozen baseline backtest on the PINNED universe, attaches each trade's conviction
(computed at its entry date, within that day's selectable pool), and asks: does conviction rank the
realised trade return better than chance? Pre-reg: diagnostics/research/preregistry/0072-conviction-within-top15.md.

    python scripts/run_conviction_c2.py            # pinned (defaults from baseline_v1.json)
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
    ap = argparse.ArgumentParser(description="C2 conviction IC vs per-trade P&L (matched null)")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=str(RESULTS_DIR / "conviction_c2.json"))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--pinned-release", default=_recorded_pin().get("release_tag"))
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--n-perm", type=int, default=5000)
    args = ap.parse_args(argv)

    import numpy as np
    import pandas as pd

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import (OHLCV_CACHE, download_ohlcv, file_sha256, load_ohlcv_cache,
                               save_ohlcv_cache)
    from nq.engine.panel import compose_ranked_panel
    from nq.research.conviction import (CONVICTION_COL, QUINTILE_COL, add_conviction_score)
    from nq.runner.research import run_backtest
    from nq.validation.factor_ic import permutation_ic_pvalue

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
        print(f"ERROR: OHLCV snapshot sha256 mismatch ({ohlcv_sha256} != {expect})", flush=True)
        return 2

    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1
    panel = add_conviction_score(panel, gate_quantile=float(cfg["gate_quantile"]))

    bt = run_backtest(panel, cfg, start=args.start, end=end)
    trades = bt["trades"]

    # attach each trade's conviction (+ quintile) at its entry date, within that day's pool
    key = (pd.to_datetime(panel["date"]).dt.strftime("%Y-%m-%d") + "|" + panel["ticker"])
    conv_by_key = dict(zip(key, panel[CONVICTION_COL]))
    quint_by_key = dict(zip(key, panel[QUINTILE_COL]))
    rows = []
    for t in trades:
        k = f"{str(t['entry_date'])[:10]}|{t['ticker']}"
        c = conv_by_key.get(k, np.nan)
        if c is not None and np.isfinite(c):
            rows.append((float(c), float(t["return_pct"]), quint_by_key.get(k, np.nan)))
    conv = np.array([r[0] for r in rows], dtype=float)
    ret = np.array([r[1] for r in rows], dtype=float)
    quint = np.array([r[2] for r in rows], dtype=float)

    ic = permutation_ic_pvalue(conv, ret, n_perm=args.n_perm)

    # per-quintile mean return (the inspectable read: does mean P&L rise with conviction?)
    q_means = {}
    for q in range(1, 6):
        sel = quint == q
        if sel.any():
            q_means[f"Q{q}"] = {"n": int(sel.sum()), "mean_return_pct": round(float(ret[sel].mean()), 3),
                                "win_rate_pct": round(float((ret[sel] > 0).mean() * 100), 1)}

    p = ic.get("p_value")
    icv = ic.get("ic")
    verdict = ("SUPPORT" if (np.isfinite(p) and p < 0.05 and icv > 0)
               else "INCONCLUSIVE" if (np.isfinite(p) and p < 0.10 and icv > 0) else "KILL")

    out = {
        "stage": "C2 — conviction IC vs per-trade P&L (measurement; NOT an n_trials trial)",
        "prereg": "diagnostics/research/preregistry/0072-conviction-within-top15.md",
        "pin": {"ohlcv_sha256": ohlcv_sha256, "release_tag": args.pinned_release},
        "config": {"mode": args.mode, "start": args.start, "end": end,
                   "n_trades_with_conviction": int(conv.size)},
        "ic": ic,
        "quintile_mean_return": q_means,
        "verdict": verdict,
        "skeptical_prior": "finding 0021 — technical base has ~0 directional IC; conviction must "
                           "rank realised P&L (convexity), not direction. KILL is acceptable.",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"C2 verdict={verdict} | IC={icv:.4f} p={p:.4f} n={ic.get('n')} "
          f"null=[{ic.get('null_p05'):.3f},{ic.get('null_p95'):.3f}] -> {out_path}", flush=True)
    for q, v in q_means.items():
        print(f"  {q}: n={v['n']:4d} mean_ret={v['mean_return_pct']:+.2f}% WR={v['win_rate_pct']}%",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
