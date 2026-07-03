"""Event study on the ~2.6k engine-A qualifying signals (weekly-uptrend + daily RSI<35 cross-up + quality
green + HVC): is the weekly filter selecting RESILIENT stocks or just slowing the bleed? Measures (1) the
days-to-recovery distribution (close back above the daily 44-SMA), (2) forward returns vs a universe
control, (3) what the buy-above-high trigger adds — outcomes of triggered vs never-triggered signals, and
(4) stop-first-vs-trigger-first ordering. Diagnostic only (no n_trials, no portfolio, no costs).

REVIEWER FIX (selection bias): the triggered-vs-untriggered split conditioned on the first ~3 days' outcome
and measured returns from the SIGNAL close, so the triggered side embedded the pop up to the trigger. The
trigger section now measures the triggered subset from the FILL price on the trigger day. Also added the
separability control: the identical trigger mechanic on a generic-dip pool (weekly uptrend + close >=8%
below its 20d high + quality green + HVC, no RSI condition) — does the trigger edge survive without RSI?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_practitioner import prep  # noqa: E402

HORIZONS = (5, 10, 20, 40, 60)
CAP = 60


def pool_masks(s):
    """(RSI pool, generic-dip control pool) — identical confirmation context, only the dip definition differs."""
    c = s["c"]
    dd20 = c / pd.Series(c).rolling(20).max().to_numpy() - 1.0
    base = s["wtrend"] & s["qgreen"] & s["hvc"]
    return base & s["rsix"], base & np.nan_to_num(dd20 <= -0.08, nan=False) & ~s["rsix"]


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    start = pd.Timestamp("2017-01-01")
    rows = []
    fills = {"rsi": [], "dip": []}                                       # fill-based triggered outcomes
    ctrl = {h: [] for h in HORIZONS}
    for t, s in P.items():
        c, h_, l_, dsma = s["c"], s["h"], s["l"], s["dsma"]
        n = len(c)
        sigA, sigDip = pool_masks(s)
        in_win = s["dates"] >= start
        # fill-based trigger outcomes for both pools (identical mechanic)
        for key, mask in (("rsi", sigA), ("dip", sigDip)):
            for i in np.flatnonzero(mask & in_win):
                if i + 3 + max(HORIZONS) >= n:
                    continue
                trig, stop = h_[i] * 1.001, l_[i] * 0.999
                rec = dict(triggered=False, knife=False)
                for k in range(1, 4):
                    if l_[i + k] <= stop:
                        rec["knife"] = True
                        break
                    if h_[i + k] >= trig:
                        j = i + k
                        fill = max(s["o"][j], trig)
                        rec["triggered"] = True
                        for hz in (10, 20, 60):
                            rec[f"f{hz}"] = c[j + hz] / fill - 1.0
                        break
                fills[key].append(rec)
        # universe control: all in-window days with valid forward horizon (same names, same window)
        for h in HORIZONS:
            v = np.full(n, np.nan)
            v[:-h] = c[h:] / c[:-h] - 1.0
            m = in_win & np.isfinite(v)
            if m.any():
                ctrl[h].append(v[m])
        for i in np.flatnonzero(sigA & in_win):
            if i + CAP + 1 >= n:
                continue
            r = dict(tkr=t)
            for h in HORIZONS:
                r[f"f{h}"] = c[i + h] / c[i] - 1.0
            # days until close back above the daily 44-SMA (resilience metric)
            rec = np.nan
            for k in range(1, CAP + 1):
                if np.isfinite(dsma[i + k]) and c[i + k] > dsma[i + k]:
                    rec = k
                    break
            r["rec_days"] = rec
            r["above_at_sig"] = bool(np.isfinite(dsma[i]) and c[i] > dsma[i])
            # trigger vs stop within 3 days (his entry rule)
            trig, stop = h_[i] * 1.001, l_[i] * 0.999
            hit = stopped_first = False
            for k in range(1, 4):
                if l_[i + k] <= stop:
                    stopped_first = True
                    break
                if h_[i + k] >= trig:
                    hit = True
                    break
            r["triggered"] = hit
            r["stopped_before_trigger"] = stopped_first
            # max adverse excursion over 20d from signal close
            r["mae20"] = l_[i + 1:i + 21].min() / c[i] - 1.0
            rows.append(r)
    df = pd.DataFrame(rows)
    cm = {h: np.concatenate(ctrl[h]).mean() for h in HORIZONS}
    print(f"engine-A qualifying signals (2017+, with 60d forward): {len(df)}\n")
    print("=== forward returns from the SIGNAL close vs universe control ===")
    for h in HORIZONS:
        print(f"  {h:>2}d: signal {df[f'f{h}'].mean()*100:+5.2f}%  vs universe {cm[h]*100:+5.2f}%  "
              f"(edge {df[f'f{h}'].mean()*100 - cm[h]*100:+5.2f}pp)")
    print("\n=== days-to-recovery (close back above the daily 44-SMA; cap 60d) ===")
    r = df["rec_days"]
    print(f"  already above at signal: {df['above_at_sig'].mean()*100:.0f}%")
    print(f"  never within 60d: {r.isna().mean()*100:.0f}%")
    q = r.dropna()
    print(f"  of recoveries: median {q.median():.0f}d | p25 {q.quantile(.25):.0f}d | p75 {q.quantile(.75):.0f}d")
    print(f"  MAE 20d: median {df['mae20'].median()*100:+.1f}% | p10 {df['mae20'].quantile(.10)*100:+.1f}%")
    print("\n=== what the buy-above-high trigger adds (3-day window; SIGNAL-CLOSE basis, biased upward) ===")
    print(f"  triggered {df['triggered'].mean()*100:.0f}% | stop hit first {df['stopped_before_trigger'].mean()*100:.0f}% "
          f"| neither {(~df['triggered'] & ~df['stopped_before_trigger']).mean()*100:.0f}%")
    for h in (10, 20, 60):
        a = df.loc[df["triggered"], f"f{h}"].mean() * 100
        b = df.loc[~df["triggered"], f"f{h}"].mean() * 100
        print(f"  {h:>2}d fwd: triggered {a:+5.2f}% vs not-triggered {b:+5.2f}%  (biased split {a-b:+.2f}pp)")

    print("\n=== FILL-BASIS trigger economics (unbiased: measured from the fill price on the trigger day) ===")
    for key, label in (("rsi", "RSI pool"), ("dip", "generic-dip control (no RSI)")):
        F = pd.DataFrame(fills[key])
        tr = F[F["triggered"]]
        print(f"  {label}: signals {len(F)} | triggered {F['triggered'].mean()*100:.0f}% | knife-refused {F['knife'].mean()*100:.0f}%")
        for h in (10, 20, 60):
            e = tr[f'f{h}'].mean() * 100
            print(f"    {h:>2}d from fill: {e:+5.2f}%  vs universe {cm[h]*100:+5.2f}%  (edge {e - cm[h]*100:+5.2f}pp)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
