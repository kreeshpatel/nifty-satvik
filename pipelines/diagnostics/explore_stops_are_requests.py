"""MEASUREMENT: "stops are requests" - re-price stop exits with the live overshoot, model lower-circuit lock, and a
2x gap-shock, for the swing, 0001 momentum and the 70/30 blend at 15% vol.

Owner request 2026-11-18 (research/robust-sizing). Analysis only: no live rule changes, no trial, no sealed read.

INPUTS
  swing book     nq.lab.runs.replay({}) - the capped live book, 2019-01-01..2024-06-28 (prices cut 2024-06-30)
  dataset A      diag_loss_diagnosis_2026_11.build_A().run(uncapped=True) - used ONLY to count trades affected
                 (A is the uncapped signal population; it has no capital NAV, so Sharpe/CAGR/drawdown are reported
                 on the capped live book above, which is the population A's money figures come from)
  momentum       0001 run of record (cached by explore_blend_drawdown_sizing.navs)
  blend          pipelines/lifecycle/core.py::vol_target_blend at 15%, both legs windowed to 2019-03-01..2024-06-28

LIVE OVERSHOOT (in R)
  For every closed live trade with exit_reason in {stop, stop_part} (results/signals_history_weekly.json), the
  card stop from results/cards_archive.jsonl (same ticker, nearest signal_date, max gap printed):
      overshoot_R = (close_price - card_stop) / (entry - card_stop)
  NOTE: "live" here is the forward scan's MODELLED exit on real post-2026-07 daily bars - the same weekly-close
  trigger and next-open fill as the backtest - not broker fills (none are in the repo). Most of these trades were
  never funded (finding 0146/0147): they are the uncapped tracker's exits.

BACKTEST OVERSHOOT (in R), per stop exit (reason stop / stop_part): (exit_px - stop0) / (entry - stop0). config P
  has no lock-in, so the stop at exit is stop0 for both reasons (engine run_bhanushali_weekly_rank.py:1118-1119).

SCENARIOS (each one at a time, everything else as the backtest)
  base         the backtest as booked
  live_ov      each stop exit re-priced to stop0 + d * risk0, d drawn with replacement from the live sample;
               N_REP replications, median reported
  circuit      lower-circuit lock (APPROXIMATE - no NSE price-band data is in the repo): a session is LOCKED when
               close/prev_close - 1 is within 0.15pp of -5%, -10% or -20%, the close is within 0.1% of the low, and
               (high - low) / prev_close <= 2%. An exit dated on a locked session moves to the first later session
               that is not locked, filled at that session's open. Applies to EVERY exit of both books.
  gap2x        every stop exit moved by 2 x the MEAN live overshoot: exit_px + 2 * mean(overshoot_R) * risk0

ACCOUNTING: a re-priced exit changes cash by shares_exited * (new_px - old_px) from the exit date onward; shares come
  from the engine's position log (last row before the exit). The engine's later SIZING does not see the change
  (equity feeds 2% risk sizing), so compounding of the difference into later position sizes is ignored - disclosed
  as an artifact below.

METRICS: Sharpe = mean/std of daily NAV returns * sqrt(252), no risk-free; CAGR on calendar years; bootstrap p95
  drawdown = 156-week, mean block 8 weeks (the most conservative block in the 2026-11-18 drawdown study), 10,000
  draws, stationary bootstrap of Friday-to-Friday returns (explore_blend_drawdown_sizing.boot_dd).

    python pipelines/diagnostics/explore_stops_are_requests.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_stops_are_requests.json"
N_REP = 200
SEED = 20261118
STOP_REASONS = ("stop", "stop_part")
BANDS = (0.05, 0.10, 0.20)
BAND_TOL, LOW_TOL, RANGE_MAX = 0.0015, 0.001, 0.02


def live_overshoot() -> tuple[np.ndarray, dict]:
    h = pd.DataFrame(json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8")))
    c = pd.read_json(ROOT / "results" / "cards_archive.jsonl", lines=True)
    h["signal_date"], c["signal_date"] = pd.to_datetime(h["signal_date"]), pd.to_datetime(c["signal_date"])
    out, gaps = [], []
    for _, r in h[h["exit_reason"].isin(STOP_REASONS)].iterrows():
        cc = c[c["ticker"] == r["ticker"]]
        k = (cc["signal_date"] - r["signal_date"]).abs().idxmin()
        gaps.append(abs((cc.loc[k, "signal_date"] - r["signal_date"]).days))
        stop = float(cc.loc[k, "stop"])
        out.append((float(r["close_price"]) - stop) / (float(r["entry"]) - stop))
    o = np.array(out)
    return o, {"n": int(len(o)), "mean": round(float(o.mean()), 3), "median": round(float(np.median(o)), 3),
               "p5": round(float(np.percentile(o, 5)), 3), "min": round(float(o.min()), 3), "max": round(float(o.max()), 3),
               "max_signal_date_gap_days": int(max(gaps)),
               "window": f"{h.loc[h.exit_reason.isin(STOP_REASONS), 'close_date'].min()}..{h.loc[h.exit_reason.isin(STOP_REASONS), 'close_date'].max()}"}


def locked_sessions(ohlcv: dict) -> dict[str, set]:
    """APPROXIMATE lower-circuit-locked sessions per ticker (see module doc)."""
    out = {}
    for t, df in ohlcv.items():
        if not len(df):
            continue
        cl = df["close"] if "close" in df else df["Close"]
        lo = df["low"] if "low" in df else df["Low"]
        hi = df["high"] if "high" in df else df["High"]
        pc = cl.shift(1)
        ret = cl / pc - 1
        at_band = np.zeros(len(df), bool)
        for b in BANDS:
            at_band |= (ret + b).abs().to_numpy() <= BAND_TOL
        m = at_band & (cl <= lo * (1 + LOW_TOL)).to_numpy() & (((hi - lo) / pc) <= RANGE_MAX).to_numpy()
        s = set(pd.DatetimeIndex(df.index[m]).normalize())
        if s:
            out[t] = s
    return out


def moved_exit(ohlcv_t: pd.DataFrame, locked: set, exit_date) -> tuple[pd.Timestamp, float] | None:
    """First session after `exit_date` that is not locked -> (date, open). None if exit_date is not locked."""
    d0 = pd.Timestamp(exit_date).normalize()
    if d0 not in locked:
        return None
    idx = pd.DatetimeIndex(ohlcv_t.index).normalize()
    op = ohlcv_t["open"] if "open" in ohlcv_t else ohlcv_t["Open"]
    for d, o in zip(idx[idx > d0], op[idx > d0]):
        if d not in locked:
            return d, float(o)
    return None


def apply_cash(nav: pd.Series, deltas: list[tuple[pd.Timestamp, float]]) -> pd.Series:
    adj = pd.Series(0.0, index=nav.index)
    for d, x in deltas:
        adj[adj.index >= pd.Timestamp(d)] += x
    return nav + adj


def apply_cash_scaled(nav: pd.Series, deltas: list[tuple[pd.Timestamp, float]]) -> pd.Series:
    """ADDED AFTER FIRST LOOK (2026-11-18): apply_cash books each re-priced exit at the ORIGINAL position size,
    even after earlier adjustments have shrunk the book, which overstates a sequence of losses (the gap2x swing
    read -68%). The engine sizes on current equity (2% risk), so as a first-order correction each delta is
    scaled by adjusted NAV / base NAV on the session before its exit. Both versions are reported."""
    adj = pd.Series(0.0, index=nav.index)
    for d, x in sorted(deltas, key=lambda t: pd.Timestamp(t[0])):
        d = pd.Timestamp(d)
        prev = nav.index[nav.index < d]
        f = float((nav + adj)[prev[-1]] / nav[prev[-1]]) if len(prev) else 1.0
        adj[adj.index >= d] += x * f
    return nav + adj


def shares_at_exit(plog: pd.DataFrame, tkr, entry, exit_date, entry_date=None) -> float:
    """Shares held on the last position-log row before the exit. The log keeps the unrounded fill price and the
    ledger rounds it to 2 dp, so rows are matched on ticker, |entry| within 0.01 and the holding window."""
    m = (plog["tkr"] == tkr) & ((plog["entry"] - entry).abs() <= 0.01) & (plog["date"] < pd.Timestamp(exit_date))
    if entry_date is not None:
        m &= plog["date"] >= pd.Timestamp(entry_date)
    g = plog[m]
    return float(g.sort_values("date")["shares"].iloc[-1]) if len(g) else float("nan")


def stats(nav: pd.Series, lo=None, hi=None, boot_seed=SEED) -> dict:
    n = nav
    if lo:
        n = n[(n.index >= pd.Timestamp(lo)) & (n.index <= pd.Timestamp(hi))]
    r = n.pct_change().dropna()
    yrs = (n.index[-1] - n.index[0]).days / 365.25
    dd = B.boot_dd(C.weekly_returns(n).to_numpy(), 156, 8, seed=boot_seed)
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(252)), "cagr_pct": float((n.iloc[-1] / n.iloc[0]) ** (1 / yrs) - 1) * 100,
            "boot156_p95_dd_pct": float(np.percentile(dd, 95)), "backtest_maxdd_pct": float((n / n.cummax() - 1).min() * 100)}


def blend_stats(mom_nav, sw_nav) -> dict:
    r, _ = C.vol_target_blend(B.window(mom_nav).pct_change().dropna(), B.window(sw_nav).pct_change().dropna())
    return stats(B.to_nav(r))


def main() -> int:
    d = B.navs()
    sw_nav, led, plog = d["swing"], d["swing_ledger"].copy(), d["swing_position_log"].copy()
    mo_nav, mtr = d["momentum"], d["momentum_trades"].copy()
    plog["date"] = pd.to_datetime(plog["date"])
    for c_ in ("entry_date", "exit_date"):
        led[c_] = pd.to_datetime(led[c_])
        mtr[c_] = pd.to_datetime(mtr[c_])
    if round(d["swing_metrics"]["sharpe"], 3) != 1.025 or (round(d["momentum_metrics"]["cagr_pct"], 2), round(d["momentum_metrics"]["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("anchor mismatch: stop")
    live, live_summary = live_overshoot()

    st = led[led["reason"].isin(STOP_REASONS)].copy()
    st["risk0"] = st["entry"] - st["stop0"]
    st["bt_ov_R"] = (st["exit_px"] - st["stop0"]) / st["risk0"]
    st["shares"] = [shares_at_exit(plog, r.tkr, r.entry, r.exit_date, r.entry_date) for r in st.itertuples()]
    if st["shares"].isna().any():
        raise SystemExit(f"{int(st.shares.isna().sum())} stop exits without a position-log row: stop")

    res = {"live_overshoot_R": live_summary,
           "backtest_overshoot_R_swing_book": {"n": int(len(st)), "mean": round(float(st.bt_ov_R.mean()), 3),
                                               "median": round(float(st.bt_ov_R.median()), 3),
                                               "min": round(float(st.bt_ov_R.min()), 3)},
           "momentum_stop_exits": int(mtr["reason"].str.contains("stop").sum()),
           "momentum_exit_reasons": mtr["reason"].value_counts().to_dict()}

    # ---------------- circuit lock (approximate)
    from run_bhanushali_path1 import corrected_universe
    full = corrected_universe()
    locked = locked_sessions(full)
    import diag_loss_diagnosis_2026_11 as D
    _cut, _P, _mem, _nifty, run = D.build_A()
    _, A = run(True)
    A["exit_date"] = pd.to_datetime(A["exit_date"])

    def circ_count(df, tcol, dcol):
        return int(sum(pd.Timestamp(r[dcol]).normalize() in locked.get(r[tcol], set()) for _, r in df.iterrows()))
    res["circuit"] = {"method": "APPROXIMATE: close within 0.15pp of -5/-10/-20%, close within 0.1% of low, range <= 2% of prior close",
                      "locked_sessions_detected": int(sum(len(v) for v in locked.values())),
                      "tickers_with_any": len(locked),
                      "trades_affected_dataset_A_uncapped": circ_count(A[A.reason != "eos"], "tkr", "exit_date"),
                      "dataset_A_closed_trades": int((A.reason != "eos").sum()),
                      "trades_affected_swing_book": circ_count(led[led.reason != "eos"], "tkr", "exit_date"),
                      "trades_affected_momentum": circ_count(mtr, "ticker", "exit_date"), "momentum_trades": int(len(mtr))}

    def circuit_deltas(df, tcol, pxcol, qty_fn):
        out = []
        for r in df.itertuples():
            t = getattr(r, tcol)
            mv = moved_exit(full[t], locked.get(t, set()), r.exit_date) if t in full else None
            if mv:
                out.append((mv[0], qty_fn(r) * (mv[1] - getattr(r, pxcol))))
        return out
    sw_closed = led[led.reason != "eos"].copy()
    sw_closed["shares"] = [shares_at_exit(plog, r.tkr, r.entry, r.exit_date, r.entry_date) for r in sw_closed.itertuples()]
    # the swing never looks past the cut: its moved exits are searched in prices truncated at 2024-06-30
    cut = pd.Timestamp("2024-06-30")
    full_mo = full
    full = {t: df[pd.DatetimeIndex(df.index) <= cut] for t, df in full_mo.items()}
    sw_circ = apply_cash(sw_nav, circuit_deltas(sw_closed, "tkr", "exit_px", lambda r: r.shares))
    full = full_mo
    mo_circ = apply_cash(mo_nav, circuit_deltas(mtr, "ticker", "exit", lambda r: r.qty))

    # ---------------- gap 2x
    g = st.assign(new=st.exit_px + 2 * live.mean() * st.risk0)
    sw_gap = apply_cash(sw_nav, list(zip(g.exit_date, g.shares * (g.new - g.exit_px))))

    # ---------------- live overshoot resample
    rng = np.random.default_rng(SEED)
    reps = []
    for k in range(N_REP):
        draw = rng.choice(live, size=len(st), replace=True)
        new = st.stop0 + draw * st.risk0
        nav_k = apply_cash(sw_nav, list(zip(st.exit_date, st.shares * (new - st.exit_px))))
        reps.append({"swing": stats(nav_k, boot_seed=SEED + k), "blend": blend_stats(mo_nav, nav_k)})

    def med(key, book):
        return round(float(np.median([r[book][key] for r in reps])), 3)
    rows = {"base": {"swing": stats(sw_nav), "momentum": stats(mo_nav), "blend": blend_stats(mo_nav, sw_nav)},
            "live_ov": {"swing": {k: med(k, "swing") for k in ("sharpe", "cagr_pct", "boot156_p95_dd_pct", "backtest_maxdd_pct")},
                        "momentum": "unchanged - 0001 has no stop exits",
                        "blend": {k: med(k, "blend") for k in ("sharpe", "cagr_pct", "boot156_p95_dd_pct", "backtest_maxdd_pct")}},
            "circuit": {"swing": stats(sw_circ), "momentum": stats(mo_circ), "blend": blend_stats(mo_circ, sw_circ)},
            "gap2x": {"swing": stats(sw_gap), "momentum": "unchanged - 0001 has no stop exits",
                      "blend": blend_stats(mo_nav, sw_gap)}}
    # ---------------- ADDED AFTER FIRST LOOK: the same scenarios with equity-scaled adjustments
    sw_circ_s = apply_cash_scaled(sw_nav, circuit_deltas(sw_closed, "tkr", "exit_px", lambda r: r.shares))
    mo_circ_s = apply_cash_scaled(mo_nav, circuit_deltas(mtr, "ticker", "exit", lambda r: r.qty))
    sw_gap_s = apply_cash_scaled(sw_nav, list(zip(g.exit_date, g.shares * (g.new - g.exit_px))))
    rng = np.random.default_rng(SEED)
    reps_s = []
    for k in range(N_REP):
        draw = rng.choice(live, size=len(st), replace=True)
        new = st.stop0 + draw * st.risk0
        nav_k = apply_cash_scaled(sw_nav, list(zip(st.exit_date, st.shares * (new - st.exit_px))))
        reps_s.append({"swing": stats(nav_k, boot_seed=SEED + k), "blend": blend_stats(mo_nav, nav_k)})

    def med_s(key, book):
        return round(float(np.median([r[book][key] for r in reps_s])), 3)
    keys = ("sharpe", "cagr_pct", "boot156_p95_dd_pct", "backtest_maxdd_pct")
    rows_scaled = {"live_ov": {"swing": {k: med_s(k, "swing") for k in keys}, "blend": {k: med_s(k, "blend") for k in keys}},
                   "circuit": {"swing": stats(sw_circ_s), "momentum": stats(mo_circ_s), "blend": blend_stats(mo_circ_s, sw_circ_s)},
                   "gap2x": {"swing": stats(sw_gap_s), "blend": blend_stats(mo_nav, sw_gap_s)}}
    res["scenarios_equity_scaled_added_after_first_look"] = json.loads(json.dumps(rows_scaled, default=float))
    res["scenarios"] = json.loads(json.dumps(rows, default=float))
    res["n_rep_live_ov"] = N_REP
    OUT_JSON.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
