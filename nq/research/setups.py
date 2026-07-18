"""Weekly swing SETUP DETECTORS — the TraderLion pattern zoo (Stage-1 wide-net substrate).

Pure, trailing-only detector functions over WEEKLY arrays. Each returns a boolean signal array
(fires on the *completed* signal week ``k``; entry is the following week, exactly like the base
book) plus a per-week stop array. All detectors are:

  * **Trailing-only / PIT-safe** — week ``k`` uses only weeks ``<= k``; no forward peeking.
  * **Long-only trend-gated** — require the 44-week SMA rising (``slope >= slope_min``), price above
    the SMA, and relative strength intact, so they stay on-thesis for a trend-momentum book.
  * **Breakout-confirmed** — the signal week is a green close breaking the pattern's trigger level.

They are consumed additively by ``run_bhanushali_weekly_rank.prep_weekly_rank`` (origins 4-8) and
must be cfg-gated OFF by default there so the golden 0094 run stays byte-identical.

Origin codes (kept in sync with build_substrate.SETUP_NAMES):
    4 vcp | 5 flag | 6 cup_handle | 7 ascending_base | 8 double_bottom
"""
from __future__ import annotations

import numpy as np

# Trend/quality gates — mirror the base book so the zoo stays on-thesis (frozen constants).
SLOPE_MIN = 0.03


def _uptrend(slope, wclose, wsma, rs_term, slope_min=SLOPE_MIN):
    """Common long-only gate: 44w SMA rising, price above it, RS intact. NaN-safe boolean array."""
    return (np.nan_to_num(slope, nan=-9) >= slope_min) & \
           np.nan_to_num(wclose > wsma, nan=False) & \
           np.nan_to_num(rs_term, nan=False)


def _green(wopen, whigh, wlow, wclose):
    """Quality-green weekly bar: up close, positive range, close in the upper half of the range."""
    rng = whigh - wlow
    return (wclose > wopen) & (rng > 0) & ((wclose - wlow) >= 0.5 * rng)


def vcp_signal(wopen, whigh, wlow, wclose, wvol, wsma, slope, rs_term, *,
               base_len=12, min_contractions=2, tighten_ratio=0.8, vol_dry=0.9,
               vol_expand=1.1, slope_min=SLOPE_MIN):
    """Volatility Contraction Pattern (Minervini): successive shallower pullbacks on drying volume,
    then a green breakout above the base high on a volume expansion.

    Over the trailing ``base_len`` weeks we measure the two most recent peak->trough contractions;
    require the later one to be at most ``tighten_ratio`` of the earlier (volatility contracting) and
    base volume drying (mean vol in the base < ``vol_dry`` x mean vol before it). The signal week is a
    green close above the base's high with volume >= ``vol_expand`` x the base average. Stop = base low.
    """
    n = len(wclose)
    sig = np.zeros(n, bool)
    stop = wlow.astype(float).copy()
    up = _uptrend(slope, wclose, wsma, rs_term, slope_min)
    grn = _green(wopen, whigh, wlow, wclose)
    for k in range(base_len + 2, n):
        if not (up[k] and grn[k]):
            continue
        lo, hi = k - base_len, k                      # base window [lo, k)
        base_hi = whigh[lo:hi].max()
        if not (wclose[k] > base_hi):                 # must break the base high
            continue
        # contraction depths: drawdowns from the running peak within the base
        seg_h = whigh[lo:hi]; seg_l = wlow[lo:hi]
        run_peak = np.maximum.accumulate(seg_h)
        dd = 1.0 - seg_l / np.where(run_peak > 0, run_peak, np.nan)
        # split base into halves; later-half max contraction must be shallower than earlier-half
        half = (hi - lo) // 2
        early = np.nanmax(dd[:half]) if half > 0 else np.nan
        late = np.nanmax(dd[half:]) if (hi - lo - half) > 0 else np.nan
        if not (early == early and late == late and late <= tighten_ratio * early and min_contractions <= 2):
            continue
        v_base = np.nanmean(wvol[lo:hi])
        v_prior = np.nanmean(wvol[max(lo - base_len, 0):lo])
        vol_ok = True
        if v_base == v_base and v_prior == v_prior and v_prior > 0:
            vol_ok = (v_base <= vol_dry * v_prior)
        v_break = wvol[k]
        if not (np.isnan(v_break) or np.isnan(v_base) or v_base <= 0):
            vol_ok = vol_ok and (v_break >= vol_expand * v_base)
        if vol_ok:
            sig[k] = True
            stop[k] = wlow[lo:hi].min()
    return sig, stop


def flag_signal(wopen, whigh, wlow, wclose, wvol, wsma, slope, rs_term, *,
                pole_len=6, pole_gain=0.30, flag_len=4, flag_tight=0.15, high_tight=False,
                slope_min=SLOPE_MIN):
    """Bull flag (and, with ``high_tight=True``, the High-Tight Flag): a strong prior impulse (the
    pole), then a tight shallow consolidation (the flag), then a green breakout above the flag high.

    Pole: ``wclose`` up >= ``pole_gain`` over the ``pole_len`` weeks ending where the flag begins.
    Flag: the last ``flag_len`` weeks form a tight range (range/price <= ``flag_tight``) holding above
    the 44w SMA. Signal = green close above the flag high. High-tight overrides to pole_gain>=1.0 over
    a short pole and a very tight flag. Stop = flag low.
    """
    if high_tight:
        pole_len, pole_gain, flag_len, flag_tight = 6, 1.0, 4, 0.25
    n = len(wclose)
    sig = np.zeros(n, bool)
    stop = wlow.astype(float).copy()
    up = _uptrend(slope, wclose, wsma, rs_term, slope_min)
    grn = _green(wopen, whigh, wlow, wclose)
    for k in range(pole_len + flag_len + 1, n):
        if not (up[k] and grn[k]):
            continue
        f0 = k - flag_len                              # flag = [f0, k)
        p0 = f0 - pole_len                             # pole = [p0, f0)
        if p0 < 0:
            continue
        pole = wclose[f0 - 1] / wclose[p0] - 1.0 if wclose[p0] > 0 else np.nan
        if not (pole == pole and pole >= pole_gain):
            continue
        f_hi = whigh[f0:k].max(); f_lo = wlow[f0:k].min()
        if not (f_lo > 0 and (f_hi - f_lo) / f_lo <= flag_tight):
            continue
        if not np.all(np.nan_to_num(wclose[f0:k], nan=-1) > np.nan_to_num(wsma[f0:k], nan=1e18)):
            continue                                   # flag held above the SMA the whole time
        if wclose[k] > f_hi:                           # breakout above the flag
            sig[k] = True
            stop[k] = f_lo
    return sig, stop


def cup_handle_signal(wopen, whigh, wlow, wclose, wvol, wsma, slope, rs_term, *,
                      cup_len=18, rim_band=0.06, min_depth=0.12, max_depth=0.40,
                      handle_len=4, handle_max=0.15, slope_min=SLOPE_MIN):
    """Cup-with-handle (O'Neil): a rounded base (two rims at similar height with a trough between),
    a short shallow handle near the right rim, then a green breakout above the rim.

    Cup = trailing ``cup_len`` weeks: left rim and right rim within ``rim_band`` of each other, with a
    mid trough ``min_depth``..``max_depth`` below the rim. Handle = last ``handle_len`` weeks, a shallow
    pullback (<= ``handle_max`` off the right rim) holding above the SMA. Signal = green close above the
    right rim. Stop = handle low.
    """
    n = len(wclose)
    sig = np.zeros(n, bool)
    stop = wlow.astype(float).copy()
    up = _uptrend(slope, wclose, wsma, rs_term, slope_min)
    grn = _green(wopen, whigh, wlow, wclose)
    for k in range(cup_len + 2, n):
        if not (up[k] and grn[k]):
            continue
        c0, c1 = k - cup_len, k - handle_len           # cup body [c0, c1), handle [c1, k)
        if c1 - c0 < 6:
            continue
        left_rim = whigh[c0:c0 + 3].max()
        right_rim = whigh[c1 - 3:c1].max()
        if not (left_rim > 0 and abs(right_rim / left_rim - 1.0) <= rim_band):
            continue
        rim = max(left_rim, right_rim)
        trough = wlow[c0:c1].min()
        depth = 1.0 - trough / rim if rim > 0 else np.nan
        if not (depth == depth and min_depth <= depth <= max_depth):
            continue
        h_lo = wlow[c1:k].min()
        handle_dd = 1.0 - h_lo / right_rim if right_rim > 0 else np.nan
        if not (handle_dd == handle_dd and handle_dd <= handle_max):
            continue
        if not np.all(np.nan_to_num(wclose[c1:k], nan=-1) > np.nan_to_num(wsma[c1:k], nan=1e18)):
            continue                                   # handle held above the SMA
        if wclose[k] > rim:                            # breakout above the rim
            sig[k] = True
            stop[k] = h_lo
    return sig, stop


def ascending_base_signal(wopen, whigh, wlow, wclose, wvol, wsma, slope, rs_term, *,
                          look=20, n_lows=3, min_rise=0.03, pull_min=0.05, pull_max=0.25,
                          slope_min=SLOPE_MIN):
    """Ascending base (O'Neil): a sequence of ``n_lows`` successively HIGHER pullback lows in an
    uptrend, each pullback ``pull_min``..``pull_max`` deep, then a green breakout to a new high.

    We find local swing lows over the trailing ``look`` weeks; require the last ``n_lows`` of them to be
    strictly rising (each >= ``min_rise`` above the prior) with pullback depths in band, and the signal
    week a green close above the trailing high. Stop = the most recent swing low.
    """
    n = len(wclose)
    sig = np.zeros(n, bool)
    stop = wlow.astype(float).copy()
    up = _uptrend(slope, wclose, wsma, rs_term, slope_min)
    grn = _green(wopen, whigh, wlow, wclose)
    for k in range(look + 3, n):
        if not (up[k] and grn[k]):
            continue
        lo = k - look
        # local swing lows: wlow[i] is the min of its +/-1 neighbourhood
        piv = [i for i in range(lo + 1, k - 1) if wlow[i] <= wlow[i - 1] and wlow[i] <= wlow[i + 1]]
        if len(piv) < n_lows:
            continue
        lows = [wlow[i] for i in piv[-n_lows:]]
        rising = all(lows[j] >= lows[j - 1] * (1 + min_rise) for j in range(1, n_lows))
        if not rising:
            continue
        # each pullback depth (from the interior peak between consecutive lows) in band
        pk = piv[-n_lows:]
        ok_depth = True
        for j in range(1, n_lows):
            seg_hi = whigh[pk[j - 1]:pk[j] + 1].max()
            d = 1.0 - lows[j] / seg_hi if seg_hi > 0 else np.nan
            if not (d == d and pull_min <= d <= pull_max):
                ok_depth = False
                break
        if not ok_depth:
            continue
        if wclose[k] > whigh[lo:k].max():              # breakout to a new base high
            sig[k] = True
            stop[k] = lows[-1]
    return sig, stop


def double_bottom_signal(wopen, whigh, wlow, wclose, wvol, wsma, slope, rs_term, *,
                         look=16, bottom_band=0.05, min_sep=3, peak_min=0.05,
                         slope_min=SLOPE_MIN):
    """Double bottom (W): two troughs at a similar level separated by a middle peak, then a green
    breakout above that middle peak. Trend-gated (44w SMA rising) so it stays a continuation-style
    higher-low base, not a countertrend reversal.

    Over the trailing ``look`` weeks find the two lowest swing lows at least ``min_sep`` weeks apart and
    within ``bottom_band`` of each other; the interior peak between them must be >= ``peak_min`` above the
    bottoms; the signal week is a green close above that peak. Stop = the second (right) bottom.
    """
    n = len(wclose)
    sig = np.zeros(n, bool)
    stop = wlow.astype(float).copy()
    up = _uptrend(slope, wclose, wsma, rs_term, slope_min)
    grn = _green(wopen, whigh, wlow, wclose)
    for k in range(look + 2, n):
        if not (up[k] and grn[k]):
            continue
        lo = k - look
        piv = [i for i in range(lo + 1, k - 1) if wlow[i] <= wlow[i - 1] and wlow[i] <= wlow[i + 1]]
        if len(piv) < 2:
            continue
        piv_sorted = sorted(piv, key=lambda i: wlow[i])[:3]  # candidate low troughs
        found = False
        for a in range(len(piv_sorted)):
            for b in range(a + 1, len(piv_sorted)):
                i1, i2 = sorted((piv_sorted[a], piv_sorted[b]))
                if i2 - i1 < min_sep:
                    continue
                b1, b2 = wlow[i1], wlow[i2]
                if b1 <= 0 or abs(b2 / b1 - 1.0) > bottom_band:
                    continue
                peak = whigh[i1:i2 + 1].max()
                if peak <= 0 or (peak / max(b1, b2) - 1.0) < peak_min:
                    continue
                if wclose[k] > peak:                   # breakout above the middle peak
                    sig[k] = True
                    stop[k] = b2
                    found = True
                    break
            if found:
                break
    return sig, stop


# origin -> (name, detector). prep_weekly_rank iterates this when the matching flag is on.
ZOO = {
    4: ("vcp", vcp_signal),
    5: ("flag", flag_signal),
    6: ("cup_handle", cup_handle_signal),
    7: ("ascending_base", ascending_base_signal),
    8: ("double_bottom", double_bottom_signal),
}
