"""MEASUREMENT (amendment to PR #214, owner additions A, B, D). Analysis, not tax advice. No live change.

A  PLAN / EXPENSES. The four funds are Direct-Plan Growth options (scheme names from AMFI's own file). A published NAV is
   net of the fund's total expense ratio. In the #212 simulator the per-instrument TER is used in two places: (1) to
   BUILD the proxy price series (cash_prices / index_price), and (2) as a reported tally (`fund_exp`) that is never
   deducted from any price. Replacing the price series with real NAVs therefore already removes (1); the real-data
   S0->S1 step is run with the liquid / arbitrage TER left at config AND set to 0, to show (2) does not move it.
B  FUND SELECTION AND THE WHOLE CATEGORY. (Cleaning rules for the category average were ADDED AFTER FIRST LOOK - see
   part_b.) Rule used for the headline pair: the two arbitrage funds named in the owner's
   instruction as "the two largest" (Kotak Arbitrage, ICICI Prudential Arbitrage) and two widely held liquid funds
   (SBI Liquid, HDFC Liquid), all Direct-Growth. AUM is NOT in AMFI's NAV files, so "largest" is NOT verified at
   either end of the window here [assumed]. Robustness: every Direct-Growth scheme in AMFI's NAV file whose name
   contains "Arbitrage" (excluding fund-of-funds: names containing "FOF" / "Fund of Fund" / "Omni") or "Liquid"
   (excluding "Overnight"), with a NAV on every anchor date 2019-03-05, 2019-12-31 ... 2023-12-29, 2024-06-28 (the last
   NAV on or before each date); calendar-year returns from those anchors; equal-weight category averages. Counts at
   the window start and end are reported.
D  S0->S1 ON REALISTIC SPREADS from the EXISTING 4,000 draws' paths and parameters: each draw's arbitrage spread is
   mapped from its original U(-1.5%, +0.3%) position onto [min - 0.3pp, max + 0.3pp] of the by-year spreads of the
   headline pair vs the real liquid average (same LHS stratum, linear map); S1 is re-simulated (S0 does not depend on
   the spread and is taken from the cache, after verifying the path regeneration reproduces cached S1 exactly at the
   original spread for the first 20 draws).

    python pipelines/diagnostics/explore_tax_mc_arbitrage_real.py
"""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import explore_india_tax_practices as T  # noqa: E402
import explore_tax_mc_amendments as AM  # noqa: E402
import explore_tax_montecarlo as M  # noqa: E402

NAV = AM.NAV
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_tax_mc_arbitrage_real.json"
ANCHORS = ["05-Mar-2019", "31-Dec-2019", "31-Dec-2020", "31-Dec-2021", "30-Dec-2022", "29-Dec-2023", "28-Jun-2024"]
YEARS = ["2019", "2020", "2021", "2022", "2023", "2024H1"]
SPREAD_RANGE_OLD = (-0.015, 0.003)


def amfi_day(d: str) -> pd.DataFrame:
    """All schemes' NAV on the last AMFI date on or before d (looks back up to 6 days)."""
    t = pd.Timestamp(d)
    for back in range(7):
        dd = (t - pd.Timedelta(days=back)).strftime("%d-%b-%Y")
        f = NAV / f"amfi_{dd}.txt"
        if not f.exists():
            r = requests.get("https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx", params={"frmdt": dd, "todt": dd},
                             headers=AM.UA, timeout=120)
            f.write_bytes(r.content)
            time.sleep(1)
        lines = f.read_text(encoding="latin-1").splitlines()
        if not lines or "Net Asset Value" not in lines[0]:
            continue
        hdr = lines[0].split(";")
        ci, cn, cv = 0, hdr.index("NAV Name") if "NAV Name" in hdr else 1, hdr.index("Net Asset Value")
        rows = []
        for ln in lines[1:]:
            p = ln.split(";")
            if len(p) > cv and p[ci].strip().isdigit():
                try:
                    rows.append((int(p[ci]), p[cn].strip(), float(p[cv])))
                except ValueError:
                    pass
        if rows:
            return pd.DataFrame(rows, columns=["code", "name", "nav"]).drop_duplicates("code").set_index("code")
    return pd.DataFrame(columns=["name", "nav"])


def category(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    n = df["name"].str.lower()
    direct_growth = n.str.contains("direct") & n.str.contains("growth") & ~n.str.contains("idcw|dividend|bonus|payout")
    if kind == "arb":
        m = n.str.contains("arbitrage") & ~n.str.contains("fof|fund of fund|omni")
    else:
        m = n.str.contains("liquid") & ~n.str.contains("overnight")
    return df[direct_growth & m]


def part_b() -> dict:
    days = {d: amfi_day(d) for d in ANCHORS}
    out = {"anchors": ANCHORS}
    for kind in ("arb", "liq"):
        start, end = category(days[ANCHORS[0]], kind), category(days[ANCHORS[-1]], kind)
        common = set(start.index)
        for d in ANCHORS[1:]:
            common &= set(category(days[d], kind).index)
        navs = pd.DataFrame({d: days[d]["nav"].reindex(sorted(common)) for d in ANCHORS})
        # ADDED AFTER FIRST LOOK: a NAV re-basing (face-value change; e.g. Navi Liquid -98.7% over the window) is not a
        # return, and one fund can carry two scheme codes with identical NAVs (HDFC Arbitrage). Drop any scheme whose NAV
        # moves by more than 2x either way between consecutive anchors; drop exact duplicate NAV paths.
        ratio = navs[ANCHORS[1:]].to_numpy() / navs[ANCHORS[:-1]].to_numpy()
        rebased = navs.index[((ratio < 0.5) | (ratio > 2.0)).any(axis=1)]
        dup = navs.round(4).duplicated()
        dropped = {"rebased": [days[ANCHORS[0]].loc[c, "name"] for c in rebased],
                   "duplicates": [days[ANCHORS[0]].loc[c, "name"] for c in navs.index[dup]]}
        navs = navs.drop(index=list(rebased)).loc[lambda x: ~x.round(4).duplicated()]
        yr = {}
        for k, y in enumerate(YEARS):
            a, b = ANCHORS[k], ANCHORS[k + 1]
            dd = (pd.Timestamp(b) - pd.Timestamp(a)).days
            r = (navs[b] / navs[a]) ** (365.25 / dd) - 1
            yr[y] = round(float(r.mean()) * 100, 2)
        dd = (pd.Timestamp(ANCHORS[-1]) - pd.Timestamp(ANCHORS[0])).days
        yr["overall"] = round(float(((navs[ANCHORS[-1]] / navs[ANCHORS[0]]) ** (365.25 / dd) - 1).mean()) * 100, 2)
        out[kind] = {"schemes_at_start": int(len(start)), "schemes_at_end": int(len(end)),
                     "present_on_every_anchor": int(len(common)), "used_after_cleaning": int(len(navs)),
                     "dropped": dropped, "equal_weight_return_pct": yr,
                     "names": sorted(start.loc[sorted(common), "name"].tolist())[:60]}
    out["category_spread_pp"] = {y: round(out["arb"]["equal_weight_return_pct"][y] - out["liq"]["equal_weight_return_pct"][y], 2)
                                 for y in [*YEARS, "overall"]}
    return out


def part_b_per_fund(navs) -> dict:
    tab = {}
    periods = [("2019", AM.WIN[0], "2019-12-31"), ("2020", "2019-12-31", "2020-12-31"), ("2021", "2020-12-31", "2021-12-31"),
               ("2022", "2021-12-31", "2022-12-31"), ("2023", "2022-12-31", "2023-12-31"), ("2024H1", "2023-12-31", AM.WIN[1]),
               ("overall", AM.WIN[0], AM.WIN[1])]
    for y, lo, hi in periods:
        r = {k: AM.ann_ret(navs[k]["series"], lo, hi) for k in AM.FUNDS}
        liq = (r["sbi_liquid"] + r["hdfc_liquid"]) / 2
        tab[y] = {f"{a}_minus_{l}": round((r[a] - r[l]) * 100, 2) for a in ("kotak_arb", "icici_arb") for l in ("sbi_liquid", "hdfc_liquid")}
        tab[y].update({f"{a}_minus_liquid_avg": round((r[a] - liq) * 100, 2) for a in ("kotak_arb", "icici_arb")})
    return tab


def part_a(navs) -> dict:
    base = T.load_cfg()
    ctx = T.context([base])
    idx = ctx["idx"]

    def daily_avg(keys):
        rets = [navs[k]["series"].reindex(idx.union(navs[k]["series"].index)).ffill().reindex(idx).pct_change() for k in keys]
        return 100 * (1 + pd.concat(rets, axis=1).mean(axis=1).fillna(0.0)).cumprod()
    real_arb, real_liq = daily_avg(["kotak_arb", "icici_arb"]), daily_avg(["sbi_liquid", "hdfc_liquid"])
    out = {}
    for label, zero in (("ter_left_in", False), ("ter_zeroed", True)):
        c = copy.deepcopy(base)
        if zero:
            c["instruments"]["liquid"]["ter"] = 0.0
            c["instruments"]["arbitrage"]["liquid_minus"] = 0.0
        ctx["px_index"][id(c)] = ctx["px_index"][id(base)]
        ctx["px_arb"][id(c)], ctx["px_liq"][id(c)] = real_arb, real_liq
        owner = c["individual"]["owner_marginal_slab"]
        for book in ("s60", "s65"):
            s0 = T.simulate(book, c, ctx, slab=owner, cash_leg=T.LIQ)
            s1 = T.simulate(book, c, ctx, slab=owner, cash_leg=T.ARB)
            out[f"{label}|{book}"] = {"S0": round(s0["final"], 0), "S1": round(s1["final"], 0),
                                      "S0->S1": round(s1["final"] - s0["final"], 0),
                                      "fund_expense_tally_S0": round(s0["fund_exp"], 0), "fund_expense_tally_S1": round(s1["fund_exp"], 0)}
    return out


# ------------------------------------------------------------------ part D (pool)
def _map_spread(old: float, new_rng) -> float:
    u = (old - SPREAD_RANGE_OLD[0]) / (SPREAD_RANGE_OLD[1] - SPREAD_RANGE_OLD[0])
    return new_rng[0] + u * (new_rng[1] - new_rng[0])


def d_one(task):
    i, p, new_rng, verify = task
    G = M.G
    r, _ = M.path_returns("boot", i, p["index_drift"])
    out = {"i": i}
    q = dict(p)
    if not verify:
        q["arb_spread"] = _map_spread(p["arb_spread"], new_rng)
    cfg = M.apply_params(G["base"], G["mc"], q)
    ctx = M.make_ctx(r, [cfg])
    owner = cfg["individual"]["owner_marginal_slab"]
    with M.scoped(p["harvest_offset_days"]):
        for book in M.BOOKS:
            out[book] = T.simulate(book, cfg, ctx, slab=owner, cash_leg=T.ARB)["final"]
    out["spread"] = q["arb_spread"]
    return out


def part_d(by_year_spreads: list[float]) -> dict:
    R = AM.rows("main") + AM.rows("main_double")
    R.sort(key=lambda r: r["i"])
    lo, hi = min(by_year_spreads) / 100 - 0.003, max(by_year_spreads) / 100 + 0.003
    with mp.Pool(6, initializer=M.init_worker) as pool:
        ver = pool.map(d_one, [(r["i"], r["p"], None, True) for r in R[:20]])
        vmax = max(abs(v[b] - r["v"][f"E|{b}"]["S1"]) for v, r in zip(ver, R[:20]) for b in M.BOOKS)
        if vmax > 1.0:
            raise SystemExit(f"path regeneration does not reproduce cached S1 (max diff {vmax}): stop")
        new = pool.map(d_one, [(r["i"], r["p"], (lo, hi), False) for r in R], chunksize=8)
    out = {"new_range_pct": [round(lo * 100, 2), round(hi * 100, 2)], "path_regeneration_max_diff_rupees": round(vmax, 2)}
    for book in M.BOOKS:
        g = np.array([n[book] - r["v"][f"E|{book}"]["S0"] for n, r in zip(new, R)])
        old = np.array([r["v"][f"E|{book}"]["S1"] - r["v"][f"E|{book}"]["S0"] for r in R])
        out[book] = {"new": {**M.pct(g), "P(S1>S0)": round(float((g > 0).mean()), 4)},
                     "old_superseded": {**M.pct(old), "P(S1>S0)": round(float((old > 0).mean()), 4)}}
    return out


def main() -> int:
    navs = AM.fetch_navs()
    out = {"plans": {k: navs[k]["scheme"] for k in AM.FUNDS},
           "nav_net_of_expenses": "yes - a mutual-fund NAV is published after the scheme's TER; all four are Direct-Plan Growth",
           "part_a_ter_double_count_check": part_a(navs),
           "part_b_per_fund_spread_pp": part_b_per_fund(navs),
           "part_b_category": part_b()}
    pair = AM.item3(navs)["annual_returns_and_spreads"]
    by_year = [x["spread_vs_real_liquid_pp"] for x in pair if x["period"] != "overall"]
    out["part_d_by_year_spreads_used_pp"] = by_year
    out["part_d"] = part_d(by_year)
    OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "part_b_category"}, indent=1, default=float)[:6000])
    print(json.dumps({k: v for k, v in out["part_b_category"].items() if k != "names"} | {"arb": {kk: vv for kk, vv in out["part_b_category"]["arb"].items() if kk != "names"},
                                                                                       "liq": {kk: vv for kk, vv in out["part_b_category"]["liq"].items() if kk != "names"}}, indent=1))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
