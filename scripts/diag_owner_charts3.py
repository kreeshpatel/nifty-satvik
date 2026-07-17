"""Per-week rule forensic for the owner's 2026-07-16 chart review (round 3).

For each flagged ticker, dump every weekly bar around the trade with EACH of the four signal
components evaluated separately, so we can say exactly WHY a week did or did not fire — instead of
inferring it. Measurement only; no trial.

    python scripts/diag_owner_charts3.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import run_bhanushali_weekly_crs as CRS
import run_bhanushali_weekly_rank as R94
from run_bhanushali_path1 import corrected_universe
from run_bhanushali_sixstep import prep

CASES = [("MINDACORP", "2024-11-15", "2025-02-20", "owner: setup ready 30-Dec + 6-Jan -> enter 13-Jan"),
         ("ASAHIINDIA", "2024-06-15", "2024-08-20", "owner: entry-week open should exceed setup-week open"),
         ("MAXHEALTH", "2025-01-15", "2025-04-05", "owner: could have entered at the bottom, entered at the top"),
         ("AEGISLOG", "2024-11-15", "2025-02-05", "owner: hit the candle high — didn't it fulfil R?"),
         ("COHANCE", "2025-01-10", "2025-03-10", "owner: entry candle opened below the green candle")]


def main():
    ohlcv = corrected_universe()
    n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
    P = prep(ohlcv)
    Pr = R94.prep_weekly_rank(ohlcv)                      # for the actual fired windows

    for tk, d0, d1, note in CASES:
        s = P[tk]
        dates = pd.DatetimeIndex(s["dates"])
        c, h, l, o = (np.asarray(s[k], float) for k in ("c", "h", "l", "o"))
        iso = dates.isocalendar(); keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
        weeks, cur, prev = [], [], None
        for i, k in enumerate(keys):
            if prev is not None and k != prev:
                weeks.append(cur); cur = []
            cur.append(i); prev = k
        if cur:
            weeks.append(cur)
        wo = np.array([o[d[0]] for d in weeks]); wh = np.array([h[d].max() for d in weeks])
        wl = np.array([l[d].min() for d in weeks]); wc = np.array([c[d[-1]] for d in weeks])
        wstart = [dates[d[0]] for d in weeks]
        wsma = pd.Series(wc).rolling(44).mean().to_numpy()
        slope = np.full(len(wsma), np.nan)
        slope[13:] = wsma[13:] / wsma[:-13] - 1.0
        rng = wh - wl
        qgreen = (wc > wo) & (rng > 0) & ((wc - wl) >= 0.5 * rng)
        touch = (wl <= wsma * 1.07) & (wc > wsma)
        ia = n50.reindex(dates, method="ffill").to_numpy(float)
        iw = np.array([ia[d[-1]] for d in weeks])
        rs = np.where(iw > 0, wc / iw, np.nan)
        rs_sma = pd.Series(rs).rolling(40).mean().to_numpy()
        rs_term = np.nan_to_num(rs > rs_sma, nan=False)
        wsig = np.nan_to_num((slope >= 0.03) & qgreen & touch & (wc > wsma) & rs_term, nan=False)

        fired = {pd.Timestamp(dates[e0 - 1]).normalize() for e0 in Pr[tk]["entry_win"] if e0 >= 1}

        print(f"\n{'='*118}\n{tk} — {note}\n{'='*118}")
        print(f"{'week':11s} {'open':>8s} {'high':>8s} {'low':>8s} {'close':>8s} {'SMA44':>8s} "
              f"{'ext%':>6s} {'slope':>6s} {'grn':>4s} {'tch':>4s} {'>sma':>5s} {'RS>':>4s} {'FIRE':>5s}")
        for k in range(len(weeks)):
            wd = pd.Timestamp(wstart[k]).normalize()
            if not (pd.Timestamp(d0) <= wd <= pd.Timestamp(d1)):
                continue
            sm = wsma[k]
            ext = (wc[k] / sm - 1) * 100 if sm == sm else np.nan
            f = "FIRE" if wsig[k] else ""
            mark = " <-- entry week" if any(abs((wd - x).days) < 4 for x in
                                           [pd.Timestamp(dates[weeks[k][-1]]).normalize()]) and wsig[k] else ""
            print(f"{wd.date()!s:11s} {wo[k]:8.2f} {wh[k]:8.2f} {wl[k]:8.2f} {wc[k]:8.2f} "
                  f"{sm:8.2f} {ext:6.1f} {slope[k]*100 if slope[k]==slope[k] else float('nan'):6.1f} "
                  f"{'Y' if qgreen[k] else '.':>4s} {'Y' if touch[k] else '.':>4s} "
                  f"{'Y' if wc[k]>sm else '.':>5s} {'Y' if rs_term[k] else '.':>4s} {f:>5s}{mark}")


if __name__ == "__main__":
    main()
