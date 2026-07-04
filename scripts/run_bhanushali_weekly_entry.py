"""Pre-reg 0088 — weekly-confirmation entry on the 0085 book.

Replace the DAILY pullback+green signal with a WEEKLY setup: a completed green weekly candle rebounding
off the weekly 44-EMA within the weekly bucket -> buy-stop at that week's HIGH, valid Monday+Tuesday of
the next week only, initial stop = that week's LOW. 0085 exits (half@2R, EMA20 -4% ratchet trail, 63d
cap, non-runner candle-low stop + daily-44SMA breach), sizing (2% risk), universe, and tiered costs are
byte-identical. Owner CAGR-hunt, reframed leak-free (a forward look on prices was refused as lookahead).

Frozen in diagnostics/research/preregistry/0088-bhanushali-weekly-entry.md.

Usage:
    python scripts/run_bhanushali_weekly_entry.py            # run of record
    python scripts/run_bhanushali_weekly_entry.py --ledger   # dump per-trade CSV
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
from run_bhanushali_faithful import EQ0, START, _rose  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import RISK, STT_PCT, _cost_leg, _row, _slices, prep  # noqa: E402
from run_bhanushali_sixstep_runner import (MA_BREACH_N, RUNNER_CAP_DAYS, TRAIL_EMA_SPAN,  # noqa: E402
                                           TRAIL_PCT, add_ema)

WEEKLY_TOUCH_BAND = 0.04   # weekly low within 4% of the weekly 44-EMA = "rebounding on it"
ENTRY_WINDOW = 2           # order valid Monday + Tuesday only


def prep_weekly(ohlcv, drop_erratum: bool = False):
    """0085 prep (daily arrays for exits) + a weekly-signal order map per ticker.

    s['wk_order'][i] = (trig, stop) means: on daily index i (the first session after a signal Friday),
    open a buy-stop at the prior week's high with a stop at the prior week's low.
    """
    P = add_ema(prep(ohlcv, drop_erratum=drop_erratum))
    for t, s in P.items():
        idx = pd.DatetimeIndex(s["dates"])
        df = pd.DataFrame({"Open": s["o"], "High": s["h"], "Low": s["l"], "Close": s["c"]}, index=idx)
        w = df.resample("W-FRI").agg(wopen=("Open", "first"), whigh=("High", "max"),
                                     wlow=("Low", "min"), wclose=("Close", "last")).dropna()
        if len(w) < 46:
            s["wk_order"] = {}
            continue
        wema = w["wclose"].ewm(span=44, adjust=False).mean()
        wsma = w["wclose"].rolling(44).mean()
        bucket = (w["wclose"] > wsma) & (wsma > wsma.shift(4))
        green = w["wclose"] > w["wopen"]
        touch = (w["wlow"] <= wema * (1 + WEEKLY_TOUCH_BAND)) & (w["wclose"] > wema)
        wsig = (green & touch & bucket).fillna(False).to_numpy()
        # map each signal week (ending Friday F) -> first daily session strictly after F
        pos = idx.searchsorted(w.index.to_numpy(), side="right")   # first daily bar index > each Friday
        wk_order = {}
        for k in np.flatnonzero(wsig):
            i = int(pos[k])
            if i < len(idx):
                wk_order[i] = (float(w["whigh"].iloc[k]), float(w["wlow"].iloc[k]) * 0.999)
        s["wk_order"] = wk_order
    return P


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None):
    """0085 engine with the WEEKLY entry (order creation reads s['wk_order']); exits unchanged."""
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    curve = []; T = []; skipped_cash = 0; activations = 0
    for d in dts:
        dd = d.date()
        # ── manage opens: EXACT 0085 exit logic ──
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
                                    net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                    stt_paid=round(float(p["stt"] + p["stt_buy"]), 2))
                    ledger.append(p["rec"])
                del op[t]
                continue
            if p["half_done"]:
                p["stop"] = max(p["stop"], s["ema20"][i] * (1 - TRAIL_PCT))
            else:
                p["mabreach"] = p["mabreach"] + 1 if s["c"][i] < s["dsma"][i] else 0
                if p["mabreach"] >= MA_BREACH_N:
                    p["pending_exit"] = True
        # ── fill / expire weekly orders ──
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
                                     sh=sh, sh0=sh, held=0, adv=o_["adv"], half_done=False,
                                     mabreach=0, pending_exit=False, cash_out=notion, proceeds=0.0,
                                     stt=0.0, stt_buy=sh * en * STT_PCT)
                        risk_pct = sh * (en - st) / eq * 100
                        assert 1.99 <= risk_pct <= 2.01, f"sizing bug: {risk_pct:.3f}%"
                        if ledger is not None:
                            op[t]["rec"] = dict(tkr=t, sig_date=o_["sig_d"], entry_date=d,
                                                entry=round(float(en), 2), stop0=round(float(st), 2),
                                                risk_pct=round(float(risk_pct), 3),
                                                entry_to_stop_pct=round((en / st - 1) * 100, 2),
                                                half_date=None, half_px=None)
                        filled = True
                    else:
                        skipped_cash += 1
            if filled or o_["live"] <= 0:
                del orders[t]
        # ── new WEEKLY orders (activation day = first session after the signal Friday) ──
        for t, s in P.items():
            if t in op or t in orders:
                continue
            i = didx[t].get(d)
            if i is None or i not in s["wk_order"]:
                continue
            if mem is not None and not ticker_in_index_on(t, dd, mem):
                continue
            trig, stop = s["wk_order"][i]
            if trig <= stop:
                continue
            activations += 1
            orders[t] = dict(trig=trig, stop=stop, adv=s["adv20"][i], live=ENTRY_WINDOW, sig_d=d)
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
                            held=p["held"], R=round(float(R), 3),
                            net_pnl=round(float(mark - p["cash_out"]), 2),
                            stt_paid=round(float(p["stt"] + p["stt_buy"] + xp * STT_PCT), 2))
            ledger.append(p["rec"])
    e = pd.Series(dict(curve)).sort_index()
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([x["R"] for x in T]); hold = np.array([x["held"] for x in T])
    reasons = pd.Series([x["reason"] for x in T]).value_counts().to_dict() if T else {}
    return dict(curve=e, ret=r, trades=len(R), tpy=len(R) / yrs, activations=activations,
                wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                medhold=float(np.median(hold)) if len(hold) else float("nan"),
                p90hold=float(np.percentile(hold, 90)) if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / EQ0,
                reasons=reasons, skipped_cash=skipped_cash)


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0088: weekly-confirmation entry (green weekly rebound off 44-EMA, buy Mon/Tue) on the 0085 book ===")
    ohlcv = corrected_universe()
    mem = load_membership()
    P = prep_weekly(ohlcv)
    print(f"corrected universe: {len(P)} names | weekly touch band {WEEKLY_TOUCH_BAND*100:.0f}% "
          f"| entry window Mon+Tue | 0085 exits\n")

    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross))
    print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    weekly activations {net['activations']} -> {net['trades']} fills "
          f"({net['trades']/max(net['activations'],1)*100:.0f}% fill rate) | exits: {net['reasons']}")
    led = pd.DataFrame(ledger)
    if len(led) and "entry_to_stop_pct" in led:
        print(f"    entry->stop width: med {led['entry_to_stop_pct'].median():.1f}% "
              f"(0085 daily ~7%) | per-year:")
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["net_pnl"].agg(["count", "sum"])
        print("    " + " | ".join(f"{y} {int(x['count'])}/{x['sum']/1e5:+.1f}L" for y, x in yr.iterrows()))

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
    print(f"\n  references (same cell): 0085 +0.587 / CAGR +11.5% | 0084 +0.477 | baseline_v1 0.667 | TRI +12.6%")
    print(f"  dSharpe vs 0085: {net['sharpe'] - 0.587:+.3f} | dCAGR vs 0085: {net['cagr']*100 - 11.5:+.1f}pp")

    net_err = backtest(prep_weekly(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))

    if "--ledger" in args and ledger:
        out = ROOT / "research" / "exports" / "bhanushali_weekly_entry_0088_trades.csv"
        pd.DataFrame(ledger).to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(ledger)} trades)")
    print("\n(run of record for pre-reg 0088; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
