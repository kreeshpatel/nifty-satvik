"""Comprehensive validation battery for pre-reg 0085 (MEASUREMENT — no n_trials cost, no retuning).

Statistical robustness: trade-sequence Monte-Carlo, skip-trade fragility, concentration/jackknife,
C1b plateau sweeps (one axis at a time, diagnostic shape only — NO selection), rolling 12m Sharpe,
underwater durations, monthly returns.
Real-world execution: MAE/MFE, profit factor/SQN/Kelly/streaks, gap-through severity, circuit proxy,
2x-slippage stress, ADV participation/capacity, alpha/beta/capture vs the N500 TRI, regime slicing.

Writes research/exports/diag_0085_battery.json for the finding + dossier.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_sixstep_runner as R85  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import STT_PCT, prep  # noqa: E402
from nq.engine.portfolio import leg_slippage  # noqa: E402
from config import BROKERAGE_PCT  # noqa: E402

RNG = np.random.default_rng(12345)
TRI_CSV = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"
OUT = ROOT / "research" / "exports" / "diag_0085_battery.json"


def sh(r):
    r = np.asarray(r, float)
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 5 and r.std() else float("nan")


def run_base(P, mem):
    led = []
    m = R85.backtest(P, mem, ledger=led)
    return m, pd.DataFrame(led)


def trade_mc(led, n=5000):
    """Shuffle the trade sequence; equity compounds 2% risk per trade -> DD / terminal distribution."""
    Rv = led["R"].to_numpy(float)
    mults = 1 + 0.02 * Rv
    term, dds = [], []
    for _ in range(n):
        seq = RNG.permutation(mults)
        eq = np.cumprod(seq)
        peak = np.maximum.accumulate(eq)
        dds.append(float((eq / peak - 1).min()))
        term.append(float(eq[-1]))
    return dict(term_p5=float(np.percentile(term, 5)), term_med=float(np.median(term)),
                term_p95=float(np.percentile(term, 95)),
                dd_p5=float(np.percentile(dds, 5)), dd_med=float(np.median(dds)),
                dd_worst1pct=float(np.percentile(dds, 1)),
                prob_loss=float(np.mean(np.array(term) < 1.0)))


def skip_frag(led, n=2000, p=0.10):
    Rv = led["R"].to_numpy(float)
    outs = []
    for _ in range(n):
        keep = RNG.random(len(Rv)) > p
        outs.append(float(np.prod(1 + 0.02 * Rv[keep])))
    full = float(np.prod(1 + 0.02 * Rv))
    return dict(full=full, p5=float(np.percentile(outs, 5)), med=float(np.median(outs)),
                p95=float(np.percentile(outs, 95)))


def concentration(led):
    pnl = led.sort_values("net_pnl", ascending=False)["net_pnl"].to_numpy(float)
    tot = pnl.sum()
    by_name = led.groupby("tkr")["net_pnl"].sum().sort_values(ascending=False)
    return dict(total=float(tot),
                top5_share=float(pnl[:5].sum() / tot), top10_share=float(pnl[:10].sum() / tot),
                top3_names_share=float(by_name.iloc[:3].sum() / tot),
                top_names=[(t, round(float(v))) for t, v in by_name.head(5).items()],
                n_names=int(led["tkr"].nunique()))


def plateau(ohlcv, mem, base_sharpe):
    """C1b sweep, one axis at a time. Diagnostic shape only — the 0085 params stay frozen."""
    rows = []
    for axis, vals, setter in (
        ("trail_pct", [0.03, 0.04, 0.05], lambda v: setattr(R85, "TRAIL_PCT", v)),
        ("ema_span", [15, 20, 25], lambda v: setattr(R85, "TRAIL_EMA_SPAN", v)),
        ("cap_days", [55, 63, 70], lambda v: setattr(R85, "RUNNER_CAP_DAYS", v)),
    ):
        for v in vals:
            R85.TRAIL_PCT, R85.TRAIL_EMA_SPAN, R85.RUNNER_CAP_DAYS = 0.04, 20, 63
            setter(v)
            P = R85.add_ema(prep(ohlcv))
            m = R85.backtest(P, mem)
            rows.append(dict(axis=axis, val=v, sharpe=round(float(m["sharpe"]), 3),
                             cagr=round(float(m["cagr"]) * 100, 1), dd=round(float(m["dd"]) * 100, 1)))
            print(f"  sweep {axis}={v}: Sh {m['sharpe']:+.3f}", flush=True)
    R85.TRAIL_PCT, R85.TRAIL_EMA_SPAN, R85.RUNNER_CAP_DAYS = 0.04, 20, 63
    spread = max(abs(r["sharpe"] - base_sharpe) for r in rows)
    return dict(rows=rows, max_dev_from_base=round(float(spread), 3),
                verdict="plateau" if spread < 0.15 else ("soft" if spread < 0.30 else "narrow_peak"))


def path_stats(P, led, curve):
    """MAE/MFE, qty/ADV participation, circuit proxy, gap-through severity."""
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    rows = []
    for _, r in led.iterrows():
        t = r["tkr"]
        if t not in P:
            continue
        s = P[t]
        i0 = didx[t].get(pd.Timestamp(r["entry_date"])); i1 = didx[t].get(pd.Timestamp(r["exit_date"]))
        if i0 is None or i1 is None or i1 <= i0:
            continue
        en = r["entry"]
        mfe = float(s["h"][i0:i1 + 1].max() / en - 1)
        mae = float(s["l"][i0:i1 + 1].min() / en - 1)
        eq_at = float(curve.asof(pd.Timestamp(r["entry_date"])))
        qty = 0.02 * eq_at / (en - r["stop0"])
        adv = float(s["adv20"][i0]) if np.isfinite(s["adv20"][i0]) else np.nan
        part = qty * en / adv if adv and np.isfinite(adv) and adv > 0 else np.nan
        circ = int((np.abs(np.diff(s["c"][i0:i1 + 1]) / s["c"][i0:i1]) >= 0.095).sum())
        rows.append(dict(tkr=t, R=r["R"], mfe=mfe, mae=mae, notional=qty * en,
                         adv_part=part, circuit_days=circ, reason=r["reason"],
                         gap=bool(r.get("gap_through", False)), net_pnl=r["net_pnl"]))
    df = pd.DataFrame(rows)
    win = df[df["R"] > 0]; loss = df[df["R"] <= 0]
    gross_prof = float(df.loc[df["net_pnl"] > 0, "net_pnl"].sum())
    gross_loss = float(-df.loc[df["net_pnl"] <= 0, "net_pnl"].sum())
    Rv = df["R"].to_numpy(float)
    streaks, cur = [], 0
    for x in Rv:
        cur = cur + 1 if x <= 0 else 0
        streaks.append(cur)
    W = float((Rv > 0).mean())
    payoff = float(win["R"].mean() / abs(loss["R"].mean())) if len(loss) else float("nan")
    return dict(
        mfe_med=float(df["mfe"].median()), mae_med=float(df["mae"].median()),
        edge_ratio=float(df["mfe"].median() / abs(df["mae"].median())),
        winners_mae_med=float(win["mae"].median()), losers_mfe_med=float(loss["mfe"].median()),
        profit_factor=float(gross_prof / gross_loss),
        payoff=payoff, win_rate=W,
        expectancy_R=float(Rv.mean()),
        sqn=float(np.sqrt(len(Rv)) * Rv.mean() / Rv.std()),
        kelly=float(W - (1 - W) / payoff) if np.isfinite(payoff) and payoff > 0 else float("nan"),
        max_loss_streak=int(max(streaks)),
        circuit_trades=int((df["circuit_days"] > 0).sum()),
        circuit_share=float((df["circuit_days"] > 0).mean()),
        gap_stops=int(df["gap"].sum()),
        adv_part_med=float(df["adv_part"].median()), adv_part_p95=float(df["adv_part"].quantile(.95)),
        notional_med=float(df["notional"].median()),
        capacity_x=float(0.05 / df["adv_part"].quantile(.95)),
    )


def gap_severity(P, led, curve):
    """Counterfactual: stop exits filled at OPEN when price gapped through the stop."""
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    delta = 0.0; n = 0
    for _, r in led.iterrows():
        if not r.get("gap_through", False) or "stop" not in str(r["reason"]):
            continue
        t = r["tkr"]; s = P[t]
        i1 = didx[t].get(pd.Timestamp(r["exit_date"]))
        if i1 is None:
            continue
        eq_at = float(curve.asof(pd.Timestamp(r["entry_date"])))
        qty = 0.02 * eq_at / (r["entry"] - r["stop0"])
        frac = 0.5 if pd.notna(r.get("half_px")) else 1.0
        delta += qty * frac * (float(s["o"][i1]) - r["exit_px"])
        n += 1
    return dict(n=n, total_worse=float(delta))


def cost_stress(ohlcv, mem):
    """2x slippage per leg (brokerage+STT unchanged) — B2 promotion-reference column."""
    orig = R85._cost_leg
    def stressed(adv, notional, cost_off=False):
        if cost_off:
            return 0.0
        return BROKERAGE_PCT + STT_PCT + 2.0 * leg_slippage(adv if np.isfinite(adv) else 0.0, notional)
    R85._cost_leg = stressed
    try:
        P = R85.add_ema(prep(ohlcv))
        m = R85.backtest(P, mem)
    finally:
        R85._cost_leg = orig
    return dict(sharpe=round(float(m["sharpe"]), 3), cagr=round(float(m["cagr"]) * 100, 1),
                dd=round(float(m["dd"]) * 100, 1))


def curve_diagnostics(curve):
    r = curve.pct_change().dropna()
    roll = r.rolling(252).apply(lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() else np.nan)
    dd = curve / curve.cummax() - 1
    under = (dd < -0.10)
    # longest stretch below -10% and time-to-new-high
    runs, cur = [], 0
    for v in under:
        cur = cur + 1 if v else 0
        runs.append(cur)
    peak_dates = curve.cummax()
    tth = (curve.index.to_series().diff().dt.days.fillna(0)).groupby((curve == peak_dates).cumsum()).cumsum()
    monthly = curve.resample("ME").last().pct_change().dropna()
    my = pd.DataFrame({"y": monthly.index.year, "m": monthly.index.month, "r": (monthly * 100).round(1)})
    return dict(roll12_med=float(np.nanmedian(roll)), roll12_min=float(np.nanmin(roll)),
                roll12_neg_share=float((roll.dropna() < 0).mean()),
                longest_below10pct_days=int(max(runs)),
                monthly=[[int(a), int(b), float(c)] for a, b, c in my.to_numpy()],
                pos_months=float((monthly > 0).mean()))


def benchmark_regime(curve, led):
    tri = pd.read_csv(TRI_CSV, parse_dates=["date"]).set_index("date")["tri_close"]
    r = curve.pct_change().dropna()
    tr = tri.pct_change().reindex(r.index).dropna()
    r2 = r.reindex(tr.index)
    beta = float(np.cov(r2, tr)[0, 1] / np.var(tr))
    alpha_ann = float((r2.mean() - beta * tr.mean()) * 252 * 100)
    corr = float(np.corrcoef(r2, tr)[0, 1])
    mo_s = curve.resample("ME").last().pct_change().dropna()
    mo_b = tri.resample("ME").last().pct_change().reindex(mo_s.index).dropna()
    mo_s = mo_s.reindex(mo_b.index)
    up = float(mo_s[mo_b > 0].mean() / mo_b[mo_b > 0].mean())
    down = float(mo_s[mo_b < 0].mean() / mo_b[mo_b < 0].mean())
    yrs = (tri.index[-1] - tri.index[0]).days / 365.25
    tri_cagr = float(((tri.iloc[-1] / tri.iloc[0]) ** (1 / yrs) - 1) * 100)
    tri_dd = float(((tri / tri.cummax()) - 1).min() * 100)
    # regime tag on the TRI: BULL above rising 200d SMA; BEAR below falling; else CHOP
    sma = tri.rolling(200).mean()
    rising = sma > sma.shift(21)
    tag = pd.Series("CHOP", index=tri.index)
    tag[(tri > sma) & rising] = "BULL"
    tag[(tri < sma) & ~rising] = "BEAR"
    tagr = tag.reindex(r.index).fillna("CHOP")
    reg = {}
    for k in ("BULL", "CHOP", "BEAR"):
        rr = r[tagr == k]
        reg[k] = dict(share=float((tagr == k).mean()), ann_ret=float(rr.mean() * 252 * 100),
                      sharpe=sh(rr.to_numpy()), days=int(len(rr)))
    led2 = led.copy()
    led2["regime"] = tag.reindex(pd.to_datetime(led2["entry_date"]), method="ffill").to_numpy()
    ent = {k: dict(n=int((led2["regime"] == k).sum()),
                   meanR=float(led2.loc[led2["regime"] == k, "R"].mean()))
           for k in ("BULL", "CHOP", "BEAR")}
    return dict(beta=beta, alpha_ann=alpha_ann, corr=corr, up_capture=up, down_capture=down,
                tri_cagr=tri_cagr, tri_dd=tri_dd, regimes=reg, entries_by_regime=ent)


def main() -> int:
    ohlcv = corrected_universe()
    mem = load_membership()
    P = R85.add_ema(prep(ohlcv))
    print("base run...", flush=True)
    m, led = run_base(P, mem)
    curve = m["curve"]
    out = {"headline": dict(sharpe=round(float(m["sharpe"]), 3), cagr=round(float(m["cagr"]) * 100, 1),
                            dd=round(float(m["dd"]) * 100, 1), trades=int(m["trades"]))}
    print("trade MC / fragility / concentration...", flush=True)
    out["trade_mc"] = trade_mc(led)
    out["skip_frag"] = skip_frag(led)
    out["concentration"] = concentration(led)
    print("path stats (MAE/MFE, capacity, circuits)...", flush=True)
    out["path"] = path_stats(P, led, curve)
    out["gap_severity"] = gap_severity(P, led, curve)
    print("curve diagnostics...", flush=True)
    out["curve"] = curve_diagnostics(curve)
    print("benchmark + regime...", flush=True)
    out["bench"] = benchmark_regime(curve, led)
    print("2x slippage stress...", flush=True)
    out["cost2x"] = cost_stress(ohlcv, mem)
    print("plateau sweeps (diagnostic only)...", flush=True)
    out["plateau"] = plateau(ohlcv, mem, out["headline"]["sharpe"])
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\n-> {OUT}")
    print(json.dumps({k: v for k, v in out.items() if k in ("headline", "trade_mc", "concentration",
                                                            "cost2x", "plateau")}, indent=1, default=str)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
