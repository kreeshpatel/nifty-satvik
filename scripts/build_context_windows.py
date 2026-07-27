"""Deliverable 2 of pre-reg 0116 — the per-trade ±1-month context dataset.

One row per substrate trade (research/substrate/trades.parquet), joined with:
  * PRE-ENTRY window features (21 trading days ending at the SIGNAL-week Friday close, inclusive —
    strictly before the entry decision; PIT-legal, the selection territory), and
  * POST-EXIT window labels (21 trading days after exit, exclusive — grading territory ONLY; the
    leakage firewall in the pre-reg forbids these ever entering a selection feature).

Feature/label definitions are FIXED in diagnostics/research/preregistry/0116-context-window-selection.md.
Output: research/substrate/context_windows.parquet

    python scripts/build_context_windows.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402

TRADES = ROOT / "research" / "substrate" / "trades.parquet"
OUT = ROOT / "research" / "substrate" / "context_windows.parquet"
W = 21  # trading days, both windows (pre-reg-fixed)


def pre_features(g: pd.DataFrame, sig_fri: pd.Timestamp) -> dict:
    """Path-shape features on the 21 trading days ending at sig_fri (inclusive). NaN-safe."""
    w = g[g.index <= sig_fri].tail(W)
    out = {k: np.nan for k in ("path_eff", "gap_share", "gap_max", "runup21", "dd_hi21",
                               "updays", "accel", "range_comp", "vol_burst")}
    if len(w) < 15:
        return out
    c = w["Close"].to_numpy(float); o = w["Open"].to_numpy(float)
    r = np.diff(c) / c[:-1]
    tot = c[-1] / c[0] - 1.0
    denom = np.abs(r).sum()
    out["path_eff"] = abs(tot) / denom if denom > 0 else np.nan
    gaps = o[1:] / c[:-1] - 1.0
    intra = c[1:] / o[1:] - 1.0
    gd = np.abs(gaps).sum() + np.abs(intra).sum()
    out["gap_share"] = np.abs(gaps).sum() / gd if gd > 0 else np.nan
    out["gap_max"] = float(np.abs(r).max())
    cum = c / c[0] - 1.0
    out["runup21"] = float(cum.max())
    out["dd_hi21"] = float(c[-1] / w["High"].max() - 1.0)
    out["updays"] = float((r > 0).mean())
    half = len(c) // 2
    out["accel"] = float((c[-1] / c[half] - 1.0) - (c[half] / c[0] - 1.0))
    rng = w["High"].max() - w["Low"].min()
    prior = g[g.index < w.index[0]].tail(W)
    prng = prior["High"].max() - prior["Low"].min() if len(prior) >= 15 else np.nan
    out["range_comp"] = float(rng / prng) if prng and prng > 0 else np.nan
    v = w["Volume"].to_numpy(float)
    out["vol_burst"] = float(v[-5:].mean() / v.mean()) if v.mean() > 0 else np.nan
    return out


def post_labels(g: pd.DataFrame, entry_dt, exit_dt, entry_px: float, risk: float, R: float,
                reason: str) -> dict:
    """POST-EXIT grading labels (21 trading days after exit, exclusive). LABELS ONLY — firewall."""
    exit_px_ref = g["Close"].asof(exit_dt)
    post = g[g.index > exit_dt].head(W)
    out = {k: np.nan for k in ("post_ret21", "post_maxup21", "post_maxdn21", "opp_quality_R")}
    out.update({k: None for k in ("exit_too_early", "exit_saved", "false_touch", "noise_stop")})
    if len(post) >= 10 and exit_px_ref == exit_px_ref and exit_px_ref > 0:
        c = post["Close"].to_numpy(float)
        out["post_ret21"] = float(c[-1] / exit_px_ref - 1.0)
        out["post_maxup21"] = float(post["High"].max() / exit_px_ref - 1.0)
        out["post_maxdn21"] = float(post["Low"].min() / exit_px_ref - 1.0)
        stop_exit = "stop" in str(reason).lower()
        out["exit_too_early"] = bool(R > 0 and out["post_maxup21"] > 0.10)
        out["exit_saved"] = bool(out["post_ret21"] < -0.10)
        out["false_touch"] = bool(stop_exit and out["post_maxup21"] < 0.05)
        out["noise_stop"] = bool(stop_exit and out["post_ret21"] > 0.05)
    horizon = g[(g.index >= entry_dt)]
    horizon = horizon[horizon.index <= (post.index[-1] if len(post) else exit_dt)]
    if len(horizon) and risk > 0:
        out["opp_quality_R"] = float((horizon["Close"].max() - entry_px) / risk)
    return out


def main() -> int:
    t = pd.read_parquet(TRADES)
    print(f"substrate: {len(t)} trades | cols: {list(t.columns)[:18]}...")
    # defensive column mapping (builder's names)
    col = {c.lower(): c for c in t.columns}
    tk = col.get("tkr") or col.get("ticker"); en_d = col.get("entry_date"); ex_d = col.get("exit_date")
    en_p = col.get("entry") or col.get("en") or col.get("entry_px")
    stop = col.get("stop0") or col.get("stop"); rr = col.get("r"); rsn = col.get("reason")
    t[en_d] = pd.to_datetime(t[en_d]); t[ex_d] = pd.to_datetime(t[ex_d])
    oh = load_ohlcv_cache(OHLCV_CACHE)
    # cross-sectional 21d-return percentile (rs21), PIT at the signal Friday
    px = pd.DataFrame({k: g["Close"] for k, g in oh.items()})
    r21 = px.pct_change(W)
    rs_rank = r21.rank(axis=1, pct=True)
    rows = []
    for i, row in t.iterrows():
        tkr = row[tk]
        if tkr not in oh:
            continue
        g = oh[tkr]
        # signal-week Friday = last W-FRI strictly before the entry date
        sig_fri = (row[en_d] - pd.Timedelta(days=row[en_d].weekday() + 3))  # prior week's Friday
        f = pre_features(g, sig_fri)
        f["rs21"] = float(rs_rank.asof(sig_fri).get(tkr, np.nan)) if sig_fri >= rs_rank.index[0] else np.nan
        risk = float(row[en_p]) - float(row[stop]) if stop else np.nan
        lab = post_labels(g, row[en_d], row[ex_d], float(row[en_p]), risk, float(row[rr]),
                          str(row[rsn]) if rsn else "")
        rows.append({"idx": i, **f, **lab})
    F = pd.DataFrame(rows).set_index("idx")
    outdf = t.join(F, how="inner")
    outdf.to_parquet(OUT)
    feat_cols = ["path_eff", "gap_share", "gap_max", "runup21", "dd_hi21", "updays", "accel",
                 "range_comp", "vol_burst", "rs21"]
    print(f"context dataset: {len(outdf)} rows -> {OUT}")
    print("feature coverage %:", {c: round(outdf[c].notna().mean() * 100) for c in feat_cols})
    print("label rates:", {c: round(pd.Series(outdf[c]).astype(float).mean(), 3)
                           for c in ("exit_too_early", "exit_saved", "false_touch", "noise_stop")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
