"""ENG-02 — does a turnover-rank universe read the same as real PIT index membership?

Criteria were pre-stated in `research/eng-02-membership-proxy.md` BEFORE this ran. Measurement only:
nothing is evaluated for adoption, no configuration competes, and `n_trials` does not move.

Gate A  set recovery — proxy MID band vs actual MID constituents, month by month, 2019-2026. >= 85%.
Gate B  functional agreement — frozen 0001 on real vs proxy membership. The decisive one.
          CAGR within +-0.75pp · dSharpe-vs-control CIs overlap · MaxDD within +-5pp

    python pipelines/diagnostics/diag_membership_proxy.py
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
sys.path.insert(0, str(ROOT / "pipelines" / "research"))
from nq.data.membership import load_membership  # noqa: E402
from nq.runner.research import adjudicate  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from run_0001_xsec_momentum import BAND, add_signals, random_control, run  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# 2019 onward: the period where PIT membership is trustworthy (pre-2018 is back-extended).
START, END = "2019-01-01", "2026-06-30"
PROXY_N = 500          # the Nifty-500 stand-in: top N by trailing rupee turnover
OUT = ROOT / "diagnostics" / "research" / "membership_proxy.json"

RECOVERY_FLOOR = 0.85
CAGR_TOL_PP = 0.75
DD_TOL_PP = 5.0


def proxy_membership(p: pd.DataFrame, n: int = PROXY_N) -> pd.Series:
    """Boolean mask: is this (date, ticker) inside the top-N by trailing turnover that day?

    This is the whole instrument. It uses only information bhavcopy carries — what traded, and how
    much — so it is computable pre-2017 where index constituent lists are not.
    """
    r = p.groupby("date")["turnover_63d"].rank(ascending=False, method="first")
    return r <= n


def gate_a(p: pd.DataFrame) -> dict:
    """Month-by-month recovery of the actual MID band by the proxy MID band."""
    q = p.copy()
    q["proxy_member"] = proxy_membership(q)
    # band within each membership definition, exactly as build_universe does: turnover rank among
    # that definition's own eligible names
    q["real_ok"] = q["is_member"] & q["liq_ok"] & q["hist_ok"] & q["price_ok"] & q["circuit_ok"]
    q["prox_ok"] = q["proxy_member"] & q["liq_ok"] & q["hist_ok"] & q["price_ok"] & q["circuit_ok"]

    rows = []
    for month, g in q.groupby(q["date"].dt.to_period("M")):
        real = _mid_set(g, "real_ok")
        prox = _mid_set(g, "prox_ok")
        if not real:
            continue
        rows.append({"month": str(month), "n_real": len(real), "n_proxy": len(prox),
                     "recovered": len(real & prox) / len(real),
                     "jaccard": len(real & prox) / max(len(real | prox), 1)})
    df = pd.DataFrame(rows)
    rec = df["recovered"]
    return {"months": len(df), "mean_recovery": float(rec.mean()),
            "median_recovery": float(rec.median()), "min_recovery": float(rec.min()),
            "p10_recovery": float(rec.quantile(0.10)),
            "months_below_floor": int((rec < RECOVERY_FLOOR).sum()),
            "mean_jaccard": float(df["jaccard"].mean()),
            "worst_months": df.nsmallest(5, "recovered").to_dict("records"),
            "pass": bool(rec.mean() >= RECOVERY_FLOOR and rec.quantile(0.10) >= RECOVERY_FLOOR)}


def _mid_set(g: pd.DataFrame, ok_col: str) -> set:
    """The MID band (turnover rank 101-250) among rows eligible under one membership definition."""
    e = g[g[ok_col]]
    if e.empty:
        return set()
    last = e[e["date"] == e["date"].max()]
    rk = last["turnover_63d"].rank(ascending=False, method="first")
    return set(last.loc[(rk > 100) & (rk <= 250), "ticker"])


def _band_panel(p: pd.DataFrame, ok_col: str) -> pd.DataFrame:
    """A 0001-shaped panel under one membership definition: rank gated, rows never filtered."""
    q = p.copy()
    rk = q[q[ok_col]].groupby("date")["turnover_63d"].rank(ascending=False, method="first")
    q["band_rank"] = rk.reindex(q.index)
    q["in_mid"] = q[ok_col] & q["band_rank"].between(101, 250)
    ever = q.loc[q["in_mid"], "ticker"].unique()
    b = q[q["ticker"].isin(ever)].copy()
    b["rank"] = np.where(b["in_mid"] & b["nms"].notna(), b["nms"], np.nan)
    return b


def gate_b(p: pd.DataFrame) -> dict:
    """Frozen 0001 on real vs proxy membership — same engine, same window, one thing changed."""
    out = {}
    for tag, ok_col in (("real", "real_ok"), ("proxy", "prox_ok")):
        band = _band_panel(p, ok_col)
        cand = run(band, )
        ctrl = run(random_control(band))
        v = adjudicate(ctrl, cand, initial_capital=1_000_000.0, sub_start="2022-01-01", end=END)
        m = cand["metrics"]
        out[tag] = {"cagr_pct": m["cagr_pct"], "sharpe": m["sharpe"],
                    "max_drawdown_pct": m["max_drawdown_pct"], "n_trades": m["n_trades"],
                    "names_ever": int(band["ticker"].nunique()),
                    "rankable_per_day": float(band[band["rank"].notna()]
                                              .groupby("date")["ticker"].nunique().mean()),
                    "dSharpe": v.get("dSharpe"), "dSharpe_ci": v.get("dSharpe_ci")}
    r, x = out["real"], out["proxy"]
    d_cagr = x["cagr_pct"] - r["cagr_pct"]
    d_dd = x["max_drawdown_pct"] - r["max_drawdown_pct"]
    ci_r, ci_x = r.get("dSharpe_ci"), x.get("dSharpe_ci")
    overlap = bool(ci_r and ci_x and ci_r[0] <= ci_x[1] and ci_x[0] <= ci_r[1])
    out["comparison"] = {
        "d_cagr_pp": round(d_cagr, 3), "d_maxdd_pp": round(d_dd, 3), "ci_overlap": overlap,
        "cagr_ok": bool(abs(d_cagr) <= CAGR_TOL_PP), "dd_ok": bool(abs(d_dd) <= DD_TOL_PP)}
    out["pass"] = bool(out["comparison"]["cagr_ok"] and out["comparison"]["dd_ok"] and overlap)
    return out


def main() -> int:
    print("=== ENG-02 — membership proxy validation ===")
    print(f"    criteria pre-stated in research/eng-02-membership-proxy.md · window {START}..{END}")
    print("    measurement only — nothing evaluated for adoption, n_trials unchanged\n")

    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    p["proxy_member"] = proxy_membership(p)
    p["real_ok"] = p["is_member"] & p["liq_ok"] & p["hist_ok"] & p["price_ok"] & p["circuit_ok"]
    p["prox_ok"] = p["proxy_member"] & p["liq_ok"] & p["hist_ok"] & p["price_ok"] & p["circuit_ok"]

    print("=== GATE A — set recovery (floor 85% mean AND 85% at the 10th pctile month) ===")
    a = gate_a(p)
    print(f"  months {a['months']} · mean {a['mean_recovery']:.1%} · median "
          f"{a['median_recovery']:.1%} · p10 {a['p10_recovery']:.1%} · min {a['min_recovery']:.1%}")
    print(f"  months below the floor: {a['months_below_floor']} · mean Jaccard {a['mean_jaccard']:.1%}")
    print(f"  worst months: " + ", ".join(f"{w['month']} {w['recovered']:.0%}"
                                          for w in a["worst_months"]))
    print(f"  GATE A: {'PASS' if a['pass'] else 'FAIL'}")

    print("\n=== GATE B — functional agreement (the decisive one) ===")
    b = gate_b(p)
    for tag in ("real", "proxy"):
        m = b[tag]
        print(f"  {tag:<6} CAGR {m['cagr_pct']:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
              f"MaxDD {m['max_drawdown_pct']:>7.2f}%  trades {m['n_trades']:>5}  "
              f"names {m['names_ever']:>4}  rankable/day {m['rankable_per_day']:.0f}")
        print(f"         dSharpe vs control {m['dSharpe']} CI {m['dSharpe_ci']}")
    c = b["comparison"]
    print(f"\n  dCAGR {c['d_cagr_pp']:+.3f}pp (tol +-{CAGR_TOL_PP}) -> {'ok' if c['cagr_ok'] else 'FAIL'}")
    print(f"  dMaxDD {c['d_maxdd_pp']:+.3f}pp (tol +-{DD_TOL_PP}) -> {'ok' if c['dd_ok'] else 'FAIL'}")
    print(f"  dSharpe CIs overlap -> {'ok' if c['ci_overlap'] else 'FAIL'}")
    print(f"  GATE B: {'PASS' if b['pass'] else 'FAIL'}")

    verdict = "PROCEED" if (a["pass"] and b["pass"]) else "DO NOT BUILD THE LOCKBOX ON THIS PROXY"
    print(f"\n=== VERDICT: {verdict} ===")
    if not (a["pass"] and b["pass"]):
        print("  Per the pre-statement: diagnose WHERE the proxy diverges before deciding anything.")
        print("  Prior is the rank-100/101 band boundary, which churns constantly.")

    OUT.write_text(json.dumps({"window": [START, END], "proxy_n": PROXY_N,
                               "gate_a": a, "gate_b": b, "verdict": verdict},
                              indent=2, default=str), encoding="utf-8")
    print(f"\n  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
