"""Verification audit 2026Q3 — session 2, item 2: alpha decomposition. VERIFICATION CLASS.

Zero trials, zero new screens, no new hypotheses. Counts frozen (14 / 1 / 138). Sealed set not
re-opened. Judge log not read.

This is an ATTRIBUTION of books that already exist, not a strategy question. It answers the one
sentence an investor actually asks: **what did this earn over the index fund, and when?**

0114 (passive hurdle) answered a NEIGHBOURING question and is re-verified here by reading its own
stated method: it compared the swing book's **monthly, after-tax NET** returns against **investable
ETF NAVs**, because the niftyindices TRI endpoint was WAF-blocked on 2026-07-27. It reported
after-tax CAGR margins, **not beta or alpha**. So the decomposition below is additive rather than a
re-run: same books, different and more standard lens (regression against a total-return index).

Method, stated plainly so it can be attacked:
  * benchmark  = Nifty-500 **TRI** (`research/exports/benchmark_nifty500_tri.csv`) — total return,
                 so dividends are in the benchmark and the comparison is not flattered.
  * regression = daily excess-of-zero returns, book on benchmark: r_book = alpha + beta * r_bench.
                 Alpha is reported ANNUALISED (alpha_daily * 252).
  * per-year   = the same regression re-run within each calendar year, so a single year cannot
                 carry the headline unnoticed.
  * risk-free  = ZERO throughout, stated rather than hidden. With an Indian RF near 6-7%, a
                 zero-RF alpha OVERSTATES true excess return; the direction of the bias is named.

Reproduce:
    python scripts/audit_alpha_decomposition_2026Q3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "diagnostics" / "research" / "verification_audit_2026Q3"
TRI = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"
SLEEVES = ROOT / "research" / "exports" / "third_sleeve_returns.csv"
TRADING_DAYS = 252


def ols(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float, float, int]:
    """alpha, beta, se(alpha), r2, n — plain least squares, no library shortcuts."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = y.size
    if n < 30:
        return (np.nan,) * 4 + (n,)
    X = np.column_stack([np.ones(n), x])
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    a, b = float(beta_hat[0]), float(beta_hat[1])
    resid = y - X @ beta_hat
    dof = n - 2
    s2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.inv(X.T @ X)
    se_a = float(np.sqrt(s2 * xtx_inv[0, 0]))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else np.nan
    return a, b, se_a, r2, n


def decompose(book: pd.Series, bench: pd.Series, label: str) -> dict:
    df = pd.concat([book.rename("b"), bench.rename("m")], axis=1).dropna()
    a, beta, se_a, r2, n = ols(df["b"].to_numpy(float), df["m"].to_numpy(float))
    ann_a, ann_se = a * TRADING_DAYS, se_a * TRADING_DAYS
    yrs = max((df.index[-1] - df.index[0]).days / 365.25, 1e-9)
    bk_cagr = (1 + df["b"]).prod() ** (1 / yrs) - 1
    mk_cagr = (1 + df["m"]).prod() ** (1 / yrs) - 1

    per_year = []
    for y, g in df.groupby(df.index.year):
        ay, by, se_y, _, ny = ols(g["b"].to_numpy(float), g["m"].to_numpy(float))
        per_year.append({
            "year": int(y), "n_days": int(ny),
            "alpha_ann_pct": None if np.isnan(ay) else round(100 * ay * TRADING_DAYS, 2),
            "beta": None if np.isnan(by) else round(by, 3),
            "book_ret_pct": round(100 * ((1 + g["b"]).prod() - 1), 2),
            "bench_ret_pct": round(100 * ((1 + g["m"]).prod() - 1), 2),
        })
    pos = [p for p in per_year if (p["alpha_ann_pct"] or 0) > 0]
    contrib = sorted(per_year, key=lambda p: -(p["alpha_ann_pct"] or 0))[:2]
    return {
        "book": label, "n_days": n, "span_years": round(yrs, 2),
        "beta_vs_nifty500_TRI": round(beta, 3), "r_squared": round(r2, 3),
        "alpha_annual_pct": round(100 * ann_a, 2),
        "alpha_annual_se_pct": round(100 * ann_se, 2),
        "alpha_t_stat": round(ann_a / ann_se, 2) if ann_se > 0 else None,
        "alpha_95ci_pct": [round(100 * (ann_a - 1.96 * ann_se), 2),
                           round(100 * (ann_a + 1.96 * ann_se), 2)],
        "book_cagr_pct": round(100 * bk_cagr, 2),
        "bench_cagr_pct": round(100 * mk_cagr, 2),
        "raw_cagr_gap_pct": round(100 * (bk_cagr - mk_cagr), 2),
        "years_with_positive_alpha": f"{len(pos)}/{len(per_year)}",
        "top2_alpha_years": [p["year"] for p in contrib],
        "per_year": per_year,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tri = pd.read_csv(TRI, parse_dates=["date"]).set_index("date")["tri_close"].sort_index()
    bench = tri.pct_change().dropna()
    sl = pd.read_csv(SLEEVES, index_col=0, parse_dates=True).sort_index()

    books = {}
    for col, label in (("swing", "swing sleeve (sole-ranker panel)"),
                       ("lowvol", "low-vol sleeve (sole-ranker panel)")):
        if col in sl.columns:
            books[col] = decompose(sl[col].dropna(), bench, label)

    # the two-sleeve pair, equal-weight — the simplest form of the structure of record
    if {"swing", "lowvol"} <= set(sl.columns):
        pair = sl[["swing", "lowvol"]].dropna().mean(axis=1)
        books["pair_ew"] = decompose(pair, bench, "swing+lowvol equal-weight")

    res = {
        "_doc": "Verification audit 2026Q3 session 2 — item 2, alpha decomposition vs Nifty-500 TRI.",
        "class": "VERIFICATION / ATTRIBUTION — 0 trials, 0 screens, no new hypotheses",
        "counts": "screens 14 · sealed opens 1 · n_trials 138 (frozen)",
        "0114_reverification": {
            "what_0114_measured": "swing book MONTHLY after-tax NET returns vs investable ETF NAVs "
                                  "(LowVol-30, AlphaLowVol-30, Nifty-50), after-tax margins",
            "what_0114_did_NOT_measure": "beta, alpha, or any regression against a total-return index",
            "why": "0114 records the niftyindices TRI endpoint as WAF-blocked on 2026-07-27 and "
                   "argues ETF NAVs are the more honest investable benchmark",
            "status": "0114's own claims are NOT contradicted here; this item is ADDITIVE — a "
                      "different, more standard lens on the same books",
        },
        "method": {
            "benchmark": "Nifty-500 TRI (total return — dividends in the benchmark)",
            "regression": "daily r_book = alpha + beta*r_bench; alpha annualised x252",
            "risk_free": "ZERO, stated not hidden — with an Indian RF of ~6-7%, a zero-RF alpha "
                         "OVERSTATES true excess return",
            "caveat": "these are the SOLE-RANKER sleeve panels from third_sleeve_returns.csv, the "
                      "same series 0115 used; they are not the capped Rs10L book of record",
        },
        "books": books,
    }
    (OUT / "session2_alpha_decomposition.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")

    for k, b in books.items():
        print(f"\n{b['book']}  ({b['span_years']}y, n={b['n_days']})")
        print(f"  beta {b['beta_vs_nifty500_TRI']}  R2 {b['r_squared']}")
        print(f"  alpha {b['alpha_annual_pct']:+.2f}%/yr  SE {b['alpha_annual_se_pct']:.2f}  "
              f"t={b['alpha_t_stat']}  95% CI {b['alpha_95ci_pct']}")
        print(f"  book CAGR {b['book_cagr_pct']}%  vs bench {b['bench_cagr_pct']}%  "
              f"raw gap {b['raw_cagr_gap_pct']:+.2f}pp")
        print(f"  positive-alpha years {b['years_with_positive_alpha']}  top-2 {b['top2_alpha_years']}")


if __name__ == "__main__":
    main()
