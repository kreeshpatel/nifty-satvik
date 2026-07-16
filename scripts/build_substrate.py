"""Stage-1 — the WIDE, UNCAPPED trade substrate for the swing research loop.

Regenerates EVERY candidate trade (not just the ~255 the ₹10L cap funds) across the full
detector set the engine already carries — 44SMA-touch (origin 0), box/Darvas (1), trend-
continuation (2), pivot-S/R (3) — and runs each through the LIVE Phase-2 exit engine
UNCAPPED, so per-trade R is capital-independent. This is the diagnostic substrate Stage 2
(AI-vision + ML) mines to answer "why do bad trades fail" on a sample large enough to have power.

Engine-faithful by construction: it reuses ``run_bhanushali_weekly_rank`` (the book of record) —
the detectors are strictly ADDITIVE (each ``& ~wsig``; touch origin-0 is never relabeled) and
``backtest(uncapped=True)`` is the engine's own per-signal lifecycle. No frozen code is edited;
``origin`` is read from ``entry_win`` (its 6th field). Determinism-gated: the capped-default run
still reproduces Sharpe 1.132 / 255.

Output: research/substrate/trades.parquet  (+ a per-origin expectancy readout to stdout).

    python scripts/build_substrate.py [--no-guard]
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.fundamentals import load_fund_store, value_quality_series  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.weekly import load_weekly_panel  # noqa: E402
from nq.research.setups import ZOO  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# The LIVE Phase-2 exit (owner-override 2026-07-15), byte-identical to run_bhanushali_cron.P2_EXIT.
P2_EXIT = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)
ZOO_ORIGINS = tuple(ZOO)  # 4..8 — the TraderLion zoo detectors
SETUP_NAMES = {0: "touch44", 1: "box", 2: "trend_pullback", 3: "sr_pivot",
               **{o: ZOO[o][0] for o in ZOO}}
OUT = ROOT / "research" / "substrate"
OUT.mkdir(parents=True, exist_ok=True)


def _day_origin_map(P):
    """Per-ticker {daily_index -> (origin, sma_sig)} covering every entry window's days."""
    m = {}
    for t, s in P.items():
        dm = {}
        for _e0, win in s["entry_win"].items():
            edays, _lo, _hi, _rk, sma_sig, origin = win
            for dcol in edays:
                dm[dcol] = (int(origin), float(sma_sig))
        m[t] = dm
    return m


def build():
    t0 = time.time()
    ohlcv = corrected_universe()
    mem = load_membership()
    fund = load_fund_store()
    print(f"[{time.time()-t0:.0f}s] universe={len(ohlcv)} fund_store={'ok' if fund else 'MISSING'}")

    # WIDE prep: every detector on. Additive -> touch trades unchanged, box/trend/sr + zoo(4-8) added.
    Pw = R94.prep_weekly_rank(ohlcv, box_breakout=True, trend_pullback=True, sr_pivot=True,
                              zoo_origins=ZOO_ORIGINS)
    didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in Pw.items()}
    dmap = _day_origin_map(Pw)
    print(f"[{time.time()-t0:.0f}s] wide prep: {len(Pw)} tickers")

    led = []
    m = R94.backtest(Pw, mem, ledger=led, start="2017-01-01", uncapped=True, **P2_EXIT)
    print(f"[{time.time()-t0:.0f}s] uncapped substrate: {len(led)} trades (activations={m['activations']})")

    rows = []
    for r in led:
        t = r["tkr"]; s = Pw[t]
        j0 = didx[t].get(pd.Timestamp(r["entry_date"]))
        j1 = didx[t].get(pd.Timestamp(r["exit_date"]))
        if j0 is None or j1 is None:
            continue
        origin, sma_sig = dmap[t].get(j0, (-1, float("nan")))
        lows = s["l"][j0:j1 + 1]; highs = s["h"][j0:j1 + 1]
        e2 = s["l"][j0:min(j0 + 11, j1 + 1)]
        en = float(r["entry"]); st = float(r["stop0"])
        rows.append(dict(
            ticker=t, entry_date=pd.Timestamp(r["entry_date"]), exit_date=pd.Timestamp(r["exit_date"]),
            origin=origin, setup=SETUP_NAMES.get(origin, "other"),
            entry=en, stop=st, exit_px=float(r["exit_px"]), reason=r["reason"],
            R=float(r["R"]), held_weeks=int(r["held_weeks"]), half_booked=r.get("half_date") is not None,
            rank_crs=float(r["rank"]),
            risk_pct=round((en - st) / en * 100, 3) if en > 0 else np.nan,
            ext_vs_sma=round((en / sma_sig - 1) * 100, 3) if sma_sig == sma_sig and sma_sig > 0 else np.nan,
            mae_pct=round((lows.min() / en - 1) * 100, 2) if len(lows) else 0.0,
            mfe_pct=round((highs.max() / en - 1) * 100, 2) if len(highs) else 0.0,
            mae_first2wk=round((e2.min() / en - 1) * 100, 2) if len(e2) else 0.0,
        ))
    df = pd.DataFrame(rows).sort_values(["ticker", "entry_date"]).reset_index(drop=True)

    # PIT-safe fundamentals at entry (strict-before merge_asof), per ticker.
    for col in ("ep", "bp", "roe", "low_debt"):
        df[col] = np.nan
    for t, g in df.groupby("ticker"):
        idx = pd.DatetimeIndex(g["entry_date"].values)
        order = np.argsort(idx.values)  # value_quality_series requires ascending dates
        vq = value_quality_series(t, fund, idx[order], df.loc[g.index[order], "entry"].to_numpy(float))
        for col in ("ep", "bp", "roe", "low_debt"):
            df.loc[g.index[order], col] = vq[col]

    # Weekly-panel features at the SIGNAL week (last completed week strictly before entry) — PIT-safe.
    wp = load_weekly_panel(cache=True).sort_values(["ticker", "week_end"])
    wp["tr_pct"] = (wp["h"] - wp["l"]) / wp["c"]
    gv = wp.groupby("ticker")
    wp["atr_pct"] = gv["tr_pct"].transform(lambda x: x.rolling(10).mean()) * 100
    wp["vol_ratio"] = gv["v"].transform(lambda x: x / x.rolling(10).mean().shift(1))
    wp["h52"] = gv["h"].transform(lambda x: x.rolling(52).max())
    feat = wp[["ticker", "week_end", "atr_pct", "vol_ratio", "h52"]]
    df = df.sort_values("entry_date").reset_index(drop=True)
    df = pd.merge_asof(df, feat.sort_values("week_end"), left_on="entry_date", right_on="week_end",
                       by="ticker", direction="backward", allow_exact_matches=False)
    df["dist_52wh_pct"] = np.where(df["h52"] > 0, (df["entry"] / df["h52"] - 1) * 100, np.nan)
    df = df.drop(columns=["week_end", "h52"])

    # Train / holdout split (survivorship-clean only >=2019).
    y = df["entry_date"].dt.year
    df["split"] = np.where(y <= 2018, "pre2019_untrusted",
                           np.where(y <= 2022, "train", "holdout"))

    OUT_PARQUET = OUT / "trades.parquet"
    df.to_parquet(OUT_PARQUET, index=False)
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()
    print(f"[{time.time()-t0:.0f}s] wrote {OUT_PARQUET} rows={len(df)} sha={h[:12]}")
    return df, ohlcv, mem


def per_origin(df):
    print("\n=== UNCAPPED per-setup expectancy (all rows) ===")
    print(f"{'setup':16s} {'N':>6s} {'win%':>6s} {'meanR':>7s} {'medR':>7s} {'PF':>6s}")
    for origin, g in sorted(df.groupby("origin")):
        R = g["R"].to_numpy()
        pf = R[R > 0].sum() / -R[R < 0].sum() if (R < 0).any() else float("inf")
        print(f"{SETUP_NAMES.get(origin, str(origin)):16s} {len(R):6d} {(R>0).mean()*100:6.1f} "
              f"{R.mean():7.3f} {np.median(R):7.3f} {pf:6.2f}")
    for split in ("train", "holdout"):
        g = df[df.split == split]
        print(f"  [{split}] N={len(g)}  meanR={g['R'].mean():.3f}  win={ (g['R']>0).mean()*100:.1f}%")


def guard(ohlcv, mem):
    """Regression gate: capped default (levers off) still reproduces the 0094 book."""
    Pd = R94.prep_weekly_rank(ohlcv)
    md = R94.backtest(Pd, mem, start="2017-01-01")
    ok = abs(md["sharpe"] - 1.132) < 0.01 and md["trades"] == 255
    print(f"\nGUARD capped-default sharpe={md['sharpe']:.4f} trades={md['trades']} -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    df, ohlcv, mem = build()
    per_origin(df)
    if "--no-guard" not in sys.argv:
        assert guard(ohlcv, mem), "determinism guard FAILED"
