"""Leakage/lookahead audit of the 0085 six-step runner-trail stack (MEASUREMENT — no n_trials cost).

Runs the skills/leakage-audit §1-§6 sweep as executable checks:
  T1 truncation test — every signal component byte-identical when the future is dropped
  T2 trail-ratchet order — the stop used on day i was set from day i-1's (or earlier) EMA
  T3 entry timing — no order fills on its own signal day
  T4 weekly-bucket PIT — bucket value on day i derives from the last COMPLETED W-FRI bar <= i
  T5 survivorship — delisted/backfill names actually appear in the trade ledger
  T6 price-only contract — no fundamentals/labels enter the signal
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import prep  # noqa: E402
from run_bhanushali_sixstep_runner import TRAIL_EMA_SPAN, add_ema  # noqa: E402

RNG = np.random.default_rng(42)


def truncation_test(ohlcv, n_pairs=10):
    """Definitive lookahead probe: feature values at date d must be identical when all bars
    after d are dropped. Applied to every signal component + the trail EMA."""
    P_full = add_ema(prep(ohlcv))
    names = [t for t, s in P_full.items() if s["sig"].sum() > 3]
    fails = []
    checked = 0
    for t in RNG.choice(names, size=min(n_pairs, len(names)), replace=False):
        s = P_full[t]
        sig_idx = np.flatnonzero(s["sig"])
        i = int(RNG.choice(sig_idx))
        if i < 250:
            continue
        d = s["dates"][i]
        df_trunc = ohlcv[t][ohlcv[t].index <= d]
        P_t = add_ema(prep({t: df_trunc}))
        st = P_t[t]
        for f in ("sig", "wbucket", "dtrend", "touch", "touch_recent", "green"):
            if bool(s[f][i]) != bool(st[f][-1]):
                fails.append((t, str(d.date()), f, bool(s[f][i]), bool(st[f][-1])))
        for f in ("dsma", "ema20", "adv20"):
            a, b = s[f][i], st[f][-1]
            if np.isfinite(a) != np.isfinite(b) or (np.isfinite(a) and abs(a - b) > 1e-9):
                fails.append((t, str(d.date()), f, a, b))
        checked += 1
    return checked, fails


def code_order_checks():
    """Static checks on the engine source (order-of-operations lookahead)."""
    src = (ROOT / "scripts" / "run_bhanushali_sixstep_runner.py").read_text(encoding="utf-8")
    results = {}
    # T2: the ratchet update must appear AFTER the exit-check block in the daily loop
    exit_pos = src.find('s["l"][i] <= p["stop"]')
    ratchet_pos = src.find('p["stop"] = max(p["stop"], s["ema20"][i]')
    results["T2_ratchet_after_exit_checks"] = 0 < exit_pos < ratchet_pos
    # T3: new orders are appended AFTER the fill loop in the same day's body -> no same-day fill
    fill_pos = src.find("for t in sorted(orders")
    new_pos = src.find('orders[t] = dict(trig=')
    results["T3_orders_created_after_fill_loop"] = 0 < fill_pos < new_pos
    # T6: no fundamentals / forward columns anywhere in the signal build
    prep_src = (ROOT / "scripts" / "run_bhanushali_sixstep.py").read_text(encoding="utf-8")
    results["T6_price_only_no_fwd_or_fundamentals"] = all(
        k not in prep_src for k in ("fwd_", "roe", "debt_equity", "_label", "target_col"))
    return results


def weekly_pit_check(ohlcv, n=5):
    """T4: bucket value on day i equals the bucket computed from weekly bars ENDING <= day i."""
    P = prep(ohlcv)
    names = [t for t, s in P.items() if s["wbucket"].any()]
    fails = 0
    for t in RNG.choice(names, size=min(n, len(names)), replace=False):
        s = P[t]
        df = ohlcv[t]
        for i in RNG.choice(np.flatnonzero(s["wbucket"]), size=3, replace=False):
            d = s["dates"][i]
            w = df[df.index <= d].resample("W-FRI").agg({"Close": "last"}).dropna()
            wsma = w["Close"].rolling(44).mean()
            ok = bool((w["Close"].iloc[-1] > wsma.iloc[-1]) and (wsma.iloc[-1] > wsma.iloc[-5]))
            if ok != bool(s["wbucket"][i]):
                fails += 1
    return fails


def survivorship_check(ohlcv):
    """T5: backfill/alias names must appear in the traded ledger (not survivor-only)."""
    import json as _json
    import pickle
    led = pd.read_csv(ROOT / "research" / "exports" / "bhanushali_sixstep_runner_0085_trades.csv")
    bf = pickle.load(open(ROOT / "data" / "ohlcv_backfill.pkl", "rb"))
    amap = _json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
    special = set(bf) | set(amap)
    traded = set(led["tkr"])
    hit = sorted(traded & special)
    return len(special), len(hit), hit[:12]


def main() -> int:
    ohlcv = corrected_universe()
    print("=== 0085 leakage audit (measurement) ===")
    checked, fails = truncation_test(ohlcv)
    print(f"T1 truncation test: {checked} (ticker,signal-date) pairs, {len(fails)} mismatches")
    for f in fails[:10]:
        print("   FAIL:", f)
    for k, v in code_order_checks().items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")
    wf = weekly_pit_check(ohlcv)
    print(f"T4 weekly-bucket PIT spot-check: {wf} mismatches")
    tot, hit, sample = survivorship_check(ohlcv)
    print(f"T5 survivorship: {hit}/{tot} backfill+alias names traded in the 0085 ledger; sample {sample}")
    print("T6 fundamentals/labels in signal path: see static check above (price+volume only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
