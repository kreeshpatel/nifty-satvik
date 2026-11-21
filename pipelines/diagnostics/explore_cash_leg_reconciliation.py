"""MEASUREMENT: cash-leg reconciliation of the long-window static 60/40 study, and the index leg's tracking difference.

(1) The study of record (explore_static_long_window_alpha.py, 2026-11-19) built its arbitrage cash leg as the equal
    average of the daily returns of Kotak Arbitrage 119771 and ICICI Prudential Arbitrage 120364 (prices_on, lines
    135-142). The 60/40 forward record holds 119771 only. This re-runs the static mixes 55/45, 60/40 and 65/35 on
    2017-01..2026-06 with the cash leg = 119771 alone, with the study's own run/met functions unchanged, and
    reproduces the study's two-fund figures first as the anchor.
(2) Index leg: the study's index fund is the Nifty Midcap150 Momentum 50 TRI less 0.30%/yr TER, accrued daily. The
    forward record holds Tata Nifty Midcap 150 Momentum 50 Index Fund Direct-Growth (AMFI 150738). Over the fund's
    life (first NAV 2022-10-31) to the TRI file's last date, report per calendar year (partial years marked):
    fund return, TRI return, modelled return (TRI less TER), and the tracking differences fund-TRI and fund-model.
    Both series are compared on the dates where both exist (fund NAV forward-filled onto TRI sessions is NOT used;
    the common-date intersection is).

NAVs: 119771 and 150738 from the pinned mfapi snapshots in diagnostics/replica/phase0/nav_20261120/ (fetched
2026-11-20); 120364 from .cache/arbitrage_nav (the study's own cache).

    python pipelines/diagnostics/explore_cash_leg_reconciliation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import explore_after_tax_comparison as AT  # noqa: E402
import explore_after_tax_frontier as F  # noqa: E402
import explore_static_long_window_alpha as L  # noqa: E402

PIN = ROOT / "diagnostics" / "replica" / "phase0" / "nav_20261120"
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-20_cash_leg_reconciliation.json"
MIXES = [0.55, 0.60, 0.65]


def nav(path: Path) -> pd.Series:
    j = json.loads(path.read_text(encoding="utf-8"))
    return pd.Series({pd.to_datetime(d["date"], format="%d-%m-%Y"): float(d["nav"]) for d in j["data"]}).sort_index()


def main() -> int:
    tri = pd.read_csv(AT.TRI, parse_dates=["date"]).set_index("date")["tri"].astype(float)
    idx = pd.DatetimeIndex(tri.index[(tri.index >= pd.Timestamp(L.FULL[0])) & (tri.index <= pd.Timestamp(L.FULL[1]))]).normalize()
    funds = {"kotak_119771": nav(PIN / "119771.json"),
             "icici_120364": nav(ROOT / ".cache" / "arbitrage_nav" / "120364.json")}

    def prices_on(ix, keys):
        r = tri.pct_change().reindex(ix).fillna(0.0)
        r.iloc[0] = 0.0
        p_ix = (1 + r - AT.TER_INDEX / 252).cumprod() * 100
        rets = [funds[k].reindex(ix.union(funds[k].index)).ffill().reindex(ix).pct_change() for k in keys]
        p_arb = 100 * (1 + pd.concat(rets, axis=1).mean(axis=1).fillna(0.0)).cumprod()
        return {AT.IDX: p_ix, F.ARB: p_arb}

    out = {"class": "MEASUREMENT", "counts": "screens 25 / sealed opens 4 / n_trials 3 (unchanged)",
           "window": [str(idx[0].date()), str(idx[-1].date())], "sessions": int(len(idx))}
    study = json.loads((ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_static_long_window_alpha.json").read_text())
    srows = {r["mix"]: r for r in study["step1_static_mixes"]["rows"]}
    legs = {"two_fund_average (study of record)": ["kotak_119771", "icici_120364"], "kotak_119771_only (forward record)": ["kotak_119771"]}
    res = {}
    for name, keys in legs.items():
        px = prices_on(idx, keys)
        rows = {}
        for w in MIXES:
            mix = f"{int(w*100)}/{int(round((1-w)*100))}"
            r = F.run("static", idx, px, w_static=w, cash=F.ARB)
            m = F.met(r)
            sl = r["mtm"][r["mtm"].index >= pd.Timestamp("2024-07-01")]
            rows[mix] = {"after_tax_cagr": m["after_tax_cagr"], "p95_dd156": m["p95_dd156"], "passes": m["passes_cap"],
                         "worst_daily_dd": m["worst_daily_dd"],
                         "slice_2024_07_2026_06_cagr_mtm": L.cagr_nav(sl), "slice_2024_07_2026_06_p95": L.p95(sl)}
        res[name] = {"cash_leg_cagr_pct": L.cagr_nav(px[F.ARB]), "rows": rows}
        print(name, json.dumps(res[name]), flush=True)
    anc = res["two_fund_average (study of record)"]["rows"]["60/40"]
    exp = srows["60/40"]["full"]
    anchor_ok = abs(anc["after_tax_cagr"] - exp["after_tax_cagr"]) < 0.005 and abs(anc["p95_dd156"] - exp["p95_dd156"]) < 0.005
    out["anchor"] = {"expected_60_40": [exp["after_tax_cagr"], exp["p95_dd156"]],
                     "reproduced": [anc["after_tax_cagr"], anc["p95_dd156"]], "match": bool(anchor_ok)}
    if not anchor_ok:
        OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
        raise SystemExit("anchor miss: stop")
    out["static_mixes"] = res

    # (2) index leg: fund 150738 vs TRI and TRI less TER, common dates
    f = nav(PIN / "150738.json")
    tri_all = tri.copy()
    tri_all.index = pd.DatetimeIndex(tri_all.index).normalize()
    model = (1 + tri_all.pct_change().fillna(0.0) - AT.TER_INDEX / 252).cumprod()
    common = f.index.intersection(tri_all.index)
    common = common[common >= f.index[0]]
    fs, ts, ms = f.reindex(common), tri_all.reindex(common), model.reindex(common)
    years = []
    for y in sorted(set(common.year)):
        prior = common[common.year < y]
        start = prior[-1] if len(prior) else common[0]
        end = common[common.year == y][-1]
        rf, rt, rm = fs[end] / fs[start] - 1, ts[end] / ts[start] - 1, ms[end] / ms[start] - 1
        years.append({"year": int(y), "from": str(start.date()), "to": str(end.date()),
                      "partial": bool(start.year < y - 1 or start.month != 12 or end.month != 12 or end.day < 24),
                      "fund_pct": 100 * rf, "tri_pct": 100 * rt, "tri_less_ter_pct": 100 * rm,
                      "td_fund_minus_tri_pp": 100 * (rf - rt), "td_fund_minus_model_pp": 100 * (rf - rm)})
    yrs = (common[-1] - common[0]).days / 365.25
    ann = lambda s: 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1)  # noqa: E731
    dr = pd.concat([fs.pct_change(), ts.pct_change()], axis=1).dropna()
    out["index_leg"] = {"fund": "150738 Tata Nifty Midcap 150 Momentum 50 Index Fund Direct-Growth",
                        "span": [str(common[0].date()), str(common[-1].date())], "common_dates": int(len(common)),
                        "by_year": years,
                        "annualised": {"fund_pct": ann(fs), "tri_pct": ann(ts), "tri_less_ter_pct": ann(ms),
                                       "td_fund_minus_tri_pp": ann(fs) - ann(ts), "td_fund_minus_model_pp": ann(fs) - ann(ms)},
                        "tracking_error_ann_pct": float(100 * (dr.iloc[:, 0] - dr.iloc[:, 1]).std() * 252 ** 0.5)}
    # (3) ADDED AFTER FIRST LOOK: 60/40 with the index leg's drag raised by the measured fund-minus-model shortfall,
    # cash leg = 119771 only. A sensitivity, not a new figure of record.
    extra = -out["index_leg"]["annualised"]["td_fund_minus_model_pp"] / 100
    px = prices_on(idx, ["kotak_119771"])
    px[AT.IDX] = px[AT.IDX] * (1 - extra / 252) ** pd.Series(range(len(idx)), index=px[AT.IDX].index)
    sens = {}
    for w in MIXES:
        mix = f"{int(w*100)}/{int(round((1-w)*100))}"
        m = F.met(F.run("static", idx, px, w_static=w, cash=F.ARB))
        sens[mix] = {"after_tax_cagr": m["after_tax_cagr"], "p95_dd156": m["p95_dd156"], "passes": m["passes_cap"]}
    out["added_after_first_look_index_drag_sensitivity"] = {"extra_drag_pp_per_year": 100 * extra, "cash_leg": "119771 only",
                                                            "rows": sens}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(sens))
    print(json.dumps(out["anchor"]), json.dumps(out["index_leg"]["annualised"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
