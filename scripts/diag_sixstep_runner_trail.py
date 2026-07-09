"""MEASUREMENT diagnostic (no n_trials cost, no promote/kill) — owner question on the 0084 book:
"what if runners are held ~3 months with a stop at most 4% below the daily 20-EMA?"

Variant vs the frozen 0084 engine, applied ONLY to runners (= trades that banked the half at +2R):
the remainder drops the +3R target and the 3-close MA-breach rule and instead trails
stop = max(stop, EMA20*0.96) (ratchet, never down), until hit or a 63-trading-day total hold cap.
Non-runners keep the exact 0084 exits (candle-low stop, +2R half, MA-breach). Entry funnel, sizing,
costs, universe identical to 0084. Same-bar precedence: stop -> tp2 (as 0084).

Learning-only: any certification of a picked variant must be a NEW pre-reg counting this search.
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
from run_bhanushali_sixstep import (EQ0, START, MA_BREACH_N, ORDER_LIFE, RISK,  # noqa: E402
                                    _cost_leg, _row, _slices, backtest as backtest_0084,
                                    corrected_universe, prep)

RUNNER_CAP = 63          # total trading-day hold cap for runners (~3 months)
TRAIL_EMA = 20           # daily EMA the runner stop trails
TRAIL_PCT = 0.04         # stop at most 4% below the EMA


def add_ema(P):
    for s in P.values():
        s["ema20"] = pd.Series(s["c"]).ewm(span=TRAIL_EMA, adjust=False).mean().to_numpy()
    return P


def backtest_runner_trail(P, mem, *, cost_off: bool = False, ledger: list | None = None):
    """0084 engine with the runner-trail exit swap. Kept structurally parallel to the frozen
    backtest (same entry/order/sizing/cost code) so the ONLY delta is the runner exit path."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    curve = []; T = []
    for d in dts:
        dd = d.date()
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            s = P[t]
            p["held"] += 1
            ex = rs = None
            if p["half_done"]:
                # ── RUNNER path: EMA trail + 63d cap; no tp3, no MA-breach ──
                p["stop"] = max(p["stop"], s["ema20"][i] * (1 - TRAIL_PCT))
                if s["l"][i] <= p["stop"]:
                    ex, rs = p["stop"], "trail"
                elif p["held"] >= RUNNER_CAP:
                    ex, rs = s["c"][i], "time_cap"
            else:
                # ── non-runner: exact 0084 exits ──
                if p["pending_exit"]:
                    ex, rs = s["o"][i], "ma_breach"
                elif s["l"][i] <= p["stop"]:
                    ex, rs = p["stop"], "stop"
                else:
                    if s["h"][i] >= p["tp2"]:
                        half = p["sh0"] * 0.5
                        hp = half * p["tp2"]
                        cash += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                        p["sh"] -= half; p["half_done"] = True
                    if ex is None and not p["half_done"]:
                        p["mabreach"] = p["mabreach"] + 1 if s["c"][i] < s["dsma"][i] else 0
                        if p["mabreach"] >= MA_BREACH_N:
                            p["pending_exit"] = True
            if ex is not None:
                xp = p["sh"] * ex
                cash += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                r_rest = (ex - p["en"]) / p["risk0"]
                R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
                T.append(dict(R=R, reason=rs, held=p["held"], half=p["half_done"]))
                if ledger is not None:
                    ledger.append(dict(tkr=t, exit_date=d, reason=rs, held=p["held"],
                                       R=round(float(R), 3), half=p["half_done"]))
                del op[t]
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
                                     half_done=False, mabreach=0, pending_exit=False)
                        filled = True
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
        eq = cash + mtm; curve.append((d, eq))
    for t, p in op.items():
        i = len(P[t]["c"]) - 1
        r_rest = (P[t]["c"][i] - p["en"]) / p["risk0"]
        R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
        T.append(dict(R=R, reason="eos", held=p["held"], half=p["half_done"]))
    e = pd.Series(dict(curve)).sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([x["R"] for x in T]); hold = np.array([x["held"] for x in T])
    reasons = pd.Series([x["reason"] for x in T]).value_counts().to_dict() if T else {}
    return dict(curve=e, ret=r, trades=len(R), tpy=len(R) / yrs,
                wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                maxR=R.max() if len(R) else float("nan"),
                medhold=float(np.median(hold)) if len(hold) else float("nan"),
                p90hold=float(np.percentile(hold, 90)) if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0, reasons=reasons)


def main() -> int:
    print("=== MEASUREMENT: 0084 vs runner-trail (EMA20-4%, 63d cap) — learning only, not a trial ===")
    P = add_ema(prep(corrected_universe()))
    mem = load_membership()
    base = backtest_0084(P, mem)
    var = backtest_runner_trail(P, mem)
    print(_row("0084 base NET", base))
    a, b, c = _slices(base)
    print(f"    slices: 2017-18 {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {base['reasons']}")
    print(_row("runner-trail NET", var))
    a, b, c = _slices(var)
    print(f"    slices: 2017-18 {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    exits: {var['reasons']} | maxR {var['maxR']:.1f}")
    print(f"\n    dSharpe {var['sharpe']-base['sharpe']:+.3f} | dCAGR {(var['cagr']-base['cagr'])*100:+.1f}pp "
          f"| dDD {(var['dd']-base['dd'])*100:+.1f}pp")
    print("(measurement only — certifying any picked variant requires a NEW pre-reg counting this search)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
