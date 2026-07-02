"""Build PIT-safe FF-India factor return series (Market + HML) for residual momentum (cand #3).

Leakage contract (skills/leakage-audit §2): the HML value input `bp` (book/price) comes from
`nq.data.fundamentals.value_quality_series` -> merge_asof(direction=backward,
allow_exact_matches=False) on the availability date (period_end + 90d ANNUAL_REPORTING_LAG_DAYS),
so no unpublished fundamental can leak. The market factor uses realized returns only. Universe =
the PIT-masked, solvent, large+mid strategy panel (factors represent the tradable universe's own
common variation — what a residual-momentum signal should strip).

SMB (size) is DEFERRED: the carried fundamentals store dropped shares/net_worth (only
period_end/eps_ttm/book_value_ps/roe/debt_equity remain), so market cap isn't reconstructable
without a Screener re-scrape. This is therefore a Market+Value 2-factor residual basis — still a
genuinely-new MULTI-factor variant vs the killed single-beta residual (O-002); SMB is a data-gated
extension.

Output: data/ff_india_factors.parquet  [date, mkt, hml]  (daily factor returns).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import DATA_DIR  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store, value_quality_series  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402

MIN_NAMES_PER_MONTH = 15   # need enough cross-section to form terciles


def _hml_month(sub: pd.DataFrame) -> pd.Series | None:
    """HML daily return for one calendar month: tercile-sort on bp AS OF each ticker's first day
    in the month (PIT — bp only steps on availability dates), hold the month, EW(H) - EW(L)."""
    first_bp = sub.sort_values("date").groupby("ticker")["bp"].first().dropna()
    if len(first_bp) < MIN_NAMES_PER_MONTH:
        return None
    hi = first_bp[first_bp >= first_bp.quantile(2 / 3)].index
    lo = first_bp[first_bp <= first_bp.quantile(1 / 3)].index
    h = sub[sub.ticker.isin(hi)].groupby("date")["ret"].mean()
    lo_r = sub[sub.ticker.isin(lo)].groupby("date")["ret"].mean()
    return (h - lo_r).rename("hml")


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    store = load_fund_store()
    panel = panel[["date", "ticker", "close"]].copy()
    panel["date"] = pd.to_datetime(panel["date"])

    # per-ticker daily return + PIT bp (book/price)
    frames = []
    for tkr, g in panel.sort_values("date").groupby("ticker"):
        g = g.sort_values("date")
        dates = pd.DatetimeIndex(g["date"].to_numpy())
        close = g["close"].to_numpy(float)
        if len(close) < 2:
            continue
        vq = value_quality_series(tkr, store, dates, close)
        ret = np.concatenate([[np.nan], close[1:] / close[:-1] - 1.0])
        frames.append(pd.DataFrame({"date": dates, "ticker": tkr, "ret": ret, "bp": vq["bp"]}))
    L = pd.concat(frames, ignore_index=True).dropna(subset=["ret"])
    L = L[np.isfinite(L["ret"])]

    mkt = L.groupby("date")["ret"].mean().rename("mkt")
    L["ym"] = L["date"].dt.to_period("M")
    hml = pd.concat([s for s in (_hml_month(sub) for _, sub in L.groupby("ym")) if s is not None])
    hml = hml.groupby(level=0).first().rename("hml")   # de-dup any month-boundary overlap

    fac = pd.concat([mkt, hml], axis=1).dropna(subset=["mkt"]).sort_index()
    fac.index.name = "date"
    out = DATA_DIR / "ff_india_factors.parquet"
    fac.reset_index().to_parquet(out, index=False)

    # ── sanity ────────────────────────────────────────────────────────────────
    def ann(s):
        s = s.dropna()
        return s.mean() * 252 * 100, s.std() * np.sqrt(252) * 100, (s.mean() / s.std() * np.sqrt(252) if s.std() else float("nan"))
    print(f"\nwrote {out}  ({len(fac)} days, {fac.index.min().date()}..{fac.index.max().date()})")
    for c in ("mkt", "hml"):
        m, v, sh = ann(fac[c])
        cov = fac[c].notna().mean()
        print(f"  {c}: ann {m:+.1f}%  vol {v:.1f}%  Sharpe {sh:+.2f}  coverage {cov*100:.0f}%")
    # market-factor validity: correlate with Nifty-500 TRI daily return
    tri_p = ROOT / "research" / "exports" / "benchmark_nifty500_tri.csv"
    if tri_p.exists():
        tri = pd.read_csv(tri_p, parse_dates=["date"]).set_index("date")["tri_ret"]
        j = pd.concat([fac["mkt"], tri], axis=1).dropna()
        print(f"  corr(mkt, Nifty500 TRI daily ret) = {j['mkt'].corr(j['tri_ret']):.3f}  (n={len(j)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
