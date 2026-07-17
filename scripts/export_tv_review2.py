"""Export a randomised trade list + a rules spec sheet (PDF) for manual TradingView review.

v3 (2026-07-16), owner request: "30 trades for loose and 30 stop trades and 20 good trades and all at
random, and a pdf for rules".

Source = the LIVE BOOK OF RECORD: base 0094 signal + P2 exit, all-grades, Rs10L, 2% risk (Sharpe 1.03 /
168 trades). Not the 4,391-trade substrate — the point is to audit what we would actually trade.

Split-cleaned: trades spanning an unadjusted split are DROPPED (the v1 list was topped by CGCL -17.32R,
which was a 1:4 split, not a loss). See DATA_BUG_unadjusted_splits.md.

Buckets are RANDOM samples (not cherry-picked extremes) so the owner sees the typical case:
  LOSS_RANDOM     30  R < 0
  STOPPED_RANDOM  30  exited via the stop
  GOOD_RANDOM     20  R >= 2
Buckets may overlap (most stops are losses); the overlap is reported.

    python scripts/export_tv_review2.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
from nq.data.membership import load_membership
from nq.data.ohlcv import load_demerger_reference
from run_bhanushali_faithful import EQ0
from run_bhanushali_path1 import corrected_universe
from diag_sleeves import P2_EXIT
from spec_sheet_pdf import build_pdf

OUT = ROOT / "research" / "substrate" / "tv_review"; OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260716
COLS = ["bucket", "tv_symbol", "signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct",
        "entry_date", "entry", "stop", "risk_pct", "ext_vs_sma", "crs_rank",
        "exit_date", "exit_px", "pct_move", "R", "mfe_pct", "mae_pct", "reason", "weeks_held"]


def find_splits(ohlcv, dem):
    """(ticker -> [dates]) of <-45% single-session moves that neither revert nor are known demergers."""
    out = {}
    for t, df in ohlcv.items():
        c = df["Close"]; r = c.pct_change()
        for d, v in r[r < -0.45].items():
            fwd = c.loc[d:].iloc[:6]
            if (fwd.max() / c.loc[d] - 1) > 0.8:
                continue                                     # reverts => bad tick, not a split
            if t in dem and str(pd.Timestamp(d).date()) in dem.get(t, set()):
                continue                                     # genuine demerger — legitimately left
            out.setdefault(t, []).append(pd.Timestamp(d))
    return out


def weekly_meta(P):
    """(ticker, entry_day_idx) -> signal-week date + that candle's geometry + the SMA."""
    meta = {}
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        c = np.asarray(s["c"], float); h = np.asarray(s["h"], float)
        l = np.asarray(s["l"], float); o = np.asarray(s["o"], float)
        iso = dates.isocalendar(); keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        wc = np.array([c[d[-1]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
        wl = np.array([l[d].min() for d in weeks]); wo = np.array([o[d[0]] for d in weeks])
        wsma = pd.Series(wc).rolling(44).mean().to_numpy()
        d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
        for e0 in s["entry_win"]:
            k = d2w.get(e0, 0) - 1
            if k < 1:
                continue
            rng = wh[k] - wl[k]
            meta[(t, dates[e0])] = dict(
                signal_week=dates[weeks[k][-1]],
                sig_ctl_pct=(wc[k] - wl[k]) / wc[k] * 100,
                sig_body_frac=((wc[k] - wo[k]) / rng) if rng > 0 else np.nan,
                sig_range_pct=rng / wl[k] * 100 if wl[k] > 0 else np.nan,
                sma=wsma[k])
    return meta


def main():
    ohlcv = corrected_universe(); mem = load_membership(); dem = load_demerger_reference()
    splits = find_splits(ohlcv, dem)
    P = R94.prep_weekly_rank(ohlcv)

    led = []
    m = R94.backtest(P, mem, ledger=led, start="2017-01-01", eq0=EQ0, **P2_EXIT)
    assert abs(m["sharpe"] - 1.0342) < 0.001 and m["trades"] == 168, "R1 baseline FAILED"
    print(f"live book of record: Sharpe {m['sharpe']:.4f} / {m['trades']} trades\n")

    t = pd.DataFrame(led)
    t["entry_date"] = pd.to_datetime(t.entry_date); t["exit_date"] = pd.to_datetime(t.exit_date)
    t = t.rename(columns={"tkr": "ticker", "stop0": "stop", "rank": "crs_rank"})

    n0 = len(t)
    t = t[~t.apply(lambda r: any(r.entry_date <= d <= r.exit_date for d in splits.get(r.ticker, [])),
                   axis=1)].copy()
    print(f"split-clean: {n0} -> {len(t)} ({n0-len(t)} dropped)")

    meta = weekly_meta(P)
    for k in ("signal_week", "sig_ctl_pct", "sig_body_frac", "sig_range_pct", "sma"):
        t[k] = [meta.get((r.ticker, r.entry_date), {}).get(k) for r in t.itertuples()]
    t = t.dropna(subset=["signal_week"])

    t["tv_symbol"] = "NSE:" + t.ticker
    t["risk_pct"] = (t.entry - t.stop) / t.entry * 100
    t["ext_vs_sma"] = (t.entry / t.sma - 1) * 100
    t["pct_move"] = (t.exit_px / t.entry - 1) * 100
    t["weeks_held"] = ((t.exit_date - t.entry_date).dt.days / 7).round(1)

    mfe, mae = [], []
    for r in t.itertuples():
        w = ohlcv[r.ticker].loc[r.entry_date:r.exit_date]
        mfe.append((w["High"].max() / r.entry - 1) * 100 if len(w) else np.nan)
        mae.append((w["Low"].min() / r.entry - 1) * 100 if len(w) else np.nan)
    t["mfe_pct"], t["mae_pct"] = mfe, mae

    rng = np.random.RandomState(SEED)
    def take(pool, n, lab):
        pool = pool.copy()
        if len(pool) > n:
            pool = pool.iloc[rng.choice(len(pool), n, replace=False)]
        return pool.assign(bucket=lab)

    loss = t[t.R < 0]; stop = t[t.reason.astype(str).str.startswith("stop")]; good = t[t.R >= 2]
    print(f"pools -> losses {len(loss)} | stopped {len(stop)} | good R>=2 {len(good)}")
    b1 = take(loss, 30, "LOSS_RANDOM"); b2 = take(stop, 30, "STOPPED_RANDOM"); b3 = take(good, 20, "GOOD_RANDOM")
    ov = len(set(b1.index) & set(b2.index))
    print(f"overlap LOSS n STOPPED: {ov} trades appear in both buckets (expected — most stops are losses)")

    allx = pd.concat([b1, b2, b3])
    for c in ("signal_week", "entry_date", "exit_date"):
        allx[c] = pd.to_datetime(allx[c]).dt.strftime("%Y-%m-%d")
    allx = allx[COLS].round(2)
    allx.to_csv(OUT / "tv_review_80.csv", index=False)
    print(f"\nwrote {OUT / 'tv_review_80.csv'}  ({len(allx)} rows)")

    print("\n=== bucket profiles ===")
    for b, g in allx.groupby("bucket", sort=False):
        print(f"  {b:16s} n={len(g):2d}  mean %move={g.pct_move.mean():+6.1f}%  meanR={g.R.mean():+5.2f}  "
              f"mean risk%={g.risk_pct.mean():4.1f}  mean ext={g.ext_vs_sma.mean():+5.1f}%  "
              f"mean MFE={g.mfe_pct.mean():+5.1f}%")

    pdf = build_pdf(OUT / "RULES_SPEC.pdf", m, len(t), allx)
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
