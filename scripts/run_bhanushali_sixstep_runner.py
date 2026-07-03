"""Pre-reg 0085 — six-step runner management: post-2R remainder rides a 20-EMA −4% ratchet trail.

Identical to pre-reg 0084 (scripts/run_bhanushali_sixstep.py: funnel, sizing, costs, corrected universe,
no-rotation) EXCEPT the runner rules: after the +2R half-book the remainder drops the +3R target and the
44-SMA-breach rule and instead trails stop = max(prev_stop, EMA20_daily * 0.96) (ratchet-only, active from
the session after the half-book), with a hard 63-trading-day cap from the ORIGINAL entry (exit at close,
reason `time`). Positions that never reach +2R keep the exact 0084 exits. Frozen in
diagnostics/research/preregistry/0085-bhanushali-sixstep-runner-trail.md.

Usage:
    python scripts/run_bhanushali_sixstep_runner.py            # run of record (gross+net, gates, verdict)
    python scripts/run_bhanushali_sixstep_runner.py --ledger   # dump per-trade CSV
    python scripts/run_bhanushali_sixstep_runner.py --audit    # first 10 RUNNER trades' arithmetic
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
from run_bhanushali_sixstep import (MA_BREACH_N, ORDER_LIFE, RISK, STT_PCT, _cost_leg, _row,  # noqa: E402
                                    _sh, _slices, prep)
from run_bhanushali_sixstep import backtest as backtest_0084  # noqa: E402

TRAIL_EMA_SPAN = 20      # daily EMA the runner trails
TRAIL_PCT = 0.04         # stop may sit at most 4% below the EMA
RUNNER_CAP_DAYS = 63     # trading days from ORIGINAL entry (3 months)


def add_ema(P):
    """Attach the runner-trail EMA to the frozen 0084 prep output (observational addition)."""
    for s in P.values():
        s["ema20"] = pd.Series(s["c"]).ewm(span=TRAIL_EMA_SPAN, adjust=False).mean().to_numpy()
    return P


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None):
    """The frozen 0085 engine — 0084 with runner-trail exits."""
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
                ex, rs = s["o"][i], "ma_breach"
            elif s["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "trail" if p["half_done"] else "stop"
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
                # RUNNER: no tp3, no MA-breach; 63d cap from original entry
                if p["half_done"] and ex is None and p["held"] >= RUNNER_CAP_DAYS:
                    ex, rs = s["c"][i], "time"
            if ex is not None:
                xp = p["sh"] * ex
                cash += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["proceeds"] += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["stt"] += xp * STT_PCT
                r_rest = (ex - p["en"]) / p["risk0"]
                R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
                T.append(dict(R=R, reason=rs + ("_half" if p["half_done"] and rs in ("stop", "ma_breach") else ""),
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
            # close-of-day bookkeeping
            if p["half_done"]:
                # ratchet the trail from the session AFTER the half-book (frozen: EMA of THIS close
                # sets the stop for FUTURE sessions; never lowers; MA-breach counter disabled)
                p["stop"] = max(p["stop"], s["ema20"][i] * (1 - TRAIL_PCT))
            else:
                p["mabreach"] = p["mabreach"] + 1 if s["c"][i] < s["dsma"][i] else 0
                if p["mabreach"] >= MA_BREACH_N:
                    p["pending_exit"] = True
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
                                     sh=sh, sh0=sh, held=0, adv=o_["adv"],
                                     half_done=False, mabreach=0, pending_exit=False,
                                     cash_out=notion, proceeds=0.0, stt=0.0,
                                     stt_buy=sh * en * STT_PCT)
                        risk_pct = sh * (en - st) / eq * 100
                        assert 1.99 <= risk_pct <= 2.01, f"sizing bug: {risk_pct:.3f}%"
                        if ledger is not None:
                            op[t]["rec"] = dict(tkr=t, sig_date=o_["sig_d"], entry_date=d,
                                                entry=round(float(en), 2), trig=round(float(o_["trig"]), 2),
                                                stop0=round(float(st), 2),
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
                maxR=R.max() if len(R) else float("nan"),
                avghold=hold.mean() if len(hold) else float("nan"),
                medhold=float(np.median(hold)) if len(hold) else float("nan"),
                p90hold=float(np.percentile(hold, 90)) if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0,
                reasons=reasons, skipped_cash=skipped_cash)


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0085: six-step runner trail (EMA20 -4%, 63d cap; frozen spec) ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = add_ema(prep(ohlcv))
    print(f"corrected universe: {len(P)} names | runner = post-2R remainder | trail EMA{TRAIL_EMA_SPAN} "
          f"-{TRAIL_PCT*100:.0f}% ratchet | cap {RUNNER_CAP_DAYS}d from entry\n")

    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {net['reasons']} | cash-skipped fills: {net['skipped_cash']}")
    led = pd.DataFrame(ledger)
    runners = led[led["half_px"].notna()] if len(led) else led
    if len(runners):
        print(f"    runners: {len(runners)}/{len(led)} trades | runner R: mean {runners['R'].mean():+.2f} "
              f"| max {runners['R'].max():+.2f} | >2.5R: {(runners['R'] > 2.5).sum()} "
              f"| hold med {runners['held'].median():.0f}d max {runners['held'].max():.0f}d")

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

    # informational reference: 0084 (target-capped runner) on the SAME P/mem
    ref = backtest_0084(P, mem)
    print(f"\n  reference (same universe): 0084 target-capped {_row('', ref).strip()}")
    print(f"  dSharpe vs 0084 (informational): {net['sharpe'] - ref['sharpe']:+.3f}")
    print("  other references: 0025 atr4 +0.397 | baseline_v1 0.667")

    # pre-declared sensitivity: drop the two pinned INDIAMART bad ticks
    net_err = backtest(add_ema(prep(ohlcv, drop_erratum=True)), mem)
    print(_row("erratum-dropped NET", net_err))

    if "--audit" in args and len(runners):
        print("\n  -- first 10 RUNNER trades --")
        cols = ["tkr", "entry_date", "entry", "stop0", "half_date", "half_px", "exit_date",
                "exit_px", "held", "reason", "R"]
        print(runners.head(10)[[c for c in cols if c in runners.columns]].to_string(index=False))
    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_sixstep_runner_0085_trades.csv"
        led.to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0085; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
