"""MEASUREMENT: after-tax efficient frontier (vol target 6-20%, four designs, two real cash legs, static index/cash
mixes), the vol-target tax layer (index 11% vs static 65/35), and the mission's rolling 3-year after-tax test.

Owner request 2026-11-19 ("prompt 3"). Method and pass rules: diagnostics/research/explore/2026-11-19_after_tax_frontier.md
(committed before any result). Analysis only: no rule, trial, sealed read or live change.

SIMULATOR  explore_blend_cost_tax.LBook (= explore_after_tax_comparison.Book + logs), imported unchanged. FBook adds one
           instrument, the ARBITRAGE fund: equity tax (STCG/LTCG by lot age), mutual-fund cost rates. Tax arithmetic is
           AT.Book.settle, untouched.
ANCHORS    from the committed JSONs (2026-11-18_after_tax_comparison.json, 2026-11-19_blend_cost_tax.json), reproduced
           on #215's proxy price set with the OLD open-position convention.

    python pipelines/diagnostics/explore_after_tax_frontier.py            # writes 2026-11-19_after_tax_frontier.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_after_tax_comparison as AT  # noqa: E402
import explore_blend_cost_tax as BCT  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

EXP = ROOT / "diagnostics" / "research" / "explore"
OUT_JSON = EXP / "2026-11-19_after_tax_frontier.json"
CACHE = ROOT / ".cache" / "after_tax_frontier"
ARB = "_ARBITRAGE"
MF = (AT.IDX, AT.LIQ, ARB)
TARGETS = [round(t / 100, 2) for t in range(6, 21)]
STATIC_W = [round(w / 100, 2) for w in range(40, 81, 5)]
BAR = 25.0
CASH_LEGS = ("liquid_real", "arbitrage_real")


# ------------------------------------------------------------------------------------------ book with an arbitrage fund
class FBook(BCT.LBook):
    """LBook + ARB: equity-taxed (kind() is 'debt' only for LIQ), charged mutual-fund cost rates."""

    def buy(self, inst, value, px, d):
        if inst != ARB or value <= 0:
            return super().buy(inst, value, px, d)
        on = self.cost_on
        self.cost_on = False
        super().buy(inst, value, px, d)
        self.cost_on = on
        c = value * AT.COST_MF_BUY * on
        self.cash -= c
        self.costs += c
        self.trades[-1]["cost"] += c

    def sell(self, inst, value, px, d):
        if inst != ARB:
            return super().sell(inst, value, px, d)
        u = min(value / px, self.units[inst])
        if u <= 0:
            return
        on = self.cost_on
        self.cost_on = False
        super().sell(inst, value, px, d)
        self.cost_on = on
        c = u * px * AT.COST_MF_SELL * on
        self.cash -= c
        self.costs += c
        self.trades[-1]["cost"] += c


# ------------------------------------------------------------------------------------------ inputs
def real_cash(idx: pd.DatetimeIndex) -> dict:
    import explore_tax_mc_amendments as AM
    navs = AM.fetch_navs()
    chk = AM.amfi_check(navs)
    if not all(v["match"] for v in chk.values()):
        raise SystemExit("AMFI cross-check failed: stop")

    def daily_avg(keys):                                  # #214 explore_tax_mc_arbitrage_real.part_a.daily_avg
        rets = [navs[k]["series"].reindex(idx.union(navs[k]["series"].index)).ffill().reindex(idx).pct_change()
                for k in keys]
        return 100 * (1 + pd.concat(rets, axis=1).mean(axis=1).fillna(0.0)).cumprod()
    return {"liquid_real": daily_avg(["sbi_liquid", "hdfc_liquid"]), "arbitrage_real": daily_avg(["kotak_arb", "icici_arb"]),
            "amfi_check_all_match": True, "schemes": {k: v["scheme"] for k, v in navs.items()}}


def open_positions(d: dict, idx: pd.DatetimeIndex) -> tuple[list, dict]:
    """Positions open at the cut -> [(inst, gain, days)] for a last-session pass-through (method: Step 2 fix)."""
    cut = idx[-1]
    led = d["swing_ledger"]
    eos = led[led["reason"] == "eos"].copy()
    out, info = [], {}
    for r in eos.itertuples():
        days = int((cut - pd.Timestamp(r.entry_date).normalize()).days)
        out.append((AT.SW, float(r.net_pnl), days))
    info["swing_open"] = {"n": int(len(eos)), "gain": round(float(eos["net_pnl"].sum()), 0),
                          "gain_held_le_365d": round(float(sum(g for _, g, dd in out if dd <= 365)), 0),
                          "n_held_le_365d": int(sum(dd <= 365 for _, _, dd in out))}
    f = CACHE / "mom_close_at_cut.json"
    mt = d["momentum_trades"].copy()
    mt["ed"], mt["xd"] = pd.to_datetime(mt["entry_date"]), pd.to_datetime(mt["exit_date"])
    op = mt[(mt["ed"] <= cut) & (mt["xd"] > cut)].copy()
    if f.exists():
        close = json.loads(f.read_text())
    else:
        from run_bhanushali_path1 import corrected_universe
        u = corrected_universe()
        close = {}
        for t in sorted(op["ticker"].unique()):
            df = u[t]
            c = df["close"] if "close" in df else df["Close"]
            c = c[pd.DatetimeIndex(df.index).normalize() <= cut]
            close[t] = float(c.iloc[-1])
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(close, sort_keys=True))
    op["gain"] = op["qty"] * (op["ticker"].map(close) - op["entry"])
    op["days"] = (cut - op["ed"]).dt.days
    mom = []
    for r in op.sort_values(["ticker", "entry_date", "exit_date"]).itertuples():
        mom.append((AT.MOM, float(r.gain), int(r.days)))
    mval = float((op["qty"] * op["ticker"].map(close)).sum())
    navc = float(B.window(d["momentum"]).iloc[-1])
    info["momentum_open"] = {"rows": int(len(op)), "names": int(op["ticker"].nunique()),
                             "gain": round(float(op["gain"].sum()), 0),
                             "gain_held_le_365d": round(float(op.loc[op["days"] <= 365, "gain"].sum()), 0),
                             "market_value_over_nav_at_cut": round(mval / navc, 4)}
    return out + mom, info


# ------------------------------------------------------------------------------------------ one generic run
def run(mode: str, idx, px: dict, *, weights=None, expo=None, w_static=None, cash=AT.LIQ, gains=None, open_pos=None,
        tax_on=True, cost_on=True) -> dict:
    """BCT.run, generalised. mode: 'vt' (daily re-target to expo), 'static' (first close + tax days), 'alone' (100%
    one sleeve, first buy free, re-targeted on tax days - BCT 'mom_only'/'sw_only')."""
    b = FBook(tax_on, cost_on, free_first_buy=(mode == "alone"))
    b.cash = AT.CAPITAL
    navs = []
    fy_last = {AT.fy_end(dd): dd for dd in idx}
    pay_days = {v for k, v in fy_last.items() if v != idx[-1]}
    insts = list(px)
    arr = {i: px[i].to_numpy(float) for i in insts}
    ex = expo.to_numpy(float) if expo is not None else None
    for k, dd in enumerate(idx):
        pr = {i: arr[i][k] for i in insts}
        if gains:
            for inst, g, days in gains.get(dd, ()):
                b.passthrough_ev(inst, g, days)
        for e in b.events:
            if e["d"] is None:
                e["d"] = dd
        if dd in pay_days:
            b.settle(dd)
        nav = b.value(pr)
        b.today_nav = nav
        b.free_first_buy = b.free_first_buy and k == 0
        if mode == "vt":
            e = float(ex[k])
            tg = {i: nav * e * w for i, w in weights.items()}
            tg[cash] = nav * (1 - e)
            b.retarget(tg, pr, dd)
        elif k == 0 or dd in pay_days:
            if mode == "static":
                tg = {AT.IDX: nav * w_static, cash: nav * (1 - w_static)}
            else:
                tg = {i: nav * w for i, w in weights.items()}
            b.retarget(tg, pr, dd)
        navs.append(b.value(pr))
    mtm = pd.Series(navs, index=idx)
    pr = {i: arr[i][-1] for i in insts}
    if open_pos:
        for inst, g, days in open_pos:
            b.passthrough_ev(inst, g, days)
        for e in b.events:
            if e["d"] is None:
                e["d"] = idx[-1]
    b.today_nav = b.value(pr)
    n_before, n_ev = len(b.trades), len(b.events)
    for i in sorted(b.units):
        if b.units[i] > 0:
            b.sell(i, b.units[i] * pr[i], pr[i], idx[-1])
    for t in b.trades[n_before:]:
        t["terminal"] = True
    for e in b.events[n_ev:]:
        if e["src"] == "unit_sale":
            e["src"] = "unit_sale_terminal"
    b.settle(idx[-1])
    return {"mtm": mtm, "liquidation_value": b.cash, "tax_paid": b.tax_paid, "costs": b.costs, "book": b}


def met(res: dict) -> dict:
    m = AT.metrics({k: res[k] for k in ("mtm", "liquidation_value", "tax_paid", "costs")})
    return {"after_tax_cagr": m["after_tax_cagr_liquidation_pct"], "p95_dd156": m["boot156_p95_b8"],
            "sharpe_excess": m["sharpe_excess"], "worst_daily_dd": m["worst_daily_dd_pct"], "tax": m["tax_total"],
            "costs": m["trading_costs"], "passes_cap": bool(m["boot156_p95_b8"] <= BAR)}


def vt_expo(r: pd.Series, idx, target) -> pd.Series:
    r = r.reindex(idx).fillna(0.0)
    vol = r.rolling(20).std().shift(1) * np.sqrt(252)
    return (target / vol).clip(upper=1.0).fillna(1.0)


# ------------------------------------------------------------------------------------------ step 4 split
def tax_split(res: dict) -> dict:
    b = res["book"]
    ev = pd.DataFrame(b.events)
    sched = BCT.tax_schedule(ev, len(b.tax_paid))
    ev["grp"] = ev["src"].map({"unit_sale": "rebalance", "unit_sale_terminal": "terminal", "book_trade": "pass_through"}) \
        + "|" + ev["inst"]
    ev["tax"] = 0.0
    for p, taxes in enumerate(sched):
        for cls, tx in zip(("st", "lt", "slab"), taxes):
            m = (ev["period"] == p) & (ev["cls"] == cls)
            if tx <= 0 or not m.any():
                continue
            net = ev[m].groupby("grp")["gain"].sum().clip(lower=0)
            if net.sum() <= 0:
                continue
            for g, v in net.items():
                mm = m & (ev["grp"] == g)
                pos = ev.loc[mm, "gain"].clip(lower=0)
                if v > 0 and pos.sum() > 0:
                    ev.loc[mm, "tax"] = tx * (v / net.sum()) * pos / pos.sum()
    eq = ev[ev["cls"].isin(["st", "lt"])]
    st_net, lt_net = float(eq.loc[eq.cls == "st", "gain"].sum()), float(eq.loc[eq.cls == "lt", "gain"].sum())
    st_pos, lt_pos = float(eq.loc[eq.cls == "st", "gain"].clip(lower=0).sum()), float(eq.loc[eq.cls == "lt", "gain"].clip(lower=0).sum())
    return {"tax_by_group": {g: round(float(v), 0) for g, v in ev.groupby("grp")["tax"].sum().items()},
            "tax_total": round(float(sum(map(sum, sched))), 0),
            "equity_realised_gain": {"st_net": round(st_net, 0), "lt_net": round(lt_net, 0),
                                     "st_share_of_net": round(st_net / (st_net + lt_net), 4) if st_net + lt_net else None,
                                     "st_share_of_gross_positive": round(st_pos / (st_pos + lt_pos), 4) if st_pos + lt_pos else None},
            "slab_gain": round(float(ev.loc[ev.cls == "slab", "gain"].sum()), 0)}


# ------------------------------------------------------------------------------------------ step 5
def excess_sharpe(r: pd.Series) -> float:
    return float((r.mean() - AT.RF_D) / r.std() * np.sqrt(252))


def rolling_windows(series: dict, idx) -> dict:
    starts = []
    for m in pd.period_range(idx[0].to_period("M"), idx[-1].to_period("M"), freq="M"):
        s = idx[idx >= m.start_time]
        if not len(s):
            continue
        s0 = s[0]
        end = s0 + pd.DateOffset(years=3)
        if end > idx[-1]:
            break
        starts.append((s0, end))
    rows = []
    for s0, end in starts:
        row = {"start": str(s0.date()), "end": str(end.date())}
        for k, nav in series.items():
            sl = nav[(nav.index >= s0) & (nav.index <= end)]
            row[k] = excess_sharpe(sl.pct_change().dropna())
        rows.append(row)
    return {"windows": rows, "n_windows": len(rows),
            "n_non_overlapping": int(((idx[-1] - idx[0]).days / 365.25) // 3)}


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    d = B.navs()
    mo = d["momentum_metrics"]
    if (round(mo["cagr_pct"], 2), round(mo["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    r_bl, expo_bl = C.vol_target_blend(rm, rs, target=0.11)
    idx = pd.DatetimeIndex(r_bl.index).normalize()
    expo_bl.index = idx
    pxi, pxl, r_tri = BCT.prices(idx, True)
    px_m, px_s, gains, mt, led = BCT.sleeves(d, idx, d["momentum"], d["swing"])
    rm_i = rm.copy(); rm_i.index = pd.DatetimeIndex(rm_i.index).normalize()
    rs_i = rs.copy(); rs_i.index = pd.DatetimeIndex(rs_i.index).normalize()
    out = {"window": [str(idx[0].date()), str(idx[-1].date())], "capital": AT.CAPITAL,
           "counts": "screens 24 / sealed opens 4 / n_trials 3 (unchanged; measurement)"}

    # -------- anchors (proxy price set, old open-position convention)
    a1 = json.loads((EXP / "2026-11-18_after_tax_comparison.json").read_text())["after_tax"]
    a2 = json.loads((EXP / "2026-11-19_blend_cost_tax.json").read_text())["step3_waterfall"]
    proxy = {AT.IDX: pxi, AT.LIQ: pxl, AT.MOM: px_m, AT.SW: px_s}
    expo_ix11 = vt_expo(r_tri, idx, 0.11)
    A = {"blend_vt11": run("vt", idx, proxy, weights={AT.MOM: 0.7, AT.SW: 0.3}, expo=expo_bl, gains=gains),
         "static_65_35": run("static", idx, proxy, w_static=0.65),
         "index_vt11": run("vt", idx, proxy, weights={AT.IDX: 1.0}, expo=expo_ix11),
         "swing_alone": run("alone", idx, proxy, weights={AT.SW: 1.0}, gains=gains),
         "0001_alone": run("alone", idx, proxy, weights={AT.MOM: 1.0}, gains=gains)}
    got = {k: met(v) for k, v in A.items()}
    exp = {"blend_vt11": (a1["a_blend_vt11"]["after_tax_cagr_liquidation_pct"], a1["a_blend_vt11"]["boot156_p95_b8"]),
           "static_65_35": (a1["d_static_65_35"]["after_tax_cagr_liquidation_pct"], a1["d_static_65_35"]["boot156_p95_b8"]),
           "index_vt11": (a1["b_index_vt11"]["after_tax_cagr_liquidation_pct"], a1["b_index_vt11"]["boot156_p95_b8"]),
           "swing_alone": (a2["swing_alone"]["after_tax_cagr"], None), "0001_alone": (a2["0001_alone"]["after_tax_cagr"], None)}
    anc = {}
    for k, (c_, p_) in exp.items():
        anc[k] = {"expected": [c_, p_], "got": [got[k]["after_tax_cagr"], got[k]["p95_dd156"] if p_ is not None else None]}
        for e_, g_ in ((c_, got[k]["after_tax_cagr"]), (p_, got[k]["p95_dd156"])):
            if e_ is None:
                continue
            if abs(e_ - g_) / abs(e_) > 0.05:
                raise SystemExit(f"anchor {k} miss over 5% relative ({e_} vs {g_}): stop")
            if abs(e_ - g_) > 0.005:
                anc[k]["miss"] = True
    out["anchors"] = anc
    print("ANCHORS", json.dumps(anc), flush=True)

    # -------- step 2: swing open positions short-term by their own holding days
    opos, oinfo = open_positions(d, idx)
    sw_open = [x for x in opos if x[0] == AT.SW]
    mo_open = [x for x in opos if x[0] == AT.MOM]
    sw_fix = met(run("alone", idx, proxy, weights={AT.SW: 1.0}, gains=gains, open_pos=sw_open))
    mo_fix = met(run("alone", idx, proxy, weights={AT.MOM: 1.0}, gains=gains, open_pos=mo_open))
    out["step2_swing_fix"] = {"open_positions": oinfo, "rule": "open positions passed through on the last session; "
                              "short-term if held <= 365 days, else long-term; basis stepped up; then terminal unit sale",
                              "swing_alone_old": got["swing_alone"]["after_tax_cagr"], "swing_alone_fixed": sw_fix["after_tax_cagr"],
                              "change_pp": round(sw_fix["after_tax_cagr"] - got["swing_alone"]["after_tax_cagr"], 2),
                              "tax_old": got["swing_alone"]["tax"], "tax_fixed": sw_fix["tax"],
                              "same_fix_0001_alone": {"old": got["0001_alone"]["after_tax_cagr"], "fixed": mo_fix["after_tax_cagr"]},
                              "blend_vt11_both_conventions": {
                                  "old": got["blend_vt11"]["after_tax_cagr"],
                                  "fixed": met(run("vt", idx, proxy, weights={AT.MOM: 0.7, AT.SW: 0.3}, expo=expo_bl,
                                                   gains=gains, open_pos=opos))["after_tax_cagr"]}}
    print("STEP2", json.dumps(out["step2_swing_fix"]), flush=True)

    # -------- step 3: frontier
    rc = real_cash(idx)
    out["cash_legs"] = {"schemes": rc["schemes"], "amfi_check_all_match": rc["amfi_check_all_match"],
                        "window_cagr_pct": {k: round(((rc[k].iloc[-1] / rc[k].iloc[0]) ** (365.25 / (idx[-1] - idx[0]).days) - 1) * 100, 3)
                                            for k in CASH_LEGS}}
    designs = {"blend": ({AT.MOM: 0.7, AT.SW: 0.3}, 0.7 * rm_i.reindex(idx).fillna(0) + 0.3 * rs_i.reindex(idx).fillna(0)),
               "0001": ({AT.MOM: 1.0}, rm_i), "swing": ({AT.SW: 1.0}, rs_i), "index": ({AT.IDX: 1.0}, r_tri)}
    pts, mtms = [], {}
    for leg in CASH_LEGS:
        cl = AT.LIQ if leg == "liquid_real" else ARB
        px = {AT.IDX: pxi, AT.MOM: px_m, AT.SW: px_s, cl: rc[leg]}
        for name, (w, r) in designs.items():
            sleeve = name != "index"
            for T in TARGETS:
                if name == "blend":
                    e = C.vol_target_blend(rm, rs, target=T)[1]
                    e.index = idx
                else:
                    e = vt_expo(r, idx, T)
                res = run("vt", idx, px, weights=w, expo=e, cash=cl, gains=gains if sleeve else None,
                          open_pos=[x for x in opos if x[0] in w] if sleeve else None)
                m = met(res)
                pts.append({"design": name, "cash": leg, "target": T, **m, "mean_exposure": round(float(e.mean()), 3)})
                mtms[(name, leg, T)] = res["mtm"]
            print("frontier", leg, name, flush=True)
        for wst in STATIC_W:
            res = run("static", idx, px, w_static=wst, cash=cl)
            pts.append({"design": "static", "cash": leg, "target": wst, **met(res)})
            mtms[("static", leg, wst)] = res["mtm"]
    ix100 = run("static", idx, {AT.IDX: pxi, AT.LIQ: rc["liquid_real"]}, w_static=1.0)
    mtms[("index_100", "-", 1.0)] = ix100["mtm"]
    pts.append({"design": "index_100_buy_hold", "cash": "-", "target": 1.0, **met(ix100)})
    for p in pts:
        p["dominated"] = any((q["after_tax_cagr"] >= p["after_tax_cagr"] and q["p95_dd156"] <= p["p95_dd156"]
                              and (q["after_tax_cagr"] > p["after_tax_cagr"] or q["p95_dd156"] < p["p95_dd156"])) for q in pts)
    ok = [p for p in pts if p["passes_cap"]]
    best = max(ok, key=lambda p: p["after_tax_cagr"]) if ok else None
    by_design = {}
    for p in ok:
        k = p["design"]
        if k not in by_design or p["after_tax_cagr"] > by_design[k]["after_tax_cagr"]:
            by_design[k] = p
    out["frontier"] = {"points": pts, "best_at_cap": best,
                       "best_passing_by_design": by_design,
                       "margins_pp_vs_best_of_each_other_design": {k: round(best["after_tax_cagr"] - v["after_tax_cagr"], 2)
                                                                   for k, v in by_design.items()} if best else None}
    print("BEST", json.dumps(best), flush=True)

    # -------- step 4: tax layer, #215 proxy set
    pre_ix = run("vt", idx, proxy, weights={AT.IDX: 1.0}, expo=expo_ix11, tax_on=False)
    pre_st = run("static", idx, proxy, w_static=0.65, tax_on=False)
    s4 = {}
    for k, aft, pre in (("index_vt11", A["index_vt11"], pre_ix), ("static_65_35", A["static_65_35"], pre_st)):
        tp = BCT.cagr(pre, idx) - BCT.cagr(aft, idx)
        sp = tax_split(aft)
        s4[k] = {"tax_pp": round(tp, 3), **sp,
                 "tax_pp_by_group": {g: round(tp * v / sp["tax_total"], 3) for g, v in sp["tax_by_group"].items()}}
    groups = sorted(set(s4["index_vt11"]["tax_pp_by_group"]) | set(s4["static_65_35"]["tax_pp_by_group"]))
    s4["difference_pp"] = {"total": round(s4["index_vt11"]["tax_pp"] - s4["static_65_35"]["tax_pp"], 3),
                           "by_group": {g: round(s4["index_vt11"]["tax_pp_by_group"].get(g, 0.0)
                                                 - s4["static_65_35"]["tax_pp_by_group"].get(g, 0.0), 3) for g in groups}}
    out["step4_tax_layer"] = s4

    # -------- step 5: mission test
    s5 = {}
    for leg in CASH_LEGS:
        cand = [p for p in pts if p["design"] == "blend" and p["cash"] == leg and p["passes_cap"]]
        if not cand:
            s5[leg] = {"cap_passing_vol": None}
            continue
        T = max(p["target"] for p in cand)
        rw = rolling_windows({"blend": mtms[("blend", leg, T)], "static_65_35": mtms[("static", leg, 0.65)],
                              "tri_index_fund": mtms[("index_100", "-", 1.0)]}, idx)
        w = pd.DataFrame(rw["windows"])
        res = {"cap_passing_vol": T, "n_windows": rw["n_windows"], "n_non_overlapping_3y": rw["n_non_overlapping"],
               "first_window": rw["windows"][0]["start"], "last_window": rw["windows"][-1]["start"]}
        for bm in ("static_65_35", "tri_index_fund"):
            m = w["blend"] - w[bm]
            res[f"vs_{bm}"] = {"share_blend_wins": round(float((m > 0).mean()), 3), "median_margin": round(float(m.median()), 3),
                               "worst_margin": round(float(m.min()), 3), "best_margin": round(float(m.max()), 3),
                               "worst_window": str(w.loc[m.idxmin(), "start"])}
        res["windows"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rw["windows"]]
        s5[leg] = res
    out["step5_mission_test"] = s5

    # -------- replica inputs
    rep = CACHE / "replica_inputs"
    rep.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"mom_nav": px_m, "swing_nav": px_s, "mom_ret": rm_i.reindex(idx), "swing_ret": rs_i.reindex(idx),
                  "index_px": pxi, "liquid_real_px": rc["liquid_real"], "arbitrage_real_px": rc["arbitrage_real"]}
                 ).to_csv(rep / "daily.csv", index_label="date", float_format="%.10g")
    mt[["ticker", "entry_date", "exit_date", "qty", "entry", "exit", "pnl", "reason"]].to_csv(rep / "momentum_trades.csv", index=False)
    led[["tkr", "entry_date", "exit_date", "net_pnl", "reason"]].to_csv(rep / "swing_ledger.csv", index=False)
    pd.DataFrame(opos, columns=["sleeve", "gain", "days"]).replace({AT.MOM: "MOM", AT.SW: "SW"}).to_csv(rep / "open_positions_at_cut.csv", index=False)

    txt = json.dumps(out, indent=1, default=str) + "\n"
    OUT_JSON.write_text(txt, encoding="utf-8")
    print("SHA256", hashlib.sha256(txt.encode()).hexdigest(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
