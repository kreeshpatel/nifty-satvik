"""Engine-assumption measurement batch, 2026-10-20 (items #1, #3, #7, #8, #9, #10 of the model audit).

TIER 0/1 (docs/PROCESS_TIERS.md): zero-trial EXPLORE / MEASURE. No pre-registration, no screen-ledger row, no
change to n_trials. Nothing here edits a production path; the engine is driven read-only through
`nq.lab.runs` (LIVE configuration, PIT membership). The one monkey-patch (item #7 cost curve) rebinds a
module attribute in this process only and is never written back.

TRAIN ONLY: every price series is cut at 2024-06-30 by `nq.lab.runs.cut_universe` (which asserts it) before
the engine sees it; reported stats start 2019-01-01. The live forward record (entries >= 2026-07-04) is read
from results/brain/position_log.csv.gz, results/portfolio_history_weekly.csv and results/attribution_ledger.csv.

    python pipelines/diagnostics/diag_engine_assumptions_batch.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.lab import runs  # noqa: E402

CUT, START = runs.CUT, runs.MIN_START
EQ0 = 1_000_000.0
OUT = ROOT / "diagnostics" / "research" / "engine_assumptions" / "2026-10-20_batch.json"
LIVE_FORWARD_FROM = "2026-07-04"
CA_DROP = 0.15
CAP = 0.20


def _f(x):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, 6)


def cagr_sharpe(nav: pd.Series) -> tuple[float, float, float]:
    """The engine's own formulas (backtest(): calendar-year CAGR, daily Sharpe x sqrt(252))."""
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    cagr = (nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1
    r = nav.pct_change().dropna()
    sh = r.mean() / r.std() * np.sqrt(252)
    dd = (nav / nav.cummax() - 1).min()
    return float(cagr), float(sh), float(dd)


# ----------------------------------------------------------------------------------------------- sizing
def sizing_rows(pl: pd.DataFrame, prev_eq: pd.Series, entries: pd.DataFrame) -> pd.DataFrame:
    """One row per fill: entry notional / sizing equity (prior-session equity) and implied risk %.

    `entries` has (tkr, entry_date). Shares and the initial stop are read from the position log's first row."""
    rows = []
    for _, e in entries.iterrows():
        g = pl[(pl["tkr"] == e["tkr"]) & (pl["date"] == e["entry_date"])]
        if g.empty:
            continue
        g = g.iloc[0]
        eq = prev_eq.get(pd.Timestamp(e["entry_date"]), np.nan)
        notional = float(g["shares"]) * float(g["entry"])
        w = (float(g["entry"]) - float(g["stop"])) / float(g["entry"])
        rows.append(dict(tkr=e["tkr"], entry_date=pd.Timestamp(e["entry_date"]), notional=notional, sizing_eq=eq,
                         notional_pct=notional / eq, stop_width=w, implied_risk_pct=notional / eq * w))
    return pd.DataFrame(rows)


def sizing_summary(df: pd.DataFrame) -> dict:
    at_cap = (df["notional_pct"] - CAP).abs() <= 2e-4
    return {"n_fills": int(len(df)), "n_at_20pct_cap": int(at_cap.sum()),
            "share_at_cap": _f(at_cap.mean()),
            "notional_pct_min": _f(df["notional_pct"].min()), "notional_pct_median": _f(df["notional_pct"].median()),
            "notional_pct_max": _f(df["notional_pct"].max()),
            "stop_width_median": _f(df["stop_width"].median()), "stop_width_max": _f(df["stop_width"].max()),
            "implied_risk_pct_median": _f(df["implied_risk_pct"].median() * 100),
            "implied_risk_pct_min": _f(df["implied_risk_pct"].min() * 100),
            "implied_risk_pct_max": _f(df["implied_risk_pct"].max() * 100),
            "implied_risk_pct_mean": _f(df["implied_risk_pct"].mean() * 100),
            "share_risk_above_2pct": _f((df["implied_risk_pct"] > 0.02 + 1e-9).mean()),
            "share_stop_clamped_at_10pct": _f((df["stop_width"] >= 0.0999).mean())}


def seats(res: dict) -> dict:
    pl, nav = res["position_log"], res["nav"]
    cnt = pl.groupby("date")["tkr"].nunique().reindex(nav.index).fillna(0)
    return {"avg_seats_all_sessions": _f(cnt.mean()), "avg_seats_when_invested": _f(cnt[cnt > 0].mean()),
            "share_sessions_5plus": _f((cnt >= 5).mean()), "max_seats": int(cnt.max())}


def run_summary(res: dict) -> dict:
    nav = res["nav"]
    n_ret = int(len(nav) - 1)
    return {"label": res["manifest"]["label"], "differs_on": res["manifest"]["differs_on"],
            "membership": res["manifest"]["membership"], "config_hash": res["config_hash"][:12],
            "cagr": _f(res["cagr"]), "sharpe": _f(res["sharpe"]), "maxdd": _f(res["maxdd"]),
            "n_trades": int(res["n_trades"]), "n_returns": n_ret, "last_bar": res["last_bar"]}


def sizing_of(res: dict) -> pd.DataFrame:
    nav = res["nav"]
    prev = nav.shift(1)
    prev.iloc[0] = EQ0
    led = res["ledger"]
    return sizing_rows(res["position_log"], prev, led[["tkr", "entry_date"]])


# ----------------------------------------------------------------------------------------------- main
def main() -> int:
    R94, live, load_demerger_rows, corrected_universe = runs._engine()
    from nq.data.membership import load_membership
    out: dict = {"window": [START, CUT], "tier": "0/1 zero-trial", "items": {}}

    full = corrected_universe()
    cut = runs.cut_universe(full)
    last = runs.assert_within_cut(cut)
    out["last_bar_seen"] = str(last.date())

    # ---------------------------------------------------------------- base run (lab LIVE configuration)
    base = runs.replay()
    assert base["manifest"]["label"] == "LIVE BOOK", base["manifest"]
    out["base"] = run_summary(base)
    cg = cagr_sharpe(base["nav"])
    assert abs(cg[0] - base["cagr"]) < 1e-9, (cg, base["cagr"])
    led, ev, pl = base["ledger"], base["event_log"], base["position_log"]
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    led["exit_date"] = pd.to_datetime(led["exit_date"])

    # ================================================================ #1 SIZING FACT
    item1: dict = {}
    # (a) live forward record
    lpl = pd.read_csv(ROOT / "results" / "brain" / "position_log.csv.gz", parse_dates=["date"])
    lhist = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"]).set_index("date")["total_value"]
    prev = lhist.shift(1)
    prev.iloc[0] = EQ0
    lfirst = lpl.sort_values("date").groupby("tkr", as_index=False).first()[["tkr", "date"]].rename(columns={"date": "entry_date"})
    lfirst = lfirst[lfirst["entry_date"] >= pd.Timestamp(LIVE_FORWARD_FROM)]
    lrows = sizing_rows(lpl, prev, lfirst)
    item1["live_forward"] = {**sizing_summary(lrows), "source": "results/brain/position_log.csv.gz (first row per name) / "
                             "prior-session equity from results/portfolio_history_weekly.csv; first session uses EQ0 1,000,000",
                             "fills": [{"tkr": r.tkr, "entry_date": str(r.entry_date.date()), "notional_pct": _f(r.notional_pct),
                                        "stop_width_pct": _f(r.stop_width * 100), "implied_risk_pct": _f(r.implied_risk_pct * 100)}
                                       for r in lrows.itertuples()]}
    # cross-check against the attribution ledger's own position_size where present (book fills only)
    att = pd.read_csv(ROOT / "results" / "attribution_ledger.csv")
    att = att[att["position_size"].notna() & (pd.to_datetime(att["bought_date"]) >= pd.Timestamp(LIVE_FORWARD_FROM))]
    item1["live_forward"]["attribution_position_size_check"] = [
        {"tkr": r.ticker, "bought": r.bought_date, "position_size": _f(r.position_size),
         "pct_of_prior_equity": _f(r.position_size / prev.get(pd.Timestamp(r.bought_date), np.nan))} for r in att.itertuples()]
    # (b) train replay base run
    brows = sizing_of(base)
    lc = lpl.groupby("date")["tkr"].nunique()
    item1["live_forward"]["seats"] = {"avg_names_held": _f(lc.mean()), "max": int(lc.max()), "n_sessions": int(len(lc))}
    item1["train_base"] = {**sizing_summary(brows), "source": "nq.lab.runs.replay() default, ledger entries x position_log first row / prior-session NAV"}

    # (c) EXPLORATORY grid
    grid = []
    for mn in (0.15, 0.20, 0.25, 0.33):
        for mr in (0.10, 0.15):
            res = runs.replay({"max_notional_pct": mn, "max_risk_pct": mr})
            grid.append({"max_notional_pct": mn, "max_risk_pct": mr, "_res": res})
    n_meter = runs.n_configs_tried()
    for g in grid:
        res = g.pop("_res")
        s = run_summary(res)
        dsr = runs.deflated_sharpe(res["sharpe"], s["n_returns"], n_meter)
        srows = sizing_of(res)
        g.update(s)
        g.update({"deflated_sharpe": _f(dsr["deflated_sharpe"]), "dsr_prob": _f(dsr["dsr"]), "sr0_annual": _f(dsr["sr0_annual"]),
                  "meter_n_trials": int(n_meter), **seats(res),
                  "share_fills_at_notional_cap": _f(((srows["notional_pct"] - g["max_notional_pct"]).abs() <= 2e-4).mean()),
                  "mean_implied_risk_pct": _f(srows["implied_risk_pct"].mean() * 100),
                  "median_notional_pct": _f(srows["notional_pct"].median())})
    item1["grid_EXPLORATORY_not_decision_grade"] = grid
    sh = [g["sharpe"] for g in grid]
    item1["grid_sharpe_range"] = [min(sh), max(sh)]
    item1["base_seats"] = seats(base)
    out["items"]["1_sizing"] = item1

    # ================================================================ shared engine inputs (items 3, 7, 8, 9, 10)
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    events = R94.build_demerger_events(cut, load_demerger_rows(), **live["LIVE_PREP"])
    mem = load_membership()

    # ================================================================ #7 COSTS
    item7: dict = {}
    pos0 = pl.sort_values("date").groupby(["tkr", "date"], as_index=False).first()
    trades = []
    for r in led.itertuples():
        fr = pos0[(pos0["tkr"] == r.tkr) & (pos0["date"] == r.entry_date)]
        sh0 = float(fr["shares"].iloc[0])
        tid = f"{r.tkr}:{r.entry_date.date()}"
        e = ev[ev["trade_id"] == tid]
        sells = [(pd.Timestamp(x.event_date), sh0 * float(x.fraction), float(x.price)) for x in e.itertuples()]
        sh_final = float(e["shares_after"].iloc[-1]) if len(e) else sh0
        trades.append(dict(tkr=r.tkr, entry_date=r.entry_date, exit_date=r.exit_date, reason=r.reason, sh0=sh0,
                           entry=float(r.entry), exit_px=float(r.exit_px), stop0=float(r.stop0), sells=sells,
                           sh_final=sh_final, eos=(r.reason == "eos")))
    nav = base["nav"]

    def adj_nav(extra: dict) -> pd.Series:
        s = pd.Series(extra, dtype=float).sort_index()
        if s.empty:
            return nav
        idx = nav.index.searchsorted(s.index)
        idx = np.clip(idx, 0, len(nav) - 1)
        step = pd.Series(0.0, index=nav.index)
        for i, v in zip(idx, s.values):
            step.iloc[i] += v
        return nav - step.cumsum()

    stamp, dp = defaultdict(float), defaultdict(float)
    stamp_tot = dp_tot = 0.0
    n_dp = 0
    for t in trades:
        s = 0.00015 * t["sh0"] * t["entry"]
        stamp[t["entry_date"]] += s; stamp_tot += s
        dates = {d for d, _, _ in t["sells"]}
        if not t["eos"]:
            dates.add(t["exit_date"])
        for d in dates:
            dp[d] += 15.93; dp_tot += 15.93; n_dp += 1
    ii_extra = defaultdict(float)
    for d, v in stamp.items():
        ii_extra[d] += v
    for d, v in dp.items():
        ii_extra[d] += v
    nav_ii = adj_nav(ii_extra)
    c0 = cagr_sharpe(nav)
    c2 = cagr_sharpe(nav_ii)
    item7["i_current_model"] = {"cagr": _f(c0[0]), "sharpe": _f(c0[1]), "maxdd": _f(c0[2]), "net_pnl_sum": _f(led["net_pnl"].sum())}
    item7["ii_stamp_plus_dp"] = {"stamp_duty_rupees": _f(stamp_tot), "dp_charges_rupees": _f(dp_tot), "n_dp_sell_scrip_days": int(n_dp),
                                 "cagr": _f(c2[0]), "sharpe": _f(c2[1]), "maxdd": _f(c2[2]),
                                 "delta_cagr_bp": _f((c2[0] - c0[0]) * 1e4), "delta_sharpe": _f(c2[1] - c0[1]),
                                 "method": "first-order: rupee charge subtracted from NAV on its date, no path re-sizing"}
    # (iii) gap: does the engine fill stop exits at the next OPEN (gap already inside the fill)?
    stops = [t for t in trades if t["reason"] in ("stop", "stop_part")]
    item7["iii_gap_slippage"] = {
        "engine_fill_rule": "weekly close <= stop queues ('pending'), filled at the NEXT SESSION OPEN (run_bhanushali_weekly_rank.py pending branch, px = s['o'][i])",
        "gap_already_in_fill": True, "extra_cost_for_gap_itself": 0,
        "residual_not_modelled": "ADV-tier slippage is the same bp on a stop exit as on any exit; no extra impact for forced selling into a gap"}
    sens = {}
    for bp in (25, 50, 100, 200):
        ex = defaultdict(float)
        for t in stops:
            ex[t["exit_date"]] += t["sh_final"] * t["exit_px"] * bp / 1e4
        n_ = adj_nav(ex)
        c = cagr_sharpe(n_)
        sens[str(bp)] = {"rupees": _f(sum(ex.values())), "delta_cagr_bp": _f((c[0] - c0[0]) * 1e4), "sharpe": _f(c[1])}
    item7["iii_gap_slippage"]["extra_bp_on_stop_exits_only_sensitivity"] = sens
    item7["iii_gap_slippage"]["n_stop_exits"] = len(stops)
    # break-even curve: extra bp per side, FULL engine re-run with the cost patched (both legs)
    orig = R94._cost_leg
    curve = []
    try:
        for bp in (0, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300):
            add = bp / 1e4
            R94._cost_leg = (lambda adv, notional, cost_off=False, _o=orig, _a=add: _o(adv, notional, cost_off) + (0.0 if cost_off else _a))
            with tempfile.TemporaryDirectory() as td:
                r = runs.replay(use_cache=False, cache_dir=Path(td), runs_path=Path(td) / "runs.jsonl")
            curve.append({"extra_bp_per_side": bp, "cagr": _f(r["cagr"]), "sharpe": _f(r["sharpe"]), "maxdd": _f(r["maxdd"]),
                          "n_trades": r["n_trades"], "manifest_label_unpatched_config": r["manifest"]["label"]})
    finally:
        R94._cost_leg = orig
    assert curve[0]["cagr"] == out["base"]["cagr"], "bp=0 patched run must equal the base run"
    item7["extra_bp_curve"] = curve
    xs = [c["extra_bp_per_side"] for c in curve]
    cs = [c["cagr"] for c in curve]

    def cross(level):
        for k in range(1, len(xs)):
            if cs[k - 1] > level >= cs[k]:
                return xs[k - 1] + (cs[k - 1] - level) / (cs[k - 1] - cs[k]) * (xs[k] - xs[k - 1])
        return None
    item7["breakeven_bp_per_side"] = {"cagr_halves": _f(cross(cs[0] / 2)), "cagr_zero": _f(cross(0.0)),
                                      "note": "extra bp added to EVERY leg (buy and each sell) on top of brokerage+STT+tiered slippage; linearly interpolated"}
    # fixed-path (first-order) curve: same 77 trades, extra bp on every leg notional deducted from NAV on its date.
    legs = defaultdict(float)
    for t in trades:
        legs[t["entry_date"]] += t["sh0"] * t["entry"]
        for d, shs, px in t["sells"]:
            legs[d] += shs * px
        if not t["eos"]:
            legs[t["exit_date"]] += t["sh_final"] * t["exit_px"]
    fp = []
    for bp in (0, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000):
        n_ = adj_nav({d: v * bp / 1e4 for d, v in legs.items()})
        c = cagr_sharpe(n_)
        fp.append({"extra_bp_per_side": bp, "cagr": _f(c[0]), "sharpe": _f(c[1]), "maxdd": _f(c[2])})
    item7["extra_bp_curve_fixed_path"] = fp
    fx, fc = [r["extra_bp_per_side"] for r in fp], [r["cagr"] for r in fp]

    def cross_fp(level):
        for k in range(1, len(fx)):
            if fc[k - 1] > level >= fc[k]:
                return fx[k - 1] + (fc[k - 1] - level) / (fc[k - 1] - fc[k]) * (fx[k] - fx[k - 1])
        return None
    item7["breakeven_bp_per_side_fixed_path"] = {"cagr_halves": _f(cross_fp(fc[0] / 2)), "cagr_zero": _f(cross_fp(0.0)),
                                                 "total_leg_notional_rupees": _f(sum(legs.values())),
                                                 "method": "first-order, trade set and sizing frozen at the base run; no re-selection under cash contention"}
    item7["rerun_curve_path_noise_sharpe_range_0_to_100bp"] = [min(c["sharpe"] for c in curve if c["extra_bp_per_side"] <= 100),
                                                               max(c["sharpe"] for c in curve if c["extra_bp_per_side"] <= 100)]
    cur_bp = {"modelled_round_trip_bp_floor": 2 * (3 + 10 + 5)}
    item7["context"] = cur_bp
    out["items"]["7_costs"] = item7

    # ================================================================ #3 GAP EXITS
    item3: dict = {}
    sx = led[led["reason"].isin(["stop", "stop_part"])].copy()
    sx["risk0"] = sx["entry"] - sx["stop0"]
    sx["beyond_r"] = (sx["stop0"] - sx["exit_px"]) / sx["risk0"]
    thru = sx[sx["exit_px"] < sx["stop0"]]
    item3["train"] = {"n_stop_exits": int(len(sx)), "n_filled_through": int(len(thru)), "share_through": _f(len(thru) / len(sx)),
                      "beyond_r_mean_through": _f(thru["beyond_r"].mean()), "beyond_r_median_through": _f(thru["beyond_r"].median()),
                      "beyond_r_p90_through": _f(thru["beyond_r"].quantile(0.9)), "beyond_r_max": _f(thru["beyond_r"].max()),
                      "beyond_r_mean_all_stop_exits": _f(sx["beyond_r"].clip(lower=0).mean()),
                      "n_gt_0p5R": int((thru["beyond_r"] > 0.5).sum()), "n_gt_1R": int((thru["beyond_r"] > 1.0).sum()),
                      "mean_R_of_stop_exits": _f(sx["R"].mean()), "n_all_trades": int(len(led)),
                      "basis": "per-unit price: (stop0 - exit_px)/(entry - stop0); live scaled exit has no ratchet so stop0 is the stop"}
    aa = pd.read_csv(ROOT / "results" / "attribution_ledger.csv")
    aa = aa[(pd.to_datetime(aa["bought_date"]) >= pd.Timestamp(LIVE_FORWARD_FROM)) & aa["exit_reason"].isin(["stop"]) ]
    athru = aa[aa["gap_through"] == True]  # noqa: E712
    item3["live_cards"] = {"n_stop_exits": int(len(aa)), "n_gap_through": int(len(athru)),
                           "share_through": _f(len(athru) / len(aa)) if len(aa) else None,
                           "beyond_stop_r_mean_through": _f(athru["beyond_stop_r"].mean()),
                           "beyond_stop_r_median_through": _f(athru["beyond_stop_r"].median()),
                           "beyond_stop_r_min": _f(aa["beyond_stop_r"].min()),
                           "basis": "results/attribution_ledger.csv (card-level reconstruction of every Grade-A signal, forward from 2026-07-04; "
                                    "gap_through / beyond_stop_r as the ledger defines them, beyond_stop_r is negative)"}
    book = pd.read_csv(ROOT / "results" / "attribution_ledger.csv")
    book = book[book["ticker"].isin(set(lpl["tkr"])) & (pd.to_datetime(book["bought_date"]) >= pd.Timestamp(LIVE_FORWARD_FROM))
                & (book["exit_reason"] == "stop")]
    item3["live_book_names"] = {"n_stop_exits": int(len(book)), "n_gap_through": int((book["gap_through"] == True).sum()),  # noqa: E712
                                "beyond_stop_r": {r.ticker: _f(r.beyond_stop_r) for r in book.itertuples()},
                                "basis": "attribution_ledger rows for the names in results/brain/position_log.csv.gz"}
    out["items"]["3_gap_exits"] = item3

    # ================================================================ #10 FREEZE
    item10: dict = {}
    reg = pd.read_csv(ROOT / "data" / "corporate_actions_demerger_register.csv", comment="#", encoding_errors="replace")
    reg_keys = {(str(r.ticker), str(r.ex_date)[:10]) for r in reg.itertuples()}
    trig, held_sessions = [], 0
    for t in trades:
        s = P.get(t["tkr"])
        if s is None:
            continue
        dts = list(pd.DatetimeIndex(s["dates"]))
        ix = {d: k for k, d in enumerate(dts)}
        i0, i1 = ix.get(t["entry_date"]), ix.get(t["exit_date"])
        if i0 is None or i1 is None:
            continue
        for i in range(i0 + 1, i1 + 1):
            held_sessions += 1
            prev_c = float(s["c"][i - 1])
            if prev_c <= 0:
                continue
            mo, mc = float(s["o"][i]) / prev_c - 1, float(s["c"][i]) / prev_c - 1
            if mo <= -CA_DROP or mc <= -CA_DROP:
                d = dts[i]
                registered = (t["tkr"], str(d.date())) in reg_keys or (t["tkr"] in events and d >= events[t["tkr"]]["ex_date"] and
                                                                      t["entry_date"] < events[t["tkr"]]["ex_date"] and
                                                                      d == events[t["tkr"]]["ex_date"])
                booked_exit = (d == t["exit_date"]) and not t["eos"]
                booked_tr = any(sd == d for sd, _, _ in t["sells"])
                leg = "open" if mo <= -CA_DROP else "close"
                # engine order: the OPEN gap is checked BEFORE a pending fill (so a freeze blocks that fill); the CLOSE move
                # is checked AFTER the day's fills (so an exit filled at the open that session was already booked).
                later_exit = (not booked_exit) and (not t["eos"]) and i < i1 and (i1 - i) <= 3
                trig.append(dict(tkr=t["tkr"], date=str(d.date()), leg=leg,
                                 exit_blocked_by_freeze=bool((leg == "open" and booked_exit) or (leg == "close" and later_exit)),
                                 exit_booked_before_freeze=bool(leg == "close" and booked_exit),
                                 open_move=_f(mo), close_move=_f(mc), registered_in_demerger_register=bool(registered),
                                 exit_fill_that_session=bool(booked_exit), exit_reason=t["reason"] if booked_exit else None,
                                 tranche_fill_that_session=bool(booked_tr)))
    tdf = pd.DataFrame(trig)
    yrs = (pd.Timestamp(CUT) - pd.Timestamp(START)).days / 365.25
    if len(tdf):
        tdf["booked"] = tdf["exit_fill_that_session"] | tdf["tranche_fill_that_session"]
    item10 = {"held_sessions_checked": int(held_sessions), "n_trades": len(trades),
              "n_trigger_sessions": int(len(tdf)),
              "n_unregistered_would_freeze": int((~tdf["registered_in_demerger_register"]).sum()) if len(tdf) else 0,
              "n_registered_in_demerger_register": int(tdf["registered_in_demerger_register"].sum()) if len(tdf) else 0,
              "n_booked_exit_that_session": int(tdf["exit_fill_that_session"].sum()) if len(tdf) else 0,
              "n_booked_tranche_that_session": int(tdf["tranche_fill_that_session"].sum()) if len(tdf) else 0,
              "n_endured_unbooked": int((~tdf["booked"]).sum()) if len(tdf) else 0,
              "n_exit_blocked_by_freeze_(frozen_not_booked)": int(tdf["exit_blocked_by_freeze"].sum()) if len(tdf) else 0,
              "n_exit_booked_before_freeze_(close-leg_after_open_fill)": int(tdf["exit_booked_before_freeze"].sum()) if len(tdf) else 0,
              "per_year": _f(len(tdf) / yrs), "events": trig,
              "reading_basis": "open or close <= -15% vs prior close on a session AFTER entry and up to and including the exit session; "
                               "R94.CA_HOLD_DROP semantics; registered = in data/corporate_actions_demerger_register.csv"}
    out["items"]["10_freeze"] = item10

    # ================================================================ #9 ENTRY WINDOW
    a_set = R94.grade_a_entries(P)
    cls = defaultdict(int)
    first_wd = defaultdict(int)
    elig = []
    for (t, e0) in sorted(a_set, key=lambda x: (x[0], x[1])):
        s = P[t]
        dts = pd.DatetimeIndex(s["dates"])
        d0 = dts[e0]
        if d0 < pd.Timestamp(START):
            continue
        cls["A_signals_total"] += 1
        if not R94.ticker_in_index_on(t, d0.date(), mem):
            cls["refused_not_member_at_activation"] += 1
            continue
        cls["activated"] += 1
        edays, lo, hi, _rk, sma, _org = s["entry_win"][e0]
        if not hi > lo:
            cls["no_fill_degenerate_band"] += 1
            continue
        opens = [float(s["o"][i]) for i in edays]
        inb = [(lo < o < hi) for o in opens]
        okcap = [(o <= sma * 1.20) for o in opens]
        fill_k = next((k for k, (a, b) in enumerate(zip(inb, okcap)) if a and b), None)
        if fill_k is not None:
            cls["fill_eligible"] += 1
            d_ = dts[edays[fill_k]]
            first_wd[d_.day_name()] += 1
            cls["eligible_first_day_k%d" % fill_k] += 1
            elig.append((t, d_))
        elif not any(inb):
            if all(o >= hi for o in opens):
                cls["no_fill_all_opens_above_band(gap-up)"] += 1
            elif all(o <= lo for o in opens):
                cls["no_fill_all_opens_below_band"] += 1
            else:
                cls["no_fill_opens_straddle_band_never_inside"] += 1
        else:
            cls["no_fill_in_band_but_over_ext_cap"] += 1
    ucfg = {"uncapped": True}
    ures = runs.replay(ucfg)
    uled = ures["ledger"]
    uled["entry_date"] = pd.to_datetime(uled["entry_date"])
    held_u = defaultdict(list)
    for r in uled.itertuples():
        held_u[r.tkr].append((r.entry_date, r.exit_date))
    held_c = defaultdict(list)
    for r in led.itertuples():
        held_c[r.tkr].append((r.entry_date, r.exit_date))
    uset = {(r.tkr, r.entry_date) for r in uled.itertuples()}
    cset = {(r.tkr, r.entry_date) for r in led.itertuples()}
    rec = defaultdict(int)
    for t, d_ in elig:
        in_u = (t, d_) in uset
        in_c = (t, d_) in cset
        held_in_u = any(a <= d_ <= b for a, b in held_u[t])
        held_in_c = any(a <= d_ <= b for a, b in held_c[t])
        rec["eligible"] += 1
        rec["uncapped_fills_it"] += in_u
        rec["uncapped_not_filled_ticker_already_held"] += (not in_u) and held_in_u
        rec["uncapped_not_filled_other"] += (not in_u) and not held_in_u
        rec["capped_fills_it"] += in_c
        rec["capped_not_filled_ticker_already_held"] += (not in_c) and held_in_c
        rec["capped_not_filled_other_cash_or_same_day_priority"] += (not in_c) and not held_in_c
    item9 = {"reconciliation_eligible_vs_fills": dict(rec), "census": dict(cls), "eligible_first_fill_weekday_census": dict(first_wd),
             "uncapped_lab_run": {**run_summary(ures), "n_fills": int(len(uled)),
                                  "fill_weekday": uled["entry_date"].dt.day_name().value_counts().to_dict()},
             "capped_base_fill_weekday": led["entry_date"].dt.day_name().value_counts().to_dict(),
             "capped_base_n_fills": int(len(led)),
             "cash_or_occupancy_blocked_eligible": int(cls["fill_eligible"] - len(led)),
             "live_book_fill_weekday": lfirst["entry_date"].dt.day_name().value_counts().to_dict()}
    n_act = cls["activated"]
    item9["shares_of_activated"] = {k: _f(v / n_act) for k, v in cls.items() if k.startswith(("fill_elig", "no_fill"))}
    out["items"]["9_entry_window"] = item9

    # ================================================================ #8 RESEARCH vs LIVE DATA
    item8: dict = {}
    from nq.data.ohlcv import load_ohlcv_cache
    plain_full = runs.cut_universe(dict(load_ohlcv_cache()))
    only_corr = sorted(set(cut) - set(plain_full))
    Pp = R94.prep_weekly_rank(plain_full, **live["LIVE_PREP"])

    def by_week(PP, member_gate: bool):
        a = R94.grade_a_entries(PP)
        w = defaultdict(set)
        for t, e0 in a:
            d0 = pd.Timestamp(PP[t]["dates"][e0])
            if d0 < pd.Timestamp(START) or d0 > pd.Timestamp(CUT):
                continue
            if member_gate and not R94.ticker_in_index_on(t, d0.date(), mem):
                continue
            iso = d0.isocalendar()
            w[(int(iso.year), int(iso.week))].add(t)
        return w
    for gate in (False, True):
        wc, wp = by_week(P, gate), by_week(Pp, gate)
        weeks = sorted(set(wc) | set(wp))
        diff = [k for k in weeks if wc.get(k, set()) != wp.get(k, set())]
        sym = [len(wc.get(k, set()) ^ wp.get(k, set())) for k in diff]
        only_c = [k for k in diff if any(x in set(only_corr) for x in (wc.get(k, set()) ^ wp.get(k, set())))]
        item8["membership_gated_top5" if gate else "raw_top5"] = {
            "weeks_with_any_A": len(weeks), "weeks_differ": len(diff), "share_differ": _f(len(diff) / len(weeks)),
            "mean_sym_diff_names_in_differing_weeks": _f(np.mean(sym) if sym else 0.0),
            "differing_weeks_symdiff_contains_corrected_only_name": len(only_c),
            "differing_weeks_symdiff_only_shared_names_(displacement)": len(diff) - len(only_c)}
    item8["universe"] = {"names_corrected": len(cut), "names_plain_pinned": len(plain_full), "names_only_in_corrected": len(only_corr)}
    from nq.data.ohlcv import OHLCV_CACHE, file_sha256
    item8["plain_cache_sha256_prefix"] = file_sha256(OHLCV_CACHE)[:8]
    item8["limits"] = ("Both sides read the same local data/ohlcv.pkl; the 'live' refreshed yfinance cache (25-day top-up, price-vintage drift, "
                       "Nifty-50 refresh) is not available here. This measures the survivor-only pinned universe vs corrected_universe(), "
                       "i.e. the universe/backfill/alias leg of the research-vs-live gap, not price-vintage drift.")
    out["items"]["8_research_vs_plain_cache"] = item8

    # ---------------------------------------------------------------- standing counts + meter
    nt = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    out["standing_counts"] = {"n_trials": nt["cumulative_n_trials"], "family_level_count": nt["family_level_count"],
                              "lab_meter_distinct_configs_in_this_worktree": runs.n_configs_tried()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
