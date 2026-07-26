"""PIT / leakage guard for the NIFTY options-OI features (nq.data.options_oi).

The stress features feed a tail-hedge arming decision, so they MUST be lookahead-clean: every feature at
date t depends only on that day's EOD bhavcopy (a decision at t+1 open is then honest). The truncation test
proves it — deriving on a dict truncated at date d gives byte-identical values (at every date <= d) as
deriving on the full dict. The monthly-expiry ROLL is the danger spot (a future expiry calendar is known,
but a future PRICE must never leak); `front_monthly` rolls off the calendar only, so truncation holds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nq.data.options_oi import (
    derive_daily_oi_features,
    front_monthly,
    monthly_expiries,
    parse_fo_bhavcopy,
)


def _synthetic_day(date: str, expiries, spot: float, seed: int) -> pd.DataFrame:
    """A UDiFF-shaped bhavcopy for NIFTY with a strike ladder around `spot` for each expiry."""
    rng = np.random.default_rng(seed)
    strikes = np.arange(round(spot / 100) * 100 - 1000, round(spot / 100) * 100 + 1100, 100)
    rows = []
    for e in expiries:
        for k in strikes:
            for ot in ("CE", "PE"):
                rows.append(dict(
                    TckrSymb="NIFTY", FinInstrmTp="IDO", XpryDt=e, StrkPric=float(k), OptnTp=ot,
                    ClsPric=max(1.0, abs(spot - k) * rng.uniform(0.2, 0.6)),
                    OpnIntrst=float(rng.integers(0, 50000)), ChngInOpnIntrst=float(rng.integers(-5000, 5000)),
                    UndrlygPric=spot,
                ))
    return parse_fo_bhavcopy(pd.DataFrame(rows), date)


def _synthetic_raw() -> dict:
    # three months of monthly expiries + intervening weeklies, spanning a roll
    dates = pd.bdate_range("2025-01-02", "2025-03-31")
    monthly = ["2025-01-30", "2025-02-27", "2025-03-27", "2025-04-24"]
    weekly = ["2025-01-09", "2025-01-16", "2025-02-06", "2025-02-13", "2025-03-06", "2025-03-13"]
    exps = sorted(set(monthly + weekly))
    raw = {}
    for i, d in enumerate(dates):
        ds = str(d.date())
        live = [e for e in exps if pd.Timestamp(e) >= d.normalize()][:6]
        if not live:
            continue
        raw[ds] = _synthetic_day(ds, live, spot=23000 + 40 * i, seed=i)
    return raw


def test_monthly_expiry_identification():
    """The monthly contract is the last (max) expiry per calendar month; weeklies are excluded."""
    exps = ["2025-01-09", "2025-01-16", "2025-01-30", "2025-02-27", "2025-03-06", "2025-03-27"]
    assert monthly_expiries(exps) == {pd.Timestamp("2025-01-30"), pd.Timestamp("2025-02-27"),
                                      pd.Timestamp("2025-03-27")}


def test_front_monthly_rolls_off_before_expiry():
    """On/near an expiry the front reference rolls to the NEXT monthly (roll_days buffer)."""
    exps = ["2025-01-30", "2025-02-27", "2025-03-27"]
    # 3 calendar days before the Jan expiry -> still Jan; on expiry day -> already Feb
    assert front_monthly("2025-01-24", exps) == pd.Timestamp("2025-01-30")
    assert front_monthly("2025-01-30", exps) == pd.Timestamp("2025-02-27")


def test_derive_is_pit_truncation_invariant():
    """Truncating future days leaves every past feature value unchanged (no lookahead across the roll)."""
    raw = _synthetic_raw()
    keys = sorted(raw)
    d = keys[len(keys) // 2]

    full = derive_daily_oi_features(raw)
    trunc = derive_daily_oi_features({k: v for k, v in raw.items() if k <= d})

    common = full.loc[:d].index
    pd.testing.assert_frame_equal(full.loc[common], trunc.loc[common])


def test_features_present_and_sane():
    feat = derive_daily_oi_features(_synthetic_raw())
    assert {"pcr_oi", "pcr_chg_oi", "tot_oi", "max_pain", "atm_straddle_pct", "front_expiry"} <= set(feat.columns)
    assert (feat["pcr_oi"].dropna() > 0).all()
    assert feat["front_expiry"].notna().all()  # a front monthly always resolves within the window
