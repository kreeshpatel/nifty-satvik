"""EXPLORATORY (tier 0) — pre-extension breakouts as their OWN capital sleeve, live exit, PIT membership.

No pre-registration, no screen row, no n_trials change. Nothing here edits the engine or a production
path. Differences from the STAGE4 sleeve script (`scripts/diag_sleeves.py`), which this reuses in
mechanism (a copy of P whose entry windows are filtered to a set of setup origins, one engine run per
sleeve, equity curves summed):
  * live exit (config P scaled exit) + live discipline + live staleness + LIVE_PREP, via
    `nq.lab.runs.engine_kwargs(DEFAULT_CONFIG)` — STAGE4 used the OLD P2 exit, no grade gate, no CUT;
  * PIT membership (`load_membership()`) — STAGE4 also did, so that is NOT a difference;
  * prices CUT at 2024-06-30 and asserted before the engine sees them; window 2019-01-01..2024-06-30.

Sleeve spec. Grade-A gate is applied INSIDE each sleeve (top-5 by CRS distance per setup week among that
sleeve's own signals) exactly as the live gate does for touch. "Seat cap" N = `max_positions=N`, all
other sizing exactly live (2% risk, 10% max stop, 20% max notional); NOT a re-spread of notional.
Capital splits are fixed at t0 and never rebalanced (equity curves summed).

    python pipelines/diagnostics/explore_breakout_sleeve_20261020.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.lab import runs  # noqa: E402
from pipelines.diagnostics.explore_hedge_overlay_20261020 import stats, sub_stats  # noqa: E402

START, CUT = runs.MIN_START, runs.CUT
SUBPERIODS = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
EQ = 1_000_000.0
NAMES = {0: "touch44", 1: "box", 3: "sr_pivot", 6: "cup_handle", 8: "double_bottom"}
OUT = ROOT / "diagnostics" / "research" / "explore" / "breakout_sleeve_20261020.json"


def filter_P(P, origins):
    """diag_sleeves.filter_P: shallow copy of P whose entry_win keeps only the given origins."""
    keep = set(origins)
    out = {}
    for t, s in P.items():
        s2 = dict(s)
        s2["entry_win"] = {k: v for k, v in s["entry_win"].items() if v[5] in keep}
        out[t] = s2
    return out


def coverage(P, mem, R94):
    from nq.data.membership import ticker_in_index_on
    rows = []
    A = {o: R94.grade_a_entries(filter_P(P, (o,))) for o in NAMES}
    for t, s in P.items():
        for i, (days, lo, hi, rk, sma, org) in s["entry_win"].items():
            d = pd.Timestamp(s["dates"][i])
            if not (pd.Timestamp(START) <= d <= pd.Timestamp(CUT)):
                continue
            opn = float(s["o"][i])
            rows.append(dict(t=t, org=org, yr=d.year, member=ticker_in_index_on(t, d.date(), mem),
                             inrange=bool(lo < opn < hi), gradeA=(t, i) in A[org], ext=opn / sma - 1 if sma and sma == sma else np.nan))
    df = pd.DataFrame(rows)
    out = {}
    yrs = (pd.Timestamp(CUT) - pd.Timestamp(START)).days / 365.25
    for org, g in df.groupby("org"):
        m = g[g.member]
        f = m[m.inrange]
        out[NAMES.get(org, str(org))] = {
            "signals_total": int(len(g)), "per_year_all": round(len(g) / yrs, 1),
            "per_year_by_calendar_year": {int(k): int(v) for k, v in g.groupby("yr").size().items()},
            "members": int(len(m)), "member_inrange_fillable": int(len(f)),
            "fillable_per_year": round(len(f) / yrs, 1),
            "share_ext_lt10_of_fillable": float((f.ext < 0.10).mean()) if len(f) else None,
            "share_ext_lt20_of_fillable": float((f.ext < 0.20).mean()) if len(f) else None,
            "share_ext_lt10_of_all": float((g.ext < 0.10).mean()),
            "gradeA_fillable_per_year": round(float(f.gradeA.sum()) / yrs, 1),
            "gradeA_fillable_ext_lt10_per_year": round(float((f.gradeA & (f.ext < 0.10)).sum()) / yrs, 1),
            "median_ext_fillable": float(f.ext.median()) if len(f) else None,
            "fillable_ext_lt10_per_year": round(float((f.ext < 0.10).sum()) / yrs, 1)}
    return out


def main() -> None:
    R94, live, load_demerger_rows, corrected_universe = runs._engine()
    from nq.data.membership import load_membership
    cut = runs.cut_universe(corrected_universe())
    last = runs.assert_within_cut(cut)
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"], box_breakout=True, sr_pivot=True, zoo_origins=(6, 8))
    events = R94.build_demerger_events(cut, load_demerger_rows(), **live["LIVE_PREP"])
    mem = load_membership()
    kw = runs.engine_kwargs(runs.DEFAULT_CONFIG)
    man = runs._manifest(runs.normalize_config(runs.DEFAULT_CONFIG), str(last.date()))
    assert man["is_live_book"] and man["membership"] == "pit"
    cov = coverage(P, mem, R94)

    def sleeve(origins, *, eq0=EQ, seats=0, ext_cap=None):
        Pf = filter_P(P, origins)
        k = dict(kw)
        if ext_cap is not None:
            k["ext_cap"] = ext_cap
        led = []
        o = R94.backtest(Pf, mem, ledger=led, a_grade=R94.grade_a_entries(Pf), eq0=eq0,
                         max_positions=seats, **k, demerger_events=events)
        nav = pd.Series(o["curve"], dtype=float)
        nav.index = pd.DatetimeIndex(nav.index).normalize()
        nav = nav[~nav.index.duplicated(keep="last")].sort_index()
        nav = nav[nav.index >= pd.Timestamp(START)]
        assert nav.index.max() <= pd.Timestamp(CUT)
        return nav, pd.DataFrame(led)

    # parity: the filtered-touch control at Rs10L must reproduce the lab's live replay
    ref = runs.replay(cache_dir=ROOT / "lab_cache")["nav"]
    sp = {}
    navs = {}
    ledgers = {}
    SPECS = {
        "T_touch": dict(origins=(0,)),
        "S_shared_touch+box+sr_5seat": dict(origins=(0, 1, 3)),
        "B13_seat5": dict(origins=(1, 3), seats=5), "B13_seat8": dict(origins=(1, 3), seats=8),
        "B1368_seat5": dict(origins=(1, 3, 6, 8), seats=5), "B1368_seat8": dict(origins=(1, 3, 6, 8), seats=8),
        "B13_ext10_seat5": dict(origins=(1, 3), seats=5, ext_cap=0.10),
        "B13_ext10_seat8": dict(origins=(1, 3), seats=8, ext_cap=0.10),
    }
    for name, sp_ in SPECS.items():
        navs[name], ledgers[name] = sleeve(**sp_)
        print(name, "done", len(ledgers[name]), "trades", flush=True)
    assert np.allclose(navs["T_touch"].values, ref.values, rtol=1e-9), "filtered touch != live replay"

    breakouts = [k for k in SPECS if k.startswith("B")]
    splits = {"60/40": 0.60, "50/50": 0.50}
    n_tr = len(SPECS) + len(breakouts) * len(splits)
    res = {"label": "EXPLORATORY — tier 0, train window 2019-01-01..2024-06-30, not evidence",
           "manifest": man, "last_bar": str(last.date()), "n_deflation_trials": n_tr,
           "program_counts": {"screens": 23, "sealed_opens": 3, "n_trials": 2},
           "seat_cap_definition": "max_positions=N; sizing otherwise exactly live",
           "touch_parity_vs_lab_replay": "byte-identical NAV", "coverage": cov, "sleeves": {}, "combos": {}}

    def rec(r: pd.Series, extra=None):
        d = {**stats(r, n_tr), "sub": {k: sub_stats(r, *v) for k, v in SUBPERIODS.items()}}
        d.update(extra or {})
        return d

    rT = navs["T_touch"].pct_change().dropna()
    for name, nav in navs.items():
        r = nav.pct_change().dropna()
        led = ledgers[name]
        closed = led[led["reason"] != "eos"] if len(led) else led
        ex = {"n_trades": int(len(led)), "mean_R_closed": float(closed["R"].mean()) if len(closed) else None,
              "origin_mix": {NAMES.get(int(k), str(k)): int(v) for k, v in
                             led["origin"].value_counts().items()} if "origin" in led else None,
              "median_stop_width_pct": float(((led["entry"] - led["stop0"]) / led["entry"]).median() * 100),
              "min_stop_width_pct": float(((led["entry"] - led["stop0"]) / led["entry"]).min() * 100),
              "top2_pnl_share_of_gross_gain": float(led["net_pnl"].nlargest(2).sum()
                                                   / led.loc[led["net_pnl"] > 0, "net_pnl"].sum()),
              "top2_trades": [f"{r.tkr} {str(r.entry_date)[:10]} pnl {r.net_pnl:,.0f} R {r.R:.1f}"
                              for r in led.nlargest(2, "net_pnl").itertuples()],
              "corr_daily_with_touch": float(r.corr(rT)) if name != "T_touch" else None}
        res["sleeves"][name] = rec(r, ex)
    for b in breakouts:
        for lab, wt in splits.items():
            tot = navs["T_touch"] / EQ * (EQ * wt) + navs[b] / EQ * (EQ * (1 - wt))
            r = tot.pct_change().dropna()
            res["combos"][f"{lab}|{b}"] = rec(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    for k, v in cov.items():
        print(f"COV {k:14s} all/yr {v['per_year_all']:6.1f}  fillable/yr {v['fillable_per_year']:5.1f}  "
              f"gradeA/yr {v['gradeA_fillable_per_year']} (ext<10: {v['gradeA_fillable_ext_lt10_per_year']}) "
              f"ext<10 of fillable {v['share_ext_lt10_of_fillable']} ; <20 {v['share_ext_lt20_of_fillable']}")
    for k, v in {**res["sleeves"], **res["combos"]}.items():
        print(f"{k:40s} Sh {v['sharpe']:.3f} (defl {v['sharpe_deflated']:.3f}) CAGR {v['cagr']*100:5.1f}% "
              f"DD {v['maxdd']*100:6.1f}% Cal {v['calmar']:.2f} worst {v['worst_year']*100:6.1f}% | "
              f"{v['sub']['2019-21']['sharpe']:.2f}/{v['sub']['2022-24H1']['sharpe']:.2f}"
              + (f" tr={v['n_trades']} corr={v['corr_daily_with_touch']}" if "n_trades" in v else ""))


if __name__ == "__main__":
    main()
