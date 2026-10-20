"""EXPLORATORY (tier 0, zero trials): information discreteness (FIP) as a within-week seat key.

Reuses the 0150 Part-1 substrate: uncapped, all-grades, live-config, PIT-membership replay; trades grouped by
ISO week of fill. For each filled trade, over the 63 sessions BEFORE the entry session (PIT):
    ID = sign(formation return) * (%negative days - %positive days)      (lower = smoother = better)
Score = -ID. Reports within-week rank IC vs R (week-clustered bootstrap), mean R of the 5 smoothest vs the rest
in the same weeks, by sub-period, the CRS IC on the same set, and the correlation of ID with extension.

TRAIN ONLY: every price series is cut at 2024-06-30 before the engine sees it; asserted.

    python pipelines/diagnostics/diag_fip_seat_key.py
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

START, CUT = "2019-01-01", "2024-06-30"
SUB = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", CUT)}
N_BOOT, SEED, FORM = 5000, 20261020, 63
OUT = ROOT / "diagnostics" / "research" / "engine_assumptions" / "fip_seat_key.json"


def week_key(d) -> str:
    iso = pd.Timestamp(d).isocalendar()
    return f"{int(iso.year)}-W{int(iso.week):02d}"


def fip_and_ext(row, df: pd.DataFrame) -> tuple[float, float, float]:
    """(ID, formation return, extension over the 44w SMA of completed weeks before entry) - all PIT."""
    ed = pd.Timestamp(row.entry_date)
    c = df["Close"][df.index < ed]                       # sessions strictly before the entry session
    if len(c) < FORM + 1:
        return np.nan, np.nan, np.nan
    w = c.iloc[-(FORM + 1):]
    ret = w.pct_change().dropna()
    pret = float(w.iloc[-1] / w.iloc[0] - 1)
    idv = float(np.sign(pret) * ((ret < 0).mean() - (ret > 0).mean()))
    wk = c.resample("W-FRI").last().dropna()
    wk = wk[wk.index < ed - pd.Timedelta(days=ed.weekday())]   # weeks that ended before the entry week began
    ext = float(row.entry / wk.iloc[-44:].mean() - 1) if len(wk) >= 44 else np.nan
    return idv, pret, ext


def wspear(x, y) -> float:
    if len(x) < 3 or np.unique(y).size < 2 or np.unique(x).size < 2:
        return np.nan
    return float(pd.Series(x).corr(pd.Series(y), method="spearman"))


def per_week(L: pd.DataFrame, score: str) -> pd.DataFrame:
    """One row per week: ic, and sums for the top-5-vs-rest edge (weeks with both groups only)."""
    rows = []
    for w, g in L.groupby("week"):
        ic = wspear(g[score].to_numpy(), g["R"].to_numpy())
        rk = g[score].rank(ascending=False, method="first")
        a, r = g[rk <= 5]["R"], g[rk > 5]["R"]
        rows.append((w, ic, a.sum(), len(a), r.sum(), len(r)))
    return pd.DataFrame(rows, columns=["week", "ic", "sA", "nA", "sR", "nR"]).set_index("week")


def summarise(W: pd.DataFrame, rng) -> dict:
    ic = W["ic"].dropna()
    both = W[(W.nA > 0) & (W.nR > 0)]
    edge = both.sA.sum() / both.nA.sum() - both.sR.sum() / both.nR.sum() if len(both) else np.nan
    ics, edges = [], []
    iv, bv = W["ic"].to_numpy(), both[["sA", "nA", "sR", "nR"]].to_numpy()
    for _ in range(N_BOOT):
        p = rng.integers(0, len(iv), len(iv))
        x = iv[p]
        x = x[~np.isnan(x)]
        if len(x):
            ics.append(x.mean())
        if len(bv):
            q = bv[rng.integers(0, len(bv), len(bv))].sum(axis=0)
            if q[1] and q[3]:
                edges.append(q[0] / q[1] - q[2] / q[3])
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if v else None  # noqa: E731
    return {"n_weeks_ic": int(len(ic)), "ic_mean": float(ic.mean()), "ic_ci95": ci(ics),
            "n_weeks_edge": int(len(both)), "edge_top5_minus_rest": float(edge), "edge_ci95": ci(edges),
            "meanR_top5": float(both.sA.sum() / both.nA.sum()), "meanR_rest": float(both.sR.sum() / both.nR.sum())}


def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe

    ohlcv = corrected_universe()
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(CUT)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    last = max(df.index.max() for df in cut.values())
    assert last <= pd.Timestamp(CUT), f"sealed data reached the engine: {last}"
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    mem = load_membership()
    led: list = []
    R94.backtest(P, mem, ledger=led, uncapped=True, a_grade=None, **LIVE_DISCIPLINE, **LIVE_STALENESS,
                 demerger_events=events, start=START, **LIVE_EXIT)
    L = pd.DataFrame(led)
    L = L[pd.to_datetime(L["entry_date"]) >= pd.Timestamp(START)].reset_index(drop=True)
    L["week"] = L["entry_date"].map(week_key)
    f = [fip_and_ext(r, cut[r.tkr]) for r in L.itertuples(index=False)]
    L["ID"], L["pret"], L["ext"] = [x[0] for x in f], [x[1] for x in f], [x[2] for x in f]
    L["fip_score"] = -L["ID"]
    n_all = len(L)
    L = L.dropna(subset=["ID", "R"]).reset_index(drop=True)
    L["ext_score"] = -L["ext"]                      # lower extension = closer to the line
    L["ext_score"] = L["ext_score"].fillna(L["ext_score"].median())
    res: dict = {"label": "EXPLORATORY (tier 0, zero trials)", "window": [START, CUT], "last_bar_seen": str(last.date()),
                 "n_trades": int(len(L)), "n_dropped_insufficient_history": int(n_all - len(L)),
                 "n_weeks": int(L.week.nunique()), "meanR_all": float(L.R.mean())}
    sets = {"all": L}
    for k, (lo, hi) in SUB.items():
        d = pd.to_datetime(L.entry_date)
        sets[k] = L[(d >= pd.Timestamp(lo)) & (d <= pd.Timestamp(hi))]
    for name, s in sets.items():
        rng = np.random.default_rng(SEED + len(name))
        out = {"n": int(len(s))}
        for key, col in (("fip(-ID)", "fip_score"), ("crs", "rank"), ("neg_ext", "ext_score")):
            out[key] = summarise(per_week(s, col), rng)
        out["corr_ID_vs_ext_spearman_pooled"] = float(s["ID"].corr(s["ext"], method="spearman"))
        wc = s.groupby("week").apply(lambda g: wspear(g["ID"].to_numpy(), g["ext"].to_numpy())).dropna()
        out["corr_ID_vs_ext_within_week_mean"] = float(wc.mean())
        out["corr_ID_vs_crs_spearman_pooled"] = float(s["ID"].corr(s["rank"], method="spearman"))
        out["corr_ext_vs_R_spearman_pooled"] = float(s["ext"].corr(s["R"], method="spearman"))
        for lbl, m in (("ext<5%", s.ext < 0.05), ("ext>=5%", s.ext >= 0.05)):
            g = s[m]
            wk_ic = g.groupby("week").apply(lambda x: wspear(x["fip_score"].to_numpy(), x["R"].to_numpy())).dropna()
            out[f"fip_ic_within_{lbl}"] = {"n": int(len(g)), "weeks": int(len(wk_ic)),
                                           "ic_mean": float(wk_ic.mean()) if len(wk_ic) else None}
        res[name] = out
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    for name in sets:
        o = res[name]
        print(f"[{name}] n={o['n']}")
        for key in ("fip(-ID)", "crs", "neg_ext"):
            s = o[key]
            print(f"  {key:9s} IC {s['ic_mean']:+.3f} {s['ic_ci95']} | top5-rest {s['edge_top5_minus_rest']:+.3f} {s['edge_ci95']}"
                  f" (top5 {s['meanR_top5']:+.3f} rest {s['meanR_rest']:+.3f}, {s['n_weeks_edge']} wks)")
        print(f"  ID~ext pooled {o['corr_ID_vs_ext_spearman_pooled']:+.3f} within-wk {o['corr_ID_vs_ext_within_week_mean']:+.3f}"
              f" | ID~crs {o['corr_ID_vs_crs_spearman_pooled']:+.3f} | ext~R {o['corr_ext_vs_R_spearman_pooled']:+.3f}")
        print(f"  fip IC ext<5%: {o['fip_ic_within_ext<5%']} ; ext>=5%: {o['fip_ic_within_ext>=5%']}")
    print(f"-> {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
