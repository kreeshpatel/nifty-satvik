"""PRACTITIONER-faithful Bhanushali backtest (pre-reg 0024) — runs the strategy the way a real trader runs
it, not just its entry/exit mechanics: weekly frozen top-50 watchlist (trend + volatility + volume-expansion
rank), max 5 positions / 3 new per week / 10d re-entry cooldown (no overtrading), NIFTY-500-TRI regime pause,
buy-stop orders live 3 days with a no-chase gap skip, quality-green + HVC volume confirmation, candle-low
initial stop (big-candle midpoint rule), half off at +2R then his swing-low ratchet trail, breakeven floor
after the half-book. PIT membership, tiered real costs. Arms fixed in the pre-reg; gross+net reported.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import BROKERAGE_PCT, SLIPPAGE, STT_PCT  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_bhanushali_faithful import EQ0, START, wilder_rsi  # noqa: E402

STT_BROK = BROKERAGE_PCT + STT_PCT
ADV_LARGE, ADV_MIN = 5e8, 5e7
TRI_CSV = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"


def _cost_leg(adv, cost_off=False):
    if cost_off:
        return 0.0
    return STT_BROK + (SLIPPAGE["LARGE_CAP"] if adv >= ADV_LARGE else SLIPPAGE["MID_CAP"])


def _rose(x: np.ndarray, k: int) -> np.ndarray:
    r = np.full(len(x), False)
    r[k:] = x[k:] > x[:-k]
    return r & np.isfinite(x)


def prep(ohlcv):
    P = {}
    for tkr, df in ohlcv.items():
        if len(df) < 300:
            continue
        idx = pd.to_datetime(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        v = df["Volume"].to_numpy(float)
        n = len(c)
        pc = np.concatenate([[np.nan], c[:-1]])
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        dsma = pd.Series(c).rolling(44).mean().to_numpy()
        slope66 = np.full(n, np.nan); slope66[66:] = dsma[66:] / dsma[:-66] - 1.0
        strong = _rose(dsma, 22) & _rose(dsma, 44) & _rose(dsma, 66) & (c > dsma) & (slope66 >= 0.08)
        rsi = wilder_rsi(df["Close"]); rsi_prev = np.concatenate([[np.nan], rsi[:-1]])
        w = df.resample("W-FRI").agg({"Close": "last"}).dropna()
        wsma = w["Close"].rolling(44).mean()
        wtrend = ((wsma > wsma.shift(4)) & (wsma.shift(4) > wsma.shift(8))).reindex(idx, method="ffill").fillna(False).to_numpy(bool)
        adv20 = pd.Series(c * v).rolling(20).mean().to_numpy()
        adv60 = pd.Series(c * v).rolling(60).mean().to_numpy()
        vavg20 = pd.Series(v).rolling(20).mean().to_numpy()
        rng = h - l
        qgreen = (c > o) & (rng > 0) & ((c - l) >= 0.5 * rng)            # quality green: close in upper half
        hvc = v >= 1.5 * vavg20
        hold44 = (l <= dsma * 1.02) & (c >= dsma)                        # touch-and-HOLD the 44-SMA
        rsix = (rsi_prev < 35) & (rsi >= 35)
        # confirmed swing lows (pivot low, 2 bars each side; usable from i+2 -> PIT-safe trail level)
        piv = np.full(n, False)
        piv[2:-2] = (l[2:-2] < l[1:-3]) & (l[2:-2] < l[:-4]) & (l[2:-2] <= l[3:-1]) & (l[2:-2] <= l[4:])
        swlow = np.full(n, np.nan)
        last = np.nan
        for i in range(n):
            if i >= 4 and piv[i - 2]:
                last = l[i - 2]
            swlow[i] = last
        P[tkr] = dict(dates=idx, o=o, h=h, l=l, c=c, atr=atr, adv20=adv20, adv60=adv60,
                      dsma=dsma, slope66=slope66, strong=strong, wtrend=wtrend,
                      qgreen=qgreen, hvc=hvc, hold44=hold44, rsix=rsix, swlow=swlow)
    return P


def regime_series():
    b = pd.read_csv(TRI_CSV, parse_dates=["date"]).set_index("date")["tri_close"]
    sma = b.rolling(44).mean()
    ok = (b > sma) & (sma > sma.shift(10))
    return ok  # dates missing / warmup -> treated as OK by caller


def build_watchlist(P, mem, dd, prev_i):
    """Top-50 rank using data strictly before the week's first session (prev_i = last index < that day)."""
    rows = []
    for t, s in P.items():
        i = prev_i.get(t)
        if i is None or not s["strong"][i]:
            continue
        if not ticker_in_index_on(t, dd, mem):
            continue
        adv = s["adv20"][i]
        if not (adv >= ADV_MIN) or not np.isfinite(s["adv60"][i]) or s["adv60"][i] <= 0:
            continue
        if not (s["atr"][i] / s["c"][i] >= 0.015):                       # volatile enough for 1:2 in days
            continue
        rows.append((t, s["slope66"][i], s["adv20"][i] / s["adv60"][i]))
    if not rows:
        return set()
    df = pd.DataFrame(rows, columns=["t", "slope", "vexp"])
    for col in ("slope", "vexp"):
        sd = df[col].std()
        df[col + "_z"] = (df[col] - df[col].mean()) / (sd if sd else 1.0)
    df["rank"] = df["slope_z"] + df["vexp_z"]
    return set(df.nlargest(50, "rank")["t"])


def backtest(P, mem, *, engines=("A", "B"), regime_on=True, vol_confirm=True, maxpos=5, max_new_wk=3,
             cooldown=10, maxhold=60, risk=0.02, notional_cap=0.30, cost_off=False):
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    reg = regime_series()
    sig = {}
    for t, s in P.items():
        base = s["qgreen"] & (s["hvc"] if vol_confirm else True)
        sA = s["wtrend"] & s["rsix"] & base if "A" in engines else np.zeros(len(s["c"]), bool)
        sB = s["strong"] & s["hold44"] & base if "B" in engines else np.zeros(len(s["c"]), bool)
        sig[t] = np.nan_to_num(sA | sB, nan=False).astype(bool)
    eq = cash = EQ0; op = {}; orders = {}; cool = {}; curve = []; T = []
    watch, cur_week, new_this_wk = set(), None, 0
    for d in dts:
        dd = d.date()
        wk = (d.isocalendar().year, d.isocalendar().week)
        if wk != cur_week:                                               # weekend: rebuild + freeze the list
            prev_i = {}
            for t, s in P.items():
                j = s["dates"].searchsorted(d) - 1
                if j >= 0:
                    prev_i[t] = j
            watch = build_watchlist(P, mem, dd, prev_i)
            cur_week, new_this_wk = wk, 0
            orders = {t: o_ for t, o_ in orders.items() if t in watch}   # stale orders off-list die
        # --- manage opens (stop first, then half-target, then trail ratchet, then time) ---
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            p["held"] += 1
            s = P[t]
            ex = rs = None
            if s["l"][i] <= p["stop"]:
                ex, rs = p["stop"], "stop"
            elif not p["half_done"] and s["h"][i] >= p["tp2"]:
                half = p["sh"] * 0.5
                cash += half * p["tp2"] * (1 - _cost_leg(p["adv"], cost_off))
                p["sh"] -= half; p["half_done"] = True
                p["stop"] = max(p["stop"], p["en"])                      # breakeven floor after the half-book
            if ex is None and p["held"] >= maxhold:
                ex, rs = s["c"][i], "time"
            if ex is None:                                               # swing-low ratchet (his §12 trail)
                sw = s["swlow"][i]
                if np.isfinite(sw):
                    p["stop"] = max(p["stop"], sw * 0.999)
            if ex is not None:
                cash += p["sh"] * ex * (1 - _cost_leg(p["adv"], cost_off))
                r_full = (ex - p["en"]) / p["risk0"]
                R = 0.5 * 2.0 + 0.5 * r_full if p["half_done"] else r_full
                T.append(dict(R=R, reason=rs, held=p["held"], half=p["half_done"]))
                cool[t] = 0
                del op[t]
        for t in list(cool):
            cool[t] += 1
            if cool[t] > cooldown:
                del cool[t]
        # --- fill / expire pending buy-stop orders ---
        regime_ok = (not regime_on) or bool(reg.get(d, True))
        for t in list(orders):
            o_ = orders[t]; i = didx[t].get(d)
            if i is None:
                continue
            o_["live"] -= 1
            filled = False
            if (t not in op and t not in cool and len(op) < maxpos and new_this_wk < max_new_wk
                    and regime_ok and P[t]["h"][i] >= o_["trig"]):
                opn = P[t]["o"][i]
                if opn <= o_["trig"] * 1.015:                            # no chasing a >1.5% gap
                    en = max(opn, o_["trig"]); st = o_["stop"]
                    if en > st:
                        sh = min(eq * risk / (en - st), eq * notional_cap / en)
                        notion = sh * en * (1 + _cost_leg(o_["adv"], cost_off))
                        if sh > 0 and notion <= cash:
                            cash -= notion
                            op[t] = dict(en=en, stop=st, risk0=en - st, tp2=en + 2 * (en - st), sh=sh,
                                         held=0, adv=o_["adv"], half_done=False)
                            new_this_wk += 1; filled = True
            if filled or o_["live"] <= 0:
                del orders[t]
        # --- new signals -> pending orders (watchlist only) ---
        for t in watch:
            if t in op or t in orders or t in cool:
                continue
            i = didx[t].get(d)
            if i is None or not sig[t][i]:
                continue
            s = P[t]
            adv = s["adv20"][i]
            if not (adv >= ADV_MIN):
                continue
            rng = s["h"][i] - s["l"][i]
            st = (s["l"][i] + 0.5 * rng if rng / s["c"][i] >= 0.06 else s["l"][i]) * 0.999  # big-candle rule
            orders[t] = dict(trig=s["h"][i] * 1.001, stop=st, adv=adv, live=3)
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm; curve.append((d, eq))
    e = pd.Series(dict(curve)).sort_index(); r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    R = np.array([t["R"] for t in T]); hold = np.array([t["held"] for t in T])
    reasons = pd.Series([t["reason"] for t in T]).value_counts().to_dict() if T else {}
    return dict(trades=len(R), tpy=len(R) / yrs, wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"), maxR=R.max() if len(R) else float("nan"),
                avghold=hold.mean() if len(hold) else float("nan"),
                cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
                sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
                dd=(e / e.cummax() - 1).min(), reasons=reasons, ret=r)


def _row(tag, m):
    return (f"  {tag:<28} tr {m['trades']:>4} ({m['tpy']:>4.0f}/yr) | win {m['wr']*100:>4.1f}% | expR {m['expR']:+.2f} "
            f"| maxR {m['maxR']:>4.1f} | hold {m['avghold']:>3.0f}d | CAGR {m['cagr']*100:+6.1f}% "
            f"| Sh {m['sharpe']:+.3f} | DD {m['dd']*100:>6.1f}%")


def _slices(m):
    r = m["ret"]
    def sh(x):
        x = x.to_numpy(); return x.mean() / x.std() * np.sqrt(252) if len(x) > 5 and x.std() else float("nan")
    return (f"    continuous-slice Sharpe: 2017-18 {sh(r[r.index < '2019-01-01']):+.2f} | "
            f"2019-21 {sh(r[(r.index >= '2019-01-01') & (r.index < '2022-01-01')]):+.2f} | "
            f"2022-26 {sh(r[r.index >= '2022-01-01']):+.2f}")


def main() -> int:
    P = prep(load_ohlcv_cache(OHLCV_CACHE))
    mem = load_membership()
    print(f"names {len(P)} | weekly top-50 watchlist | 5 pos / 3 new-wk / 10d cooldown | half@2R + swing-low trail "
          f"| regime pause | window {START}..2026\n")
    hg = backtest(P, mem, cost_off=True)
    hn = backtest(P, mem)
    print("===== HEADLINE: combined A+B, practitioner process =====")
    print(_row("combined GROSS", hg)); print(_slices(hg))
    print(_row("combined NET", hn)); print(_slices(hn))
    print(f"    exits: {hn['reasons']}")
    print("\n===== pre-declared arms (net) =====")
    for tag, kw in (("B only (pullback)", dict(engines=("B",))),
                    ("A only (RSI)", dict(engines=("A",))),
                    ("regime OFF", dict(regime_on=False)),
                    ("volume-confirm OFF", dict(vol_confirm=False)),
                    ("throttle OFF (15pos/inf)", dict(maxpos=15, max_new_wk=10**9))):
        print(_row(tag, backtest(P, mem, **kw)))
    print("\nbaseline_v1 (63d momentum): Sharpe 0.667 / CAGR 15.5% / DD -46.3%")
    print("(measurement per pre-reg 0024; survivor-only cache -> optimistic; forward wall = only certifier)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
