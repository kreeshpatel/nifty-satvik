"""Pre-reg 0089 — fully-weekly six-step: in-range open entry + weekly-close/Monday exits.

Weekly 44-EMA trend + a green weekly bounce off it (low within 7%) = the signal week. Entry: the FOLLOWING
week, buy at the first day whose OPEN prints inside the signal week's [low, high] range (a cheaper in-range
fill, not 0088's breakout). Stop = signal-week low. 0085 exit LEVELS (half@+2R, 20-EMA -4% ratchet trail,
13-week cap) but every exit is DECIDED at the weekly close and EXECUTED at the next Monday's open — a true
once-a-week system. Equity is marked daily so the Sharpe is comparable to the rest of the family.

Frozen in diagnostics/research/preregistry/0089-bhanushali-weekly-full.md.

Usage:
    python scripts/run_bhanushali_weekly_full.py            # run of record
    python scripts/run_bhanushali_weekly_full.py --ledger   # dump per-trade CSV
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
from run_bhanushali_sixstep import RISK, STT_PCT, _cost_leg, _row, _slices, prep  # noqa: E402
from run_bhanushali_sixstep_runner import TRAIL_PCT, add_ema  # noqa: E402

TOUCH_BAND = 0.07        # weekly low within 7% of the weekly 44-EMA = "rebounding on it"
TRAIL_EMA_SPAN = 20      # daily 20-EMA level for the runner trail (0085), sampled at Friday
CAP_WEEKS = 13           # ~3-month time cap, all positions


def prep_weekly(ohlcv, drop_erratum: bool = False):
    """0085 daily arrays (for the 20-EMA trail + daily MTM) + weekly signal/entry structure per ticker."""
    P = add_ema(prep(ohlcv, drop_erratum=drop_erratum))
    for t, s in P.items():
        idx = pd.DatetimeIndex(s["dates"])
        iso = idx.isocalendar()
        keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        # group day-indices by ISO week, preserving order
        weeks = []  # list of [day indices]
        cur, prev = [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        o, h, l, c = s["o"], s["h"], s["l"], s["c"]
        wopen = np.array([o[d[0]] for d in weeks])
        whigh = np.array([h[d].max() for d in weeks])
        wlow = np.array([l[d].min() for d in weeks])
        wclose = np.array([c[d[-1]] for d in weeks])
        wema = pd.Series(wclose).ewm(span=44, adjust=False).mean().to_numpy()
        rising = np.full(len(wema), False)
        rising[4:] = wema[4:] > wema[:-4]
        trend = (wclose > wema) & rising
        green = wclose > wopen
        touch = wlow <= wema * (1 + TOUCH_BAND)
        wsig = green & touch & (wclose > wema) & trend
        # week-end day index per ticker (last trading day of each ISO week)
        s["weekend"] = {d[-1] for d in weeks}
        # entry windows: for each signal week k, the NEXT week's day indices + the signal week's [low,high]
        s["entry_win"] = {}   # first-day-index-of-entry-week -> (day_index_list, lo, hi)
        for k in np.flatnonzero(np.nan_to_num(wsig, nan=False)):
            if k + 1 >= len(weeks):
                continue
            edays = weeks[k + 1]
            s["entry_win"][edays[0]] = (edays, float(wlow[k]), float(whigh[k]))
    return P


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None,
             start: str | None = None, return_state: bool = False):
    """start (default START) filters the daily loop; return_state=True skips the end-of-window
    force-close and returns the LIVE open positions + active entry windows (for the paper runner).
    Both default to preserve byte-identical research behavior (0089/0091 findings)."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(start or START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}          # ticker -> {days:set, lo, hi}
    curve = []; T = []; skipped_cash = 0; activations = 0
    for d in dts:
        dd = d.date()
        # ── manage opens: execute pending (Monday) first, else evaluate at the weekly close ──
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            s = P[t]
            if p["pending"] is not None:                    # Monday execution of last Friday's decision
                act, rs = p["pending"]
                px = s["o"][i]
                if act == "half":
                    half = p["sh0"] * 0.5; hp = half * px
                    cash += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    p["sh"] -= half; p["half_done"] = True
                    p["proceeds"] += hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    p["stt"] += hp * STT_PCT; p["pending"] = None
                    if "rec" in p:
                        p["rec"].update(half_date=d, half_px=round(float(px), 2))
                else:                                        # full exit
                    xp = p["sh"] * px
                    cash += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                    p["proceeds"] += xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                    p["stt"] += xp * STT_PCT
                    r_rest = (px - p["en"]) / p["risk0"]
                    R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
                    T.append(dict(R=R, reason=rs, held=p["weeks"], half=p["half_done"]))
                    if "rec" in p:
                        p["rec"].update(exit_date=d, exit_px=round(float(px), 2), reason=rs,
                                        held_weeks=p["weeks"], R=round(float(R), 3),
                                        net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                        stt_paid=round(float(p["stt"] + p["stt_buy"]), 2))
                        ledger.append(p["rec"])
                    del op[t]
                    continue
            if i in s["weekend"]:                            # decide at the weekly close
                p["weeks"] += 1
                wc = s["c"][i]
                if wc <= p["stop"]:
                    p["pending"] = ("full", "stop" + ("_half" if p["half_done"] else ""))
                elif not p["half_done"] and wc >= p["tp2"]:
                    p["pending"] = ("half", "half")
                elif p["half_done"]:
                    p["trail"] = max(p["trail"], s["ema20"][i] * (1 - TRAIL_PCT))
                    if wc < p["trail"]:
                        p["pending"] = ("full", "trail")
                if p["pending"] is None and p["weeks"] >= CAP_WEEKS:
                    p["pending"] = ("full", "time")
        # ── entry: activate a one-week window on the signal week's next Monday; buy first in-range open ──
        for t, s in P.items():
            i = didx[t].get(d)
            if i is None:
                continue
            if t not in op and t not in orders and i in s["entry_win"]:
                if mem is None or ticker_in_index_on(t, dd, mem):
                    days, lo, hi = s["entry_win"][i]
                    orders[t] = {"days": set(days), "lo": lo, "hi": hi}; activations += 1
            o_ = orders.get(t)
            if o_ is not None and i in o_["days"] and t not in op:
                opn = s["o"][i]
                if o_["lo"] < opn < o_["hi"]:                # open inside last week's range
                    en = opn; st = o_["lo"]
                    if en > st:
                        sh = eq * RISK / (en - st)
                        notion = sh * en * (1 + _cost_leg(s["adv20"][i], sh * en, cost_off))
                        if notion <= cash and sh > 0:
                            cash -= notion
                            op[t] = dict(en=en, stop=st, risk0=en - st, tp2=en + 2 * (en - st),
                                         sh=sh, sh0=sh, weeks=0, adv=s["adv20"][i], half_done=False,
                                         trail=st, pending=None, cash_out=notion, proceeds=0.0,
                                         stt=0.0, stt_buy=sh * en * STT_PCT)
                            rp = sh * (en - st) / eq * 100
                            assert 1.99 <= rp <= 2.01, f"sizing {rp:.3f}"
                            if ledger is not None:
                                op[t]["rec"] = dict(tkr=t, entry_date=d, entry=round(float(en), 2),
                                                    stop0=round(float(st), 2), risk_pct=round(float(rp), 3),
                                                    entry_to_stop_pct=round((en / st - 1) * 100, 2),
                                                    half_date=None, half_px=None)
                            del orders[t]
                        else:
                            skipped_cash += 1
                if i == max(o_["days"]) and t in orders:      # window expired unfilled
                    del orders[t]
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm
        assert cash >= -1e-6
        curve.append((d, eq))
    # Backtest convention: force-close open positions at the window end so metrics realize them.
    # LIVE mode (return_state) skips this — those positions are still open, not closed.
    if not return_state:
        for t, p in op.items():
            i = len(P[t]["c"]) - 1; ex = P[t]["c"][i]
            r_rest = (ex - p["en"]) / p["risk0"]
            R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
            T.append(dict(R=R, reason="eos", held=p["weeks"], half=p["half_done"]))
            if ledger is not None and "rec" in p:
                xp = p["sh"] * ex; mark = p["proceeds"] + xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["rec"].update(exit_date=P[t]["dates"][i], exit_px=round(float(ex), 2), reason="eos",
                                held_weeks=p["weeks"], R=round(float(R), 3),
                                net_pnl=round(float(mark - p["cash_out"]), 2),
                                stt_paid=round(float(p["stt"] + p["stt_buy"] + xp * STT_PCT), 2))
                ledger.append(p["rec"])
    e = pd.Series(dict(curve)).sort_index()
    r = e.pct_change().dropna()
    # empty window (e.g. a live inception past the last data bar) -> degenerate metrics, no crash.
    # Never hit by a 2017-start research run, so byte-identical there.
    empty = len(e) < 2
    yrs = (e.index[-1] - e.index[0]).days / 365.25 if not empty else 1.0
    R = np.array([x["R"] for x in T])
    reasons = pd.Series([x["reason"] for x in T]).value_counts().to_dict() if T else {}
    out = dict(curve=e, ret=r, trades=len(R), tpy=len(R) / yrs, activations=activations,
                wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                medhold_w=float(np.median([x["held"] for x in T])) if T else float("nan"),
                medhold=float(np.median([x["held"] for x in T]) * 5) if T else float("nan"),
                p90hold=float(np.percentile([x["held"] for x in T], 90) * 5) if T else float("nan"),
                cagr=((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) if not empty else 0.0,
                sharpe=r.mean() / r.std() * np.sqrt(252) if (not empty and r.std()) else float("nan"),
                dd=(e / e.cummax() - 1).min() if not empty else 0.0,
                mult=(e.iloc[-1] / EQ0) if not empty else 1.0,
                reasons=reasons, skipped_cash=skipped_cash)
    if return_state:
        out["open_positions"] = op        # ticker -> live position dict (en/stop/tp2/trail/weeks/half_done/sh...)
        out["active_orders"] = orders     # ticker -> {days, lo, hi} entry windows still open this week
        out["cash"] = cash
        out["equity"] = float(eq)
        out["didx"] = didx
    return out


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0089: fully-weekly six-step (in-range open entry, weekly-close/Monday exits) ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = prep_weekly(ohlcv)
    print(f"corrected universe: {len(P)} names | weekly 44-EMA, {TOUCH_BAND*100:.0f}% touch | "
          f"in-range open entry | exits decided Fri close, filled Mon | {CAP_WEEKS}w cap\n")
    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    activations {net['activations']} -> {net['trades']} fills "
          f"({net['trades']/max(net['activations'],1)*100:.0f}%) | med hold {net['medhold_w']:.0f}w "
          f"| exits: {net['reasons']}")
    led = pd.DataFrame(ledger)
    if len(led) and "entry_to_stop_pct" in led:
        print(f"    entry->stop width med {led['entry_to_stop_pct'].median():.1f}% "
              f"(0088 breakout was 12.8%, 0085 daily ~7%)")
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"])
        print("    per-year: " + " | ".join(f"{y} {int(x['count'])}/{x['sum']/1e5:+.1f}L" for y, x in yr.iterrows()))
    arr = net["ret"].to_numpy(float)
    n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}] "
          f"| DSR @ n_trials={n_tr}: {dsr:.3f}")
    gates = {"DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
             "CI_low>0": bool(ci.lower > 0), "all_slices>0": bool(a > 0 and b > 0 and c > 0)}
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
    print(f"\n  references (same cell): 0085 +0.587/+11.5% | 0088 weekly-breakout +0.215/+2.3% | "
          f"baseline_v1 0.667 | TRI +12.6%")
    print(f"  dSharpe vs 0085: {net['sharpe'] - 0.587:+.3f} | dCAGR vs 0085: {net['cagr']*100 - 11.5:+.1f}pp")
    net_err = backtest(prep_weekly(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))
    if "--ledger" in args and ledger:
        out = ROOT / "research" / "exports" / "bhanushali_weekly_full_0089_trades.csv"
        pd.DataFrame(ledger).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(ledger)} trades)")
    print("\n(run of record for pre-reg 0089; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
