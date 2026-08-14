"""Delivery ACCUMULATION as a temporal entry-timing signal — the measurement chain behind finding
0139. MEASUREMENT ONLY: no promote/kill decision, no screen-ledger row, no trial. It characterizes a
composite weekly delivery-accumulation score `A` and answers, with matched controls, why the real
universe-level delivery alpha (0118, +0.363R) does not help the Bhanushali momentum book (0119,
-1.29 R/yr) — and where it DOES pay.

Narrow (vs 0118/0119, which tested delivery CROSS-SECTIONALLY at the fixed entry): this is the
TEMPORAL within-name accumulation-window formulation, untested there. Composite (owner-chosen, all
four facets), equal-weight — NO fitted weights (Law VIII / 0133 specification-multiplicity).

Sections
  [1] universe weekly IC + IC-decay + regime stability + persistence/half-life
  [2] book collapse: partial correlation of A on Bhanushali trades, controlling ext & CRS
  [3] mechanism: matched high-A vs low-A within ext x CRS cells; A-tercile behaviour (MFE/stop/hold)
  [4] flip-side: accumulation-onset forward returns vs ext-matched null; base-onset vs extended-onset

Run:  python pipelines/diagnostics/diag_delivery_accumulation.py [--chart PATH]
All features are trailing-only (delivery is EOD-available; PIT per tests/test_delivery_pit.py).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import DATA_DIR  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

TRADES = Path(__file__).resolve().parents[2] / "research" / "substrate" / "trades.parquet"


def _slope(x: np.ndarray) -> float:
    n = len(x)
    return np.nan if n < 3 or np.isnan(x).any() else float(np.polyfit(np.arange(n), x, 1)[0])


def build_weekly_A() -> pd.DataFrame:
    """Weekly (W-FRI) per-symbol panel with the four trailing-only accumulation z-components, their
    equal-weight composite `A`, a 44-week SMA extension, and forward returns."""
    dlv = pd.read_parquet(DATA_DIR / "_delivery_raw.parquet")
    dlv = dlv[dlv["series"].isin(["EQ", "BE"])].copy()
    dlv["date"] = pd.to_datetime(dlv["date"])
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    rows = []
    for s in [x for x in dlv["symbol"].unique() if x in ohlcv]:
        d = dlv[dlv["symbol"] == s].set_index("date").sort_index()
        wk = pd.DataFrame({"dqty": d["deliv_qty"].resample("W-FRI").sum(),
                           "tqty": d["traded_qty"].resample("W-FRI").sum()})
        px = ohlcv[s]
        px.index = pd.to_datetime(px.index)
        wk["close"] = (px["c"] if "c" in px else px["Close"]).resample("W-FRI").last()
        wk = wk[wk["tqty"] > 0].dropna(subset=["close"])
        if len(wk) < 60:
            continue
        wk["symbol"] = s
        wk["dpct"] = 100 * wk["dqty"] / wk["tqty"]
        wk["ret"] = wk["close"].pct_change()
        rows.append(wk.reset_index())
    W = pd.concat(rows, ignore_index=True).rename(columns={"date": "wk", "index": "wk"})
    W = W.sort_values(["symbol", "wk"])
    g = W.groupby("symbol", sort=False)

    def zroll(s: pd.Series, w: int) -> pd.Series:
        m = s.groupby(W["symbol"]).transform(lambda x: x.rolling(w, min_periods=w // 2).mean())
        sd = s.groupby(W["symbol"]).transform(lambda x: x.rolling(w, min_periods=w // 2).std(ddof=0))
        return (s - m) / sd.replace(0, np.nan)

    W["A_level"] = zroll(g["dpct"].transform(lambda x: x.rolling(4, min_periods=2).mean()), 52)
    W["A_trend"] = zroll(g["dpct"].transform(lambda x: x.rolling(8, min_periods=4).apply(_slope, raw=True)), 52)
    W["A_surge"] = zroll(np.log(W["dqty"].clip(lower=1)), 26) - zroll(np.log(W["tqty"].clip(lower=1)), 26)
    obd = (np.sign(W["ret"].fillna(0)) * W["dqty"]).groupby(W["symbol"]).cumsum()
    W["A_div"] = (zroll(obd.groupby(W["symbol"]).transform(lambda x: x.rolling(8, min_periods=4).apply(_slope, raw=True)), 52)
                  - zroll(g["close"].transform(lambda x: x.rolling(8, min_periods=4).apply(_slope, raw=True)), 52))
    W["A"] = W[["A_level", "A_trend", "A_surge", "A_div"]].mean(axis=1)
    W["sma44"] = g["close"].transform(lambda x: x.rolling(44, min_periods=30).mean())
    W["ext"] = 100 * (W["close"] / W["sma44"] - 1)
    for k in (1, 2, 4, 8, 13, 26):
        W[f"f{k}"] = g["close"].transform(lambda x: x.shift(-k) / x - 1) * 100
    return W


def section_universe(W: pd.DataFrame) -> None:
    print(f"\n[1] UNIVERSE — {W['symbol'].nunique()} names, {len(W):,} stock-weeks, "
          f"{W['wk'].min().date()}..{W['wk'].max().date()}")
    for col in ("dpct", "A"):
        x = W[col]
        xl = W.groupby("symbol")[col].shift(1)
        msk = x.notna() & xl.notna()
        rho = np.corrcoef(xl[msk], x[msk])[0, 1]
        hl = -np.log(2) / np.log(rho) if 0 < rho < 1 else np.nan
        print(f"    persistence {col:5}: AR(1) rho={rho:+.3f}  half-life={hl:.1f} wk")
    for k in (1, 4, 13):
        ics = []
        for _, gg in W.dropna(subset=["A", f"f{k}"]).groupby("wk"):
            if len(gg) >= 30:
                ics.append(stats.spearmanr(gg["A"], gg[f"f{k}"]).correlation)
        ics = np.array([v for v in ics if not np.isnan(v)])
        t = ics.mean() / ics.std(ddof=1) * np.sqrt(len(ics))
        print(f"    IC fwd-{k:2}w: mean {ics.mean():+.4f}  IC-IR {ics.mean()/ics.std(ddof=1):+.3f}  t={t:+.2f}")


def merge_book(W: pd.DataFrame) -> pd.DataFrame:
    tr = pd.read_parquet(TRADES)
    tr = tr[pd.to_datetime(tr["entry_date"]) >= "2019-01-01"].copy()
    tr["wk"] = pd.to_datetime(tr["entry_date"]).dt.to_period("W-FRI").dt.end_time.dt.normalize()
    Aw = W[["symbol", "wk", "A"]].copy()
    Aw["wk"] = Aw["wk"].dt.normalize()
    tr = tr.merge(Aw, left_on=["ticker", "wk"], right_on=["symbol", "wk"], how="left")
    return tr.dropna(subset=["A", "R", "ext_vs_sma", "rank_crs", "mfe_pct"]).copy()


def section_book(m: pd.DataFrame) -> None:
    print(f"\n[2] BOOK COLLAPSE — {len(m)} Bhanushali trades")
    X = np.column_stack([np.ones(len(m)), m["ext_vs_sma"], m["rank_crs"], m["A"]])
    y = m["R"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X) * (resid @ resid) / (len(y) - X.shape[1])))
    print(f"    raw corr(A,R) {m['A'].corr(m['R']):+.4f}  corr(A,ext) {m['A'].corr(m['ext_vs_sma']):+.4f}")
    print(f"    OLS R~ext+CRS+A: A coef {beta[3]:+.4f}  t={beta[3]/se[3]:+.2f}  (adds nothing beyond ext & CRS)")


def section_mechanism(m: pd.DataFrame) -> None:
    print("\n[3] MECHANISM — matched high-A vs low-A within ext x CRS, and A-tercile behaviour")
    m = m.copy()
    m["extT"] = pd.qcut(m["ext_vs_sma"], 3, labels=["Lo", "Mid", "Hi"])
    m["crsT"] = pd.qcut(m["rank_crs"], 3, labels=["Lo", "Mid", "Hi"])
    gaps = []
    for _, cell in m.groupby(["extT", "crsT"]):
        if len(cell) < 30:
            continue
        med = cell["A"].median()
        gaps.append((cell[cell.A > med]["R"].mean() - cell[cell.A <= med]["R"].mean(), len(cell)))
    pooled = np.average([g for g, _ in gaps], weights=[n for _, n in gaps])
    print(f"    POOLED matched high-A minus low-A R gap = {pooled:+.3f} R (<=0 means edge does not survive)")
    m["Aq"] = pd.qcut(m["A"], 3, labels=["A-Lo", "A-Mid", "A-Hi"])
    ag = m.groupby("Aq").agg(meanR=("R", "mean"), held=("held_weeks", "median"),
                             mfe=("mfe_pct", "mean"), ext=("ext_vs_sma", "mean"),
                             stop=("reason", lambda x: 100 * x.str.startswith("stop").mean()))
    print(ag.round(2).to_string().replace("\n", "\n    "))


def section_prebreakout(W: pd.DataFrame) -> tuple:
    print("\n[4] FLIP-SIDE — accumulation-onset fwd returns vs ext-matched null; base vs extended")
    W = W.copy()
    W["onset"] = (W["A"] >= 1) & (W.groupby("symbol")["A"].shift(1) < 1)
    W["extband"] = pd.cut(W["ext"], [-1e9, -10, 0, 10, 1e9], labels=["deep", "base", "ext", "far"])
    ev = W[W["onset"]].dropna(subset=["ext"])
    rng = np.random.RandomState(0)
    pool = W[~W["onset"]].dropna(subset=["ext"])
    by = {k: v.index.values for k, v in pool.groupby(["wk", "extband"])}
    nidx = [rng.choice(by[(e.wk, e.extband)]) for e in ev.itertuples()
            if (e.wk, e.extband) in by and len(by[(e.wk, e.extband)])]
    nul = W.loc[nidx]
    hz = [1, 2, 4, 8, 13, 26]
    base = [ev.loc[ev.ext < 0, f"f{k}"].mean() for k in hz]
    extd = [ev.loc[ev.ext >= 0, f"f{k}"].mean() for k in hz]
    null = [nul[f"f{k}"].mean() for k in hz]
    for k, b, x, n in zip(hz, base, extd, null):
        acc = ev[f"f{k}"].mean()
        print(f"    +{k:2}w  onset {acc:+6.2f}%  null {n:+6.2f}%  edge {acc-n:+5.2f}pp | base {b:+6.2f}% ext {x:+6.2f}%")
    bt = stats.ttest_ind(ev.loc[ev.ext < 0, "f13"].dropna(), ev.loc[ev.ext >= 0, "f13"].dropna(), equal_var=False)
    print(f"    base-onset vs ext-onset @13w: Welch t={bt.statistic:+.2f} p={bt.pvalue:.3f}")
    return hz, base, extd, null


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chart", default=None, help="write the two-phase PNG here")
    args = ap.parse_args(argv)
    print("=" * 80)
    print("DELIVERY ACCUMULATION — measurement chain (finding 0139). MEASUREMENT ONLY.")
    print("Standing counts: screens 19 · sealed opens 1 · n_trials 2.")
    print("=" * 80)
    W = build_weekly_A()
    section_universe(W)
    m = merge_book(W)
    section_book(m)
    section_mechanism(m)
    hz, base, extd, null = section_prebreakout(W)
    if args.chart:
        _chart(m, hz, base, extd, null, Path(args.chart))
        print(f"\nwrote chart {args.chart}")
    return 0


def _chart(m, hz, base, extd, null, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mq = m.copy()
    mq["Aq"] = pd.qcut(mq["A"], 3, labels=["A-Lo", "A-Mid", "A-Hi"])
    mech = mq.groupby("Aq").agg(mfe=("mfe_pct", "mean"), ext=("ext_vs_sma", "mean"),
                                stop=("reason", lambda x: 100 * x.str.startswith("stop").mean()))
    plt.rcParams.update({"font.size": 10, "figure.facecolor": "#0e1220", "axes.facecolor": "#141a2b",
                         "text.color": "#e6e9f2", "axes.labelcolor": "#c7cee0", "xtick.color": "#8b93ab",
                         "ytick.color": "#8b93ab", "axes.edgecolor": "#39415a"})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2))
    fig.suptitle("Delivery accumulation & the Bhanushali book — two opposite phases", fontsize=13, fontweight="bold")
    xx = np.arange(3)
    a1.plot(xx, mech["mfe"], "-o", color="#3fdd8a", lw=2.2, label="Follow-through MFE %")
    a1.plot(xx, mech["ext"], "-o", color="#4f8cff", lw=2.2, label="Extension @ entry")
    a1.plot(xx, mech["stop"], "-o", color="#ff6363", lw=2.2, label="Stop-out rate %")
    a1.set_xticks(xx); a1.set_xticklabels(["A-Lo", "A-Mid", "A-Hi"]); a1.legend(frameon=False, fontsize=9)
    a1.set_title("On the momentum book: accumulation is the WRONG phase", fontsize=10); a1.grid(alpha=0.15)
    a2.plot(hz, base, "-o", color="#3fdd8a", lw=2.4, label="Accumulation in a BASE (pre-breakout)")
    a2.plot(hz, extd, "-o", color="#ffb454", lw=2.2, label="Accumulation when already extended")
    a2.plot(hz, null, "--", color="#8b93ab", lw=1.8, label="Ext-matched random null")
    a2.set_xlabel("weeks held"); a2.set_ylabel("mean forward return %"); a2.legend(frameon=False, fontsize=9, loc="upper left")
    a2.set_title("On the broad universe: the payoff is PRE-BREAKOUT", fontsize=10); a2.grid(alpha=0.15)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(out, dpi=130, facecolor=fig.get_facecolor())


if __name__ == "__main__":
    raise SystemExit(main())
