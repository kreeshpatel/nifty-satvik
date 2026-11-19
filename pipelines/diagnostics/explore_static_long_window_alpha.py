"""MEASUREMENT: (1) static index/arbitrage mixes 40/60..80/20 after tax on 2017-01..2026-06 plus sub-periods;
(2) gross alpha over beta (pre-tax; pre-cost and net-of-cost) of the blend, 0001 and swing, weekly, 2019-03..2024-06.

Owner request 2026-11-19 ("prompt 4"). Method + Step 0 sealed check: diagnostics/research/explore/
2026-11-19_static_long_window_alpha.md (committed before any result). Strategy outputs stay cut at 2024-06-30.

    python pipelines/diagnostics/explore_static_long_window_alpha.py     # -> 2026-11-19_static_long_window_alpha.json
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
import explore_after_tax_frontier as F  # noqa: E402
import explore_blend_cost_tax as BCT  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402

EXP = ROOT / "diagnostics" / "research" / "explore"
OUT_JSON = EXP / "2026-11-19_static_long_window_alpha.json"
REP = ROOT / ".cache" / "static_long_window_alpha" / "replica_inputs"
FULL = ("2017-01-01", "2026-06-30")
SUBS = {"2017-01..2019-02": ("2017-01-01", "2019-02-28"), "2024-07..2026-06": ("2024-07-01", "2026-06-30")}
STATIC_W = [round(w / 100, 2) for w in range(40, 81, 5)]
NW_LAG = 8
RF_W = (1 + AT.RF) ** (1 / 52) - 1


# ------------------------------------------------------------------------------------------ helpers
def p95(nav: pd.Series) -> float:
    return round(float(np.percentile(B.boot_dd(C.weekly_returns(nav).to_numpy(), 156, 8), 95)), 2)


def cagr_nav(nav: pd.Series) -> float:
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    return round(((nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1) * 100, 2)


def ols_nw(y: np.ndarray, x: np.ndarray, lag: int = NW_LAG) -> dict:
    X = np.column_stack([np.ones(len(x)), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    S = (X * e[:, None]).T @ (X * e[:, None])
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        G = (X[l:] * e[l:, None]).T @ (X[:-l] * e[:-l, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return {"a_weekly": float(b[0]), "beta": float(b[1]), "se_a_nw": float(np.sqrt(V[0, 0])),
            "t_nw": float(b[0] / np.sqrt(V[0, 0])), "r2": float(r2), "n": int(len(y))}


def regress(book_nav: pd.Series, ix_nav: pd.Series) -> dict:
    rb, rx = C.weekly_returns(book_nav), C.weekly_returns(ix_nav)
    j = pd.concat([rb, rx], axis=1, join="inner").dropna()
    yb, yx = j.iloc[:, 0].to_numpy(), j.iloc[:, 1].to_numpy()
    o = ols_nw(yb - RF_W, yx - RF_W)
    beta = o["beta"]
    mix = beta * yx + (1 - beta) * RF_W
    yrs = (j.index[-1] - j.index[0]).days / 365.25 + 7 / 365.25
    return {"alpha_ann_pct": round(o["a_weekly"] * 52 * 100, 2), "beta": round(beta, 3),
            "t_nw_lag8": round(o["t_nw"], 2), "r2": round(o["r2"], 3), "n_weeks": o["n"],
            "significant_|t|>=2": bool(abs(o["t_nw"]) >= 2),
            "alpha_vs_beta_matched_mix_ann_pct": round(float((yb - mix).mean()) * 52 * 100, 2),
            "book_cagr_weekly_pct": round(float(np.prod(1 + yb) ** (1 / yrs) - 1) * 100, 2),
            "beta_matched_mix_cagr_pct": round(float(np.prod(1 + mix) ** (1 / yrs) - 1) * 100, 2)}


# ------------------------------------------------------------------------------------------ main
def main() -> int:
    out = {"counts": "screens 24 / sealed opens 4 / n_trials 3 (unchanged; measurement)",
           "sealed_check": "index TRI and fund NAVs after 2024-06-30 are not a sealed slice (see the .md Step 0); "
                           "strategy outputs cut at 2024-06-30"}
    d = B.navs()
    mo = d["momentum_metrics"]
    if (round(mo["cagr_pct"], 2), round(mo["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("0001 anchor mismatch: stop")

    # -------- anchors: #215 (committed JSON) and the owner fallback (prompt 1 committed JSON)
    rm, rs = B.window(d["momentum"]).pct_change().dropna(), B.window(d["swing"]).pct_change().dropna()
    r_bl, expo_bl = C.vol_target_blend(rm, rs, target=0.11)
    idx = pd.DatetimeIndex(r_bl.index).normalize()
    expo_bl.index = idx
    pxi, pxl, r_tri = BCT.prices(idx, True)
    px_m, px_s, gains, mt, led = BCT.sleeves(d, idx, d["momentum"], d["swing"])
    proxy = {AT.IDX: pxi, AT.LIQ: pxl, AT.MOM: px_m, AT.SW: px_s}
    a1 = json.loads((EXP / "2026-11-18_after_tax_comparison.json").read_text())["after_tax"]
    g_bl = F.met(F.run("vt", idx, proxy, weights={AT.MOM: 0.7, AT.SW: 0.3}, expo=expo_bl, gains=gains))
    g_st = F.met(F.run("static", idx, proxy, w_static=0.65))
    rmb = json.loads((EXP / "2026-11-18_risk_matched_benchmark.json").read_text())["q3_risk_matched"]["full_0001_window"]
    import explore_risk_matched_benchmark as RMB
    rt = RMB.win(RMB.tri_returns(), RMB.FULL_WIN)
    grid = []
    for e in [round(x / 100, 2) for x in range(5, 101, 5)]:
        s = RMB.stats(RMB.static(rt, e), blocks=(8,))
        grid.append((e, s["cagr_pct"], s["boot156_p95_b8"]))
    ok8 = max((g for g in grid if g[2] <= 25.0), key=lambda g: g[0])
    anc = {"blend_vt11": {"expected": [a1["a_blend_vt11"]["after_tax_cagr_liquidation_pct"], a1["a_blend_vt11"]["boot156_p95_b8"]],
                          "got": [g_bl["after_tax_cagr"], g_bl["p95_dd156"]]},
           "static_65_35": {"expected": [a1["d_static_65_35"]["after_tax_cagr_liquidation_pct"], a1["d_static_65_35"]["boot156_p95_b8"]],
                            "got": [g_st["after_tax_cagr"], g_st["p95_dd156"]]},
           "owner_fallback_2017_2026_b8": {"expected": [rmb["bench_static_meeting_bar_b8"]["exposure"], rmb["bench_static_meeting_bar_b8"]["cagr_pct"],
                                                        rmb["bench_static_meeting_bar_b8"]["boot156_p95_b8"]],
                                           "got": [ok8[0], ok8[1], ok8[2]]}}
    for k, v in anc.items():
        for e_, g_ in zip(v["expected"], v["got"]):
            if abs(e_ - g_) / abs(e_) > 0.05:
                raise SystemExit(f"anchor {k} miss over 5% relative: stop")
            if abs(e_ - g_) > 0.005:
                v["miss"] = True
    out["anchors"] = anc
    print("ANCHORS", json.dumps(anc), flush=True)

    # -------- step 1: static index/arbitrage mixes, 2017-01..2026-06
    tri = pd.read_csv(AT.TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    idx_f = pd.DatetimeIndex(tri.index[(tri.index >= pd.Timestamp(FULL[0])) & (tri.index <= pd.Timestamp(FULL[1]))]).normalize()
    import explore_tax_mc_amendments as AM
    navs = AM.fetch_navs()
    starts = {k: str(navs[k]["series"].index[0].date()) for k in ("kotak_arb", "icici_arb")}
    assert all(pd.Timestamp(v) < idx_f[0] for v in starts.values()), "arbitrage NAVs start after the window: proxy needed"
    if not all(v["match"] for v in AM.amfi_check(navs).values()):
        raise SystemExit("AMFI cross-check failed: stop")

    def prices_on(ix):
        r = tri.pct_change().reindex(ix).fillna(0.0)
        r.iloc[0] = 0.0
        p_ix = (1 + r - AT.TER_INDEX / 252).cumprod() * 100
        rets = [navs[k]["series"].reindex(ix.union(navs[k]["series"].index)).ffill().reindex(ix).pct_change()
                for k in ("kotak_arb", "icici_arb")]
        p_arb = 100 * (1 + pd.concat(rets, axis=1).mean(axis=1).fillna(0.0)).cumprod()
        return {AT.IDX: p_ix, F.ARB: p_arb}
    px_f = prices_on(idx_f)
    out["step1_data"] = {"window": [str(idx_f[0].date()), str(idx_f[-1].date())], "sessions": int(len(idx_f)),
                         "arbitrage_nav_first_dates": starts, "liquid_proxy_used": False,
                         "arbitrage_cash_leg_cagr_pct": cagr_nav(px_f[F.ARB]), "index_fund_cagr_pct": cagr_nav(px_f[AT.IDX])}
    rows = []
    full_mtm = {}
    for w in STATIC_W:
        res = F.run("static", idx_f, px_f, w_static=w, cash=F.ARB)
        m = F.met(res)
        full_mtm[w] = res["mtm"]
        row = {"mix": f"{int(w*100)}/{int(round((1-w)*100))}", "index_w": w, "full": {"after_tax_cagr": m["after_tax_cagr"],
               "p95_dd156": m["p95_dd156"], "passes": m["passes_cap"], "sharpe_excess": m["sharpe_excess"],
               "worst_daily_dd": m["worst_daily_dd"], "tax": m["tax"]}}
        for name, (lo, hi) in SUBS.items():
            sl = res["mtm"][(res["mtm"].index >= pd.Timestamp(lo)) & (res["mtm"].index <= pd.Timestamp(hi))]
            ix_s = idx_f[(idx_f >= pd.Timestamp(lo)) & (idx_f <= pd.Timestamp(hi))]
            fresh = F.met(F.run("static", ix_s, prices_on(ix_s), w_static=w, cash=F.ARB))
            row[name] = {"slice_after_tax_cagr_mtm": cagr_nav(sl), "slice_p95_dd156": p95(sl),
                         "fresh_capital_after_tax_cagr": fresh["after_tax_cagr"], "fresh_capital_p95_dd156": fresh["p95_dd156"]}
        rows.append(row)
        print("static", row["mix"], row["full"], flush=True)
    passing = [r for r in rows if r["full"]["passes"]]
    out["step1_static_mixes"] = {"rows": rows, "highest_passing_full_window": max(passing, key=lambda r: r["index_w"])["mix"] if passing else None}

    # -------- step 2: alpha over beta, 2019-03..2024-06, weekly
    gb = BCT.gross_books(d)
    rmg, rsg = B.window(gb["momentum_gross"]).pct_change().dropna(), B.window(gb["swing_gross"]).pct_change().dropna()
    cash_d = (1 + AT.RF_D) * (1 - AT.TER_LIQUID / 252) - 1
    gi = rmg.index.intersection(rsg.index)
    e_g = expo_bl.reindex(pd.DatetimeIndex(gi).normalize()).fillna(1.0).to_numpy()
    r_blg = pd.Series(e_g * (0.7 * rmg.reindex(gi).fillna(0).to_numpy() + 0.3 * rsg.reindex(gi).fillna(0).to_numpy())
                      + (1 - e_g) * cash_d, index=pd.DatetimeIndex(gi).normalize())
    blend_net = F.run("vt", idx, proxy, weights={AT.MOM: 0.7, AT.SW: 0.3}, expo=expo_bl, gains=gains, tax_on=False)["mtm"]
    books = {"gross": {"blend": (1 + r_blg).cumprod(), "0001": B.window(gb["momentum_gross"]), "swing": B.window(gb["swing_gross"])},
             "net_of_cost": {"blend": blend_net, "0001": B.window(d["momentum"]), "swing": B.window(d["swing"])}}
    tri_w = tri[(tri.index >= pd.Timestamp(B.COMMON[0])) & (tri.index <= pd.Timestamp(B.COMMON[1]))]
    regs = {"index_fund": pxi, "tri_raw": tri_w}
    s2 = {}
    for cv, bk in books.items():
        for name, nav in bk.items():
            nav = nav.copy()
            nav.index = pd.DatetimeIndex(nav.index).normalize()
            nav = nav[~nav.index.duplicated(keep="last")]
            nav = nav[(nav.index >= pd.Timestamp(B.COMMON[0])) & (nav.index <= pd.Timestamp(B.COMMON[1]))]
            for rg, ixn in regs.items():
                s2[f"{cv}|{name}|{rg}"] = regress(nav, ixn)
    out["step2_alpha_over_beta"] = {"window": list(B.COMMON), "rf_annual": AT.RF, "nw_lag": NW_LAG, "results": s2}
    for k, v in s2.items():
        print(k, v, flush=True)

    # -------- replica inputs
    REP.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"index_px": px_f[AT.IDX], "arbitrage_px": px_f[F.ARB]}).to_csv(REP / "step1_daily.csv", index_label="date", float_format="%.10g")
    bn = blend_net.copy()
    pd.DataFrame({"blend_net_nav": bn, "index_fund_px": pxi.reindex(bn.index)}).to_csv(REP / "step2_daily.csv", index_label="date", float_format="%.10g")

    txt = json.dumps(out, indent=1, default=str) + "\n"
    OUT_JSON.write_text(txt, encoding="utf-8")
    print("SHA256", hashlib.sha256(txt.encode()).hexdigest(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
