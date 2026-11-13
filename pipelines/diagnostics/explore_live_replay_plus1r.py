"""EXPLORE (tier 0): the +1R management arms replayed trade-by-trade on the live record (2026-07-06 onward).

Every live trade in results/signals_history_weekly.json, with its initial stop from results/cards_archive.jsonl, is
re-simulated on Yahoo daily bars under the live exit mechanics:
  - the stop is tested on the weekly close and filled at the next session's open;
  - 40% books at +2R as a resting limit (intraweek high);
  - 40% books on the blow-off pattern (MFE >= 2.5R, a new weekly high closing in its lower third) at the next open;
  - the runner exits on a weekly close below the 44-week SMA, at the next open.
Open trades are marked at the last close. R is gross of costs. The engine convention is mirrored: the ratchet peak
is the max of week-end-session highs. The base replay is checked against the recorded R of the closed trades
before any arm is read. Arms come from explore_plus1r_arms.py. No screen row, no n_trials change.

    python pipelines/diagnostics/explore_live_replay_plus1r.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
from explore_plus1r_arms import ARMS, path_stats, summarise  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_live_replay_plus1r.json"
LIVE_SE = dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0, pattern_frac=0.40, pattern_arm_r=2.5,
               pattern_third=0.34)


def load_trades() -> list[dict]:
    h = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    H = h if isinstance(h, list) else h["signals"]
    C = [json.loads(ln) for ln in (ROOT / "results" / "cards_archive.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for r in H:
        m = [c for c in C if c["ticker"] == r["ticker"] and c.get("stop")
             and abs((pd.Timestamp(c["signal_date"]) - pd.Timestamp(r["signal_date"])).days) <= 3]
        m.sort(key=lambda c: c.get("as_of", ""))
        out.append(dict(tkr=r["ticker"], sig=pd.Timestamp(r["signal_date"]), en=float(r["entry"]), stop0=float(m[0]["stop"]),
                        status=r["status"], R_rec=r.get("r_multiple"), bought=m[0].get("bought_date"),
                        exit_reason=r.get("exit_reason"), close_date=r.get("close_date")))
    return out


def simulate(t: dict, df: pd.DataFrame, se: dict) -> dict:
    en, risk = t["en"], t["en"] - t["stop0"]
    start = pd.Timestamp(t["bought"]) if t.get("bought") else t["sig"]
    w = df[df.index >= start]
    if not len(w) or risk <= 0:
        return {"R": float("nan"), "reason": "no_data"}
    wk_close = df["Close"].resample("W-FRI").last().dropna()
    sma44 = wk_close.rolling(44).mean()
    week_of = lambda d: d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    last_in_week = w.groupby(w.index.map(week_of)).tail(1).index
    stop, frac, real, pk, pk_wh = t["stop0"], 1.0, 0.0, en, 0.0
    t1 = t2 = pt = False
    pending = None
    for i, d in enumerate(w.index):
        o, hi, lo, c = (float(w[k].iloc[i]) for k in ("Open", "High", "Low", "Close"))
        if pending is not None:                                 # weekly decision fills at this open
            act, f = pending
            r_px = (o - en) / risk
            if act == "full":
                real += frac * r_px
                return {"R": real, "reason": "stop" if f == "stop" else f, "exit": str(d.date())}
            take = min(f, frac); real += take * r_px; frac -= take; pending = None
        for done, rk, fk in (("t1", "tp1_r", "tp1_frac"), ("t2", "tp2_r", "tp2_frac")):
            if (done == "t1" and t1) or (done == "t2" and t2):
                continue
            if done == "t2" and not t1:
                break
            if hi < en + se[rk] * risk:
                break
            take = min(se[fk], frac); real += take * se[rk]; frac -= take
            if done == "t1":
                t1 = True
            else:
                t2 = True
        if frac <= 1e-9:
            return {"R": real, "reason": "targets", "exit": str(d.date())}
        if se.get("peak_all_days"):                             # variant: peak from every daily high, not week-end only
            pk = max(pk, hi)
        partial_week = d == df.index[-1] and d.weekday() < 4       # this week has not closed yet
        if d in last_in_week and not partial_week:
            pk = max(pk, hi)
            mfe = (pk - en) / risk
            if se.get("lockin_mfe") and mfe >= se["lockin_mfe"]:
                stop = max(stop, en + se.get("lockin_at", 1.5) * risk)
            for lm, la in se.get("lockin_ladder", ()):
                if mfe >= lm:
                    stop = max(stop, en + la * risk)
            wkey = week_of(d)
            wslice = w[w.index.map(week_of) == wkey]
            wh, wl = float(wslice["High"].max()), float(wslice["Low"].min())
            if c <= stop:
                pending = ("full", "stop" + ("_part" if t1 or pt else ""))
            elif (se.get("pattern_frac") and not pt and mfe >= se["pattern_arm_r"] and wh > wl and wh >= pk_wh
                  and (c - wl) < se["pattern_third"] * (wh - wl)):
                pending = ("part", se["pattern_frac"]); pt = True
            else:
                sm = sma44.get(wkey, np.nan)
                if sm == sm and c < sm:
                    pending = ("full", "sma_break")
            pk_wh = max(pk_wh, wh)
    last = float(w["Close"].iloc[-1])
    return {"R": real + frac * (last - en) / risk, "reason": "open", "exit": None}


def main() -> int:
    import yfinance as yf
    trades = load_trades()
    tick = sorted({t["tkr"] for t in trades})
    raw = yf.download([f"{x}.NS" for x in tick], start="2025-06-01", auto_adjust=True, progress=False, group_by="ticker")
    bars = {x: raw[f"{x}.NS"].dropna(subset=["Close"]) for x in tick if f"{x}.NS" in raw.columns.get_level_values(0)}
    res: dict = {"tier": "EXPLORE", "n_trades": len(trades), "last_bar": str(max(b.index.max() for b in bars.values()).date()),
                 "arms": {}, "validation": {}}
    variants = {**ARMS, **{f"{k}|intraweek_peak": {**v, "peak_all_days": True} for k, v in ARMS.items()
                           if any(x in v for x in ("lockin_mfe", "lockin_ladder"))}}
    for name, extra in variants.items():
        se = {**LIVE_SE, **extra}
        rows = []
        for t in trades:
            sim = simulate(t, bars[t["tkr"]], se) if t["tkr"] in bars else {"R": float("nan"), "reason": "no_data"}
            rows.append({**{k: t[k] for k in ("tkr", "status", "R_rec")}, "sig": str(t["sig"].date()), **sim})
        d = pd.DataFrame(rows)
        closed = d[d.reason != "open"]
        res["arms"][name] = {"sum_R_all_marked": round(float(d.R.sum()), 1), "sum_R_closed": round(float(closed.R.sum()), 1),
                             "n_closed": int(len(closed)), "n_full_stop": int((d.reason == "stop").sum()),
                             "n_open": int((d.reason == "open").sum()), "no_data": int((d.reason == "no_data").sum())}
        if name == "live":
            rec = d[d.status != "ACTIVE"].dropna(subset=["R_rec"])
            res["validation"] = {"recorded_closed_sum_R": round(float(rec.R_rec.astype(float).sum()), 1),
                                 "simulated_same_trades_sum_R": round(float(rec.R.sum()), 1),
                                 "trades_off_by_gt_0.25R": rec[(rec.R - rec.R_rec.astype(float)).abs() > 0.25][["tkr", "sig", "R_rec", "R", "reason"]].to_dict("records")}
        print(name, res["arms"][name], flush=True)
    # round-trip losers and dips on the recorded live trades (open trades run to the last bar)
    far = pd.Timestamp.today().normalize() + pd.Timedelta(days=1)
    led = pd.DataFrame([dict(tkr=t["tkr"], entry_date=pd.Timestamp(t["bought"]) if t.get("bought") else t["sig"], entry=t["en"],
                             stop0=t["stop0"], exit_date=pd.Timestamp(t["close_date"]) if t.get("close_date") and t["status"] != "ACTIVE" else far,
                             reason=(t.get("exit_reason") or "open") if t["status"] != "ACTIVE" else "open",
                             R=float(t["R_rec"]) if t["R_rec"] is not None and t["status"] != "ACTIVE" else float("nan"))
                        for t in trades])
    ps = path_stats(led, bars)
    last_close = {x: float(b["Close"].iloc[-1]) for x, b in bars.items()}
    for i, t in enumerate(trades):                               # mark open trades for the big-winner count
        if t["status"] == "ACTIVE":
            ps.loc[ps.tkr.eq(t["tkr"]) & ps.R.isna(), "R"] = (last_close[t["tkr"]] - t["en"]) / (t["en"] - t["stop0"])
    res["round_trip_live"] = summarise(ps)
    res["round_trip_live"]["note"] = "big winners include open trades marked at the last close"
    print(json.dumps(res["round_trip_live"], indent=1))
    print(json.dumps(res["validation"], indent=1, default=str))
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
