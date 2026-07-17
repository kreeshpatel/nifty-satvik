"""Pre-reg 0094 — CRS-strength fill ranking on the live weekly book (Level-0, no training).

Signal set is byte-identical to the LIVE 0093 + Nifty-50 config (finding 0037). The ONE change: when
multiple signals compete for limited cash, fillable candidates are attempted in DESCENDING CRS distance
(rank = RS / SMA40(RS) − 1 at the signal week; RS = weekly close / Nifty-50) instead of arbitrary dict
order. Nothing is added to or dropped from the signal set — only who gets the cash first.

Pre-declared diagnostic: rank-IC (Spearman of rank vs realized trade R) — decides whether any trained
(Level-2) ranker is ever worth building.

Frozen in diagnostics/research/preregistry/0094-weekly-crs-rank-fill.md.

    python scripts/run_bhanushali_weekly_rank.py [--ledger]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS  # noqa: E402
import run_bhanushali_weekly_full as W89  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.engine.portfolio import vol_target_scalar  # noqa: E402  — O-009 de-gross scalar (shared formula, pre-reg 0095)
from nq.runner.research import _dsr_from_bootstrap  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_faithful import EQ0, START  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import RISK, STT_PCT, _cost_leg, _row, _slices, prep  # noqa: E402
from run_bhanushali_sixstep_runner import TRAIL_PCT  # noqa: E402
from run_bhanushali_weekly_full import CAP_WEEKS  # noqa: E402

SLOPE_MIN, SLOPE_LOOKBACK, TOUCH_BAND, CRS_LEN = 0.03, 13, 0.07, 40   # the live 0093-N50 params (frozen)


def prep_weekly_rank(ohlcv, drop_erratum: bool = False, index_provider=None, drop_rs: bool = False,
                     first_touch: bool = False, base_min: int = 0, base_lookback: int = 8,
                     base_band: float = 0.12, decouple_touch_green: bool = False, green_wait: int = 3,
                     box_breakout: bool = False, box_len: int = 8, box_tight: float = 0.30,
                     box_close_range: bool = False, box_maxrunup: float = 0.0,
                     trend_pullback: bool = False, tp_band: float = 0.05,
                     sr_breakout: bool = False, sr_len: int = 12, sr_test_band: float = 0.03,
                     sr_recent: int = 2, sr_pivot: bool = False, sr_piv_len: int = 14,
                     sr_piv_band: float = 0.03, sr_piv_stop: float = 0.06,
                     zoo_origins: tuple = (), zoo_params: dict | None = None,
                     require_progress: bool = False, slope_min: float | None = None,
                     prior_above_n: int = 0, prior_above_lookback: int = 4):
    """The live 0093+Nifty-50 prep, with each entry window carrying its CRS-distance rank.

    index_provider (pre-reg 0096): optional callable(ticker) -> pd.Series to override the CRS
    denominator per ticker (e.g. the stock's own sector index). Returning None for a ticker falls
    back to Nifty-50. index_provider=None (default) => Nifty-50 for all => byte-identical 0094 run."""
    n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
    P = prep(ohlcv, drop_erratum=drop_erratum)
    for t, s in P.items():
        c = s["c"]
        s["ema20"] = pd.Series(c).rolling(20).mean().to_numpy()
        idx = pd.DatetimeIndex(s["dates"]); iso = idx.isocalendar()
        keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        o, h, l = s["o"], s["h"], s["l"]
        wopen = np.array([o[dd[0]] for dd in weeks]); whigh = np.array([h[dd].max() for dd in weeks])
        wlow = np.array([l[dd].min() for dd in weeks]); wclose = np.array([c[dd[-1]] for dd in weeks])
        # weekly VOLUME (sum), aligned to the same ISO-week groups — read only by the zoo detectors
        # (VCP/flag volume tests). Extra data; the frozen 0094 run never reads it => byte-identical.
        _vraw = (ohlcv[t]["Volume"].reindex(pd.DatetimeIndex(s["dates"])).to_numpy(float)
                 if "Volume" in ohlcv[t].columns else np.full(len(c), np.nan))
        wvol = np.array([np.nansum(_vraw[dd]) for dd in weeks])
        wsma = pd.Series(wclose).rolling(44).mean().to_numpy()
        # weekly HLC + 20-WEEK SMA keyed by the weekend day — READ ONLY by the Phase-2 blow-off / 20wk-trail
        # exits (the visual exit forensic showed the giveback tell is a weekly blow-off bar closing in its lower
        # third, and the correct trail reference is the 20-WEEK line, not the 20-day ema20). Extra data only;
        # not read by the frozen run => byte-identical 0094.
        _w20wk = pd.Series(wclose).rolling(20).mean().to_numpy()
        s["wk_hlc"] = {weeks[_j][-1]: (float(whigh[_j]), float(wlow[_j]), float(wclose[_j]),
                       float(_w20wk[_j]) if _w20wk[_j] == _w20wk[_j] else float("nan")) for _j in range(len(weeks))}
        slope = np.full(len(wsma), np.nan); slope[SLOPE_LOOKBACK:] = wsma[SLOPE_LOOKBACK:] / wsma[:-SLOPE_LOOKBACK] - 1.0
        rng = whigh - wlow
        qgreen = (wclose > wopen) & (rng > 0) & ((wclose - wlow) >= 0.5 * rng)
        touch = (wlow <= wsma * (1 + TOUCH_BAND)) & (wclose > wsma)
        idx_series = index_provider(t) if index_provider is not None else None
        if idx_series is None:
            idx_series = n50
        ia = idx_series.reindex(idx, method="ffill").to_numpy(float)
        iw = np.array([ia[dd[-1]] for dd in weeks])
        rs = np.where(iw > 0, wclose / iw, np.nan)
        rs_sma = pd.Series(rs).rolling(CRS_LEN).mean().to_numpy()
        crs_dist = rs / rs_sma - 1.0                                    # the FROZEN rank
        # forensic lever 1: the RS>SMA40(RS) gate blocks the earlier clean near-SMA touch and only clears
        # on the blow-off week; drop_rs lets those earlier touches fire (crs_dist still ranks the fills).
        _rs_term = np.ones(len(rs), bool) if drop_rs else np.nan_to_num(rs > rs_sma, nan=False)
        # forensic lever (winner contrast): the runners had a real BASE near the SMA in the weeks BEFORE the
        # signal; losers fired on a lone blow-off wick descending from far overhead. base_min>0 requires at
        # least base_min of the prior base_lookback weeks to have CLOSED within base_band of the SMA (i.e. a
        # recent base near the line preceded the touch). base_min=0 => off => byte-identical 0094.
        if base_min > 0:
            _near = np.nan_to_num(wclose <= wsma * (1 + base_band), nan=False) & np.nan_to_num(wclose > 0, nan=False)
            _base_ok = np.zeros(len(wclose), bool)
            for _k in range(len(wclose)):
                _lo = max(_k - base_lookback, 0)
                if _k > _lo and _near[_lo:_k].sum() >= base_min:
                    _base_ok[_k] = True
        else:
            _base_ok = np.ones(len(wclose), bool)
        if decouple_touch_green:
            # PHASE-1 entry TIMING lever: the owner's rule is a SEQUENCE — price TOUCHES the SMA (that week may
            # be red / close below the line), THEN you buy the first GREEN week that follows. The base engine
            # instead requires touch AND green on the SAME bar, which pushes the fire onto the explosive reclaim
            # week (extended). Here we ARM on a touch (low in band, uptrend — no green / close>SMA required) and
            # fire on the FIRST green+close>SMA week within green_wait weeks of that touch. off => byte-identical.
            _touched = np.nan_to_num((wlow <= wsma * (1 + TOUCH_BAND)) & (slope >= SLOPE_MIN), nan=False)
            _greenok = (np.nan_to_num(qgreen, nan=False) & np.nan_to_num(wclose > wsma, nan=False)
                        & (np.nan_to_num(slope, nan=-9) >= SLOPE_MIN) & _rs_term & _base_ok)
            wsig = np.zeros(len(wclose), bool); _armed = -1
            for _k in range(len(wclose)):
                if _touched[_k]:
                    _armed = _k + green_wait                     # arm the buy window from this touch
                if _k <= _armed and _greenok[_k]:
                    wsig[_k] = True; _armed = -1                 # first green after the touch — consume the arm
        else:
            # OWNER RULE-FAITHFUL LEVERS (chart review 2026-07-16), default OFF => byte-identical.
            #  slope_min:        C4 — "not even in a proper visible uptrend" (RAIN). The live floor is a
            #                    weak 3%/13wk; a visible uptrend needs a higher bar. None => SLOPE_MIN.
            #  require_progress: C1/C2 — "the setup candle should close ABOVE the previous candle"
            #                    (APOLLOHOSP/RAINBOW). qgreen only checks close>open, so a green candle
            #                    inside a downswing qualifies (RAINBOW closed 1444.8 vs prior 1454.3).
            _slope_floor = SLOPE_MIN if slope_min is None else slope_min
            _prog = np.ones(len(wclose), bool)
            if require_progress:
                _prog = np.zeros(len(wclose), bool)
                _prog[1:] = wclose[1:] > wclose[:-1]
            # OWNER LEVER C5 — "it was already BELOW our SMA and one candle we bought it"
            # (ZFCVINDIA 2024-05-31: 6 straight weeks -7..-10% BELOW the SMA, then ONE +30% candle closes
            #  +15% above -> fires. RCF 2024-11-29: 5 of 6 weeks below, one +15% candle -> fires.)
            # The touch rule (low<=SMA*1.07 AND close>SMA) cannot distinguish a genuine PULLBACK (price
            # above the line, dips to it, bounces) from a RECOVERY THROUGH the line from below — both
            # satisfy it. The 44w SMA lags, so slope still reads "rising" after weeks of price below it.
            # prior_above_n>0 requires >= n of the prior `prior_above_lookback` weeks to have CLOSED ABOVE
            # the SMA, i.e. we were already in an uptrend above the line. (Distinct from base_min, which
            # requires closes NEAR/below the SMA within a band.) 0 => off => byte-identical.
            _prior_above = np.ones(len(wclose), bool)
            if prior_above_n > 0:
                _ab = np.nan_to_num(wclose > wsma, nan=False)
                _prior_above = np.zeros(len(wclose), bool)
                for _k in range(len(wclose)):
                    _lo = max(_k - prior_above_lookback, 0)
                    if _k > _lo and _ab[_lo:_k].sum() >= prior_above_n:
                        _prior_above[_k] = True
            wsig = ((slope >= _slope_floor) & qgreen & touch & (wclose > wsma) & _rs_term & _base_ok
                    & _prog & _prior_above)
        # PHASE-1 entry lever (owner's GAIL case): the flat-base / Darvas-box breakout. Some leaders never pull
        # BACK to the SMA — they consolidate in a tight range ABOVE the rising line and let the SMA rise INTO
        # them (a TIME correction), then break out. The touch rule (low<=SMA*1.07) is blind to this. box_breakout
        # ARMS an additive signal: a tight base (range<=box_tight) that held ABOVE the SMA for box_len weeks in
        # an uptrend, then a GREEN week CLOSES above the box high. Stop = box low. off => byte-identical 0094.
        _stop_arr = wlow.astype(float).copy()
        _origin = np.where(np.nan_to_num(wsig, nan=False), 0, -1).astype(int)   # 0=touch, 1=box, 2=trend, 3=sr
        if box_breakout:
            _bsig = np.zeros(len(wclose), bool); _box_lo = np.full(len(wclose), np.nan)
            for _k in range(box_len, len(wclose)):
                if not (np.nan_to_num(slope[_k], nan=-9) >= SLOPE_MIN):
                    continue
                _bh = whigh[_k - box_len:_k].max(); _bl = wlow[_k - box_len:_k].min()
                # tightness test: CLOSE-range (box_close_range) ignores lone wick spikes that inflate the hi-lo
                # range and wrongly reject a real base (the MAZDOCK miss — an Apr-22 spike blocked a tight base).
                if box_close_range:
                    _ch = wclose[_k - box_len:_k].max(); _cl = wclose[_k - box_len:_k].min()
                    _tight_ok = (_cl > 0 and (_ch - _cl) / _cl <= box_tight)
                else:
                    _tight_ok = (_bl > 0 and (_bh - _bl) / _bl <= box_tight)
                if not _tight_ok:
                    continue                                            # base not tight enough
                # late-cycle guard: skip a breakout on a name already parabolic (52-wk run-up > box_maxrunup) —
                # the ASTRAL top was a REAL box that broke out after a 3x year and rolled over. off (0) => no guard.
                if box_maxrunup and _k >= 52 and wclose[_k - 52] > 0 and wclose[_k] / wclose[_k - 52] - 1 > box_maxrunup:
                    continue
                _sm = wsma[_k]
                if not (_sm == _sm and np.nanmin(wclose[_k - box_len:_k]) > _sm):
                    continue                                            # base did not hold above the SMA
                if (np.nan_to_num(qgreen[_k], nan=False) and wclose[_k] > _bh
                        and _rs_term[_k] and np.nan_to_num(_base_ok[_k], nan=False)):
                    _bsig[_k] = True; _box_lo[_k] = _bl                 # breakout — stop at the box low
            # additive: a week already firing the touch signal keeps its own (tighter) stop.
            # (Assign the box stop ONLY to NEW box weeks — writing _stop_arr in-loop corrupted the
            #  stop of touch weeks that also met the box condition; masked-assign fixes that.)
            _new_box = _bsig & ~np.nan_to_num(wsig, nan=False)
            _stop_arr[_new_box] = _box_lo[_new_box]
            wsig = np.nan_to_num(wsig, nan=False) | _new_box
            _origin[_new_box] = 1
        # PHASE-1 setup #3 — TREND CONTINUATION (owner's VBL case): a leader in a strong 44-SMA uptrend that
        # rides ABOVE the line and pulls back only shallowly — to the 20-WEEK MA — never reaching the 44-SMA
        # touch band. Distinct from setup #1 (needs low near the 44) and #2 (needs a tight flat base). Arms when
        # in an uptrend the week's low tags the 20wk MA (within tp_band) while still ABOVE the 44-SMA, closes
        # green above the 20wk. Stop = pullback low. off => byte-identical 0094.
        if trend_pullback:
            _w20 = pd.Series(wclose).rolling(20).mean().to_numpy()
            _tsig = (np.nan_to_num(slope, nan=-9) >= SLOPE_MIN) & np.nan_to_num(qgreen, nan=False) & _rs_term
            _tsig &= np.nan_to_num(wlow <= _w20 * (1 + tp_band), nan=False)      # pulled back to the 20wk MA
            _tsig &= np.nan_to_num(wclose > _w20, nan=False)                     # closed back above the 20wk
            _tsig &= np.nan_to_num(wlow > wsma * (1 + TOUCH_BAND), nan=False)    # but NOT a 44-SMA touch (distinct)
            _tsig = _tsig & ~np.nan_to_num(wsig, nan=False)                      # additive to touch+box
            wsig = np.nan_to_num(wsig, nan=False) | _tsig
            _origin[_tsig] = 2
        # PHASE-1 setup #4 — SUPPORT/RESISTANCE BREAKOUT: a horizontal resistance (a prior swing high TESTED
        # >=2 times) that price has sat UNDER, then a GREEN week CLOSES above it in an uptrend. Looser than the
        # box (#2 needs a tight range); this only needs a tested level + a clean break. Stop = the base low
        # under the resistance. off => byte-identical 0094.
        if sr_breakout:
            _srsig = np.zeros(len(wclose), bool); _sr_lo = np.full(len(wclose), np.nan)
            for _k in range(sr_len, len(wclose)):
                if not (np.nan_to_num(slope[_k], nan=-9) >= SLOPE_MIN
                        and np.nan_to_num(qgreen[_k], nan=False) and _rs_term[_k]):
                    continue
                _lo = _k - sr_len; _res = whigh[_lo:_k].max()                     # prior swing-high resistance
                _tested = int(np.sum(whigh[_lo:_k] >= _res * (1 - sr_test_band))) # times the level was hit
                _sm = wsma[_k]
                if (_tested >= 2 and wclose[_k - 1] <= _res and wclose[_k] > _res  # sat under, now breaks out
                        and _sm == _sm and wclose[_k] > _sm):                      # above the 44 (uptrend)
                    _srsig[_k] = True; _sr_lo[_k] = wlow[_lo:_k].min()             # stop = base low
            _srsig = _srsig & ~np.nan_to_num(wsig, nan=False)
            _stop_arr[_srsig] = _sr_lo[_srsig]                                     # only NEW weeks (don't corrupt touch stops)
            wsig = np.nan_to_num(wsig, nan=False) | _srsig
        # PHASE-1 setup #4b — PROPER pivot-based S/R breakout (chart-validated, replaces the crude trailing-high
        # version whose 33% stops were a mirage). A resistance LEVEL = >=2 PIVOT HIGHS clustered within
        # sr_piv_band of each other (price rejected there repeatedly); a green week closes above it in an
        # uptrend; stop = level*(1-sr_piv_stop) — just below the broken resistance (now support). off => identical.
        if sr_pivot:
            _piv = np.zeros(len(whigh), bool); _sp_lo = np.full(len(wclose), np.nan)
            for _i in range(2, len(whigh) - 2):
                if whigh[_i] >= whigh[_i - 2:_i + 3].max():
                    _piv[_i] = True
            _spsig = np.zeros(len(wclose), bool)
            for _k in range(sr_piv_len, len(wclose)):
                if not (np.nan_to_num(slope[_k], nan=-9) >= SLOPE_MIN
                        and np.nan_to_num(qgreen[_k], nan=False) and _rs_term[_k]):
                    continue
                _pv = [whigh[_i] for _i in range(_k - sr_piv_len, _k - 1) if _piv[_i]]
                if len(_pv) < 2:
                    continue
                _lvl = float(np.median(_pv))
                _near = int(np.sum([abs(p / _lvl - 1) <= sr_piv_band for p in _pv]))
                _sm = wsma[_k]
                if (_near >= 2 and wclose[_k - 1] <= _lvl and wclose[_k] > _lvl
                        and _sm == _sm and wclose[_k] > _sm):
                    _spsig[_k] = True; _sp_lo[_k] = _lvl * (1 - sr_piv_stop)      # tight stop below the level
            _spsig = _spsig & ~np.nan_to_num(wsig, nan=False)
            _stop_arr[_spsig] = _sp_lo[_spsig]                                    # only NEW weeks (don't corrupt touch stops)
            wsig = np.nan_to_num(wsig, nan=False) | _spsig
            _origin[_spsig] = 3
        # PHASE-1 setups #5-9 — the TraderLion pattern zoo (VCP / flag / cup&handle / ascending base /
        # double bottom). Pure detectors in nq.research.setups, wired here ADDITIVELY (each & ~wsig, so
        # touch/box/trend/sr are never relabeled) with origins 4-8. zoo_origins=() (default) => off =>
        # byte-identical 0094. Chart-validated before trust (scripts/render_chart.py).
        if zoo_origins:
            from nq.research import setups as _zoo
            _zp = zoo_params or {}
            for _org in zoo_origins:
                _zsig, _zstop = _zoo.ZOO[_org][1](wopen, whigh, wlow, wclose, wvol, wsma, slope,
                                                  _rs_term, **_zp.get(_org, {}))
                _znew = np.nan_to_num(_zsig, nan=False) & ~np.nan_to_num(wsig, nan=False)
                _stop_arr[_znew] = _zstop[_znew]
                wsig = np.nan_to_num(wsig, nan=False) | _znew
                _origin[_znew] = _org
        s["weekend"] = {dd[-1] for dd in weeks}
        # WEEKLY ATR(10) in PRICE units — read only by the `stop_atr_mult` lever (owner spec 2026-07-16).
        # Measured: weekly ATR median = 7.83% of price, so 1.0x ~= today's 7.1% median stop width. (The
        # repo's "2.5x/4x ATR" results are DAILY-ATR multiples; daily ATR ~3.5%, so they do NOT transfer.)
        _watr = pd.Series(whigh - wlow).rolling(10).mean().to_numpy()
        s["atr_at"] = {}
        s["entry_win"] = {}
        _wsflag = np.nan_to_num(wsig, nan=False)
        for k in np.flatnonzero(_wsflag):
            if k + 1 >= len(weeks):
                continue
            # forensic lever: first-touch — if the prior 1-2 weeks also fired, this is a LATER fire up the
            # same leg (the blow-off); keep only the FIRST fire of a consecutive run. Off => byte-identical.
            if first_touch and ((k >= 1 and _wsflag[k - 1]) or (k >= 2 and _wsflag[k - 2])):
                continue
            edays = weeks[k + 1]
            s["entry_win"][edays[0]] = (edays, float(_stop_arr[k]), float(whigh[k]), float(crs_dist[k]),
                                        float(wsma[k]) if wsma[k] == wsma[k] else float(_stop_arr[k]), int(_origin[k]))
            s["atr_at"][edays[0]] = float(_watr[k]) if _watr[k] == _watr[k] else float("nan")
        # LIVE actionable signal (latest COMPLETED week) + its rank — read only by the paper runner.
        # Completeness guard (fault F7): only ever surface a card from a COMPLETED weekly bar, never a
        # partial week the backtest doesn't score. weekday()>=4 = Friday or a Saturday NSE session.
        # Robustness (2026-07-13): if the run lands MID-WEEK (data extends into a new partial week),
        # step back to the last COMPLETED week so the board still shows last week's fresh buys — a
        # Monday-data run otherwise found 0 signals and every card fell through to HOLD.
        s["last_signal"] = None
        _ws = np.nan_to_num(wsig, nan=False)
        li = len(weeks) - 1
        if li >= 1 and pd.Timestamp(s["dates"][weeks[li][-1]]).weekday() < 4:
            li -= 1                                            # current week partial -> last completed week
        if li >= 0 and pd.Timestamp(s["dates"][weeks[li][-1]]).weekday() >= 4 and _ws[li]:
            s["last_signal"] = {"fri_idx": int(weeks[li][-1]), "lo": float(wlow[li]),
                                "hi": float(whigh[li]), "rank": float(crs_dist[li])}
    return P


def grade_a_entries(P, top_n: int = 5) -> set:
    """The set of (ticker, entry_day_idx) whose signal is TOP-N by CRS distance in its setup week —
    'Grade A'. Passed to backtest(a_grade=...) to trade only A, and used to filter the OPEN cards.
    Entry windows that start the same ISO week came from the same setup Friday, so ranking them by
    CRS distance and keeping the top-N is exactly the weekly A/B split shown on the cards."""
    from collections import defaultdict
    by_week = defaultdict(list)
    for t, s in P.items():
        dates = s["dates"]
        for e0, win in s["entry_win"].items():
            iso = pd.Timestamp(dates[e0]).isocalendar()
            by_week[(int(iso.year), int(iso.week))].append((float(win[3]), t, e0))
    a = set()
    for lst in by_week.values():
        lst.sort(key=lambda x: -x[0])
        for _rank, t, e0 in lst[:top_n]:
            a.add((t, e0))
    return a


def backtest(P, mem, *, cost_off: bool = False, ledger: list | None = None,
             start: str | None = None, return_state: bool = False,
             vol_target: tuple | None = None, eq0: float | None = None,
             uncapped: bool = False, a_grade: set | None = None,
             tp_on_high: bool = False, early_cut_pct: float = 0.0, early_cut_weeks: int = 2,
             trail_always: bool = False, trail_after: int = 2, cap_weeks: int = 0,
             lockin_mfe: float = 0.0, lockin_at: float = 1.0,
             chand_pct: float = 0.0, chand_after_r: float = 0.0,
             soft_stop_pct: float = 0.0,
             lh_arm_r: float = 0.0, lh_n: int = 2, no_time_cap: bool = False,
             trendhold_pct: float = 0.0, blowoff_arm_r: float = 0.0, blowoff_third: float = 0.34,
             wk20_trail_pct: float | None = None,
             risk_pct: float | None = None, max_positions: int = 0,
             entry_band: float | None = None, entry_strict: bool = False,
             ext_cap: float | None = None, ext_cap_touch_only: bool = False, fill_order: str = "crs",
             exit_by_origin: dict | None = None, conv_score: dict | None = None,
             ext_floor: float | None = None, entry_mode: str = "in_range",
             stop_atr_mult: float | None = None):
    """W89's weekly engine with ONE change: fillable candidates are attempted strongest-CRS-first.
    start/return_state mirror W89's live kwargs (defaults preserve the 0094 run of record).

    vol_target (pre-reg 0095): when set = (target_annual, window, floor), de-gross the SIZING equity
    by the shared O-009 scalar so fills shrink when the book's trailing realised vol is above target.
    None (default) => sizing_eq == eq exactly => byte-identical to the 0094 run of record.

    eq0: starting-capital override. None (default) => EQ0 (the ₹10L paper book). A very large eq0
    makes the book UNCAPPED — cash never runs out, so EVERY fillable signal enters and gets tracked
    (the signal ledger), not just the capital-constrained subset. Per-trade R / return_pct are
    capital-independent, so an uncapped run is the correct per-signal lifecycle; its NAV is ignored."""
    vt_ann, vt_win, vt_floor = vol_target if vol_target else (0.0, 42, 1.0)
    _EQ0 = EQ0 if eq0 is None else float(eq0)
    dts = pd.DatetimeIndex(sorted(set().union(*[set(s["dates"]) for s in P.values()])))
    dts = dts[dts >= pd.Timestamp(start or START)]
    didx = {t: {d: i for i, d in enumerate(s["dates"])} for t, s in P.items()}
    eq = cash = _EQ0
    op: dict[str, dict] = {}
    orders: dict[str, dict] = {}
    curve = []; T = []; skipped_cash = 0; activations = 0
    eq_hist: list[float] = []                       # book equity by day (for the vol-target scalar; prior-day only)
    for d in dts:
        dd = d.date()
        # ── manage opens: EXACT 0089/0093 exit logic (pending Monday fills, weekly-close decisions) ──
        for t in list(op):
            p = op[t]; i = didx[t].get(d)
            if i is None:
                continue
            s = P[t]
            if p["pending"] is not None:
                act, rs = p["pending"]
                px = s["o"][i]
                if act == "half":
                    half = p["sh0"] * 0.5; hp = half * px
                    got = hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                    cash += got; p["proceeds"] += got
                    p["sh"] -= half; p["half_done"] = True
                    p["stt"] += hp * STT_PCT; p["pending"] = None
                    if "rec" in p:
                        p["rec"].update(half_date=d, half_px=round(float(px), 2))
                else:
                    xp = p["sh"] * px
                    got = xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                    cash += got; p["proceeds"] += got
                    p["stt"] += xp * STT_PCT
                    r_rest = (px - p["en"]) / p["risk0"]
                    R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
                    T.append(dict(R=R, reason=rs, held=p["weeks"], half=p["half_done"]))
                    if "rec" in p:
                        p["rec"].update(exit_date=d, exit_px=round(float(px), 2), reason=rs,
                                        held_weeks=p["weeks"], R=round(float(R), 3),
                                        net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                        stt_paid=round(float(p["stt"]), 2))
                        ledger.append(p["rec"])
                    del op[t]
                    continue
            # forensic lever 2b: book the +2R half at a RESTING LIMIT the day the intraweek HIGH crosses
            # 2R (not the weekly close), capturing gains that spike through 2R then close below (e.g.
            # TRIVENI H512 vs target 495). Off (tp_on_high=False) => byte-identical.
            if tp_on_high and p["pending"] is None and not p["half_done"] and s["h"][i] >= p["tp2"]:
                px = p["tp2"]
                half = p["sh0"] * 0.5; hp = half * px
                got = hp * (1 - _cost_leg(p["adv"], hp, cost_off))
                cash += got; p["proceeds"] += got
                p["sh"] -= half; p["half_done"] = True
                p["stt"] += hp * STT_PCT
                if "rec" in p:
                    p["rec"].update(half_date=d, half_px=round(float(px), 2))
            # forensic lever: early-MAE cut — winners work immediately (median 1st-2wk MAE −3.9%) while
            # losers dig deep (−8.3%); cut a position that draws down > early_cut_pct% within the first
            # early_cut_weeks weeks (frees the slot for a fresh runner). Off (early_cut_pct=0) => byte-identical.
            if (early_cut_pct and p["pending"] is None and not p["half_done"]
                    and p["weeks"] <= early_cut_weeks):
                lvl = p["en"] * (1 - early_cut_pct / 100.0)
                if s["l"][i] <= lvl:
                    px = min(s["o"][i], lvl)
                    xp = p["sh"] * px
                    got = xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                    cash += got; p["proceeds"] += got; p["stt"] += xp * STT_PCT
                    R = (px - p["en"]) / p["risk0"]
                    T.append(dict(R=R, reason="earlycut", held=p["weeks"], half=False))
                    if "rec" in p:
                        p["rec"].update(exit_date=d, exit_px=round(float(px), 2), reason="earlycut",
                                        held_weeks=p["weeks"], R=round(float(R), 3),
                                        net_pnl=round(float(p["proceeds"] - p["cash_out"]), 2),
                                        stt_paid=round(float(p["stt"]), 2))
                        ledger.append(p["rec"])
                    del op[t]; continue
            if i in s["weekend"]:
                p["weeks"] += 1
                wc = s["c"][i]
                # CONTEXT-ROUTER: resolve this position's exit params by its setup origin. Stage-3 showed
                # each branch wants a different exit (touch -> P2 book+blowoff; box -> let-run). Absent key
                # falls back to the global arg; exit_by_origin=None (default) => the global args exactly
                # => byte-identical to the frozen run.
                _eo = exit_by_origin.get(p.get("origin", 0)) if exit_by_origin else None
                _blow = _eo.get("blowoff_arm_r", blowoff_arm_r) if _eo else blowoff_arm_r
                _wk20p = _eo.get("wk20_trail_pct", wk20_trail_pct) if _eo else wk20_trail_pct
                _ntc = _eo.get("no_time_cap", no_time_cap) if _eo else no_time_cap
                # PHASE-2 exit lever: lock-in ratchet — once a trade's intraweek MFE reaches lockin_mfe R, raise
                # the stop to lock in lockin_at R (attacks the giveback: trades peak at 2R+ then drift to the
                # 13wk cap at ~1R). off (lockin_mfe=0) => no ratchet.
                if lockin_mfe and p["weeks"] >= 1:
                    _mfe_r = (s["h"][i] - p["en"]) / p["risk0"] if p["risk0"] > 0 else 0.0
                    if _mfe_r >= lockin_mfe:
                        p["stop"] = max(p["stop"], p["en"] + lockin_at * p["risk0"])
                # PHASE-2 exit lever: CHANDELIER — a peak-based trailing stop (highest high since entry ×
                # (1-chand_pct)), engaged once MFE ≥ chand_after_r R. Trails the PEAK (not an MA), so it protects
                # the giveback from the high-water mark. off (chand_pct=0) => byte-identical.
                if chand_pct and p["weeks"] >= 1:
                    p["peak_h"] = max(p.get("peak_h", p["en"]), s["h"][i])
                    _mfe_r = (p["peak_h"] - p["en"]) / p["risk0"] if p["risk0"] > 0 else 0.0
                    if _mfe_r >= chand_after_r:
                        p["stop"] = max(p["stop"], p["peak_h"] * (1 - chand_pct))
                if wc <= p["stop"]:
                    p["pending"] = ("full", "stop" + ("_half" if p["half_done"] else ""))
                # PHASE-2 exit lever: SOFT STOP — cut on a trend break (weekly close < 20d-SMA×(1-soft_stop_pct))
                # BEFORE the hard stop is hit, to trim the −1.32R stop-outs. off (0) => byte-identical.
                elif soft_stop_pct and wc < s["ema20"][i] * (1 - soft_stop_pct):
                    p["pending"] = ("full", "soft" + ("_half" if p["half_done"] else ""))
                elif not p["half_done"] and wc >= p["tp2"]:
                    p["pending"] = ("half", "half")
                # PHASE-2 exit lever: trail_always applies the 20SMA*(1-TRAIL_PCT) trail even BEFORE the 2R half
                # books (after trail_after weeks) — the base engine has NO trail until 2R, so a trade that runs
                # to ~1.8R MFE but never hits 2R rides the 13wk cap and gives it all back. off => byte-identical.
                elif p["half_done"] or (trail_always and p["weeks"] >= trail_after):
                    p["trail"] = max(p["trail"], s["ema20"][i] * (1 - TRAIL_PCT))
                    if wc < p["trail"]:
                        p["pending"] = ("full", "trail")
                # PHASE-2 AI-derived exit (exit forensic): the giveback tell is a blow-off then LOWER weekly
                # closes while still above the loose trail; the bigger leak is the 13wk cap severing live trends.
                # lh_arm_r>0: once MFE ≥ lh_arm_r R, exit on lh_n consecutive LOWER weekly closes (the topping
                # tell) — lets winners run but cuts the round-trip. trendhold_pct: also exit if close < 20SMA×
                # (1-trendhold_pct) once up ≥2R (confirmed trend break). no_time_cap: drop the 13wk clock (52wk
                # backstop) so trend-intact winners run. All off => byte-identical.
                p["pk"] = max(p.get("pk", p["en"]), s["h"][i])
                _mfe_r = (p["pk"] - p["en"]) / p["risk0"] if p["risk0"] > 0 else 0.0
                if p["pending"] is None and lh_arm_r and _mfe_r >= lh_arm_r:
                    p["lc"] = (p.get("lc", 0) + 1) if wc < p.get("prev_wc", 1e18) else 0
                    if p["lc"] >= lh_n:
                        p["pending"] = ("full", "lhexit" + ("_half" if p["half_done"] else ""))
                if p["pending"] is None and trendhold_pct and _mfe_r >= 2.0 and wc < s["ema20"][i] * (1 - trendhold_pct):
                    p["pending"] = ("full", "thold" + ("_half" if p["half_done"] else ""))
                p["prev_wc"] = wc
                # PHASE-2 VISUAL exit levers (from the chart forensic): BLOW-OFF bar exit + 20-WEEK trail.
                _wk = s.get("wk_hlc", {}).get(i)
                if _wk is not None:
                    _wH, _wL, _wC, _w20 = _wk
                    # blow-off: after MFE≥blowoff_arm_r, exit if this week made a NEW high but CLOSED in its lower
                    # third (long upper wick = momentum exhaustion — the tell on YESBANK/IOB/CENTURYPLY/QUESS).
                    if (_blow and p["pending"] is None and _mfe_r >= _blow and (_wH - _wL) > 0
                            and _wH >= p.get("pk_wh", 0.0) and (_wC - _wL) < blowoff_third * (_wH - _wL)):
                        p["pending"] = ("full", "blowoff" + ("_half" if p["half_done"] else ""))
                    p["pk_wh"] = max(p.get("pk_wh", 0.0), _wH)
                    # 20-WEEK trail (the correct reference the charts use): once up ≥2R, exit on a weekly CLOSE
                    # below the 20-week SMA × (1-pct). Slow enough to let the monsters run, catches the rollover.
                    if (_wk20p is not None and p["pending"] is None and _mfe_r >= 2.0
                            and _w20 == _w20 and _wC < _w20 * (1 - _wk20p)):
                        p["pending"] = ("full", "wk20" + ("_half" if p["half_done"] else ""))
                _cap = 52 if _ntc else (cap_weeks if cap_weeks > 0 else CAP_WEEKS)
                if p["pending"] is None and p["weeks"] >= _cap:
                    p["pending"] = ("full", "time")
        # ── activate windows, then fill candidates STRONGEST-CRS-FIRST (the 0094 change) ──
        cands = []
        for t, s in P.items():
            i = didx[t].get(d)
            if i is None:
                continue
            if t not in op and t not in orders and i in s["entry_win"]:
                # a_grade (when passed): only enter TOP-N-by-CRS signals of the setup week (Grade A).
                is_a = a_grade is None or (t, i) in a_grade
                if is_a and (mem is None or ticker_in_index_on(t, dd, mem)):
                    days, lo, hi, rk, sma_sig, _org = s["entry_win"][i]
                    orders[t] = {"days": set(days), "lo": lo, "hi": hi, "rank": rk, "sma": sma_sig, "origin": _org,
                                 "atr": s.get("atr_at", {}).get(i, float("nan")),   # weekly ATR at the signal week
                                 # L3 conviction fill-ranking: the candidate's score, looked up at ACTIVATION
                                 # by (ticker, entry-window key) — i.e. from the completed signal week, PIT-safe.
                                 "conv": (conv_score.get((t, i), 0.0) if conv_score else 0.0)}
                    activations += 1
            o_ = orders.get(t)
            if o_ is not None and i in o_["days"] and t not in op:
                opn = s["o"][i]
                if entry_band is not None:
                    # PHASE-1 entry lever: buy NEAR the SMA, not the chased next-open. Rest a limit at
                    # SMA_signal*(1+entry_band); fill only if the week trades down to it (a pullback toward
                    # the line), at px = min(open, limit). If the open is already at/below the limit, fill at
                    # the open (it opened near the SMA). If price never reaches the limit within the entry
                    # window, entry_strict skips the trade (near-SMA-only); else falls back to the 0094 open.
                    lim = o_["sma"] * (1 + entry_band)
                    if opn <= lim:
                        cands.append((o_["rank"], t, i, opn))
                    elif s["l"][i] <= lim and o_["lo"] < lim < o_["hi"]:
                        cands.append((o_["rank"], t, i, lim))
                    elif (not entry_strict) and i == max(o_["days"]) and o_["lo"] < opn < o_["hi"]:
                        cands.append((o_["rank"], t, i, opn))     # window's last day: fallback fill at open
                elif entry_mode == "buystop":
                    # OWNER RULE-FAITHFUL LEVER C3 (chart review 2026-07-16): the taught rule is
                    # "buy Rs1 ABOVE the green candle's high" — a buy-stop, i.e. only enter if strength
                    # CONTINUES. The 0089 in-range fill enters on the next open regardless, so every
                    # reviewed trade filled BELOW the signal high (APOLLOHOSP -157.8, SOBHA -44.5) and some
                    # below the SMA (KENNAMET -1.5%). Here we fill only if the week trades through the
                    # signal high, at max(open, trigger). NOTE the known cost (pre-reg 0088): entry at the
                    # HIGH with the stop at the LOW makes the whole candle the risk (~12.8% vs ~7%).
                    # entry_mode="in_range" (default) => byte-identical.
                    _trig = o_["hi"]
                    if s["h"][i] >= _trig:
                        _px = max(opn, _trig)
                        if (ext_cap is not None and (not ext_cap_touch_only or o_.get("origin", 0) == 0)
                                and _px > o_["sma"] * (1 + ext_cap)):
                            continue
                        if (ext_floor is not None and o_["sma"] > 0
                                and _px <= o_["sma"] * (1 + ext_floor)):
                            continue
                        cands.append((o_["rank"], t, i, _px))
                elif o_["lo"] < opn < o_["hi"]:
                    # PHASE-1 entry lever: fill-time extension cap. The 20%+ blow-off fills are near-dead
                    # money (per-trade 47-51% win, ~0R) while <10% fires win 87%; skip a fill whose OPEN is
                    # > ext_cap over the signal-week SMA (PIT-safe: the open is observed before we buy).
                    # ext_cap_touch_only: apply the cap ONLY to touch-origin fills (origin 0) — the box/S/R
                    # breakouts are EXTENDED by nature (that IS their edge), so a <5% cap must not touch them.
                    if (ext_cap is not None and (not ext_cap_touch_only or o_.get("origin", 0) == 0)
                            and opn > o_["sma"] * (1 + ext_cap)):
                        continue
                    # OWNER GUARD (chart review 2026-07-16): the signal requires close>SMA, but the
                    # in-range fill (0089) can still land BELOW the line if the entry week opens down
                    # through it (e.g. KENNAMET -1.5%, NAVA -1.8%) — buying a name that has already
                    # broken back under support. ext_floor skips those fills. None => byte-identical.
                    if (ext_floor is not None and o_["sma"] > 0
                            and opn <= o_["sma"] * (1 + ext_floor)):
                        continue
                    cands.append((o_["rank"], t, i, opn))
        # vol-target de-gross (pre-reg 0095): scale the sizing equity by the shared O-009 scalar,
        # computed from PRIOR-day book returns only. Off (vol_target=None) => scl==1.0 => sizing_eq==eq.
        if vol_target and len(eq_hist) >= 2:
            eh = np.asarray(eq_hist, dtype=float)
            scl = vol_target_scalar(np.diff(eh) / eh[:-1], target_annual=vt_ann, floor=vt_floor, window=vt_win)
        else:
            scl = 1.0
        # Uncapped ledger sizes off a FIXED equity so every signal fills at a sane size even though
        # `eq`/cash go meaningless (NAV is ignored there); per-trade R/return are size-independent.
        sizing_eq = (_EQ0 if uncapped else eq) * scl
        # PHASE-1 entry lever: fill PRIORITY under the capital cap. Default 'crs' = strongest-CRS-first (the
        # 0094 run of record). 'near_sma' fills the candidate CLOSEST to the SMA first (lower extension = the
        # 90%-win 5–10% bucket) so scarce capital funds the higher-quality near-SMA fires before the extended
        # ones. Trade SET is unchanged (no trades dropped); only order under the cap changes. 'crs' => identical.
        if fill_order == "near_sma":
            _key = lambda x: (orders[x[1]]["sma"] and x[3] / orders[x[1]]["sma"], x[1])   # ascending extension
        elif fill_order == "conviction":
            # L3: fund the highest-CONVICTION candidate first (a trained multi-feature score) instead of
            # the strongest CRS. The book funds only ~2.6% of activated signals, so WHO gets the scarce
            # cash is the dominant decision. Trade SET is unchanged (nothing added/dropped) — only order.
            _key = lambda x: (-orders[x[1]].get("conv", 0.0), x[1])
        else:
            _key = lambda x: (-x[0], x[1])                                                # descending CRS distance
        _risk = RISK if risk_pct is None else risk_pct         # PHASE-3 sizing: per-trade risk (default 2%)
        for rk, t, i, opn in sorted(cands, key=_key):
            o_ = orders.get(t)
            if o_ is None or t in op:
                continue
            if max_positions and len(op) >= max_positions:     # PHASE-3 sizing: hard concurrent-position cap
                break
            s = P[t]
            en = opn; st = o_["lo"]
            # OWNER SPEC 2026-07-16 — ATR stop. The taught buy-stop (entry at the signal HIGH, stop at the
            # signal LOW) makes the WHOLE candle the risk (~12.8%), which is precisely why pre-reg 0088
            # died: position size halves and the R-multiple collapses. stop_atr_mult replaces the candle
            # low with entry - mult x weekly ATR, so the risk width is preserved (1.0x ~= 7.8% ~= today's
            # 7.1%) and 0088's failure cause is neutralised. None => the taught low => byte-identical.
            if stop_atr_mult:
                _atr = o_.get("atr", float("nan"))
                if _atr == _atr and _atr > 0:
                    st = en - stop_atr_mult * _atr
            if en > st:
                sh = sizing_eq * _risk / (en - st)
                notion = sh * en * (1 + _cost_leg(s["adv20"][i], sh * en, cost_off))
                if (uncapped or notion <= cash) and sh > 0:   # uncapped: fill EVERY signal (ledger mode)
                    cash -= notion
                    op[t] = dict(en=en, stop=st, risk0=en - st, tp2=en + 2 * (en - st), sh=sh, sh0=sh,
                                 weeks=0, adv=s["adv20"][i], half_done=False, trail=st, pending=None,
                                 stt=sh * en * STT_PCT, cash_out=notion, proceeds=0.0,
                                 origin=int(o_.get("origin", 0)))   # CONTEXT-ROUTER: per-branch exit lookup
                    rp = sh * (en - st) / sizing_eq * 100      # risk as % of SIZING equity
                    assert _risk * 100 - 0.02 <= rp <= _risk * 100 + 0.02, f"sizing {rp:.3f}"
                    if ledger is not None:
                        op[t]["rec"] = dict(tkr=t, entry_date=d, entry=round(float(en), 2),
                                            stop0=round(float(st), 2), rank=round(float(rk), 4),
                                            half_date=None, half_px=None)
                    del orders[t]
                else:
                    skipped_cash += 1
        # window expiry (unfilled orders whose entry week ended today)
        for t in list(orders):
            i = didx[t].get(d)
            if i is not None and i == max(orders[t]["days"]):
                del orders[t]
        mtm = sum(p["sh"] * (P[t]["c"][didx[t][d]] if d in didx[t] else p["en"]) for t, p in op.items())
        eq = cash + mtm
        assert uncapped or cash >= -1e-6   # uncapped mode lets cash go negative (NAV is ignored there)
        curve.append((d, eq))
        eq_hist.append(eq)
    if not return_state:                       # backtest convention: realize open positions at window end
        for t, p in op.items():
            i = len(P[t]["c"]) - 1; ex = P[t]["c"][i]
            r_rest = (ex - p["en"]) / p["risk0"]
            R = 0.5 * 2.0 + 0.5 * r_rest if p["half_done"] else r_rest
            T.append(dict(R=R, reason="eos", held=p["weeks"], half=p["half_done"]))
            if ledger is not None and "rec" in p:
                xp = p["sh"] * ex
                mark = p["proceeds"] + xp * (1 - _cost_leg(p["adv"], xp, cost_off))
                p["rec"].update(exit_date=P[t]["dates"][i], exit_px=round(float(ex), 2), reason="eos",
                                held_weeks=p["weeks"], R=round(float(R), 3),
                                net_pnl=round(float(mark - p["cash_out"]), 2),
                                stt_paid=round(float(p["stt"] + xp * STT_PCT), 2))
                ledger.append(p["rec"])
    e = pd.Series(dict(curve)).sort_index()
    r = e.pct_change().dropna()
    empty = len(e) < 2
    yrs = (e.index[-1] - e.index[0]).days / 365.25 if not empty else 1.0
    R = np.array([x["R"] for x in T])
    reasons = pd.Series([x["reason"] for x in T]).value_counts().to_dict() if T else {}
    out = dict(curve=e, ret=r, trades=len(R), tpy=len(R) / yrs, activations=activations,
                wr=(R > 0).mean() if len(R) else float("nan"),
                expR=R.mean() if len(R) else float("nan"),
                medhold=float(np.median([x["held"] for x in T]) * 5) if T else float("nan"),
                p90hold=float(np.percentile([x["held"] for x in T], 90) * 5) if T else float("nan"),
                cagr=((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) if not empty else 0.0,
                sharpe=r.mean() / r.std() * np.sqrt(252) if (not empty and r.std()) else float("nan"),
                dd=(e / e.cummax() - 1).min() if not empty else 0.0,
                mult=(e.iloc[-1] / _EQ0) if not empty else 1.0,
                reasons=reasons, skipped_cash=skipped_cash)
    if return_state:
        out["open_positions"] = op
        out["active_orders"] = orders          # ticker -> {days, lo, hi, rank}
        out["cash"] = cash
        out["equity"] = float(eq)
    return out


def main() -> int:
    args = sys.argv[1:]
    print("=== pre-reg 0094: CRS-strength fill ranking (Level-0) on the live 0093+Nifty-50 book ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    print(f"corrected universe: {len(P)} names | rank = RS/SMA40(RS)-1, fill strongest-first | live 0093-N50 config\n")

    ledger: list = []
    net = backtest(P, mem, ledger=ledger)
    gross = backtest(P, mem, cost_off=True)
    print(_row("corrected GROSS", gross)); print(_row("corrected NET", net))
    a, b, c = _slices(net)
    print(f"    continuous-slice Sharpe: 2017-18* {a:+.2f} | 2019-21 {b:+.2f} | 2022-26 {c:+.2f}")
    print(f"    {net['trades']} trades ({net['tpy']:.0f}/yr) | win {net['wr']*100:.0f}% | exits: {net['reasons']}")
    led = pd.DataFrame(ledger)
    if len(led):
        from scipy.stats import spearmanr
        ic, pv = spearmanr(led["rank"], led["R"])
        print(f"    RANK-IC (Spearman rank vs trade R): {ic:+.3f} (p={pv:.3f}) over {len(led)} fills  <- decides Level-2")
        led["yr"] = pd.to_datetime(led["entry_date"]).dt.year
        yr = led.groupby("yr")["R"].agg(["count", "mean"])
        print("    per-year fills/meanR: " + " | ".join(f"{y} {int(x['count'])}/{x['mean']:+.2f}" for y, x in yr.iterrows()))

    arr = net["ret"].to_numpy(float); n_tr = cumulative_n_trials()
    ci = block_bootstrap_metric(arr, sharpe_fn, block_size=DEFAULT_BLOCK, n_samples=5000, seed=12345)
    dsr = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))
    calmar = net["cagr"] / abs(net["dd"]) if net["dd"] else float("nan")
    print(f"\n  NET Sharpe {net['sharpe']:+.3f} | CAGR {net['cagr']*100:+.1f}% | MaxDD {net['dd']*100:.1f}% | Calmar {calmar:.2f}")
    print(f"  bootstrap 95% CI [{ci.lower:+.3f}, {ci.upper:+.3f}] | DSR @ n_trials={n_tr}: {dsr:.3f}")
    gates = {"DSR>0.95": bool(np.isfinite(dsr) and dsr > 0.95),
             "CI_low>0": bool(ci.lower > 0), "all_slices>0": bool(a > 0 and b > 0 and c > 0)}
    print("  gates:", {k: ("PASS" if v else "FAIL") for k, v in gates.items()})
    if all(gates.values()):
        verdict = "PROMOTE -> forward-wall watched sleeve"
    elif ci.lower > 0 and net["sharpe"] > 0:
        verdict = f"UNDERPOWERED (real-looking, not certified at n_trials={n_tr})"
    elif net["sharpe"] > 0:
        verdict = "UNDERPOWERED/WEAK (positive but CI straddles 0)"
    else:
        verdict = "KILL"
    print(f"  VERDICT: {verdict}")

    # same-cell reference: the live 0093-N50 (arbitrary fill), same engine family
    CRS.INDEX = ("nifty50", CRS.NIFTY50_CSV, "nifty50_close")
    ref = W89.backtest(CRS.prep_weekly_crs(ohlcv), mem)
    print(f"\n  reference 0093-N50 (arbitrary fill, same run): Sharpe {ref['sharpe']:+.3f} | CAGR {ref['cagr']*100:+.1f}% | DD {ref['dd']*100:.1f}%")
    print(f"  head-to-head: dSharpe {net['sharpe']-ref['sharpe']:+.3f} | dCAGR {(net['cagr']-ref['cagr'])*100:+.1f}pp "
          f"| dMaxDD {(net['dd']-ref['dd'])*100:+.1f}pp")

    net_err = backtest(prep_weekly_rank(ohlcv, drop_erratum=True), mem)
    print(_row("erratum-dropped NET", net_err))
    if "--ledger" in args and len(led):
        out = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
        led.drop(columns=["yr"], errors="ignore").to_csv(out, index=False)
        print(f"\n  ledger -> {out} ({len(led)} trades)")
    print("\n(run of record for pre-reg 0094; corrected universe; params frozen — no retuning.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
