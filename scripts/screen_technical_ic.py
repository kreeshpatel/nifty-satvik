"""Pre-reg 0079 Stage A — cross-sectional rank-IC of the technical-signal zoo vs the forward-63d return.

MEASUREMENT (no trial cost): does any chart/oscillator/breakout/volume signal predict the 63d return
on the eligible long-horizon universe, vs the incumbent sma200_slope_63? Signals trailing-only
(PIT-safe); the forward-63d return is the label (IC is inherently label-based, not leakage). Oscillators
are reported so a NEGATIVE IC = the reversal direction works, POSITIVE = the momentum direction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402

FWD = 63


def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _mfi(h, low, c, v, n=14):
    tp = (h + low + c) / 3
    rmf = tp * v
    pos = rmf.where(tp > tp.shift(1), 0.0).rolling(n).sum()
    neg = rmf.where(tp < tp.shift(1), 0.0).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    """~18 trailing-only technical signals for one ticker (title-cased OHLCV)."""
    h, low, c, v = df["High"], df["Low"], df["Close"], df["Volume"]
    tp = (h + low + c) / 3
    sma20, std20 = c.rolling(20).mean(), c.rolling(20).std()
    hh14, ll14 = h.rolling(14).max(), low.rolling(14).min()
    ema12, ema26 = c.ewm(span=12).mean(), c.ewm(span=26).mean()
    macd = ema12 - ema26
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    out = pd.DataFrame(index=df.index)
    out["roc_21"] = c / c.shift(21) - 1
    out["roc_63"] = c / c.shift(63) - 1
    out["roc_126"] = c / c.shift(126) - 1
    out["mom_252_21"] = c.shift(21) / c.shift(252) - 1
    out["dist_sma50"] = c / c.rolling(50).mean() - 1
    out["dist_sma200"] = c / c.rolling(200).mean() - 1
    out["macd_hist"] = (macd - macd.ewm(span=9).mean()) / c
    out["rsi_14"] = _rsi(c)
    out["stoch_k"] = (c - ll14) / (hh14 - ll14) * 100
    out["williams_r"] = (hh14 - c) / (hh14 - ll14) * -100
    out["cci_20"] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
    out["boll_pctb"] = (c - (sma20 - 2 * std20)) / ((sma20 + 2 * std20) - (sma20 - 2 * std20))
    out["prox_52wh"] = c / c.rolling(252).max()
    out["donchian63"] = (c - low.rolling(63).min()) / (h.rolling(63).max() - low.rolling(63).min())
    out["breakout_20"] = c / c.rolling(20).max()
    out["vol_ratio"] = v / v.rolling(20).mean()
    out["obv_63"] = obv - obv.shift(63)
    out["mfi_14"] = _mfi(h, low, c, v)
    out["rvol_63"] = c.pct_change().rolling(63).std()
    out["fwd63"] = c.shift(-FWD) / c - 1
    return out


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"panel build ({len(ohlcv)} names) ...", flush=True)
    panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                 fund_store=load_fund_store(), membership=load_membership())
    panel["date"] = pd.to_datetime(panel["date"])
    elig = panel[["date", "ticker", "sma200_slope_63"]].copy()

    print("computing technical battery + forward-63d label ...", flush=True)
    frames = []
    for tkr, g in ohlcv.items():
        ind = indicators(g)
        ind["ticker"] = tkr
        ind["date"] = pd.to_datetime(ind.index)
        frames.append(ind.reset_index(drop=True))
    ind_all = pd.concat(frames, ignore_index=True)
    df = elig.merge(ind_all, on=["date", "ticker"], how="inner")

    sigs = [c for c in df.columns if c not in ("date", "ticker", "fwd63")]
    df = df.dropna(subset=["fwd63"])
    rows = []
    for s in sigs:
        sub = df[["date", s, "fwd63"]].dropna()
        daily = sub.groupby("date").apply(
            lambda g: g[s].corr(g["fwd63"], method="spearman") if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        if len(daily) < 100:
            continue
        rows.append((s, daily.mean(), daily.mean() / daily.std(), (daily > 0).mean(), len(daily)))
    res = pd.DataFrame(rows, columns=["signal", "mean_IC", "IC_IR", "pct_days_pos", "n_days"])
    res = res.reindex(res["mean_IC"].abs().sort_values(ascending=False).index)

    base_ic = res.loc[res["signal"] == "sma200_slope_63", "mean_IC"]
    b = float(base_ic.iloc[0]) if len(base_ic) else float("nan")
    print(f"\n{'signal':<14}{'mean_IC':>9}{'IC_IR':>8}{'%days+':>8}{'vs base |IC|':>13}")
    print("-" * 52)
    for _, r in res.iterrows():
        flag = "  <== BASE" if r["signal"] == "sma200_slope_63" else (
            "  beats base" if abs(r["mean_IC"]) >= abs(b) else "")
        print(f"{r['signal']:<14}{r['mean_IC']:>+9.4f}{r['IC_IR']:>+8.3f}{r['pct_days_pos']*100:>7.0f}%"
              f"{abs(r['mean_IC'])/abs(b):>12.2f}x{flag}")
    print(f"\nBase sma200_slope_63 |mean_IC| = {abs(b):.4f}. A signal is worth a Stage-B backtest if "
          "|IC| >= ~0.5x base AND IC_IR is consistent (same sign). Reversal works if IC is NEGATIVE.")
    res.to_csv(ROOT / "research" / "exports" / "technical_ic_0079.csv", index=False)
    print(f"wrote {ROOT / 'research' / 'exports' / 'technical_ic_0079.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
