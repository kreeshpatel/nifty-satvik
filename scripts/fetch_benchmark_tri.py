"""Fetch the Nifty 500 TRI (Total Returns Index) daily series and splice it onto the strategy
return path — the benchmark for the beta-vs-factor drawdown decomposition.

Source: niftyindices.com official ``getTotalReturnIndexString`` endpoint (the NSE-canonical TRI;
gross ``TotalReturnsIndex`` reinvests full dividends, ``NTR_Value`` reinvests net of withholding).
The strategy trades dividend-ADJUSTED yfinance prices, so the total-return index — not the price
index (^CRSLDX / PRI) — is the apples-to-apples benchmark; PRI would understate beta and inflate
apparent alpha.

Writes ``research/exports/benchmark_nifty500_tri.csv``:
    date, tri_close, tri_ret, ntr_close, pri_note
aligned (left-joined) to the dates already in ``research/exports/daily_returns.csv`` so the
downstream study can join on date directly. Also prints a quick beta + drawdown-window attribution
and records it in ``benchmark_manifest.json``.

Usage:
    python scripts/fetch_benchmark_tri.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "research" / "exports"
URL = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Referer": "https://www.niftyindices.com/reports/historical-data",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json; charset=UTF-8",
    })
    try:
        s.get("https://www.niftyindices.com/reports/historical-data", timeout=20)
    except requests.RequestException:
        pass
    return s


def _fetch_chunk(s: requests.Session, name: str, start: str, end: str) -> list[dict]:
    """One [start, end] window (dates as DD-Mon-YYYY). Returns list of raw record dicts."""
    payload = {"cinfo": f"{{'name':'{name}','startDate':'{start}','endDate':'{end}','indexName':'{name}'}}"}
    r = s.post(URL, data=json.dumps(payload), timeout=40)
    r.raise_for_status()
    inner = json.loads(r.json()["d"])
    return inner


def fetch_tri(name: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Full-range TRI, fetched in yearly chunks (the endpoint is happiest with bounded windows)."""
    s = _session()
    rows: list[dict] = []
    yr = start.year
    while yr <= end.year:
        lo = max(start, pd.Timestamp(yr, 1, 1))
        hi = min(end, pd.Timestamp(yr, 12, 31))
        chunk = _fetch_chunk(s, name, lo.strftime("%d-%b-%Y"), hi.strftime("%d-%b-%Y"))
        rows.extend(chunk)
        print(f"  {yr}: {len(chunk)} rows", flush=True)
        yr += 1
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("ERROR: TRI fetch returned no rows")
    df["date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
    df["tri_close"] = pd.to_numeric(df["TotalReturnsIndex"], errors="coerce")
    df["ntr_close"] = pd.to_numeric(df.get("NTR_Value"), errors="coerce")
    df = (df[["date", "tri_close", "ntr_close"]]
          .dropna(subset=["tri_close"]).drop_duplicates("date").sort_values("date")
          .reset_index(drop=True))
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch + splice Nifty 500 TRI")
    ap.add_argument("--name", default="NIFTY 500")
    ap.add_argument("--strategy-csv", default=str(EXPORTS / "daily_returns.csv"))
    ap.add_argument("--out", default=str(EXPORTS / "benchmark_nifty500_tri.csv"))
    args = ap.parse_args(argv)

    strat = pd.read_csv(args.strategy_csv, parse_dates=["date"])
    lo, hi = strat["date"].min(), strat["date"].max()
    print(f"fetching {args.name} TRI {lo.date()} .. {hi.date()} ...", flush=True)
    # pad the start so the first strategy day has a prior TRI close for its return
    tri = fetch_tri(args.name, lo - pd.Timedelta(days=10), hi)
    tri["tri_ret"] = tri["tri_close"].pct_change()

    # ── splice: left-join onto the strategy trading dates ────────────────────
    merged = strat[["date"]].merge(tri, on="date", how="left")
    missing = int(merged["tri_close"].isna().sum())
    # recompute tri_ret on the STRATEGY calendar (so a skipped date compounds correctly)
    merged["tri_ret"] = merged["tri_close"].pct_change()
    out = merged[["date", "tri_close", "tri_ret", "ntr_close"]].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, float_format="%.6f")

    # ── quick attribution: full-period beta + worst-drawdown-window overlay ──
    j = strat.merge(tri, on="date", how="inner").dropna(subset=["ret_net", "tri_ret"])
    a = j["ret_net"].to_numpy(float)
    b = j["tri_ret"].to_numpy(float)
    beta = float(np.cov(a, b, ddof=0)[0, 1] / np.var(b)) if np.var(b) > 0 else float("nan")
    corr = float(np.corrcoef(a, b)[0, 1])
    ann_alpha = float((a - beta * b).mean() * 252 * 100)

    # strategy global peak-to-trough
    eq = strat.set_index("date")["equity_net"]
    peak = eq.cummax()
    dd = eq / peak - 1.0
    trough_dt = dd.idxmin()
    peak_dt = eq.loc[:trough_dt].idxmax()
    strat_dd = float(dd.min() * 100)
    tri_win = tri[(tri["date"] >= peak_dt) & (tri["date"] <= trough_dt)]
    tri_dd = (float(tri_win["tri_close"].iloc[-1] / tri_win["tri_close"].iloc[0] - 1.0) * 100
              if len(tri_win) > 1 else float("nan"))

    manifest = {
        "source": "niftyindices.com getTotalReturnIndexString (gross TRI + NTR)",
        "index": args.name, "n_tri_rows": int(len(tri)),
        "aligned_to": Path(args.strategy_csv).name,
        "strategy_dates": [str(lo.date()), str(hi.date())],
        "missing_tri_on_strategy_dates": missing,
        "attribution": {
            "full_period_beta_vs_tri": round(beta, 3),
            "daily_return_corr": round(corr, 3),
            "annualized_alpha_pct": round(ann_alpha, 2),
            "worst_drawdown_window": {
                "peak": str(peak_dt.date()), "trough": str(trough_dt.date()),
                "strategy_dd_pct": round(strat_dd, 2),
                "nifty500_tri_return_same_window_pct": round(tri_dd, 2),
                "beta_explained_dd_pct": round(beta * tri_dd, 2),
                "residual_factor_dd_pct": round(strat_dd - beta * tri_dd, 2),
            },
        },
        "notes": [
            "tri_close = gross TotalReturnsIndex (full dividend reinvest); ntr_close = net-of-withholding.",
            "tri_ret recomputed on the STRATEGY trading calendar (join on date, then pct_change).",
            "beta = cov(ret_net, tri_ret)/var(tri_ret) over common days; alpha annualized x252.",
            "worst-window decomposition is first-order (constant-beta); use event-study for the path.",
        ],
    }
    (EXPORTS / "benchmark_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nwrote {args.out}  (rows={len(out)}, missing_tri={missing})")
    print(f"full-period beta vs Nifty500 TRI = {beta:.3f}  corr={corr:.3f}  ann_alpha={ann_alpha:.2f}%")
    print(f"worst DD {peak_dt.date()}->{trough_dt.date()}: strategy {strat_dd:.1f}%  "
          f"| TRI same window {tri_dd:.1f}%  | beta-explained {beta*tri_dd:.1f}%  "
          f"| residual(factor) {strat_dd - beta*tri_dd:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
