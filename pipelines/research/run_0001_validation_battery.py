"""Validation battery for pre-reg 0001 — the placebo layer.

The primary gate answers "did it beat a control". This answers the harder question: **is the return
coming from the ranking, or from something that would produce the same number with no information
in it at all.** Five tests, each aimed at a different way a backtest lies.

1. **LAG TEST** — delay the signal by 1, 5 and 10 extra sessions.
   Genuine cross-sectional momentum is a slow signal; one extra day of lag should barely register.
   A sharp collapse at +1 day means the edge was living in information not available at execution
   time. This is the highest-value leakage detector per minute of effort, and the defect class it
   targets is the one no test in this repo currently covers.

2. **SIGNAL PERMUTATION** — shuffle the signal across names *within each date*, preserving the
   cross-sectional distribution exactly. Edge must collapse to the random control. If it does not,
   the return is coming from portfolio construction (equal weight, the buffer, the rebalance
   cadence) rather than from the ranking, which is a very different claim.

3. **SYNTHETIC DATA** — run the whole pipeline on geometric random walks with matched volatility.
   There is no structure to find, so any "edge" is by construction a bug or an artifact of the
   construction rules.

4. **INVERTED TIME** — run on reversed price series. Behavioural anomalies should not be
   time-symmetric; several classes of artifact are.

5. **TRADE FORENSICS** — sample 50 random fills and verify each one against the raw panel: the
   price existed on that date, sat inside the bar's high/low, and the size was small against that
   day's turnover. Execution leakage (filling where no trade was possible) does not show up in any
   aggregate statistic.

MEASUREMENT class. No new trial is spent — this validates trial 1 rather than testing a new
configuration.

    python pipelines/research/run_0001_validation_battery.py
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
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from run_0001_xsec_momentum import (BAND, BOOK, END, SEED, START, add_signals,  # noqa: E402
                                    random_control)
from run_bhanushali_path1 import corrected_universe  # noqa: E402

OUT = ROOT / "research" / "0001-xsec-momentum"


def run(panel: pd.DataFrame, **over) -> dict:
    cfg = RebalanceConfig(**{**BOOK, **over})
    return simulate_rebalance_book(panel, cfg=cfg, start=START, end=END, initial_capital=1_000_000.0)


def lag_signal(p: pd.DataFrame, days: int) -> pd.DataFrame:
    """Shift each name's rank forward by `days` sessions — strictly less information, never more."""
    q = p.copy()
    q["rank"] = q.groupby("ticker")["rank"].shift(days)
    return q


def permute_signal(p: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Shuffle ranks across names WITHIN each date. Same distribution, no information."""
    rng = np.random.default_rng(seed)
    q = p.copy()

    def _shuf(s: pd.Series) -> pd.Series:
        v = s.to_numpy(copy=True)
        m = np.isfinite(v)
        if m.sum() > 1:
            vals = v[m]
            rng.shuffle(vals)
            v[m] = vals
        return pd.Series(v, index=s.index)

    q["rank"] = q.groupby("date", group_keys=False)["rank"].apply(_shuf)
    return q


def invert_time(p: pd.DataFrame) -> pd.DataFrame:
    """Reverse each name's price series in place, keeping the date index. Ranks are recomputed
    downstream by the caller; here we only flip the prices the engine trades on."""
    q = p.sort_values(["ticker", "date"]).copy()
    for col in ("open", "high", "low", "close"):
        q[col] = q.groupby("ticker")[col].transform(lambda s: s.to_numpy()[::-1])
    return q.sort_values(["date", "ticker"]).reset_index(drop=True)


def synthetic_panel(p: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Geometric random walk per name with that name's own realised volatility and zero drift."""
    rng = np.random.default_rng(seed)
    out = []
    for tkr, g in p.groupby("ticker", sort=True):
        g = g.sort_values("date").copy()
        n = len(g)
        sd = float(pd.Series(g["close"].to_numpy()).pct_change().std(ddof=1) or 0.02)
        c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sd, n) - 0.5 * sd ** 2))
        g["close"] = c
        g["open"] = c
        g["high"] = c * 1.005
        g["low"] = c * 0.995
        out.append(g)
    return pd.concat(out, ignore_index=True)


def forensic(trades: list[dict], panel: pd.DataFrame, n: int = 50, seed: int = SEED) -> dict:
    """Verify sampled fills against the raw panel. Aggregates never reveal execution leakage."""
    rng = np.random.default_rng(seed)
    if not trades:
        return {"checked": 0}
    px = panel.set_index(["date", "ticker"])
    picks = rng.choice(len(trades), size=min(n, len(trades)), replace=False)
    bad_date, bad_range, big_size, ok = [], [], [], 0
    for i in picks:
        t = trades[int(i)]
        key = (pd.Timestamp(t["exit_date"]), t["ticker"])
        if key not in px.index:
            bad_date.append(t)
            continue
        bar = px.loc[key]
        lo, hi = float(bar["low"]), float(bar["high"])
        # `exit` is net of slippage+costs, so allow a 2% band around the bar
        if not (lo * 0.98 <= float(t["exit"]) <= hi * 1.02):
            bad_range.append({**t, "bar_low": lo, "bar_high": hi})
            continue
        adv = float(bar.get("adv_rupees_20d", 0.0) or 0.0)
        if adv > 0 and t["qty"] * float(t["exit"]) > 0.05 * adv:
            big_size.append({**t, "adv": adv})
            continue
        ok += 1
    return {"checked": len(picks), "clean": ok,
            "fill_on_a_date_with_no_bar": len(bad_date),
            "fill_outside_bar_range": len(bad_range),
            "size_above_5pct_of_adv": len(big_size),
            "examples": (bad_date + bad_range + big_size)[:3]}


def line(tag: str, m: dict) -> None:
    print(f"  {tag:<34} CAGR {m['cagr_pct']:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
          f"MaxDD {m['max_drawdown_pct']:>7.2f}%  trades {m['n_trades']:>5}")


def main() -> int:
    print("=== VALIDATION BATTERY — pre-reg 0001 ===")
    print("    the primary gate asked 'did it beat a control'. this asks whether the return")
    print("    comes from the RANKING or from something with no information in it.\n")

    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    band = p[keep].copy()
    band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                            band["nms"], np.nan)

    base = run(band)
    ctrl = run(random_control(band))
    print("=== REFERENCE ===")
    line("candidate", base["metrics"])
    line("random control", ctrl["metrics"])

    results = {"candidate": base["metrics"], "control": ctrl["metrics"]}

    print("\n=== 1. LAG TEST (a slow signal should barely notice +1 day) ===")
    lag_out = {}
    for d in (1, 5, 10):
        m = run(lag_signal(band, d))["metrics"]
        lag_out[f"lag_{d}"] = m
        drop = m["sharpe"] - base["metrics"]["sharpe"]
        line(f"+{d} session lag", m)
        print(f"      dSharpe vs base {drop:+.3f}")
    s0 = base["metrics"]["sharpe"]
    s1 = lag_out["lag_1"]["sharpe"]
    frac = (s0 - s1) / s0 if s0 else float("nan")
    print(f"    one-day decay: {frac*100:.1f}% of Sharpe")
    print("    READING: a monthly-ranked signal losing a large share of its Sharpe to ONE extra")
    print("    day of lag would indicate the edge sat in information unavailable at execution.")
    results["lag"] = {k: v["sharpe"] for k, v in lag_out.items()}
    results["one_day_sharpe_decay_frac"] = round(float(frac), 4)

    print("\n=== 2. SIGNAL PERMUTATION (same distribution, zero information) ===")
    perm = run(permute_signal(band))["metrics"]
    line("permuted ranks", perm)
    print(f"    vs random control Sharpe {ctrl['metrics']['sharpe']:.3f} — these should agree;")
    print("    a permuted book that still outperforms means the RETURN IS FROM CONSTRUCTION,")
    print("    not from the ranking.")
    results["permuted"] = perm

    print("\n=== 3. SYNTHETIC DATA (geometric random walk, matched vol, zero drift) ===")
    syn = synthetic_panel(band)
    syn_scored = add_signals(syn.assign(eligible=True, size_band=BAND))
    syn_scored["rank"] = syn_scored["nms"]
    sm = run(syn_scored)["metrics"]
    line("synthetic prices", sm)
    print("    READING: there is no structure to find. Any material edge here is a bug or an")
    print("    artifact of the construction rules, not a discovery.")
    results["synthetic"] = sm

    print("\n=== 4. INVERTED TIME (behavioural anomalies should not be symmetric) ===")
    inv = invert_time(band)
    inv_scored = add_signals(inv)
    inv_scored["rank"] = np.where(inv_scored["eligible"] & inv_scored["nms"].notna(),
                                  inv_scored["nms"], np.nan)
    im = run(inv_scored)["metrics"]
    line("reversed price series", im)
    results["inverted"] = im

    print("\n=== 5. TRADE FORENSICS (50 sampled fills vs the raw panel) ===")
    f = forensic(base["trades"], band, n=50)
    print(f"    checked {f['checked']} · clean {f['clean']}")
    print(f"    fill on a date with no bar   : {f['fill_on_a_date_with_no_bar']}")
    print(f"    fill outside the bar's range : {f['fill_outside_bar_range']}")
    print(f"    size above 5% of ADV         : {f['size_above_5pct_of_adv']}")
    for ex in f.get("examples", []):
        print(f"      e.g. {ex.get('ticker')} {ex.get('exit_date')} exit {ex.get('exit')}")
    results["forensics"] = {k: v for k, v in f.items() if k != "examples"}

    (OUT / "validation_battery.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n  -> {OUT / 'validation_battery.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
