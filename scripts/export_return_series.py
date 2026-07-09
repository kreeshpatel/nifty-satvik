"""Export the baseline_v1 daily portfolio return series + trade log for external research.

Regenerates the frozen-cfg long-horizon backtest from the PINNED OHLCV snapshot (the same
byte-reproducible input behind research/baseline_v1.json) and writes two flat files that the
downstream Sharpe/Sortino/drawdown study asked for:

  * ``daily_returns.csv`` — date, equity_net, ret_net, ret_gross, n_positions
      - ret_net   = daily return of the net-of-cost book (brokerage + STT + slippage baked in).
      - ret_gross = daily return of a COSTLESS re-run counterfactual (all fill costs zeroed);
                    labelled as a counterfactual because zeroing costs changes fills/sizing, so
                    it is NOT exactly ret_net + additive costs. ret_net is the trustworthy series.
      - post-tax is NOT a daily quantity in this engine (STCG is applied per-calendar-year on
        realized gains) — omitted here; approximate it from the trade log's per-year pnl.
  * ``tradelog.csv`` — entry_date, exit_date, symbol, trade_ret, exit_reason, hold_days, pnl
      - exit_reason normalized to {target, atr_stop, trailing, time_exit, stale}.
      - pnl (rupees, net) is kept so the STCG(20%) after-tax approximation is reproducible.

Also writes ``export_manifest.json`` (sha256 of the OHLCV pin, frozen cfg, headline metrics)
for provenance. The daily series is NOT otherwise persisted by run_cpcv.py (which saves only
summary JSON), so this script is the source of truth for the return path.

Usage (defaults reproduce baseline_v1):

    python scripts/export_return_series.py            # pinned dataset-pin-20260701, corrected
    python scripts/export_return_series.py --out-dir research/exports
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import load_frozen_cfg  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402

_REASON_MAP = {"stop": "atr_stop", "time": "time_exit", "target": "target",
               "trailing": "trailing", "stale": "stale"}


def _returns(equity_curve):
    """(dates, equities) -> list of (date, equity, ret) with ret=None on the first row."""
    out = []
    prev = None
    for e in equity_curve:
        eq = float(e["equity"])
        ret = None if prev is None or prev <= 0 else (eq / prev - 1.0)
        out.append((e["date"], eq, ret, int(e["n_positions"])))
        prev = eq
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export baseline daily returns + trade log")
    ap.add_argument("--mode", choices=["current", "union", "corrected"], default="corrected")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--pinned-release", default="dataset-pin-20260701")
    ap.add_argument("--out-dir", default=str(ROOT / "research" / "exports"))
    args = ap.parse_args(argv)

    from nq.data.features import compute_all_features
    from nq.data.fundamentals import load_fund_store
    from nq.data.ohlcv import OHLCV_CACHE, file_sha256, load_ohlcv_cache
    from nq.engine.panel import compose_ranked_panel
    import nq.engine.portfolio as portfolio
    from nq.engine.portfolio import simulate
    from run_cpcv import _fetch_pinned_release, _recorded_pin, build_universe

    cfg = load_frozen_cfg()
    cache = OHLCV_CACHE
    if not cache.exists():
        print(f"fetching pinned snapshot from release {args.pinned_release!r} -> {cache}", flush=True)
        _fetch_pinned_release(args.pinned_release, cache)

    ohlcv = load_ohlcv_cache(cache)
    if not ohlcv:
        print(f"ERROR: no OHLCV at {cache}", flush=True)
        return 2
    sha = file_sha256(cache)
    expect = _recorded_pin().get("ohlcv_sha256")
    pin_ok = (expect is None) or (sha == expect)
    print(f"OHLCV sha256={sha[:16]}... pin_match={pin_ok} names={len(ohlcv)}", flush=True)

    universe = build_universe(args.mode)
    features = compute_all_features(ohlcv)
    panel = compose_ranked_panel(features, ohlcv, fund_store=load_fund_store(),
                                 membership=load_membership())
    if panel.empty:
        print("ERROR: composed panel is empty", flush=True)
        return 1

    # ── net-of-cost run (the trustworthy series) ─────────────────────────────
    print("running NET backtest ...", flush=True)
    net = simulate(panel, cfg, start=args.start, end=args.end)

    # ── costless counterfactual (gross): zero per-leg cost + slippage on the module ──
    print("running GROSS (costless) counterfactual ...", flush=True)
    _leg, _slip = portfolio.LEG_COST, portfolio._slip
    portfolio.LEG_COST = 0.0
    portfolio._slip = lambda *a, **k: 0.0
    try:
        gross = simulate(panel, cfg, start=args.start, end=args.end)
    finally:
        portfolio.LEG_COST, portfolio._slip = _leg, _slip

    net_rows = _returns(net["equity_curve"])
    gross_by_date = {d: ret for d, _eq, ret, _n in _returns(gross["equity_curve"])}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dr_path = out_dir / "daily_returns.csv"
    with open(dr_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "equity_net", "ret_net", "ret_gross", "n_positions"])
        for d, eq, ret, npos in net_rows:
            w.writerow([d, f"{eq:.2f}",
                        "" if ret is None else f"{ret:.8f}",
                        "" if gross_by_date.get(d) is None else f"{gross_by_date[d]:.8f}",
                        npos])

    tl_path = out_dir / "tradelog.csv"
    trades = sorted(net["trades"], key=lambda t: (t["entry_date"], t["ticker"]))
    with open(tl_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entry_date", "exit_date", "symbol", "trade_ret", "exit_reason",
                    "hold_days", "pnl"])
        for t in trades:
            w.writerow([t["entry_date"], t["exit_date"], t["ticker"],
                        f"{t['return_pct'] / 100.0:.6f}",
                        _REASON_MAP.get(t["reason"], t["reason"]),
                        t["days_held"], f"{t['pnl']:.2f}"])

    m = net["metrics"]
    reason_counts: dict[str, int] = {}
    for t in trades:
        r = _REASON_MAP.get(t["reason"], t["reason"])
        reason_counts[r] = reason_counts.get(r, 0) + 1

    manifest = {
        "as_of_run": "regenerated locally from pinned snapshot",
        "ohlcv_sha256": sha, "pin_match_baseline_v1": pin_ok,
        "release_tag": args.pinned_release,
        "mode": args.mode, "start": args.start, "end": args.end,
        "n_names_with_data": len(ohlcv), "frozen_cfg": dict(cfg),
        "metrics_net": m, "exit_reason_counts": reason_counts,
        "files": {"daily_returns": dr_path.name, "tradelog": tl_path.name},
        "notes": [
            "ret_net is net of brokerage(0.03%/leg)+STT(0.10%/leg)+tiered slippage.",
            "ret_gross is a COSTLESS re-run counterfactual (fills re-priced at zero cost); "
            "not exactly ret_net+costs.",
            "post-tax is per-calendar-year STCG(20%) on realized pnl, not daily — approximate "
            "from tradelog pnl by exit-year.",
            "exit_reason: stop->atr_stop, time->time_exit; 'stale' = rare data-gap force-close.",
        ],
    }
    (out_dir / "export_manifest.json").write_text(json.dumps(manifest, indent=2, default=str),
                                                  encoding="utf-8")

    print(f"\nSANITY (net): CAGR {m.get('cagr_pct')}%  Sharpe {m.get('sharpe')}  "
          f"Sortino {m.get('sortino')}  MaxDD {m.get('max_drawdown_pct')}%  "
          f"Calmar {m.get('calmar')}  win {m.get('win_rate_pct')}%  n_trades {m.get('n_trades')}",
          flush=True)
    print(f"exit reasons: {reason_counts}", flush=True)
    print(f"wrote:\n  {dr_path}\n  {tl_path}\n  {out_dir / 'export_manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
