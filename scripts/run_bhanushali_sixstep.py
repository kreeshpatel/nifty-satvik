"""Pre-reg 0084 — the owner's "six-step" Bhanushali variant, reconstructed from the source videos.

Two-stage funnel: weekend bucket (weekly close > 44-WEEK SMA, SMA rising) -> daily 44-SMA pullback touch
-> green candle at/above the MA within 10 sessions -> buy-stop at the candle high (lives 3 sessions),
initial stop = candle low. Exits: half at +2R, rest at +3R, stop, or 3 consecutive daily closes below the
44-DMA (next-open fill). NO time cap, NO rotation, NO notional cap — cash is the only capacity constraint.
2% equity risk per fill, ADV-tiered real costs, PIT Nifty-500 membership, CORRECTED backfilled universe
(mandatory: no time cap -> long holds -> survivorship bias scales with hold, finding 0025).

Every parameter is frozen in diagnostics/research/preregistry/0084-bhanushali-sixstep.md. New formulation
vs the closed arc: 0022 tested the taught exits (1:2, 3-10d, killed); 0025 tested 4xATR geometry. This
tests the scaled-exit + MA-breach-trail geometry with the candle-low stop retained.

Usage:
    python scripts/run_bhanushali_sixstep.py                 # run of record (gross+net, gates, verdict)
    python scripts/run_bhanushali_sixstep.py --ledger        # also dump the per-trade CSV
    python scripts/run_bhanushali_sixstep.py --audit         # print the first 10 trades' arithmetic
    python scripts/run_bhanushali_sixstep.py --check TKR DATE  # print all gate components for one day
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import BROKERAGE_PCT, STT_PCT  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.portfolio import leg_slippage  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_faithful import EQ0, START, _rose  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

STT_BROK = BROKERAGE_PCT + STT_PCT
BAND = 0.02            # pullback touch band (0022 house definition)
TOUCH_WINDOW = 10      # green candle valid within 10 sessions of a touch (touch candle inclusive)
ORDER_LIFE = 3         # buy-stop lives 3 sessions (house T+1..T+3 convention)
RISK = 0.02            # fraction of current equity risked per fill
MA_BREACH_N = 3        # consecutive closes below the daily 44-SMA -> exit remainder next open
# pinned bad-tick erratum (finding 0025): pre-declared sensitivity line drops these two bars
ERRATUM_BARS = {("INDIAMART", "2019-10-27"), ("INDIAMART", "2020-11-14")}


def _cost_leg(adv: float, notional: float, cost_off: bool = False) -> float:
    """Per-leg cost fraction: brokerage + STT + ADV-tiered slippage (NaN adv -> SMALL_CAP tier)."""
    if cost_off:
        return 0.0
    return STT_BROK + leg_slippage(adv if np.isfinite(adv) else 0.0, notional)


def prep(ohlcv, drop_erratum: bool = False):
    """Per-ticker cached components. Signal = weekly bucket & daily trend & recent touch & green & c>=dsma."""
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < 300:
            continue
        if drop_erratum:
            bad = [pd.Timestamp(d) for t, d in ERRATUM_BARS if t == tkr]
            if bad:
                df = df[~df.index.isin(bad)]
        idx = pd.to_datetime(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        v = df["Volume"].to_numpy(float) if "Volume" in df.columns else np.full(len(c), np.nan)
        dsma = pd.Series(c).rolling(44).mean().to_numpy()
        dtrend = _rose(dsma, 10)                                        # daily 44-SMA rising (~2 weeks)
        w = df.resample("W-FRI").agg({"Close": "last"}).dropna()
        wsma = w["Close"].rolling(44).mean()                            # 44-WEEK SMA
        wbucket_w = (w["Close"] > wsma) & (wsma > wsma.shift(4))        # step 1: above + rising
        wbucket = wbucket_w.reindex(idx, method="ffill").fillna(False).to_numpy(bool)
        touch = (l <= dsma * (1 + BAND)) & (c >= dsma * (1 - BAND))     # pullback to the MA
        touch_recent = (pd.Series(np.nan_to_num(touch, nan=False).astype(float))
                        .rolling(TOUCH_WINDOW + 1, min_periods=1).max().to_numpy() > 0)
        green = c > o
        sig = wbucket & np.nan_to_num(dtrend, nan=False) & touch_recent & green & (c >= dsma)
        adv20 = pd.Series(c * v).rolling(20).mean().to_numpy()
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, dsma=dsma, adv20=adv20,
                      sig=np.nan_to_num(sig, nan=False).astype(bool),
                      wbucket=wbucket, dtrend=np.nan_to_num(dtrend, nan=False).astype(bool),
                      touch=np.nan_to_num(touch, nan=False).astype(bool),
                      touch_recent=touch_recent, green=green)
    return P


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None):
    """The frozen 0084 engine. No time cap, no rotation, no MAXPOS/notional cap; cash-limited only."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    curve = []; T = []; skipped_cash = 0
    for d in dts:
        dd = d.date()
        # ── manage opens: pending MA-exit at open -> stop -> tp2 half -> tp3 rest -> breach counter ──
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            s = P[t]
            p["held"] += 1
            ex = rs = None
            if p["pending_exit"]:                                       # MA breach fired yesterday
                ex, rs = s["o"][i], "ma_breach"
            elif s["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "stop"
                p["gap_through"] = bool(s["o"][i] < p["stop"])          # informational (optimistic fill)
            else:
                if not p["half_done"] and s["h"][i] >= p["tp2"]:
                    half = p["sh0"] * 0.5
                    hp = half * p["tp2"]
                    cash += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    p["sh"] -= half; p["half_done"] = True              # stop UNCHANGED (frozen: no breakeven)
                    p["proceeds"] += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    p["stt"] += hp * STT_PCT
                    if "rec" in p:
                        p["rec"].update(half_date=d, half_px=p["tp2"])
                if p["half_done"] and p["sh"] > 0 and s["h"][i] >= p["tp3"]:
                    ex, rs = p["tp3"], "target3"
            if ex is not None:
                xp = p["sh"] * ex
                cash += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["proceeds"] += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["stt"] += xp * STT_PCT
                r_rest = (ex - p["en"]) / p["risk0"]
                R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
                T.append(dict(R=R, reason=rs + ("_half" if p["half_done"] and rs != "target3" else ""),
                              held=p["held"], half=p["half_done"]))
                if "rec" in p:
                    # rupee cashflow fields are OBSERVATIONAL (tax analysis) — no decision path reads them
                    p["rec"].update(exit_date=d, exit_px=round(float(ex), 2), reason=T[-1]["reason"],
                                    held=p["held"], R=round(float(R), 3),
                                    gap_through=p.get("gap_through", False),
                                    net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                    stt_paid=round(float(p["stt"] + p["stt_buy"]), 2))
                    ledger.append(p["rec"])
                del op[t]
                continue
            # close-of-day MA-breach counter (from the fill session inclusive)
            p["mabreach"] = p["mabreach"] + 1 if s["c"][i] < s["dsma"][i] else 0
            if p["mabreach"] >= MA_BREACH_N:
                p["pending_exit"] = True
        # ── fill / expire pending buy-stop orders (deterministic order) ──
        for t in sorted(orders, key=lambda k: (orders[k]["sig_d"], k)):
            o_ = orders[t]; i = didx[t].get(d)
            if i is None:
                continue
            o_["live"] -= 1
            filled = False
            if t not in op and P[t]["h"][i] >= o_["trig"]:
                en = max(P[t]["o"][i], o_["trig"]); st = o_["stop"]
                if en > st:
                    sh = eq * RISK / (en - st)
                    notion = sh * en * (1 + _cost_leg(o_["adv"], sh * en, cost_off))
                    if notion <= cash and sh > 0:
                        cash -= notion
                        op[t] = dict(en=en, stop=st, risk0=en - st, tp2=en + 2 * (en - st),
                                     tp3=en + 3 * (en - st), sh=sh, sh0=sh, held=0, adv=o_["adv"],
                                     half_done=False, mabreach=0, pending_exit=False,
                                     cash_out=notion, proceeds=0.0, stt=0.0,
                                     stt_buy=sh * en * STT_PCT)
                        risk_pct = sh * (en - st) / eq * 100
                        assert 1.99 <= risk_pct <= 2.01, f"sizing bug: realized risk {risk_pct:.3f}%"
                        if ledger is not None:
                            op[t]["rec"] = dict(tkr=t, sig_date=o_["sig_d"], entry_date=d,
                                                entry=round(float(en), 2), trig=round(float(o_["trig"]), 2),
                                                stop0=round(float(st), 2),
                                                stop_pct=round((en / st - 1) * 100, 2),
                                                risk_pct=round(float(risk_pct), 3),
                                                notional_pct=round(sh * en / eq * 100, 2),
                                                half_date=None, half_px=None)
                        filled = True
                    else:
                        skipped_cash += 1                               # order stays live, retry while alive
            if filled or o_["live"] <= 0:
                del orders[t]
        # ── new signals -> pending orders (no rotation: held names get no new orders) ──
        for t, s in P.items():
            if t in op or t in orders:
                continue
            i = didx[t].get(d)
            if i is None or not s["sig"][i]:
                continue
            if mem is not None and not ticker_in_index_on(t, dd, mem):
                continue
            if s["h"][i] <= s["l"][i] * 0.999:                          # degenerate candle
                continue
            orders[t] = dict(trig=s["h"][i], stop=s["l"][i] * 0.999, adv=s["adv20"][i],
                             live=ORDER_LIFE, sig_d=d)
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm
        assert cash >= -1e-6, f"cash went negative: {cash}"
        curve.append((d, eq))
    # end of window: force-close remaining opens at their last close (tagged eos, included in stats)
    for t, p in op.items():
        i = len(P[t]["c"]) - 1
        ex = P[t]["c"][i]
        r_rest = (ex - p["en"]) / p["risk0"]
        R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
        T.append(dict(R=R, reason="eos", held=p["held"], half=p["half_done"]))
        if ledger is not None and "rec" in p:
            xp = p["sh"] * ex
            mark = p["proceeds"] + xp * (1 - _cost_leg(p["adv"], xp, cost_off))
            p["rec"].update(exit_date=P[t]["dates"][i], exit_px=round(float(ex), 2), reason="eos",
                            held=p["held"], R=round(float(R), 3), gap_through=False,
                            net_pnl=round(float(mark - p["cash_out"]), 2),
                            stt_paid=round(float(p["stt"] + p["stt_buy"] + xp * STT_PCT), 2))
            ledger.append(p["rec"])
    e = pd.Series(dict(curve)).sort_index()
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([x["R"] for x in T]); hold = np.array([x["held"] for x in T])
    reasons = pd.Series([x["reason"] for x in T]).value_counts().to_dict() if T else {}
    return dict(curve=e, ret=r, trades=len(R), tpy=len(R) / yrs,
                wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                maxR=R.max() if len(R) else float("nan"),
                avghold=hold.mean() if len(hold) else float("nan"),
                medhold=float(np.median(hold)) if len(hold) else float("nan"),
                p90hold=float(np.percentile(hold, 90)) if len(hold) else float("nan"),
                maxhold=int(hold.max()) if len(hold) else 0,
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0,
                reasons=reasons, skipped_cash=skipped_cash)


def _row(tag, m):
    return (f"  {tag:<24} tr {m['trades']:>4} ({m['tpy']:>4.0f}/yr) | win {m['wr']*100:>4.1f}% "
            f"| expR {m['expR']:+.2f} | hold med {m['medhold']:>3.0f}d p90 {m['p90hold']:>3.0f}d "
            f"| CAGR {m['cagr']*100:+6.1f}% | Sh {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}% | {m['mult']:.2f}x")


def _sh(x):
    x = np.asarray(x, float)
    return x.mean() / x.std() * np.sqrt(252) if len(x) > 5 and x.std() else float("nan")


def _slices(m):
    r = m["ret"]
    a = _sh(r[r.index < "2019-01-01"]); b = _sh(r[(r.index >= "2019-01-01") & (r.index < "2022-01-01")])
    c = _sh(r[r.index >= "2022-01-01"])
    return a, b, c


def _check(P, tkr, date):
    s = P.get(tkr)
    if s is None:
        print(f"{tkr}: not in universe (or <300 bars)"); return
    d = pd.Timestamp(date)
    j = s["dates"].searchsorted(d)
    if j >= len(s["dates"]) or s["dates"][j] != d:
        j = max(0, j - 1)
    d = s["dates"][j]
    print(f"{tkr} @ {d.date()}  close {s['c'][j]:.2f}  dsma44 {s['dsma'][j]:.2f}")
    w = pd.Series(s['c'], index=s['dates']).resample('W-FRI').last().dropna()
    wsma = w.rolling(44).mean()
    k = wsma.index.searchsorted(d)
    k = min(k, len(wsma) - 1)
    if wsma.index[k] > d and k > 0:
        k -= 1
    print(f"  weekly close {w.iloc[k]:.2f} | 44w SMA {wsma.iloc[k]:.2f} | rising(shift4) "
          f"{bool(wsma.iloc[k] > wsma.iloc[k-4]) if k >= 4 else 'warmup'}")
    for f in ("wbucket", "dtrend", "touch", "touch_recent", "green", "sig"):
        print(f"  {f:<13} {bool(s[f][j])}")
    if s["sig"][j]:
        print(f"  -> signal candle: buy-stop {s['h'][j]:.2f} | stop {s['l'][j]*0.999:.2f}")


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0084: Bhanushali six-step owner variant (frozen spec) ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = prep(ohlcv)
    print(f"corrected universe: {len(P)} names | PIT membership ON | window {START}..2026 "
          f"| risk {RISK*100:.0f}%/trade | order life {ORDER_LIFE}d | MA-breach N={MA_BREACH_N}\n")

    if "--check" in args:
        k = args.index("--check")
        _check(P, args[k + 1], args[k + 2]); return 0

    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {net['reasons']} | cash-skipped fills: {net['skipped_cash']}")
    led = pd.DataFrame(ledger)
    if len(led):
        rp = led["risk_pct"]
        print(f"    realized risk %/fill: mean {rp.mean():.3f} | med {rp.median():.3f} "
              f"| p5 {rp.quantile(.05):.3f} | p95 {rp.quantile(.95):.3f} | <1.9%: {(rp < 1.9).sum()}")
        gt = led["gap_through"].sum() if "gap_through" in led else 0
        print(f"    gap-through-stop fills (optimistic): {gt}")
        yr = led.groupby(pd.to_datetime(led["entry_date"]).dt.year)["R"].agg(["count", "mean"])
        print("    per-year entries / meanR: " +
              " | ".join(f"{y} {int(r['count'])}/{r['mean']:+.2f}" for y, r in yr.iterrows()))

    # ── certification stats on the ONE net curve ──
    arr = net["ret"].to_numpy(float)
    n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}] "
          f"| DSR @ n_trials={n_tr}: {dsr:.3f}")
    gates = {"DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
             "CI_low>0": bool(ci.lower > 0),
             "all_slices>0": bool(a > 0 and b > 0 and c > 0)}
    print("  gates:", {k: ("PASS" if v else "FAIL") for k, v in gates.items()})
    if all(gates.values()):
        verdict = "PROMOTE -> forward-wall watched sleeve"
    elif ci.lower > 0 and net["sharpe"] > 0:
        verdict = f"UNDERPOWERED (real-looking, not certified at n_trials={n_tr})"
    elif net["sharpe"] > 0:
        verdict = "UNDERPOWERED/WEAK (positive but CI straddles 0)"
    else:
        verdict = "KILL"
    print(f"  VERDICT: {verdict}")

    # ── references (informational, not gates) ──
    print("\n  reference: 0025 atr4 corrected NET Sharpe +0.397 | baseline_v1 63d momentum 0.667")
    surv = backtest(prep(load_ohlcv_cache(OHLCV_CACHE)), mem)       # survivor-only pinned cache
    print(_row("survivor-only NET (ref)", surv))

    # pre-declared sensitivity: drop the two pinned INDIAMART bad-tick bars (report, no tune)
    net_err = backtest(prep(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))

    if "--audit" in args and len(led):
        print("\n  -- first 10 trades (arithmetic audit) --")
        cols = ["tkr", "sig_date", "entry_date", "trig", "entry", "stop0", "risk_pct",
                "half_date", "half_px", "exit_date", "exit_px", "reason", "held", "R"]
        print(led.head(10)[[c for c in cols if c in led.columns]].to_string(index=False))
    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_sixstep_0084_trades.csv"
        led.to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0084; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
