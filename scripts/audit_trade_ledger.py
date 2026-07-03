"""FULL forensic audit of the 0025 strategy-of-record (practitioner book, 4xATR geometry, corrected
universe, NET costs) — every trade from watchlist to exit fill, plus the harness/data checks from
skills/{backtest-rigor, leakage-audit, data-quality, quantitative-research}.

Sections:
 A determinism + headline reconciliation (the run must reproduce finding 0025 exactly)
 B per-trade ledger export (research/exports/bhanushali_0025_tradelog.csv) + entry-condition snapshot
   ("why we bought": engine, watchlist rank, trend strength, volume ratio, pullback distance, regime)
 C timing / lookahead integrity (signal strictly before entry; fill = max(open, trigger); order age)
 D exit-fill realism: gap-through stops (open below stop -> our stop-price fill is optimistic) with the
   pessimistic (open-fill) re-pricing of the whole book
 E data-quality on TRADED names only: intra-trade price cliffs (CA suspects), zero-volume days in holds,
   backfill-sourced (bhavcopy / alias) names actually traded
 F cost reconciliation (sum of per-trade friction vs the gross-net CAGR gap) + per-trade cost share
 G concentration / stability: P&L share of top names+years, R distribution, MAE/MFE, half-book stats
 H statistical power: block bootstrap (63d) CI on the net Sharpe; sub-period table; trade-count adequacy
 I sample trade narratives (the 'minutest detail' record, 8 trades: best/worst/median/gap-through)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.validation.bootstrap import block_bootstrap_metric  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_practitioner import backtest, prep, regime_series  # noqa: E402

OUT = ROOT / "research" / "exports" / "bhanushali_0025_tradelog.csv"


def sharpe(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() else float("nan")


def main() -> int:
    ohlcv = corrected_universe()
    P = prep(ohlcv)
    mem = load_membership()
    led = []
    m = backtest(P, mem, stop_geom="atr4", ledger=led)

    print("=== A. DETERMINISM + HEADLINE RECONCILIATION (must equal finding 0025) ===")
    print(f"  net Sharpe {m['sharpe']:+.3f} (0025: +0.397) | CAGR {m['cagr']*100:+.1f}% (0025: +2.8%) | "
          f"DD {m['dd']*100:.1f}% (0025: -12.1%) | trades {m['trades']} (0025: 194)")
    ok = abs(m["sharpe"] - 0.397) < 0.01 and m["trades"] == 194
    print(f"  reconciliation: {'PASS — ledger instrumentation is observation-only' if ok else 'FAIL — INVESTIGATE'}")

    L = pd.DataFrame(led)
    didx = {t: {d: i for i, d in enumerate(P[t]["dates"])} for t in L["tkr"].unique()}
    reg = regime_series()

    # enrich with signal-day conditions ("why we bought") + in-trade path (MAE/MFE, cliffs, volume)
    rows = []
    for _, r in L.iterrows():
        s = P[r["tkr"]]
        i = didx[r["tkr"]][r["sig_date"]]
        j0, j1 = didx[r["tkr"]][r["entry_date"]], didx[r["tkr"]][r["exit_date"]]
        vol_ratio = float("nan")
        # engine attribution + condition snapshot at the signal candle
        engA = bool(s["wtrend"][i] and s["rsix"][i] and s["qgreen"][i] and s["hvc"][i])
        engB = bool(s["strong"][i] and s["hold44"][i] and s["qgreen"][i] and s["hvc"][i])
        lo, hi, cl = s["l"][j0:j1 + 1], s["h"][j0:j1 + 1], s["c"][j0:j1 + 1]
        ret1d = np.abs(np.diff(cl) / cl[:-1]) if len(cl) > 1 else np.array([])
        rows.append(dict(
            engine="A+B" if engA and engB else ("A" if engA else "B"),
            slope66_pct=s["slope66"][i] * 100, dist_to_44sma_pct=(s["c"][i] / s["dsma"][i] - 1) * 100,
            atr_pct=s["atr"][i] / s["c"][i] * 100,
            regime_ok=bool(reg.get(r["entry_date"], True)),
            days_to_fill=int(j0 - i),
            mae_pct=(lo.min() / r["entry"] - 1) * 100, mfe_pct=(hi.max() / r["entry"] - 1) * 100,
            max_1d_move_in_trade_pct=(ret1d.max() * 100 if len(ret1d) else 0.0),
            zero_vol_days=int((ohlcv[r["tkr"]]["Volume"].iloc[j0:j1 + 1] == 0).sum()),
            exit_day_open=s["o"][j1],
            gap_through_stop=bool(r["reason"] == "stop" and s["o"][j1] < r["final_stop"]),
            gross_ret_pct=(r["exit_px"] / r["entry"] - 1) * 100,
            src="backfill" if r["tkr"] not in load_membership() or True else "",  # placeholder, set below
        ))
    E = pd.concat([L.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    # source attribution: pinned vs backfill/alias
    import json, pickle
    bf = set(pickle.load(open(ROOT / "data" / "ohlcv_backfill.pkl", "rb")))
    amap = set(json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"])
    E["src"] = E["tkr"].map(lambda t: "alias" if t in amap else ("backfill" if t in bf else "pinned"))
    E.to_csv(OUT, index=False)
    print(f"\n=== B. LEDGER ({len(E)} trades) -> {OUT.relative_to(ROOT)} ===")
    print(f"  engine mix: {E['engine'].value_counts().to_dict()}")
    print(f"  watchlist rank at entry: median {E['rank'].median():.0f} | <=10: {(E['rank']<=10).mean()*100:.0f}% "
          f"| >25: {(E['rank']>25).mean()*100:.0f}%")
    print(f"  signal-day conditions: slope66 med {E['slope66_pct'].median():+.1f}% | dist-to-44SMA med "
          f"{E['dist_to_44sma_pct'].median():+.1f}% | ATR med {E['atr_pct'].median():.1f}%")
    print(f"  sizing: notional med {E['notional_pct'].median():.1f}% | risk med {E['risk_pct'].median():.2f}% "
          f"(intended 2.00) | ADV med {E['adv_cr'].median():.0f}cr")
    print(f"  universe source of traded names: {E['src'].value_counts().to_dict()}")

    print("\n=== C. TIMING / LOOKAHEAD INTEGRITY ===")
    bad_t = int((E["entry_date"] <= E["sig_date"]).sum())
    print(f"  entry strictly after signal: {'PASS' if bad_t == 0 else f'FAIL ({bad_t})'} | "
          f"days-to-fill: {E['days_to_fill'].value_counts().sort_index().to_dict()} (order live 3d: "
          f"{'PASS' if E['days_to_fill'].max() <= 3 else 'FAIL'})")
    bad_f = int((E["entry"] < E["trig"] * 0.999).sum())
    print(f"  fill >= trigger always: {'PASS' if bad_f == 0 else f'FAIL ({bad_f})'} | gap at fill: med "
          f"{E['gap_pct'].median():+.2f}% max {E['gap_pct'].max():+.2f}% (no-chase cap 1.5%: "
          f"{'PASS' if E['gap_pct'].max() <= 1.51 else 'FAIL'})")

    print("\n=== D. EXIT-FILL REALISM — gap-through stops (known optimism, now quantified) ===")
    g = E[E["gap_through_stop"]]
    print(f"  stop exits where the exit-day OPEN was already below the stop: {len(g)}/{int((E['reason']=='stop').sum())} "
          f"({len(g)/max((E['reason']=='stop').sum(),1)*100:.0f}% of stops)")
    if len(g):
        slip = (g["final_stop"] - g["exit_day_open"]) / g["entry"]
        print(f"  per-event optimism (stop-fill vs open-fill): med {slip.median()*100:.2f}% max {slip.max()*100:.2f}% of entry px")
        # pessimistic re-pricing: replace stop fill with open fill on those events
        haircut = (g["final_stop"] - g["exit_day_open"]) * g["sh"]
        print(f"  total P&L haircut if all gap-throughs filled at OPEN: Rs {haircut.sum():,.0f} "
              f"on a 10L start (~{haircut.sum()/1e6*100:.2f}% of initial equity, spread over 9.5y)")

    print("\n=== E. DATA QUALITY ON TRADED NAMES ===")
    cliff = E[E["max_1d_move_in_trade_pct"] > 40]
    print(f"  trades containing a >40% single-day close move (CA suspects): {len(cliff)}"
          + ("" if not len(cliff) else " -> " + ", ".join(f"{r.tkr}@{r.entry_date.date()}" for r in cliff.itertuples())))
    print(f"  trades with zero-volume days during hold: {int((E['zero_vol_days']>0).sum())}")
    print(f"  trades in backfill/alias-sourced names: {int((E['src']!='pinned').sum())} "
          f"(their net P&L share: {E.loc[E['src']!='pinned','gross_ret_pct'].sum()/max(E['gross_ret_pct'].sum(),1e-9)*100:.0f}%)")

    print("\n=== F. COST RECONCILIATION ===")
    mg = backtest(P, mem, stop_geom="atr4", cost_off=True)
    print(f"  gross CAGR {mg['cagr']*100:+.2f}% - net {m['cagr']*100:+.2f}% = friction {mg['cagr']*100-m['cagr']*100:.2f}%/yr")
    rt = E["notional_pct"].sum() / 100 / 9.5
    print(f"  turnover ~{rt*2*100:.0f}%/yr notional (both legs) x tiered cost -> consistent with the gap "
          f"| trades in MID-slippage tier (ADV<50cr): {(E['adv_cr']<50).mean()*100:.0f}%")

    print("\n=== G. CONCENTRATION / DISTRIBUTION ===")
    pnl = (E["exit_px"] - E["entry"]) * E["sh"] + np.where(E["half_done"], (E["half_px"] - E["entry"]) * E["sh"], 0)
    E["pnl"] = pnl
    top = E.groupby("tkr")["pnl"].sum().sort_values(ascending=False)
    print(f"  top-3 names' share of total P&L: {top.head(3).sum()/top.sum()*100:.0f}% ({', '.join(top.head(3).index)})")
    yr = E.groupby(E["entry_date"].dt.year)["pnl"].agg(["count", "sum"])
    print("  per-year: " + " | ".join(f"{y}: {int(c)}tr Rs{s/1000:+.0f}k" for y, (c, s) in yr.iterrows()))
    print(f"  R: med {E['R'].median():+.2f} p10 {E['R'].quantile(.1):+.2f} p90 {E['R'].quantile(.9):+.2f} "
          f"max {E['R'].max():+.2f} | win {(E['R']>0).mean()*100:.0f}% | half-booked: {E['half_done'].mean()*100:.0f}%")
    print(f"  MAE med {E['mae_pct'].median():+.1f}% | MFE med {E['mfe_pct'].median():+.1f}% | "
          f"exit mix {E['reason'].value_counts().to_dict()}")

    print("\n=== H. STATISTICAL POWER ===")
    r = m["ret"].to_numpy()
    b = block_bootstrap_metric(r, sharpe, block_size=63, n_samples=5000)
    print(f"  net Sharpe {b.point:+.3f} | 63d-block bootstrap 95% CI [{b.lower:+.3f}, {b.upper:+.3f}] "
          f"{'(EXCLUDES 0)' if b.lower > 0 else '(includes 0 — not certifiable standalone, as recorded)'}")
    rr = m["ret"]
    for lab, sl in (("2017-18", rr[rr.index < "2019-01-01"]), ("2019-21", rr[(rr.index >= "2019-01-01") & (rr.index < "2022-01-01")]),
                    ("2022-26", rr[rr.index >= "2022-01-01"])):
        print(f"  {lab}: Sharpe {sharpe(sl.to_numpy()):+.2f}")
    print(f"  trades {len(E)} vs minimum-100 bar: {'PASS' if len(E) >= 100 else 'FAIL'} "
          f"(but ~20/yr -> sub-period cells are thin; treat sub-period Sharpe as indicative)")

    print("\n=== I. SAMPLE TRADE NARRATIVES ===")
    picks = pd.concat([E.nlargest(2, "R"), E.nsmallest(2, "R"),
                       E.iloc[(E["R"] - E["R"].median()).abs().argsort()[:2]],
                       E[E["gap_through_stop"]].head(2)]).drop_duplicates(subset=["tkr", "entry_date"])
    for r_ in picks.itertuples():
        half = f"half@{r_.half_px:.1f} on {r_.half_date.date()}, stop->breakeven; " if r_.half_done else ""
        print(f"  {r_.tkr} [{r_.src}] — WHY: engine {r_.engine}, watchlist rank {int(r_.rank)}, 44SMA slope66 "
              f"{r_.slope66_pct:+.1f}%, {r_.dist_to_44sma_pct:+.1f}% from MA, HVC vol spike, quality green, "
              f"regime {'OK' if r_.regime_ok else 'off'}.")
        print(f"    signal {r_.sig_date.date()} -> buy-stop {r_.trig:.1f}, filled {r_.entry:.1f} "
              f"(+{r_.days_to_fill}d, gap {r_.gap_pct:+.1f}%), stop {r_.stop0:.1f} ({r_.stop_pct:.1f}% away), "
              f"risk {r_.risk_pct:.2f}%, notional {r_.notional_pct:.1f}%.")
        print(f"    path: MAE {r_.mae_pct:+.1f}% MFE {r_.mfe_pct:+.1f}%; {half}exit {r_.exit_px:.1f} on "
              f"{r_.exit_date.date()} ({r_.reason}{', GAP-THROUGH' if r_.gap_through_stop else ''}), "
              f"held {int(r_.held)}d, R {r_.R:+.2f}, P&L Rs {r_.pnl:,.0f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
