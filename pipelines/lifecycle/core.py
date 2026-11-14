"""Strategy-lifecycle core (ADR-0020): band maths, weekly status, write-once and append-only file helpers.

Pure functions, stdlib + numpy/pandas only, so the Saturday workflow and the tests can use them without an engine.
Rules are the ones in skills/strategy-lifecycle/SKILL.md; change them there first, with a dated amendment.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

HORIZONS = (13, 26, 52, 104)                 # weeks
PCTS = (5, 25, 50, 75, 95)
MIN_VERDICT_WEEKS = 26
DD_BREAKER_MULT = 1.25
BLOCK_WEEKS = 8
N_DRAWS = 5000
RECORD_COLUMNS = ("date", "nav", "weekly_return", "holdings", "turnover", "benchmark_tri", "note")
BENCHMARK = "Nifty Midcap150 Momentum 50 TRI"


# --------------------------------------------------------------------------------------------- band maths
def weekly_returns(nav: pd.Series) -> pd.Series:
    """Friday-to-Friday returns of a daily NAV."""
    w = nav.dropna().resample("W-FRI").last().dropna()
    return w.pct_change().dropna()


def _path_stats(r: np.ndarray) -> tuple[float, float]:
    """(cumulative return %, max drawdown depth % as a positive number) of one path of weekly returns."""
    nav = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    depth = float((1.0 - nav / np.maximum.accumulate(nav)).max())
    return float(nav[-1] - 1.0) * 100.0, depth * 100.0


def rolling_windows(weekly: Sequence[float], h: int) -> tuple[np.ndarray, np.ndarray]:
    """Every overlapping h-week window of one weekly-return series -> (cum %, drawdown depth %)."""
    r = np.asarray(weekly, dtype=float)
    out = [_path_stats(r[i:i + h]) for i in range(0, len(r) - h + 1)]
    a = np.array(out, dtype=float).reshape(-1, 2)
    return a[:, 0], a[:, 1]


def stationary_bootstrap(weekly: Sequence[float], h: int, n: int = N_DRAWS, block: int = BLOCK_WEEKS,
                         seed: int = 20261113) -> tuple[np.ndarray, np.ndarray]:
    """Politis-Romano stationary bootstrap: blocks of geometric length (mean `block` weeks), wrapping around."""
    r = np.asarray(weekly, dtype=float)
    T = len(r)
    rng = np.random.default_rng(seed + h)
    cum, dd = np.empty(n), np.empty(n)
    for j in range(n):
        idx = np.empty(h, dtype=int)
        i = rng.integers(0, T)
        for k in range(h):
            if k and rng.random() < 1.0 / block:
                i = rng.integers(0, T)
            idx[k] = i % T
            i += 1
        cum[j], dd[j] = _path_stats(r[idx])
    return cum, dd


def pct_table(v: Iterable[float]) -> dict[str, float]:
    a = np.asarray(list(v), dtype=float)
    return {f"p{p}": round(float(np.percentile(a, p)), 2) for p in PCTS} if len(a) else {}


def wider(a: Mapping[str, float], b: Mapping[str, float], *, kind: str) -> dict[str, float]:
    """The wider of two percentile tables, percentile by percentile.

    Returns: the low side (p5, p25, p50) takes the LOWER value, the high side (p75, p95) the HIGHER.
    Drawdown depth (positive %): p5 and p25 take the SHALLOWER value, p50, p75 and p95 the DEEPER.
    Either way the band never narrows, and the median is the more cautious of the two."""
    if not a:
        return dict(b)
    if not b:
        return dict(a)
    low = ("p5", "p25", "p50") if kind == "return" else ("p5", "p25")
    return {k: round(min(a[k], b[k]) if k in low else max(a[k], b[k]), 2) for k in a}


def build_band(strategy: str, backtest_weekly: Sequence[float], ensemble_weekly: Sequence[Sequence[float]],
               worst_backtest_dd_pct: float, meta: Mapping | None = None, built: str | None = None) -> dict:
    out = {"strategy": strategy, "built": built or str(pd.Timestamp.today().date()), "frozen": True,
           "worst_backtest_drawdown_pct": round(float(worst_backtest_dd_pct), 2),
           "drawdown_breaker_pct": round(float(worst_backtest_dd_pct) * DD_BREAKER_MULT, 2),
           "method": {"ensemble_paths": len(ensemble_weekly), "ensemble": "every overlapping window of every path, pooled",
                      "bootstrap": f"stationary block bootstrap, mean block {BLOCK_WEEKS} weeks, {N_DRAWS} draws",
                      "band": "the wider of the two, percentile by percentile (pipelines/lifecycle/core.py::wider)",
                      "drawdown_sign": "depth as a positive percentage"},
           "meta": dict(meta or {}), "horizons": {}}
    for h in HORIZONS:
        e_c, e_d = [], []
        for w in ensemble_weekly:
            if len(w) >= h:
                c, d = rolling_windows(w, h)
                e_c.append(c); e_d.append(d)
        ec = pct_table(np.concatenate(e_c)) if e_c else {}
        ed = pct_table(np.concatenate(e_d)) if e_d else {}
        b_c, b_d = stationary_bootstrap(backtest_weekly, h)
        bc, bd = pct_table(b_c), pct_table(b_d)
        out["horizons"][str(h)] = {
            "cum_return_pct": {"ensemble": ec, "bootstrap": bc, "band": wider(ec, bc, kind="return")},
            "drawdown_depth_pct": {"ensemble": ed, "bootstrap": bd, "band": wider(ed, bd, kind="drawdown")}}
    return out


def check_monotone(band: Mapping) -> None:
    """Percentiles must be non-decreasing inside every table of a band file."""
    for h, blk in band["horizons"].items():
        for metric in ("cum_return_pct", "drawdown_depth_pct"):
            for src, t in blk[metric].items():
                v = [t[f"p{p}"] for p in PCTS if f"p{p}" in t]
                if any(b < a - 1e-9 for a, b in zip(v, v[1:])):
                    raise ValueError(f"non-monotone percentiles: horizon {h} {metric} {src}: {v}")


# --------------------------------------------------------------------------------------------- frozen files
def write_once(path: Path, obj: Mapping) -> Path:
    """Write a frozen JSON file. Refuses to overwrite: a band is rebuilt under a NEW date, never edited."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists and is frozen (ADR-0018 / ADR-0020). Build a new dated file instead.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    return path


def read_record(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=list(RECORD_COLUMNS))
    return pd.read_csv(path, dtype={"date": str, "note": str})


def append_row(path: Path, row: Mapping) -> bool:
    """Append ONE weekly row to a forward record. Never rewrites a line; refuses a date that is not after the last one.

    Returns True if a row was appended, False if the date was already recorded (a re-run of the same week)."""
    path = Path(path)
    date = str(row["date"])[:10]
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if rows:
            last = rows[-1]["date"]
            if date == last:
                return False
            if date < last:
                raise ValueError(f"{path.name}: refusing to append {date} before the last recorded week {last} (append-only)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(RECORD_COLUMNS)
    with path.open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerow(
            ["" if row.get(c) is None or (isinstance(row.get(c), float) and np.isnan(row.get(c))) else row.get(c) for c in RECORD_COLUMNS])
    return True


# --------------------------------------------------------------------------------------------- weekly status
def nearest_horizon(weeks: int) -> int:
    return min(HORIZONS, key=lambda h: (abs(h - weeks), h))


def classify(cum_return_pct: float, drawdown_depth_pct: float, band_h: Mapping, worst_backtest_dd_pct: float) -> dict:
    """GREEN / AMBER / RED for one strategy at one horizon (skills/strategy-lifecycle §3).

    `band_h` is one horizon block of a band file. A return exactly on p25 is GREEN; exactly on p5 is AMBER."""
    rb, db = band_h["cum_return_pct"]["band"], band_h["drawdown_depth_pct"]["band"]
    breaker = abs(float(worst_backtest_dd_pct)) * DD_BREAKER_MULT
    reasons = []
    if drawdown_depth_pct > breaker:
        reasons.append(f"drawdown {drawdown_depth_pct:.1f}% is deeper than the breaker {breaker:.1f}% (1.25 x backtest worst)")
    if cum_return_pct < rb["p5"]:
        reasons.append(f"return {cum_return_pct:.1f}% is below the 5th percentile {rb['p5']:.1f}%")
    if reasons:
        return {"status": "RED", "reasons": reasons, "drawdown_breaker": drawdown_depth_pct > breaker}
    if cum_return_pct < rb["p25"]:
        return {"status": "AMBER", "reasons": [f"return {cum_return_pct:.1f}% is between the 5th ({rb['p5']:.1f}%) and 25th ({rb['p25']:.1f}%) percentile"],
                "drawdown_breaker": False}
    if drawdown_depth_pct > db["p95"]:
        return {"status": "AMBER", "reasons": [f"drawdown {drawdown_depth_pct:.1f}% is deeper than the band's 95th percentile {db['p95']:.1f}%"],
                "drawdown_breaker": False}
    return {"status": "GREEN", "reasons": [], "drawdown_breaker": False}


def return_percentile(cum_return_pct: float, band_h: Mapping) -> str:
    """Where the return sits in the band, as a bracket (the band stores five percentiles, not the whole curve)."""
    b = band_h["cum_return_pct"]["band"]
    edges = [(5, b["p5"]), (25, b["p25"]), (50, b["p50"]), (75, b["p75"]), (95, b["p95"])]
    if cum_return_pct < edges[0][1]:
        return "below 5th"
    for (lo, _), (hi, v) in zip(edges, edges[1:]):
        if cum_return_pct < v:
            return f"{lo}th-{hi}th"
    return "above 95th"


def vol_target_blend(r_a: pd.Series, r_b: pd.Series, w_a: float = 0.70, target: float = 0.15, lookback: int = 20,
                     cash_rate: float = 0.06) -> tuple[pd.Series, pd.Series]:
    """The 70/30 blend with the 15% volatility target, exactly as defined in the 2026-11 inventory study.

    Daily fixed weights; exposure = min(1, target / realised vol of the combined book over the prior `lookback`
    sessions); the rest in cash at `cash_rate` a year. Returns (daily returns, exposure)."""
    idx = r_a.index.intersection(r_b.index)
    r = w_a * r_a.reindex(idx).fillna(0) + (1 - w_a) * r_b.reindex(idx).fillna(0)
    vol = r.rolling(lookback).std().shift(1) * np.sqrt(252)
    expo = (target / vol).clip(upper=1.0).fillna(1.0)
    return expo * r + (1 - expo) * (cash_rate / 252), expo


# --------------------------------------------------------------------------------------------- execution
def tracking_error(fills: Sequence[Mapping], model: Mapping[str, Mapping]) -> dict:
    """Real fills against the model's prices (ADR-0020, Part F).

    `fills`: rows with signal_id, side (BUY / SELL), qty, price. `model`: signal_id -> {entry, stop, exit}.
    Slippage is signed so that POSITIVE is worse for the trader: a buy above the model entry, a sell below the model
    exit. Reported in basis points of the model price and in R (the model's entry minus its stop)."""
    rows = []
    for f in fills:
        m = model.get(str(f.get("signal_id")))
        side = str(f.get("side", "")).upper()
        ref = (m or {}).get("entry" if side == "BUY" else "exit")
        if not m or not ref or side not in ("BUY", "SELL"):
            continue
        px, q = float(f["price"]), float(f.get("qty") or 0)
        adverse = (px - float(ref)) if side == "BUY" else (float(ref) - px)
        risk = float(m["entry"]) - float(m["stop"]) if m.get("entry") and m.get("stop") else float("nan")
        rows.append({"side": side, "qty": q, "bps": adverse / float(ref) * 1e4, "R": adverse / risk if risk and risk > 0 else float("nan"),
                     "notional": q * float(ref)})
    if not rows:
        return {"n_fills_matched": 0, "note": "no real fills recorded, so tracking error cannot be measured"}
    d = pd.DataFrame(rows)
    w = d["notional"] / d["notional"].sum() if d["notional"].sum() > 0 else 1 / len(d)
    out = {"n_fills_matched": int(len(d)), "mean_slippage_bps": round(float((d["bps"] * w).sum()), 1),
           "mean_slippage_R": round(float(d["R"].mean()), 3), "worst_slippage_bps": round(float(d["bps"].max()), 1)}
    for side in ("BUY", "SELL"):
        g = d[d["side"] == side]
        if len(g):
            out[f"{side.lower()}_mean_bps"] = round(float(g["bps"].mean()), 1)
    return out
