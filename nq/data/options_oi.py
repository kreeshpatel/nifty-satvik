"""PIT-clean NIFTY index-option open-interest features from NSE F&O bhavcopies.

Owner request (2026-07-26): import the monthly-expiry NIFTY options OI + related positioning
so a defined-risk TAIL HEDGE can be armed when the options market prices stress (the registry-
sanctioned shape for this book's drawdown — a hedge, NOT a regime sell, which is triple-killed:
findings 0090 regime + 0095 de-gross; overlay_registry O-001/A5).

Two on-disk bhavcopy schemas span the 2017-2026 window (proven reachable, `scripts/harvest_fo_bhavcopy.py`):
  * OLD  (2017-01 .. 2024-06): INSTRUMENT==OPTIDX & SYMBOL==NIFTY; OI col OPEN_INT / CHG_IN_OI;
                               no underlying column -> use the near-month FUTIDX NIFTY close as spot proxy.
  * UDiFF (2024-07 ..)       : FinInstrmTp==IDO & TckrSymb==NIFTY; OI col OpnIntrst / ChngInOpnIntrst;
                               carries UndrlygPric (true spot).

`parse_fo_bhavcopy` and `derive_daily_oi_features` are pure, testable cores (no I/O). Every feature at
date t uses ONLY that day's EOD bhavcopy (known after the close), so a decision taken at t+1 open is
lookahead-clean — the same close->next-open cadence the swing book already certifies on. Proven by
`tests/test_options_oi_pit.py` (truncation test on the monthly-expiry roll).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import DATA_DIR

OI_PIT_PATH = DATA_DIR / "options_oi_pit.parquet"
# the raw per-day accumulation the harvester writes (NIFTY index-option long rows only)
OI_RAW_PATH = DATA_DIR / "_fo_oi_raw.parquet"

# normalized long-frame columns produced by parse_fo_bhavcopy
LONG_COLS = ["date", "expiry", "strike", "otype", "close", "oi", "chg_oi", "underlying"]


def parse_fo_bhavcopy(df: pd.DataFrame, trade_date) -> pd.DataFrame:
    """Normalize ONE F&O bhavcopy DataFrame -> NIFTY index-option long frame (`LONG_COLS`).

    Auto-detects schema by column presence. `underlying` is the true spot (UDiFF `UndrlygPric`) or,
    for the OLD format which lacks it, the near-month FUTIDX NIFTY close (a tight spot proxy — index
    futures trade within a small basis). Returns an empty frame (right columns) if no NIFTY options
    are present (holiday / pre-listing).
    """
    d = pd.Timestamp(trade_date).normalize()
    if "FinInstrmTp" in df.columns:  # ── UDiFF ──
        opt = df[(df["TckrSymb"] == "NIFTY") & (df["FinInstrmTp"] == "IDO")]
        if opt.empty:
            return pd.DataFrame(columns=LONG_COLS)
        out = pd.DataFrame({
            "date": d,
            "expiry": pd.to_datetime(opt["XpryDt"]).values,
            "strike": pd.to_numeric(opt["StrkPric"], errors="coerce").values,
            "otype": opt["OptnTp"].astype(str).str.upper().values,
            "close": pd.to_numeric(opt["ClsPric"], errors="coerce").values,
            "oi": pd.to_numeric(opt["OpnIntrst"], errors="coerce").values,
            "chg_oi": pd.to_numeric(opt["ChngInOpnIntrst"], errors="coerce").values,
            "underlying": pd.to_numeric(opt["UndrlygPric"], errors="coerce").values,
        })
    else:  # ── OLD historical format ──
        opt = df[(df["INSTRUMENT"] == "OPTIDX") & (df["SYMBOL"] == "NIFTY")]
        if opt.empty:
            return pd.DataFrame(columns=LONG_COLS)
        fut = df[(df["INSTRUMENT"] == "FUTIDX") & (df["SYMBOL"] == "NIFTY")].copy()
        spot = np.nan
        if len(fut):
            fut["_exp"] = pd.to_datetime(fut["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce")
            fut = fut.sort_values("_exp")
            spot = float(pd.to_numeric(fut["CLOSE"], errors="coerce").iloc[0])  # near-month future close
        out = pd.DataFrame({
            "date": d,
            "expiry": pd.to_datetime(opt["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce").values,
            "strike": pd.to_numeric(opt["STRIKE_PR"], errors="coerce").values,
            "otype": opt["OPTION_TYP"].astype(str).str.upper().values,
            "close": pd.to_numeric(opt["CLOSE"], errors="coerce").values,
            "oi": pd.to_numeric(opt["OPEN_INT"], errors="coerce").values,
            "chg_oi": pd.to_numeric(opt["CHG_IN_OI"], errors="coerce").values,
            "underlying": spot,
        })
    out = out[out["otype"].isin(("CE", "PE"))].dropna(subset=["expiry", "strike"])
    return out[LONG_COLS].reset_index(drop=True)


def monthly_expiries(expiries) -> set:
    """The MONTHLY expiries within a set of NIFTY index-option expiries = the last (max) expiry in each
    calendar (year, month). Weekly expiries (2019+) are the earlier same-month Thursdays; the monthly
    contract is the last Thursday, i.e. the group max. Robust to weeks-only or months-only inputs.
    """
    exp = pd.Series(sorted({pd.Timestamp(e).normalize() for e in pd.to_datetime(list(expiries))}))
    if exp.empty:
        return set()
    grp = exp.groupby([exp.dt.year, exp.dt.month]).max()
    return {pd.Timestamp(x) for x in grp.values}


def front_monthly(date, expiries, roll_days: int = 3) -> pd.Timestamp | None:
    """The front-month hedge reference: the nearest monthly expiry at least `roll_days` calendar days
    ahead of `date`. Rolling off the contract ~3d before expiry avoids the expiry-day artifact (OI
    bleeds to the next series and premium collapses to intrinsic) and mirrors a real hedge roll. This
    is PIT-clean — expiry dates are fixed at contract listing, so no future *price* is consulted.
    None if no monthly qualifies.
    """
    cutoff = pd.Timestamp(date).normalize() + pd.Timedelta(days=roll_days)
    fut = sorted(e for e in monthly_expiries(expiries) if pd.Timestamp(e) >= cutoff)
    return pd.Timestamp(fut[0]) if fut else None


def second_monthly(date, expiries, roll_days: int = 3) -> pd.Timestamp | None:
    """The NEXT monthly expiry after `front_monthly` (the far leg for the IV term-structure slope)."""
    cutoff = pd.Timestamp(date).normalize() + pd.Timedelta(days=roll_days)
    fut = sorted(e for e in monthly_expiries(expiries) if pd.Timestamp(e) >= cutoff)
    return pd.Timestamp(fut[1]) if len(fut) > 1 else None


def _atm_straddle_pct(chain: pd.DataFrame, spot: float) -> float:
    """ATM (CE+PE) close / spot for a single-expiry chain — a per-expiry IV proxy. NaN if unusable."""
    if not (np.isfinite(spot) and spot > 0 and len(chain)):
        return np.nan
    atm = float(chain.iloc[(chain["strike"] - spot).abs().argsort().iloc[:1]]["strike"].iloc[0])
    cc = chain[(chain["strike"] == atm) & (chain["otype"] == "CE")]["close"].sum()
    pp = chain[(chain["strike"] == atm) & (chain["otype"] == "PE")]["close"].sum()
    return float((cc + pp) / spot)


def _max_pain(chain: pd.DataFrame) -> float:
    """Strike minimizing total option-writer payout given the current OI (classic max-pain).
    `chain` has strike/otype/oi for a single expiry+day. NaN if unusable.
    """
    if chain.empty:
        return np.nan
    ce = chain[chain["otype"] == "CE"].groupby("strike")["oi"].sum()
    pe = chain[chain["otype"] == "PE"].groupby("strike")["oi"].sum()
    strikes = np.array(sorted(set(ce.index) | set(pe.index)), dtype=float)
    if strikes.size == 0:
        return np.nan
    ce = ce.reindex(strikes, fill_value=0.0).values
    pe = pe.reindex(strikes, fill_value=0.0).values
    # pain at settlement S = sum_i CE_oi_i*max(S-K_i,0) + PE_oi_i*max(K_i-S,0), over candidate S=strikes
    pain = np.array([(ce * np.maximum(s - strikes, 0)).sum() + (pe * np.maximum(strikes - s, 0)).sum()
                     for s in strikes])
    return float(strikes[int(np.argmin(pain))])


def _day_features(day: pd.DataFrame) -> dict:
    """Stress features for ONE trading day's NIFTY option long-frame (`parse_fo_bhavcopy` output).
    Built on the FRONT-MONTHLY chain (the hedge reference); a couple of all-expiry robustness twins.
    Pure: depends only on rows in `day` (all dated t) -> lookahead-clean by construction.
    """
    d = pd.Timestamp(day["date"].iloc[0]).normalize()
    spot = float(pd.to_numeric(day["underlying"], errors="coerce").dropna().median()) if len(day) else np.nan
    fm = front_monthly(d, day["expiry"].unique())
    ce_all = day[day["otype"] == "CE"]
    pe_all = day[day["otype"] == "PE"]
    feat = {
        "date": d,
        "front_expiry": fm,
        "spot": spot,
        "pcr_oi_all": float(pe_all["oi"].sum() / ce_all["oi"].sum()) if ce_all["oi"].sum() > 0 else np.nan,
        "tot_oi_all": float(day["oi"].sum()),
    }
    fmc = day[day["expiry"] == fm] if fm is not None else day.iloc[0:0]
    ce = fmc[fmc["otype"] == "CE"]
    pe = fmc[fmc["otype"] == "PE"]
    ce_oi, pe_oi = float(ce["oi"].sum()), float(pe["oi"].sum())
    feat["pcr_oi"] = pe_oi / ce_oi if ce_oi > 0 else np.nan
    ce_coi, pe_coi = float(ce["chg_oi"].sum()), float(pe["chg_oi"].sum())
    feat["pcr_chg_oi"] = pe_coi / ce_coi if ce_coi > 0 else np.nan
    feat["tot_oi"] = ce_oi + pe_oi
    feat["max_pain"] = _max_pain(fmc)
    feat["max_pain_gap"] = (spot / feat["max_pain"] - 1) if feat["max_pain"] and feat["max_pain"] > 0 else np.nan
    # ATM straddle / spot = a cheap IV proxy (no risk-free/T needed for a relative stress signal)
    if np.isfinite(spot) and len(fmc):
        atm = float(fmc.iloc[(fmc["strike"] - spot).abs().argsort().iloc[:1]]["strike"].iloc[0])
        cc = ce[ce["strike"] == atm]["close"].sum()
        pp = pe[pe["strike"] == atm]["close"].sum()
        feat["atm_strike"] = atm
        feat["atm_straddle_pct"] = float((cc + pp) / spot) if spot > 0 else np.nan
        # ── S2 put-SKEW (best-evidenced LEAD; built from the wings, not just ATM) ──
        # richness of the ~5%-OTM put vs the symmetric ~5%-OTM call, normalized by spot: a premium-space
        # risk-reversal. High/rising = crash insurance bid up = fear priced ahead.
        kput = float(pe["strike"][pe["strike"] <= spot * 0.95].max()) if (pe["strike"] <= spot * 0.95).any() else np.nan
        kcall = float(ce["strike"][ce["strike"] >= spot * 1.05].min()) if (ce["strike"] >= spot * 1.05).any() else np.nan
        pput = pe[pe["strike"] == kput]["close"].sum() if np.isfinite(kput) else np.nan
        pcall = ce[ce["strike"] == kcall]["close"].sum() if np.isfinite(kcall) else np.nan
        feat["put_skew"] = float((pput - pcall) / spot) if (np.isfinite(pput) and np.isfinite(pcall)) else np.nan
    else:
        feat["atm_strike"] = np.nan
        feat["atm_straddle_pct"] = np.nan
        feat["put_skew"] = np.nan
    # ── S1 IV TERM STRUCTURE: front vs next-month ATM straddle (>0 = backwardation = stress) ──
    m2 = second_monthly(d, day["expiry"].unique())
    m2c = day[day["expiry"] == m2] if m2 is not None else day.iloc[0:0]
    feat["atm_straddle_pct_m2"] = _atm_straddle_pct(m2c, spot)
    feat["iv_term_slope"] = (feat["atm_straddle_pct"] - feat["atm_straddle_pct_m2"]
                             if np.isfinite(feat.get("atm_straddle_pct", np.nan))
                             and np.isfinite(feat["atm_straddle_pct_m2"]) else np.nan)
    return feat


def derive_daily_oi_features(raw_by_day: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Map `{date_str -> parsed long frame}` -> a daily feature panel indexed by date (sorted).

    Trailing add-ons (z-scores / changes) are computed with trailing-only windows so
    `derive_daily_oi_features({d: v for d,v in raw.items() if d <= D})` == `derive_daily_oi_features(raw).loc[:D]`.
    """
    rows = []
    for ds in sorted(raw_by_day):
        day = raw_by_day[ds]
        if day is None or len(day) == 0:
            continue
        rows.append(_day_features(day))
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).set_index("date").sort_index()
    # ── S3 VRP veto: expected 1m move (ATM straddle) − realized 1m move (trailing 20d spot vol) ──
    # both dimensionless fractions; high VRP = protection richest -> the "don't arm" filter (blocks 0100).
    if "spot" in out:
        rvol = out["spot"].pct_change().rolling(20, min_periods=10).std(ddof=0) * np.sqrt(21)
        out["realized_vol_1m"] = rvol
        if "atm_straddle_pct" in out:
            out["vrp"] = out["atm_straddle_pct"] - rvol
    # trailing-only z-scores (percentile over a trailing year; no future rows used -> PIT-safe)
    for col in ("pcr_oi", "atm_straddle_pct", "put_skew", "iv_term_slope", "vrp"):
        if col in out:
            r = out[col].rolling(252, min_periods=63)
            out[f"{col}_z"] = (out[col] - r.mean()) / r.std(ddof=0)
    return out


def build_oi_series(raw_path=OI_RAW_PATH, out_path=OI_PIT_PATH, persist: bool = True) -> pd.DataFrame:
    """I/O wrapper: read the harvested raw NIFTY-option long parquet, derive the daily PIT feature panel,
    and persist it. Pure derivation lives in `derive_daily_oi_features` (truncation-tested).
    """
    long = pd.read_parquet(raw_path)
    long["date"] = pd.to_datetime(long["date"])
    raw_by_day = {str(d.date()): g for d, g in long.groupby("date")}
    feat = derive_daily_oi_features(raw_by_day)
    if persist and len(feat):
        feat.to_parquet(out_path)
    return feat
