"""Pre-reg 0087 — trend-death exit on the 0084 six-step book: sell any held name whose daily 44-EMA
stalls for 2 weeks OR whose price falls >6.5% below it.

0084 entry/stop/targets are byte-identical (T+1..T+3 buy-stop, candle-low stop, half@+2R, rest@+3R).
The ONLY change: 0084's 3-close-below-SMA44 ma_breach rule is replaced by two daily-EMA44 trend-death
rules applied to ALL open positions —
  stall: EMA44_t / EMA44_{t-10} - 1 < 0.005   (44-EMA rose <0.5% over the trailing 10 sessions)
  deep : close_t < EMA44_t * (1 - 0.065)       (close >6.5% below the 44-EMA)
either → set pending exit → sell the whole remaining position at the next session's open (PIT-safe).

Motivated by the locked-capital problem (findings 0026/0029). Frozen in
diagnostics/research/preregistry/0087-bhanushali-sixstep-trend-death-exit.md.

Usage:
    python scripts/run_bhanushali_sixstep_stall.py            # run of record
    python scripts/run_bhanushali_sixstep_stall.py --ledger   # dump per-trade CSV
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_faithful import EQ0, START  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import ORDER_LIFE, RISK, STT_PCT, _cost_leg, _row, _slices, prep  # noqa: E402
from run_bhanushali_sixstep import backtest as backtest_0084  # noqa: E402

EMA_SPAN = 44          # daily EMA the trend-death detector reads (owner spec)
STALL_RISE_10D = 0.005  # 44-EMA rose < 0.5% over trailing 10 sessions -> stalled
STALL_LOOKBACK = 10     # ~2 weeks
DEEP_FRAC = 0.065       # close > 6.5% below the 44-EMA -> deep break


def add_ema44(P):
    for s in P.values():
        s["ema44"] = pd.Series(s["c"]).ewm(span=EMA_SPAN, adjust=False).mean().to_numpy()
    return P


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None):
    """0084 engine with the ma_breach rule replaced by the EMA44 stall/deep trend-death exit (all positions)."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    curve = []; T = []; skipped_cash = 0
    for d in dts:
        dd = d.date()
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            s = P[t]
            p["held"] += 1
            ex = rs = None
            if p["pending_exit"]:
                ex, rs = s["o"][i], p["pending_reason"]
            elif s["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "stop"
                p["gap_through"] = bool(s["o"][i] < p["stop"])
            else:
                if not p["half_done"] and s["h"][i] >= p["tp2"]:
                    half = p["sh0"] * 0.5
                    hp = half * p["tp2"]
                    cash += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    p["sh"] -= half; p["half_done"] = True
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
                T.append(dict(R=R, reason=rs + ("_half" if p["half_done"] and rs in ("stop", "stall", "deep") else ""),
                              held=p["held"], half=p["half_done"]))
                if "rec" in p:
                    p["rec"].update(exit_date=d, exit_px=round(float(ex), 2), reason=T[-1]["reason"],
                                    held=p["held"], R=round(float(R), 3),
                                    gap_through=p.get("gap_through", False),
                                    net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                    stt_paid=round(float(p["stt"] + p["stt_buy"]), 2))
                    ledger.append(p["rec"])
                del op[t]
                continue
            # close-of-day trend-death detector (replaces the SMA44 ma_breach counter)
            ema = s["ema44"][i]
            stalled = i >= STALL_LOOKBACK and np.isfinite(s["ema44"][i - STALL_LOOKBACK]) and \
                (ema / s["ema44"][i - STALL_LOOKBACK] - 1.0) < STALL_RISE_10D
            deep = np.isfinite(ema) and s["c"][i] < ema * (1 - DEEP_FRAC)
            if deep:
                p["pending_exit"] = True; p["pending_reason"] = "deep"
            elif stalled:
                p["pending_exit"] = True; p["pending_reason"] = "stall"
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
                                     half_done=False, pending_exit=False, pending_reason=None,
                                     cash_out=notion, proceeds=0.0, stt=0.0, stt_buy=sh * en * STT_PCT)
                        risk_pct = sh * (en - st) / eq * 100
                        assert 1.99 <= risk_pct <= 2.01, f"sizing bug: {risk_pct:.3f}%"
                        if ledger is not None:
                            op[t]["rec"] = dict(tkr=t, sig_date=o_["sig_d"], entry_date=d,
                                                entry=round(float(en), 2), stop0=round(float(st), 2),
                                                risk_pct=round(float(risk_pct), 3),
                                                half_date=None, half_px=None)
                        filled = True
                    else:
                        skipped_cash += 1
            if filled or o_["live"] <= 0:
                del orders[t]
        for t, s in P.items():
            if t in op or t in orders:
                continue
            i = didx[t].get(d)
            if i is None or not s["sig"][i]:
                continue
            if mem is not None and not ticker_in_index_on(t, dd, mem):
                continue
            if s["h"][i] <= s["l"][i] * 0.999:
                continue
            orders[t] = dict(trig=s["h"][i], stop=s["l"][i] * 0.999, adv=s["adv20"][i],
                             live=ORDER_LIFE, sig_d=d)
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm
        assert cash >= -1e-6
        curve.append((d, eq))
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
                avghold=hold.mean() if len(hold) else float("nan"),
                medhold=float(np.median(hold)) if len(hold) else float("nan"),
                p90hold=float(np.percentile(hold, 90)) if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0,
                reasons=reasons, skipped_cash=skipped_cash)


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0087: trend-death exit (EMA44 stall 2wk / deep 6.5%; all positions) on the 0084 book ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = add_ema44(prep(ohlcv))
    print(f"corrected universe: {len(P)} names | stall EMA44 <{STALL_RISE_10D*100:.1f}%/{STALL_LOOKBACK}d "
          f"| deep {DEEP_FRAC*100:.1f}% below EMA44 | 0084 entry+stop+targets\n")

    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {net['reasons']} | cash-skipped fills: {net['skipped_cash']}")

    ref84 = backtest_0084(P, mem)
    print(f"    capital: cash-skips {net['skipped_cash']} vs 0084 {ref84['skipped_cash']} "
          f"| hold med {net['medhold']:.0f}d vs {ref84['medhold']:.0f}d")

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
    print(f"\n  references (same cell): 0084 +0.477 | 0085 +0.587 | baseline_v1 0.667 | TRI buy-hold +12.6% CAGR")
    print(f"  dSharpe vs 0084: {net['sharpe'] - ref84['sharpe']:+.3f}")

    net_err = backtest(add_ema44(prep(ohlcv, drop_erratum=True)), mem)
    print(_row("erratum-dropped NET", net_err))

    if "--ledger" in args and ledger:
        out = ROOT / "research" / "exports" / "bhanushali_sixstep_stall_0087_trades.csv"
        pd.DataFrame(ledger).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(ledger)} trades)")
    print("\n(run of record for pre-reg 0087; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
