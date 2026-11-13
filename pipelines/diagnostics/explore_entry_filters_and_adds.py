"""EXPLORE (tier 0): entry filters, a +1R add, and half size in a weak market, on the live rules, 2019..2024-06-30.

Owner request 2026-11-13. No screen row, no n_trials change, nothing changes live. PIT membership, prices cut at
2024-06-30 and asserted; nothing sealed is read.

Arms (each against the live book, single path):
  (a) add_unit_at_1R   one extra unit (same rupee risk) at the next open after the first Friday close at or above
                       +1R; it shares the parent's stop and exits, selling in the same proportion as the parent's
                       remaining shares. Priced per trade from the engine's own exit events (no engine change), so it
                       has a per-trade book and an R-drawdown but no capped-book result.
  (b) entry filters    skip the signal when, on its signal Friday:
      b1 midcap_breadth_lt_40   midcap breadth < 40%. APPROXIMATION: there is no midcap index membership in the data,
                                so "midcap" = PIT Nifty-500 members ranked 101-250 by trailing 63-session median traded
                                value; breadth = share of them closing above their own 40-week SMA.
      b2 below_own_40w          the stock's weekly close is below its own 40-week SMA. VACUOUS on this book: every
                                Grade-A signal closes above its rising 44-week SMA, and so above its 40-week SMA
                                (minimum +0.7% over 1,524 signals); the filter removes nothing
      b3 weak_6m_rs             the stock's 26-week return minus the Nifty's 26-week return is below zero
      b4 results_within_4w      a results board meeting is scheduled within 28 days after the signal Friday,
                                counting only meetings announced on or before it (nq.data.earnings, PIT)
  (c) half_size_below_40w  entries in weeks whose signal-week Nifty close is below its 40-week SMA are taken at
                           half size (entry_size_scale_by_week = 0.5, the S1 throttle at half).

Reported per arm: per-trade (uncapped) closed trades and mean R over them, total R (open trades marked at the cut), worst drawdown of
the cumulative-R curve by exit date; capped ₹10L book Sharpe / CAGR / MaxDD; and how many of the live book's big
winners (uncapped, R >= +2) the arm skips or shrinks.

    python pipelines/diagnostics/explore_entry_filters_and_adds.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
import diag_giveback_ratchet_0148 as G  # noqa: E402
import diag_problem1_throttle_bound as T  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-13_entry_filters_and_adds.json"
BIG = 2.0


def signal_friday(d: pd.Timestamp) -> pd.Timestamp:
    """The Friday before an entry session (the setup week's close)."""
    back = (d.weekday() - 4) % 7 or 7
    return (d - pd.Timedelta(days=back)).normalize()


def weekly(df: pd.DataFrame, col: str = "Close") -> pd.Series:
    return df[col].resample("W-FRI").last().dropna()


def r_drawdown(led: pd.DataFrame, extra: pd.Series | None = None) -> float:
    """Worst peak-to-trough of cumulative R, booked at each trade's exit date (open trades at the cut)."""
    d = led.copy()
    d["R2"] = d["R"] + (extra.reindex(d.index).fillna(0.0) if extra is not None else 0.0)
    d["when"] = pd.to_datetime(d["exit_date"].fillna(G.CUT))
    cum = d.sort_values("when").groupby("when")["R2"].sum().cumsum()
    return float((cum - cum.cummax()).min())


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
    from run_bhanushali_path1 import corrected_universe
    from run_bhanushali_weekly_rank import ticker_in_index_on
    from nq.data.membership import load_membership
    from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table
    from nq.lab import runs as L

    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(G.CUT)] for t, df in corrected_universe().items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    assert max(df.index.max() for df in cut.values()) <= pd.Timestamp(G.CUT), "sealed data reached the engine"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    ev = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem, A = load_membership(), R94.grade_a_entries(P)
    nifty = L.load_nifty()
    nifty = nifty[nifty.index <= pd.Timestamp(G.CUT)]
    base_kw = dict(**LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS, demerger_events=ev)

    def run(a_set, unc, scale=None, event_log=None):
        led: list = []
        kw = dict(base_kw)
        if scale is not None:
            kw["entry_size_scale_by_week"] = scale
        out = R94.backtest(P, mem, ledger=led, start=G.START, uncapped=unc, a_grade=a_set, event_log=event_log, **kw)
        d = pd.DataFrame(led)
        d = d[(d.entry - d.stop0) / d.entry >= 0.005]                      # degenerate-stop rule (nq.lab.stats)
        return out, d

    # ---- per-signal features on the signal Friday -------------------------------------------------------------
    wk = {t: weekly(df) for t, df in cut.items()}
    sma40 = {t: s.rolling(40, min_periods=40).mean() for t, s in wk.items()}
    nwk = nifty.resample("W-FRI").last().dropna()
    tv = {t: (df["Close"] * df["Volume"]).rolling(63, min_periods=40).median().resample("W-FRI").last() for t, df in cut.items()}
    TV = pd.DataFrame(tv).sort_index()
    W = pd.DataFrame(wk).reindex(TV.index)
    S40 = pd.DataFrame(sma40).reindex(TV.index)
    fridays = TV.index[(TV.index >= pd.Timestamp("2018-06-01"))]
    breadth = {}
    for f in fridays:
        members = [t for t in TV.columns if ticker_in_index_on(t, f.date(), mem)]
        row = TV.loc[f, members].dropna().sort_values(ascending=False)
        mid = row.index[100:250]
        ok = [t for t in mid if pd.notna(S40.at[f, t]) and pd.notna(W.at[f, t])]
        breadth[f] = float(np.mean([W.at[f, t] > S40.at[f, t] for t in ok])) if len(ok) >= 30 else np.nan
    breadth = pd.Series(breadth)

    events = build_event_table(pd.read_parquet(EARNINGS_RAW_PATH))
    ev_by = {s: g for s, g in events.groupby("symbol")}

    def feats(t: str, idx: int) -> dict:
        d = pd.Timestamp(P[t]["dates"][idx])
        f = signal_friday(d)
        s, sm = wk[t], sma40[t]
        s_f = s[s.index <= f]
        below40 = bool(len(s_f) and pd.notna(sm.get(s_f.index[-1], np.nan)) and s_f.iloc[-1] < sm[s_f.index[-1]])
        n_f = nwk[nwk.index <= f]
        rs = np.nan
        if len(s_f) > 26 and len(n_f) > 26:
            rs = (s_f.iloc[-1] / s_f.iloc[-27] - 1) - (n_f.iloc[-1] / n_f.iloc[-27] - 1)
        b = breadth[breadth.index <= f]
        g = ev_by.get(t)
        res = False
        if g is not None:
            known = g[(g.ann_ts <= f + pd.Timedelta(hours=23, minutes=59)) & (g.event_date > f)
                      & (g.event_date <= f + pd.Timedelta(days=28))]
            res = len(known) > 0
        return {"entry_date": d.normalize(), "breadth": float(b.iloc[-1]) if len(b) else np.nan,
                "below40": below40, "rs6m": rs, "results4w": res}

    F = {(t, i): feats(t, i) for (t, i) in A}
    FILTERS = {
        "b1_midcap_breadth_lt_40": lambda x: pd.notna(x["breadth"]) and x["breadth"] < 0.40,
        "b2_below_own_40w": lambda x: x["below40"],
        "b3_weak_6m_rs": lambda x: pd.notna(x["rs6m"]) and x["rs6m"] < 0,
        "b4_results_within_4w": lambda x: x["results4w"],
    }

    # ---- live baseline ----------------------------------------------------------------------------------------
    evlog: list = []
    out_u, base_u = run(A, True, event_log=evlog)
    out_c, base_c = run(A, False)
    base_u = base_u.reset_index(drop=True)
    big = base_u[base_u.R >= BIG]
    sig_of = {}                                                             # (tkr, entry_date) -> (t, idx)
    for (t, i), x in F.items():
        sig_of[(t, x["entry_date"])] = (t, i)

    def capped_stats(out):
        st = G._curve_stats(out["curve"], G.START, G.CUT)
        return {"sharpe": round(st["sharpe"], 3), "maxdd_pct": round(st["maxdd_pct"], 1), "cagr_pct": round(out["cagr"] * 100, 1)}

    def book(d, extra=None):
        c = d[d.reason != "eos"]
        x = extra.reindex(d.index).fillna(0.0) if extra is not None else pd.Series(0.0, index=d.index)
        tot = d.R.sum() + x.sum()
        closed_R = c.R + x.loc[c.index]
        return {"n_closed": int(len(c)), "n_open_at_cut": int(len(d) - len(c)),
                "mean_R_closed": round(float(closed_R.mean()), 3), "total_R_incl_open": round(float(tot), 1),
                "win_pct_closed": round(float((c.R > 0).mean() * 100), 1), "worst_R_drawdown": round(r_drawdown(d, extra), 1)}

    res: dict = {"tier": "EXPLORE", "window": [G.START, G.CUT], "big_winner_def": f"uncapped live trade with R >= +{BIG}",
                 "live_big_winners": {"count": int(len(big)), "sum_R": round(float(big.R.sum()), 1)}, "arms": {}}
    res["arms"]["live"] = {"uncapped": book(base_u), "capped": capped_stats(out_c), "big_winners_skipped": 0}

    # ---- (b) entry filters ------------------------------------------------------------------------------------
    for name, fail in FILTERS.items():
        keep = {k for k in A if not fail(F[k])}
        o_u, d_u = run(keep, True)
        o_c, _ = run(keep, False)
        skipped = [r for r in big.itertuples() if (k := sig_of.get((r.tkr, pd.Timestamp(r.entry_date).normalize()))) and fail(F[k])]
        res["arms"][name] = {"uncapped": book(d_u), "capped": capped_stats(o_c),
                             "signals_removed": len(A) - len(keep), "signals_total": len(A),
                             "big_winners_skipped": len(skipped), "big_winner_R_skipped": round(float(sum(r.R for r in skipped)), 1)}
        print(name, res["arms"][name], flush=True)

    # ---- (c) half size below the Nifty 40-week SMA -------------------------------------------------------------
    keys = T.iso_weeks(pd.Timestamp(L.MIN_START), pd.Timestamp(L.CUT))
    s1 = T.s1_scale(nifty, nwk, keys)
    half = {k: (0.5 if v == 0.0 else 1.0) for k, v in s1.items()}
    o_c, _ = run(A, False, scale=half)
    wkey = lambda d: tuple(pd.Timestamp(d).isocalendar()[:2])
    sc = base_u.entry_date.map(lambda d: half.get(wkey(d), 1.0))
    weighted = base_u.copy()
    weighted["R"] = base_u.R * sc
    shrunk = big[sc.loc[big.index] < 1.0]
    res["arms"]["c_half_size_below_40w"] = {"uncapped_size_weighted": book(weighted), "capped": capped_stats(o_c),
                                            "share_of_entries_at_half": round(float((sc < 1).mean()), 3),
                                            "big_winners_skipped": 0, "big_winners_at_half_size": int(len(shrunk)),
                                            "big_winner_R_given_up": round(float((shrunk.R * 0.5).sum()), 1)}
    print("c_half_size_below_40w", res["arms"]["c_half_size_below_40w"], flush=True)

    # ---- (a) one extra unit at +1R on a Friday close -----------------------------------------------------------
    E = pd.DataFrame(evlog)
    parts = E[E.event_type == "partial_book"] if len(E) else E
    add_R = pd.Series(0.0, index=base_u.index)
    n_add = 0
    for i, r in base_u.iterrows():
        t, en, st0 = r.tkr, float(r.entry), float(r.stop0)
        risk = en - st0
        df = cut[t]
        lo, hi = pd.Timestamp(r.entry_date), pd.Timestamp(r.exit_date) if pd.notna(r.exit_date) else pd.Timestamp(G.CUT)
        w = df[(df.index >= lo) & (df.index < hi)]
        fri = w["Close"].groupby(w.index.to_period("W-FRI")).tail(1)
        hit = fri[fri >= en + risk]
        if not len(hit):
            continue
        after = df[df.index > hit.index[0]]
        if not len(after) or after.index[0] >= hi:
            continue
        add_d, add_px = after.index[0], float(after["Open"].iloc[0])
        add_risk = add_px - st0
        if add_risk <= 0:
            continue
        mine = parts[(parts.ticker == t) & (parts.entry_date == str(lo.date()))] if len(parts) else parts
        before = mine[pd.to_datetime(mine.event_date) < add_d] if len(mine) else mine
        later = mine[pd.to_datetime(mine.event_date) >= add_d] if len(mine) else mine
        rem_at_add = 1.0 - (before.fraction.sum() if len(before) else 0.0)
        if rem_at_add <= 1e-9:
            continue
        rr = 0.0
        for e in later.itertuples():
            rr += (e.fraction / rem_at_add) * (float(e.price) - add_px) / add_risk
        left = 1.0 - (later.fraction.sum() / rem_at_add if len(later) else 0.0)
        exit_px = float(r.exit_px) if pd.notna(r.get("exit_px")) else float(df["Close"].iloc[-1])
        rr += max(left, 0.0) * (exit_px - add_px) / add_risk
        add_R.loc[i] = rr                       # same rupee risk as the parent, so its R adds 1:1
        n_add += 1
    big_add = add_R.loc[big.index]
    res["arms"]["a_add_unit_at_1R"] = {"uncapped": book(base_u, add_R), "capped": "not measured (needs an engine lever)",
                                       "adds_taken": n_add, "add_unit_mean_R": round(float(add_R[add_R != 0].mean()), 3),
                                       "big_winners_skipped": 0, "add_R_on_big_winners": round(float(big_add.sum()), 1),
                                       "add_R_on_the_rest": round(float(add_R.drop(big.index).sum()), 1)}
    print("a_add_unit_at_1R", res["arms"]["a_add_unit_at_1R"], flush=True)

    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res["arms"]["live"]), res["live_big_winners"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
