"""MEASUREMENT (amendment to PR #214, items 1, 3, 4, 5). Analysis, not tax advice. No live change; counts unchanged.

ITEM 1  harvest timing as a decision variable, from the EXISTING 4,000 draws (.cache/tax_mc/main*.jsonl, law E):
        S1->S2 gain split by harvest_offset_days <= +15 (harvest on or before 30 March, i.e. inside the FY before the
        31-March tax day) vs > +15 (31 March or later, i.e. on the tax day or in the next FY), and in 5-day offset bins.
ITEM 3  the arbitrage proxy replaced by data. Nifty 50 Arbitrage TRI: niftyindices.com getTotalReturnIndexString returns
        an HTML page (tried 2026-11-19 with four spellings of the index name). Fallback, as the owner specified: AMFI NAV
        history of the two largest arbitrage funds (Direct-Growth): Kotak Arbitrage Fund (AMFI 119771), ICICI Prudential
        Arbitrage Fund (120364); real liquid funds: SBI Liquid (119800), HDFC Liquid (119091). Daily NAVs from
        api.mfapi.in/mf/<code> (a mirror of AMFI's history), cross-checked against AMFI's own
        portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx file on three dates.
        Spread = (mean of the two arbitrage funds' returns) - (liquid return), per calendar year (partial years
        annualised by calendar days) and over the whole 2019-03-05..2024-06-28 window, against (a) the #212 liquid proxy
        (6.5% gross less 0.15% TER) and (b) the two real liquid funds. Direct-plan NAVs are already net of expenses.
        Deterministic S0->S1 re-run (historical path, base config, #212 simulator unchanged): the arbitrage price series
        in the simulator's context replaced by the real fund average; S0 on the proxy liquid series, and on the real
        liquid average.
ITEM 4  convergence restated: steps with |median| < Rs 10,000 use an absolute tolerance of Rs 1,000 on the p50 change
        (first 2,000 draws vs all 4,000); others keep 1% relative; P(gain>0) keeps 0.01 absolute.
ITEM 5  level comparability: base-law step medians from the paths-only run (500 paths, base parameters, historical index
        growth ~34%/yr, .cache/tax_mc/paths_only.jsonl) beside the Monte Carlo medians and #212's deterministic values.

    python pipelines/diagnostics/explore_tax_mc_amendments.py
"""
from __future__ import annotations

import json
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

MC = ROOT / ".cache" / "tax_mc"
NAV = ROOT / ".cache" / "arbitrage_nav"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_tax_mc_amendments.json"
FUNDS = {"kotak_arb": 119771, "icici_arb": 120364, "sbi_liquid": 119800, "hdfc_liquid": 119091}
WIN = ("2019-03-05", "2024-06-28")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
STEPS = (("S0", "S1"), ("S1", "S2"), ("S2", "S3"), ("S2", "S4"))
DET_212 = {"S0->S1": 48122.0, "S1->S2": 13460.0, "S2->S3": 238886.0, "S2->S4": -847439.0}


def rows(tag):
    f = MC / f"{tag}.jsonl"
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []


def q(x):
    x = np.asarray(x, float)
    return {"p5": round(float(np.percentile(x, 5)), 0), "p50": round(float(np.percentile(x, 50)), 0),
            "p95": round(float(np.percentile(x, 95)), 0), "P(gain>0)": round(float((x > 0).mean()), 4), "n": int(len(x))}


# ------------------------------------------------------------------ item 1
def item1(R) -> dict:
    out = {}
    for book in ("s60", "s65"):
        off = np.array([r["p"]["harvest_offset_days"] for r in R])
        g = np.array([r["v"][f"E|{book}"]["S2"] - r["v"][f"E|{book}"]["S1"] for r in R])
        pre, post = off <= 15, off > 15
        bins = list(range(-30, 26, 5))
        tab = []
        for lo in bins:
            hi = lo + 4 if lo < 25 else 30
            m = (off >= lo) & (off <= hi)
            tab.append({"offset": f"{lo:+d}..{hi:+d}", **q(g[m])})
        out[book] = {"pre_31_march_le_15": {**q(g[pre]), "share": round(float(pre.mean()), 4)},
                     "on_or_after_31_march_gt_15": {**q(g[post]), "share": round(float(post.mean()), 4)},
                     "bins": tab}
    return out


# ------------------------------------------------------------------ item 3
def fetch_navs() -> dict:
    NAV.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, code in FUNDS.items():
        f = NAV / f"{code}.json"
        if not f.exists():
            f.write_bytes(requests.get(f"https://api.mfapi.in/mf/{code}", headers=UA, timeout=60).content)
            time.sleep(1)
        j = json.loads(f.read_text(encoding="utf-8"))
        s = pd.Series({pd.to_datetime(d["date"], format="%d-%m-%Y"): float(d["nav"]) for d in j["data"]}).sort_index()
        out[name] = {"series": s, "scheme": j["meta"].get("scheme_name")}
    return out


def amfi_check(navs: dict) -> dict:
    res = {}
    for d in ("01-Mar-2019", "31-Dec-2021", "28-Jun-2024"):
        f = NAV / f"amfi_{d}.txt"
        if not f.exists():
            r = requests.get("https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx", params={"frmdt": d, "todt": d},
                             headers=UA, timeout=120)
            f.write_bytes(r.content)
            time.sleep(1)
        lines = f.read_text(encoding="latin-1").splitlines()
        col = lines[0].split(";").index("Net Asset Value")      # header-located; the file layout has varied over time
        got = {}
        for ln in lines:
            p = ln.split(";")
            if len(p) > col and p[0].strip().isdigit() and int(p[0]) in FUNDS.values():
                try:
                    got[int(p[0])] = float(p[col])
                except ValueError:
                    pass
        for name, code in FUNDS.items():
            mf = navs[name]["series"].get(pd.Timestamp(d))
            res[f"{name}|{d}"] = {"amfi": got.get(code), "mfapi": mf,
                                  "match": (got.get(code) is not None and mf is not None and abs(got[code] - mf) < 1e-3)}
    return res


def ann_ret(s: pd.Series, lo, hi) -> float:
    s = s[(s.index >= pd.Timestamp(lo)) & (s.index <= pd.Timestamp(hi))]
    days = (s.index[-1] - s.index[0]).days
    return float((s.iloc[-1] / s.iloc[0]) ** (365.25 / days) - 1)


def item3(navs: dict) -> dict:
    base = T.load_cfg()
    ins = base["instruments"]
    proxy_liq = (1 + ins["liquid"]["gross_return"]) * (1 - ins["liquid"]["ter"]) - 1   # annual, approx. of the daily accrual
    periods = [("2019", WIN[0], "2019-12-31"), ("2020", "2019-12-31", "2020-12-31"), ("2021", "2020-12-31", "2021-12-31"),
               ("2022", "2021-12-31", "2022-12-31"), ("2023", "2022-12-31", "2023-12-31"), ("2024H1", "2023-12-31", WIN[1]),
               ("overall", WIN[0], WIN[1])]
    tab = []
    for name, lo, hi in periods:
        r = {k: ann_ret(navs[k]["series"], lo, hi) for k in FUNDS}
        arb = (r["kotak_arb"] + r["icici_arb"]) / 2
        liq = (r["sbi_liquid"] + r["hdfc_liquid"]) / 2
        tab.append({"period": name, **{k: round(v * 100, 2) for k, v in r.items()},
                    "arb_avg": round(arb * 100, 2), "real_liquid_avg": round(liq * 100, 2), "proxy_liquid": round(proxy_liq * 100, 2),
                    "spread_vs_proxy_liquid_pp": round((arb - proxy_liq) * 100, 2),
                    "spread_vs_real_liquid_pp": round((arb - liq) * 100, 2)})
    overall = tab[-1]
    rng = (-1.5, 0.3)
    pos = {k: {"spread_pp": overall[k], "inside_drawn_range": rng[0] <= overall[k] <= rng[1],
               "percentile_in_uniform_range": round(100 * (overall[k] - rng[0]) / (rng[1] - rng[0]), 1)}
           for k in ("spread_vs_proxy_liquid_pp", "spread_vs_real_liquid_pp")}
    # deterministic S0->S1 with the real series
    ctx = T.context([base])
    idx = ctx["idx"]

    def daily_avg(keys):
        rets = [navs[k]["series"].reindex(idx.union(navs[k]["series"].index)).ffill().reindex(idx).pct_change() for k in keys]
        r = pd.concat(rets, axis=1).mean(axis=1).fillna(0.0)
        return 100 * (1 + r).cumprod()
    real_arb, real_liq = daily_avg(["kotak_arb", "icici_arb"]), daily_avg(["sbi_liquid", "hdfc_liquid"])
    det = {}
    owner = base["individual"]["owner_marginal_slab"]
    for book in ("s60", "s65"):
        s0p = T.simulate(book, base, ctx, slab=owner, cash_leg=T.LIQ)["final"]
        s1p = T.simulate(book, base, ctx, slab=owner, cash_leg=T.ARB)["final"]
        keep_arb, keep_liq = ctx["px_arb"][id(base)], ctx["px_liq"][id(base)]
        ctx["px_arb"][id(base)] = real_arb
        s1r = T.simulate(book, base, ctx, slab=owner, cash_leg=T.ARB)["final"]
        ctx["px_liq"][id(base)] = real_liq
        s0r = T.simulate(book, base, ctx, slab=owner, cash_leg=T.LIQ)["final"]
        ctx["px_arb"][id(base)], ctx["px_liq"][id(base)] = keep_arb, keep_liq
        det[book] = {"proxy_both (=#212)": round(s1p - s0p, 0), "real_arb_vs_proxy_liquid": round(s1r - s0p, 0),
                     "real_arb_vs_real_liquid": round(s1r - s0r, 0),
                     "values": {"S0_proxy": round(s0p, 0), "S1_proxy": round(s1p, 0), "S1_real_arb": round(s1r, 0), "S0_real_liquid": round(s0r, 0)}}
    return {"niftyindices": "getTotalReturnIndexString returned an HTML page for 'NIFTY 50 ARBITRAGE' (4 spellings), 2026-11-19",
            "schemes": {k: navs[k]["scheme"] for k in FUNDS}, "annual_returns_and_spreads": tab,
            "position_in_drawn_range": pos, "deterministic_S0_to_S1": det}


# ------------------------------------------------------------------ item 4
def item4(R) -> dict:
    half = R[: len(R) // 2]
    out = {}
    for book in ("s60", "s65"):
        for a, b in STEPS:
            g_all = np.array([r["v"][f"E|{book}"][b] - r["v"][f"E|{book}"][a] for r in R])
            g_h = np.array([r["v"][f"E|{book}"][b] - r["v"][f"E|{book}"][a] for r in half])
            m_all, m_h = float(np.median(g_all)), float(np.median(g_h))
            dp = abs(float((g_all > 0).mean()) - float((g_h > 0).mean()))
            if abs(m_all) < 10_000:
                rule, chg, ok = "absolute Rs 1,000", round(abs(m_h - m_all), 0), abs(m_h - m_all) <= 1000
            else:
                rule, chg, ok = "relative 1%", round(abs(m_h / m_all - 1), 4), abs(m_h / m_all - 1) < 0.01
            out[f"{book}|{a}->{b}"] = {"p50_first_half": round(m_h, 0), "p50_all": round(m_all, 0), "rule": rule,
                                       "p50_change": chg, "p50_ok": bool(ok), "P_change": round(dp, 4), "P_ok": bool(dp < 0.01)}
    return out


# ------------------------------------------------------------------ item 5
def item5(R, PO) -> dict:
    out = {}
    for book in ("s60", "s65"):
        for a, b in STEPS:
            k = f"{a}->{b}"
            mc = float(np.median([r["v"][f"E|{book}"][b] - r["v"][f"E|{book}"][a] for r in R]))
            po = float(np.median([r["v"][f"E|{book}"][b] - r["v"][f"E|{book}"][a] for r in PO]))
            out[f"{book}|{k}"] = {"mc_median_drift_6_16": round(mc, 0), "paths_only_median_hist_growth": round(po, 0),
                                  "deterministic_212": DET_212[k] if book == "s60" else None}
    return out


def main() -> int:
    R = rows("main") + rows("main_double")
    R.sort(key=lambda r: r["i"])
    PO = rows("paths_only")
    navs = fetch_navs()
    out = {"n_draws": len(R), "item1_harvest": item1(R), "item3_arbitrage": {"amfi_crosscheck": amfi_check(navs), **item3(navs)},
           "item4_convergence": item4(R), "item5_levels": item5(R, PO)}
    OUT_JSON.write_text(json.dumps(out, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, default=float)[:9000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
