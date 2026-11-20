"""Blind replica (spec-only) of the phase-0 top-decile gross-alpha null.

Written without reading nq/research/layer_gate.py, pipelines/diagnostics/phase0_calibrate.py
or diagnostics/research/explore/2026-11-20_*. Imports from nq/ only for data loading and the
NMS score inputs (named in the spec); the statistic under test is implemented here.

Ambiguity resolutions (see report):
  A1 close panel = union of session dates across symbols >= 2016-01-01, columns sorted.
  A2 vol_adjusted_return applied to each symbol's panel column as-is (NaNs where the symbol
     has no bar on a union session), not on its own dropna'd series.
  A3 random draw shape = (all weekly dates from 2016, all panel symbols, sorted), drawn once per
     seed then masked to coverage; dates/symbols outside coverage just discard their draws.
  A4 t+5 = 5 rows later on the union session index; r NaN if either close NaN.
  A5 membership tested on the signal date t only.
  A6 weekly date = last session in each W-FRI period.
  A7 pct rank default method='average'; top decile strictly > 0.9.
  A8 weeks with empty top decile dropped; beta via np.cov ddof=1 / np.var ddof=1.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from nq.data.ohlcv import load_ohlcv_cache, clean_ohlcv_dict  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.signals import vol_adjusted_return, nse_momentum_score  # noqa: E402

CUTOFF = pd.Timestamp("2024-06-30")
H = 5
NW_LAG = 8
OUT = Path(__file__).resolve().parent / "null_replica.json"


def load_close():
    d = dict(pd.read_pickle(ROOT / "data/ohlcv_backfill.pkl"))
    d.update(load_ohlcv_cache())
    d = clean_ohlcv_dict(d)
    cols = {}
    for k in sorted(d):
        s = d[k]["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s = s.copy()
        s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
        s = s[~s.index.duplicated(keep="last")]
        cols[k] = s.astype(float)
    close = pd.DataFrame(cols).sort_index()
    close = close[close.index >= "2016-01-01"]
    return close


def member_mask(dates, symbols, mem):
    M = np.zeros((len(dates), len(symbols)), dtype=bool)
    dd = np.array([d.date() for d in dates])
    for j, s in enumerate(symbols):
        for (a, b) in mem.get(s.upper(), []):
            M[:, j] |= (dd >= a) & (dd <= b)
    return M


def nw_t(e, L=NW_LAG):
    n = len(e)
    ed = e - e.mean()
    V = np.sum(ed * ed) / n
    for k in range(1, L + 1):
        V += 2 * (1 - k / (L + 1)) * np.sum(ed[k:] * ed[:-k]) / n
    return e.mean() / np.sqrt(V / n)


def stat(score, R, wk_idx):
    """score, R: (n_weeks_all, n_sym) arrays; wk_idx: rows to use."""
    rp, rm = [], []
    for i in wk_idx:
        sc, r = score[i], R[i]
        ok = ~np.isnan(sc) & ~np.isnan(r)
        if ok.sum() == 0:
            continue
        pr = pd.Series(sc[ok]).rank(pct=True).to_numpy()
        top = pr > 0.9
        if top.sum() == 0:
            continue
        rp.append(r[ok][top].mean())
        rm.append(r[ok].mean())
    rp, rm = np.array(rp), np.array(rm)
    beta = np.cov(rp, rm, ddof=1)[0, 1] / np.var(rm, ddof=1)
    e = rp - beta * rm
    return dict(alpha_ann=52 * e.mean(), t=nw_t(e), beta=beta, n_weeks=len(e))


def main():
    close = load_close()
    sessions, symbols = close.index, list(close.columns)
    C = close.to_numpy()
    mem = load_membership()

    # weekly signal dates: last session of each W-FRI week
    wk = pd.Series(sessions, index=sessions).groupby(sessions.to_period("W-FRI")).max()
    wdates = pd.DatetimeIndex(wk.values)
    wpos = sessions.get_indexer(wdates)

    # forward 5-session return
    fwd = np.full_like(C, np.nan)
    fwd[:-H] = C[H:] / C[:-H] - 1
    R = fwd[wpos]
    exit_ok = np.array([p + H < len(sessions) and sessions[p + H] <= CUTOFF for p in wpos])

    MEM = member_mask(wdates, symbols, mem)
    R = np.where(MEM, R, np.nan)

    # NMS
    mr12 = np.column_stack([vol_adjusted_return(C[:, j], 252) for j in range(len(symbols))])[wpos]
    mr6 = np.column_stack([vol_adjusted_return(C[:, j], 126) for j in range(len(symbols))])[wpos]
    ii, jj = np.nonzero(MEM & ~np.isnan(mr12) & ~np.isnan(mr6))
    long = pd.DataFrame({"date": wdates[ii], "symbol": np.array(symbols)[jj],
                         "mr12": mr12[ii, jj], "mr6": mr6[ii, jj], "_i": ii, "_j": jj})
    long = nse_momentum_score(long)
    NMS = np.full(C[wpos].shape, np.nan)
    NMS[long["_i"].to_numpy(), long["_j"].to_numpy()] = long["nms"].to_numpy()
    COV = ~np.isnan(NMS)

    use = np.nonzero(exit_ok & COV.any(axis=1))[0]
    # weeks actually contributing (score & r both present)
    used = [i for i in use if (COV[i] & ~np.isnan(R[i])).any()]

    real = stat(NMS, R, used)
    ts = []
    for s in range(50):
        z = np.random.default_rng(s).standard_normal(NMS.shape)
        z = np.where(COV, z, np.nan)
        ts.append(stat(z, R, used)["t"])
    ts = np.array(ts)
    out = dict(
        n_weekly_dates=len(used),
        first_signal=str(wdates[used[0]].date()), last_signal=str(wdates[used[-1]].date()),
        last_exit=str(sessions[wpos[used[-1]] + H].date()),
        n_symbols=len(symbols), coverage_cells_used=int(sum(COV[i].sum() for i in used)),
        null=dict(n_seeds=50, pass_two_sided=float(np.mean(np.abs(ts) >= 2.6)),
                  pass_one_sided=float(np.mean(ts >= 2.6)),
                  mean_t=float(ts.mean()), sd_t=float(ts.std(ddof=1)),
                  max_abs_t=float(np.abs(ts).max()), t_by_seed=[round(float(x), 4) for x in ts]),
        real_nms={k: float(v) for k, v in real.items()},
    )
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
