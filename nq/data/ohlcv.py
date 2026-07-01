"""OHLCV acquisition, caching, and lookahead-safe cleaning for the long-horizon path.

Two responsibilities:

1. **Acquisition / cache** — download per-ticker OHLCV from yfinance (``auto_adjust=True``),
   persist a ``{ticker -> DataFrame}`` pickle cache, and load the live incremental JSON cache
   (``results/ohlcv_cache_lh.json``). Frames are **title-cased** ``Open/High/Low/Close/Volume``
   on a ``DatetimeIndex`` — the convention the feature + panel layers expect.

2. **Cleaning** — :func:`clean_ohlcv_for_features` applies the repo's OHLC hygiene so the
   SIGNAL is computed on the same series the SIMULATOR fills on: drop NSE-holiday phantom bars,
   drop zero-volume placeholder bars, back-adjust unadjusted splits/bonuses, drop 1-bar bad
   ticks. It is **CA-aware**: a value-leaving demerger listed in the carried reference is left
   as an honest discontinuity instead of being back-adjusted into a fabricated soaring trend
   (the VEDL bug — see ``skills/data-quality`` §1.2). :func:`demerger_suspect_names` is the
   live-path quarantine guard that flags names with a recent >=50% raw drop.

Ported verbatim (behaviour-preserving) from the validated source so Stage 2's golden master
reproduces; the only changes are import paths (``nq`` / root ``config``) and docstrings.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_DIR, NSE_HOLIDAYS, RESULTS_DIR

# Single-session move beyond this is treated as a corporate-action artifact (unadjusted
# split/bonus) or a bad tick, not a real price move (F5 / DV_EX_FINDINGS).
_CORP_ACTION_MOVE = 0.50

OHLCV_CACHE = DATA_DIR / "ohlcv.pkl"
OHLCV_JSON_CACHE = RESULTS_DIR / "ohlcv_cache_lh.json"
DEMERGER_REF_PATH = DATA_DIR / "corporate_actions_demergers.csv"

# Demerger-quarantine guard tuning (W-01). A >=50% raw single-session drop within the
# sma200_slope_63 window (200d trend + 63d lookback) flags a value-leaving spin-off.
DEMERGER_LOOKBACK_BARS = 263
DEMERGER_DROP_THRESH = 0.50

_OHLC_COLS = ("Open", "High", "Low", "Close", "Volume")
_DEMERGER_REF_CACHE: dict[str, set[str]] | None = None


# ── Demerger reference ────────────────────────────────────────────────────────────────

def load_demerger_reference(path: Path | None = None) -> dict[str, set[str]]:
    """Load the committed demerger reference ``{ticker -> set(ISO dates)}``.

    Reads ``data/corporate_actions_demergers.csv`` (cols ``ticker,date``). A missing file
    yields an empty mapping, so callers degrade to the pre-CA-aware behaviour (every big
    drop back-adjusted as a split). Cached after the first read; pass an explicit ``path``
    to bypass the cache (used in tests).
    """
    global _DEMERGER_REF_CACHE
    if path is None and _DEMERGER_REF_CACHE is not None:
        return _DEMERGER_REF_CACHE
    ref_path = path if path is not None else DEMERGER_REF_PATH
    out: dict[str, set[str]] = {}
    try:
        if ref_path.exists():
            ref = pd.read_csv(ref_path, comment="#")
            ref.columns = [c.strip().lower() for c in ref.columns]
            if {"ticker", "date"}.issubset(ref.columns):
                for _, row in ref.iterrows():
                    tk = str(row["ticker"]).strip()
                    dt = pd.to_datetime(str(row["date"]).strip()).strftime("%Y-%m-%d")
                    out.setdefault(tk, set()).add(dt)
    except Exception:
        out = {}
    if path is None:
        _DEMERGER_REF_CACHE = out
    return out


# ── Cleaning ──────────────────────────────────────────────────────────────────────────

def clean_ohlcv_for_features(
    df: pd.DataFrame, holidays: set[str] | None = None,
    *, ticker: str | None = None, demerger_dates: set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Lookahead-safe OHLCV hygiene before feature computation.

    Steps (each uses only data up to the bar, leaving ratio features unchanged except where
    they were corrupted):

      1. Drop NSE-holiday-dated phantom bars (markets closed). Weekends are NOT dropped —
         NSE runs legitimate weekend sessions (Diwali Muhurat, Budget Saturday).
      2. Drop zero-volume flat-OHLC placeholder bars (suspension / pre-listing).
      3. Back-adjust unadjusted corporate actions: a persistent single-session move
         > ``_CORP_ACTION_MOVE`` (not a 1-bar reversing tick) is treated as a split/bonus;
         PRE-event OHLC is scaled continuous and volume inversely scaled (rupee turnover
         invariant). Ratio features are scale-invariant, so no lookahead is introduced.
      4. Drop 1-bar bad ticks (a >move that reverses by >=50% the next bar).

    CA-aware: a value-leaving DEMERGER (``ticker`` known AND the bar's date in
    ``demerger_dates``) is NOT back-adjusted — it is left as the honest discontinuity and
    counted in ``report['demergers_detected']``. When ``ticker``/``demerger_dates`` is None
    the behaviour is identical to the non-CA-aware cleaner (every big non-reversing drop
    back-adjusted as a split) — fully backward-compatible.

    Returns ``(cleaned_df, report)``. Pure — does not mutate the input or any cache.
    """
    report: dict[str, int] = {"dropped_holiday": 0, "dropped_zero_vol": 0,
                              "splits_adjusted": 0, "bad_ticks_dropped": 0,
                              "demergers_detected": 0}
    _demerger_set = {str(d) for d in demerger_dates} if (ticker and demerger_dates) else None
    if df is None or df.empty:
        return df, report
    df = df.copy()

    # 1. listed-holiday phantom bars (markets closed). Weekends intentionally NOT dropped.
    if holidays:
        idx = pd.to_datetime(df.index)
        keep = ~pd.Index(idx.strftime("%Y-%m-%d")).isin(holidays)
        report["dropped_holiday"] = int((~keep).sum())
        df = df[keep]
        if df.empty:
            return df, report

    # 2. zero-volume flat placeholder bars
    o = df["Open"].astype(float)
    h = df["High"].astype(float)
    lo = df["Low"].astype(float)
    c = df["Close"].astype(float)
    v = df["Volume"].astype(float)
    flat = (v <= 0) & (o == h) & (h == lo) & (lo == c)
    report["dropped_zero_vol"] = int(flat.sum())
    df = df[~flat.values]
    if len(df) < 3:
        return df, report

    # 3 + 4. extreme single-session moves
    cols = ["Open", "High", "Low", "Close"]
    if "Close_Raw" in df.columns:
        cols.append("Close_Raw")
    price = df["Close"].astype(float).to_numpy()
    n = len(price)
    bar_dates = (pd.to_datetime(df.index).strftime("%Y-%m-%d").to_numpy()
                 if _demerger_set else None)
    drop_idx = np.zeros(n, dtype=bool)
    adj = np.ones(n)   # cumulative back-adjust factor applied to bars BEFORE each split
    for i in range(1, n):
        prev = price[i - 1]
        if prev <= 0 or price[i] <= 0:
            continue
        r = price[i] / prev - 1.0
        if abs(r) <= _CORP_ACTION_MOVE:
            continue
        # bad tick: reverses by >=50% on the very next bar
        if i + 1 < n and price[i] > 0:
            nxt = price[i + 1] / price[i] - 1.0
            if np.sign(nxt) != np.sign(r) and abs(nxt) >= 0.50:
                drop_idx[i] = True
                continue
        # CA-aware: a value-leaving DEMERGER on this bar -> do NOT back-adjust; leave the
        # honest re-basing discontinuity. Only a same-sign DOWN move can be a demerger.
        if _demerger_set is not None and r < 0 and bar_dates[i] in _demerger_set:
            report["demergers_detected"] += 1
            continue
        # otherwise: corporate action — scale all PRIOR bars to be continuous
        f = price[i] / prev   # <1 for a forward split (price drops)
        adj[:i] *= f
        report["splits_adjusted"] += 1
    report["bad_ticks_dropped"] = int(drop_idx.sum())

    if report["splits_adjusted"]:
        for col in cols:
            df[col] = df[col].astype(float).to_numpy() * adj
        # keep rupee turnover invariant: volume scales inversely to price
        nz = adj != 0
        vol = df["Volume"].astype(float).to_numpy().copy()
        vol[nz] = vol[nz] / adj[nz]
        df["Volume"] = vol
    if drop_idx.any():
        df = df[~drop_idx]

    return df, report


def clean_ohlcv_dict(
    ohlcv: Mapping[str, pd.DataFrame],
    *, holidays: set[str] | None = None, demerger_ref: Mapping[str, set[str]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Clean every frame with :func:`clean_ohlcv_for_features` so the simulator fills on the
    same cleaned series the signal was computed on. Per-ticker demerger reference is consulted
    so value-leaving spin-offs are left as the honest discontinuity. Falls back to the raw
    frame per-ticker if the cleaner errors. ``holidays`` / ``demerger_ref`` default to the
    carried config + reference file.
    """
    hol = set(NSE_HOLIDAYS) if holidays is None else set(holidays)
    ref = load_demerger_reference() if demerger_ref is None else demerger_ref
    out: dict[str, pd.DataFrame] = {}
    for t, df in ohlcv.items():
        try:
            cleaned, _ = clean_ohlcv_for_features(
                df, holidays=hol, ticker=t, demerger_dates=ref.get(t))
            out[t] = cleaned
        except Exception:
            out[t] = df
    return out


# ── Demerger-quarantine guard (live-path, raw close) ──────────────────────────────────

def demerger_suspect(raw_close, lookback: int = DEMERGER_LOOKBACK_BARS,
                     drop_thresh: float = DEMERGER_DROP_THRESH) -> bool:
    """Is this name's RAW price history demerger-suspect? (W-01 live-path quarantine.)

    A name is suspect if, within the last ``lookback`` trading bars, the raw close has a
    single-session drop >= ``drop_thresh`` that does NOT reverse within a few sessions (a
    bad tick / transient gap snaps back; a real value-leaving event does not). Detection on
    the RAW close — does NOT touch the feature math or the cleaner. VEDL -> True, RELIANCE
    -> False. Pure + importable so a unit test can target it directly.
    """
    c = np.asarray(raw_close, dtype=float)
    c = c[np.isfinite(c)]
    if c.size < 2:
        return False
    window = c[-lookback:] if c.size > lookback else c
    n = window.size
    REVERSAL_SESSIONS = 5          # a bad tick / transient gap snaps back inside this many bars
    REVERSAL_RECOVER_FRAC = 0.80   # "reversed" = price climbs back to >= 80% of the pre-drop level
    for i in range(1, n):
        prev = window[i - 1]
        if prev <= 0:
            continue
        ret = window[i] / prev - 1.0
        if ret <= -drop_thresh:
            recov_end = min(i + REVERSAL_SESSIONS, n - 1)
            if recov_end > i:
                post_max = float(np.max(window[i + 1: recov_end + 1]))
                if post_max >= REVERSAL_RECOVER_FRAC * prev:
                    continue   # reverted — treat as a tick/transient, not a demerger
            return True
    return False


def demerger_suspect_names(ohlcv_dict: Mapping[str, pd.DataFrame] | None,
                           lookback: int = DEMERGER_LOOKBACK_BARS,
                           drop_thresh: float = DEMERGER_DROP_THRESH) -> set[str]:
    """Set of tickers whose RAW OHLCV (title-cased ``Close``) is demerger-suspect per
    :func:`demerger_suspect`. Wired into the entry loop to quarantine these names from NEW
    entries (they would otherwise rank on a fabricated post-split slope)."""
    suspect: set[str] = set()
    for sym, df in (ohlcv_dict or {}).items():
        try:
            if df is None or len(df) == 0 or "Close" not in df.columns:
                continue
            if demerger_suspect(df["Close"].to_numpy(float), lookback=lookback,
                                drop_thresh=drop_thresh):
                suspect.add(sym)
        except Exception:
            continue
    return suspect


# ── Acquisition + cache ───────────────────────────────────────────────────────────────

def download_ohlcv(tickers: list[str], start: str = "2015-01-01",
                   end: str | None = None, *, batch_size: int = 25) -> dict[str, pd.DataFrame]:
    """Download full OHLCV history for ``tickers`` from yfinance (``auto_adjust=True``).

    Returns ``{ticker -> DataFrame}`` with title-cased ``Open/High/Low/Close/Volume`` on a
    ``DatetimeIndex``. Names with < 50 usable bars or no data are skipped. Network-bound —
    not exercised by the hermetic Stage-1 gate; the backtest reads a cache instead.
    """
    import time
    from datetime import datetime

    import yfinance as yf

    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    # yfinance's `end` is EXCLUSIVE — passing it verbatim drops the `end` day's own bar, so the
    # live paper cron never captured the just-closed session and lagged one trading day (the
    # dashboard looked "stuck" a day behind). Bump by a day so `end` is inclusive of the last
    # session the caller asked for.
    from datetime import timedelta
    yf_end = (datetime.strptime(str(end)[:10], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    out: dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        tickers_ns = [f"{s}.NS" for s in batch]
        try:
            data = yf.download(tickers_ns, start=start, end=yf_end, group_by="ticker",
                               auto_adjust=True, threads=True, progress=False)
        except Exception:
            continue
        for t_ns in tickers_ns:
            t = t_ns.replace(".NS", "")
            try:
                df = data[t_ns].copy() if len(batch) > 1 else data.copy()
                df = df.dropna(subset=["Close"])
                if len(df) >= 50:
                    out[t] = df
            except Exception:
                pass
        time.sleep(1)
    return out


def save_ohlcv_cache(ohlcv: Mapping[str, pd.DataFrame], path: Path | None = None) -> Path:
    """Persist the OHLCV dict to a pickle cache (default ``data/ohlcv.pkl``)."""
    p = path or OHLCV_CACHE
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(dict(ohlcv), f)
    return p


def load_ohlcv_cache(path: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the pickled OHLCV dict (default ``data/ohlcv.pkl``). ``{}`` if absent."""
    p = path or OHLCV_CACHE
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return pickle.load(f)


def file_sha256(path: Path | None = None, *, chunk_size: int = 1 << 20) -> str:
    """SHA-256 hex digest of a cache file's raw bytes (default ``data/ohlcv.pkl``).

    The dataset-pin primitive. yfinance history drifts run-to-run (observed CAGR
    14.2/15.6/16.25 on identical commands), so a headline number is only reproducible against a
    FIXED OHLCV snapshot. We identify that snapshot by the sha256 of its exact pickle bytes: a
    pinned run that loads the same blob is guaranteed byte-identical INPUT, which (with the
    pinned deps) makes the baseline byte-reproducible. Returns ``''`` if the file is absent.
    """
    p = path or OHLCV_CACHE
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def merge_ohlcv(existing: Mapping[str, pd.DataFrame],
                new: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Merge ``new`` OHLCV bars into ``existing`` (the incremental-cache update the daily paper cron
    uses so it refreshes only recent days, not the full history). Per ticker: concat, drop duplicate
    dates keeping the NEW bar (adjustments/late-prints win), sort. Pure — returns a new dict."""
    out: dict[str, pd.DataFrame] = {t: df for t, df in existing.items()}
    for t, df in new.items():
        if df is None or len(df) == 0:
            continue
        if t in out and out[t] is not None and len(out[t]):
            comb = pd.concat([out[t], df])
            out[t] = comb[~comb.index.duplicated(keep="last")].sort_index()
        else:
            out[t] = df
    return out


def load_ohlcv_json(path: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the live incremental JSON cache ``{ticker: {dates, open, high, low, close,
    volume}}`` into ``{ticker -> DataFrame}`` with title-cased columns on a DatetimeIndex.
    This is the cache the live cron maintains (``results/ohlcv_cache_lh.json``)."""
    p = path or OHLCV_JSON_CACHE
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, pd.DataFrame] = {}
    for t, rec in raw.items():
        try:
            idx = pd.to_datetime(rec["dates"])
            df = pd.DataFrame(
                {"Open": rec["open"], "High": rec["high"], "Low": rec["low"],
                 "Close": rec["close"], "Volume": rec["volume"]},
                index=idx,
            )
            out[t] = df
        except Exception:
            continue
    return out
