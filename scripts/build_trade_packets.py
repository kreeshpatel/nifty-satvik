"""Phase A of the AI per-trade forensic: build one self-contained 'chart packet' per 0094 trade so an AI
agent can reason over it like a chart. Weekly O/H/L/C + 44w SMA/slope/RS around the setup, the entry-week
daily bars, MAE/MFE, and the EARLIER-ENTRY candidates (prior weeks near the SMA + why each did/didn't fire
+ the hypothetical earlier entry/stop). Pinned, determinism-gated. Output: research/losers_analysis/packets/*.json"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_rank as R94
import run_bhanushali_weekly_crs as CRS
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership
from run_bhanushali_weekly_rank import SLOPE_MIN, SLOPE_LOOKBACK, TOUCH_BAND, CRS_LEN
OUT = ROOT / "research" / "losers_analysis" / "packets"; OUT.mkdir(parents=True, exist_ok=True)

ohlcv = corrected_universe(); mem = load_membership(); P = R94.prep_weekly_rank(ohlcv)
didx = {t: {d: i for i, d in enumerate(pd.DatetimeIndex(s["dates"]))} for t, s in P.items()}
n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()


def weekly(t):
    s = P[t]; idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy())); weeks, cur, prev = [], [], None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur); cur = []
        cur.append(i); prev = k
    if cur:
        weeks.append(cur)
    o, h, l, c = s["o"], s["h"], s["l"], s["c"]
    wo = np.array([o[d[0]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
    wl = np.array([l[d].min() for d in weeks]); wc = np.array([c[d[-1]] for d in weeks])
    ws = pd.Series(wc).rolling(44).mean().to_numpy()
    sl = np.full(len(ws), np.nan); sl[SLOPE_LOOKBACK:] = ws[SLOPE_LOOKBACK:] / ws[:-SLOPE_LOOKBACK] - 1.0
    rng = wh - wl; green = (wc > wo) & (rng > 0) & ((wc - wl) >= 0.5 * rng)
    touch = (wl <= ws * (1 + TOUCH_BAND)) & (wc > ws)
    ia = n50.reindex(idx, method="ffill").to_numpy(float); iw = np.array([ia[d[-1]] for d in weeks])
    rs = np.where(iw > 0, wc / iw, np.nan); rs_sma = pd.Series(rs).rolling(CRS_LEN).mean().to_numpy()
    fired = (sl >= SLOPE_MIN) & green & touch & (wc > ws) & np.nan_to_num(rs > rs_sma, nan=False)
    wkdate = [pd.Timestamp(s["dates"][d[0]]) for d in weeks]
    d2w = {i: wp for wp, d in enumerate(weeks) for i in d}
    return dict(weeks=weeks, wo=wo, wh=wh, wl=wl, wc=wc, ws=ws, sl=sl, green=green, touch=touch,
                rs=rs, rs_sma=rs_sma, fired=fired, wkdate=wkdate, d2w=d2w)


def pct(a, b):
    return round((a / b - 1) * 100, 1) if (b and b > 0) else None


led = []; m = R94.backtest(P, mem, ledger=led, start="2017-01-01")
assert abs(m["sharpe"] - 1.132) < 0.01 and m["trades"] == 255, "determinism FAIL"
print(f"determinism PASS ({m['sharpe']:.3f}/{m['trades']}) — building {len(led)} packets")
WK = {}
built = 0
for r in led:
    t = r["tkr"]
    if t not in WK:
        WK[t] = weekly(t)
    w = WK[t]; s = P[t]
    j0 = didx[t][pd.Timestamp(r["entry_date"])]; j1 = didx[t][pd.Timestamp(r["exit_date"])]
    wp = w["d2w"][j0]; sig = wp - 1
    sm = w["ws"][sig]
    lows = s["l"][j0:j1 + 1]; highs = s["h"][j0:j1 + 1]
    e2 = s["l"][j0:min(j0 + 11, j1 + 1)]
    # weekly context window: 20 wk before signal .. exit week
    xwp = w["d2w"][j1]; a = max(sig - 20, 0)
    ctx = [dict(week=w["wkdate"][i].strftime("%Y-%m-%d"), O=round(w["wo"][i], 1), H=round(w["wh"][i], 1),
               L=round(w["wl"][i], 1), C=round(w["wc"][i], 1), SMA=round(w["ws"][i], 1) if w["ws"][i] == w["ws"][i] else None,
               low_vs_SMA=pct(w["wl"][i], w["ws"][i]), close_vs_SMA=pct(w["wc"][i], w["ws"][i]),
               slope_pct=round(w["sl"][i] * 100, 1) if w["sl"][i] == w["sl"][i] else None,
               green=bool(w["green"][i]), touch=bool(w["touch"][i]), rs_above=bool(np.nan_to_num(w["rs"][i] > w["rs_sma"][i])),
               fired=bool(w["fired"][i])) for i in range(a, xwp + 1)]
    # earlier-entry candidates: weeks sig-3..sig, why each did/didn't fire + hypothetical entry(next-wk open)/stop
    earlier = []
    for k in range(max(sig - 3, 0), sig + 1):
        nk = k + 1
        hypo_entry = round(w["wo"][nk], 1) if nk < len(w["wo"]) else None   # next week's open
        earlier.append(dict(signal_week=w["wkdate"][k].strftime("%Y-%m-%d"), low_vs_SMA=pct(w["wl"][k], w["ws"][k]),
                            close_vs_SMA=pct(w["wc"][k], w["ws"][k]), green=bool(w["green"][k]), touch=bool(w["touch"][k]),
                            rs_above=bool(np.nan_to_num(w["rs"][k] > w["rs_sma"][k])),
                            slope_ok=bool(w["sl"][k] >= SLOPE_MIN), fired=bool(w["fired"][k]),
                            hypothetical_entry=hypo_entry, hypothetical_stop=round(w["wl"][k], 1)))
    pk = dict(ticker=t, won=bool(r["R"] > 0), R=round(r["R"], 2), reason=r["reason"],
              entry_date=str(r["entry_date"])[:10], entry=round(r["entry"], 1), stop=round(r["stop0"], 1),
              exit_date=str(r["exit_date"])[:10], exit_px=round(r["exit_px"], 1), held_weeks=int(r["held_weeks"]),
              half_booked_at_2R=(r.get("half_date") is not None),
              entry_ext_vs_SMA=pct(r["entry"], sm), risk_pct=round((r["entry"] - r["stop0"]) / r["entry"] * 100, 1),
              mae_pct=round((lows.min() / r["entry"] - 1) * 100, 1) if len(lows) else 0.0,
              mfe_pct=round((highs.max() / r["entry"] - 1) * 100, 1) if len(highs) else 0.0,
              mae_first2wk=round((e2.min() / r["entry"] - 1) * 100, 1) if len(e2) else 0.0,
              signal_week=ctx[sig - a] if 0 <= sig - a < len(ctx) else None,
              entry_week_daily=[dict(date=str(pd.Timestamp(s["dates"][i]).date()), O=round(s["o"][i], 1),
                                     H=round(s["h"][i], 1), L=round(s["l"][i], 1), C=round(s["c"][i], 1))
                                for i in w["weeks"][wp]],
              earlier_candidates=earlier, weekly_context=ctx)
    fn = f"{'W' if pk['won'] else 'L'}_{t}_{pk['entry_date']}.json"
    (OUT / fn).write_text(json.dumps(pk, indent=1)); built += 1
print(f"built {built} packets -> {OUT}")
