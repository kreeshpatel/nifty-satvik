"""0149 — sleeve allocation between swing and low-vol: activation bound (Track P3).

Pre-registration: diagnostics/research/preregistry/0149-sleeve-allocation-bound.md (committed before this
file existed). Screen ledger row 22. No trial; nothing here changes a live weight.

TRAIN ONLY: rows after 2024-06-30 are dropped at load and never computed on. 2017-09..2018 is estimation
warm-up only; every reported number is on 2019-01-01..2024-06-30.

    python pipelines/diagnostics/diag_sleeve_allocation_0149.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SRC = ROOT / "research" / "exports" / "blend_hybrid_returns.csv"
OUT = ROOT / "diagnostics" / "research" / "sleeve_allocation" / "result.json"
EVAL_START, CUT = pd.Timestamp("2019-01-01"), pd.Timestamp("2024-06-30")
SUB = {"2019-21": ("2019-01-01", "2021-12-31"), "2022-24H1": ("2022-01-01", "2024-06-30")}
LB = 126
CONTROL = "fixed_0.60"


def load() -> pd.DataFrame:
    d = pd.read_csv(SRC, index_col=0, parse_dates=True)[["swing", "lowvol"]]
    d = d[d.index <= CUT].dropna()                       # sealed rows never enter a computation
    assert d.index.max() <= CUT
    return d


def _w_swing(rule: str, hist: pd.DataFrame) -> float:
    """Swing weight from data strictly before the rebalance. Pure."""
    if rule.startswith("fixed_"):
        return float(rule.split("_")[1])
    h = hist.tail(LB)
    if len(h) < LB // 2:
        return 0.60                                      # warm-up: hold the control until estimable
    sd = h.std().to_numpy()
    cov = h.cov().to_numpy()
    if rule == "invvol_126":
        w = (1 / sd) / (1 / sd).sum()
    elif rule == "minvar_126":
        a, b, c = cov[0, 0], cov[1, 1], cov[0, 1]
        w0 = (b - c) / (a + b - 2 * c) if (a + b - 2 * c) > 0 else 0.5
        w = np.array([w0, 1 - w0])
    elif rule == "maxdiv_126":
        raw = np.linalg.solve(cov, sd)
        w = raw / raw.sum() if raw.sum() > 0 else np.array([0.5, 0.5])
    else:
        raise ValueError(rule)
    return float(np.clip(w[0], 0.0, 1.0))


def simulate(d: pd.DataFrame, rule: str) -> tuple[pd.Series, pd.Series]:
    """Quarterly-rebalanced, drift-between-rebalances two-sleeve book. Returns (daily return, swing weight)."""
    q_start = d.index.to_series().groupby(d.index.to_period("Q")).transform("min")
    reb = set(q_start.unique())
    rets, ws = [], []
    w = None
    vals = None
    for t, row in d.iterrows():
        if w is None or t in reb:
            w = _w_swing(rule, d[d.index < t])
            vals = np.array([w, 1 - w])
        r = np.array([row["swing"], row["lowvol"]])
        port = float((vals * r).sum() / vals.sum())
        vals = vals * (1 + r)
        rets.append(port)
        ws.append(vals[0] / vals.sum())
    return pd.Series(rets, index=d.index), pd.Series(ws, index=d.index)


def stats(r: pd.Series, lo, hi) -> dict:
    x = r[(r.index >= pd.Timestamp(lo)) & (r.index <= pd.Timestamp(hi))]
    e = (1 + x).cumprod()
    yrs = (x.index[-1] - x.index[0]).days / 365.25
    yearly = (1 + x).groupby(x.index.year).prod() - 1
    return {"sharpe": float(x.mean() / x.std() * np.sqrt(252)), "maxdd_pct": float((e / e.cummax() - 1).min() * 100),
            "cagr_pct": float((e.iloc[-1] ** (1 / yrs) - 1) * 100), "worst_year_pct": float(yearly.min() * 100)}


def main() -> int:
    from nq.runner.research import adjudicate_family

    d = load()
    rules = ["fixed_0.60", "fixed_0.50", "invvol_126", "minvar_126", "maxdiv_126"]
    res: dict = {"eval_window": [str(EVAL_START.date()), str(CUT.date())], "last_row_used": str(d.index.max().date()),
                 "rules": {}}
    curves = {}
    for rule in rules:
        r, w = simulate(d, rule)
        r_eval, w_eval = r[r.index >= EVAL_START], w[w.index >= EVAL_START]
        curves[rule] = r_eval
        res["rules"][rule] = {"full": stats(r_eval, EVAL_START, CUT),
                              "sub": {k: stats(r_eval, *v) for k, v in SUB.items()},
                              "swing_weight_mean": float(w_eval.mean()),
                              "swing_weight_range": [float(w_eval.min()), float(w_eval.max())]}
    # adjudicate_family takes the simulate() contract: a list of {date, equity} records.
    fam = adjudicate_family({k: {"equity_curve": [{"date": str(t.date()), "equity": float(e)}
                                                  for t, e in (1 + v).cumprod().items()]}
                             for k, v in curves.items()})
    res["family"] = {k: fam.get(k) for k in ("pbo", "selection_informative", "n_configs") if k in fam}
    c = res["rules"][CONTROL]
    res["vs_control"] = {}
    for rule in rules[1:]:
        a = res["rules"][rule]
        dsub = {k: round(a["sub"][k]["sharpe"] - c["sub"][k]["sharpe"], 3) for k in SUB}
        ds = a["full"]["sharpe"] - c["full"]["sharpe"]
        ddd = a["full"]["maxdd_pct"] - c["full"]["maxdd_pct"]          # positive = shallower
        ok = ds >= 0.10 and ddd >= 0 and all(v > 0 for v in dsub.values()) and (res["family"].get("pbo", 1) < 0.5)
        res["vs_control"][rule] = {"d_sharpe": round(ds, 3), "d_maxdd_pp": round(ddd, 2),
                                   "d_cagr_pp": round(a["full"]["cagr_pct"] - c["full"]["cagr_pct"], 2),
                                   "d_sharpe_by_sub": dsub,
                                   "reading": "ELIGIBLE for a watched forward book proposal" if ok
                                   else "BOUND RECORDED — the 0.60 control stays"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    for rule, a in res["rules"].items():
        f = a["full"]
        print(f"{rule:<11} Sharpe {f['sharpe']:.3f} DD {f['maxdd_pct']:.1f}% CAGR {f['cagr_pct']:.1f}% "
              f"worst yr {f['worst_year_pct']:.1f}% | w_swing mean {a['swing_weight_mean']:.2f} "
              f"[{a['swing_weight_range'][0]:.2f},{a['swing_weight_range'][1]:.2f}]")
    for rule, v in res["vs_control"].items():
        print(f"  vs 0.60: {rule:<11} dSharpe {v['d_sharpe']:+.3f} dDD {v['d_maxdd_pp']:+.2f}pp "
              f"dCAGR {v['d_cagr_pp']:+.2f}pp sub {v['d_sharpe_by_sub']} -> {v['reading']}")
    print(f"family: {res['family']} | last row used {res['last_row_used']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
