"""Pre-reg 0096 - sector-relative CRS denominator on the weekly-swing-0094 book.

Baseline = Nifty-50 denominator (the 0094 run of record). Overlay = RS vs the stock's OWN sector
equal-weight index (config.SECTOR_MAP); 'Others'/thin sectors fall back to Nifty-50. Verifies the
engine invariant, then scores against the signal/ranker bar fixed in
diagnostics/research/preregistry/0096-sectorrel-crs-swing.md.

    python scripts/run_0096_sectorrel_swing.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import get_sector  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_0095_voltarget_swing import _calmar, _dsharpe_ci  # noqa: E402  (reuse scorecard helpers)
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

REC_SHARPE, REC_DD = 1.132, -0.424
MIN_SECTOR = 8   # sectors with fewer members get no index (those tickers fall back to N50)


def _close(df):
    return (df["Close"] if "Close" in df.columns else df["close"]).astype(float)


def build_sector_indices(ohlcv: dict) -> dict:
    """Equal-weight daily-return price index per sector (config.SECTOR_MAP), built from the corrected
    universe. Per day = cross-sectional mean of member daily returns (skipna: unlisted/delisted names
    drop out), cumprod. 'Others' and sub-MIN_SECTOR sectors are skipped -> those tickers fall back to N50."""
    bysec: dict[str, list[str]] = defaultdict(list)
    for t in ohlcv:
        bysec[get_sector(t)].append(t)
    out = {}
    for sec, tks in bysec.items():
        if sec == "Others" or len(tks) < MIN_SECTOR:
            continue
        M = pd.DataFrame({t: _close(ohlcv[t]) for t in tks}).sort_index()
        ew = M.pct_change().mean(axis=1)                 # cross-sectional mean daily return (skipna)
        out[sec] = (1.0 + ew.fillna(0.0)).cumprod()
        out[sec].name = f"sector_{sec}"
    return out


def main() -> int:
    print("=== pre-reg 0096: sector-relative CRS denominator on the weekly-swing-0094 book ===")
    ohlcv = corrected_universe(); mem = load_membership()
    sect = build_sector_indices(ohlcv)
    covered = sum(1 for t in ohlcv if get_sector(t) in sect)
    print(f"corrected universe: {len(ohlcv)} names | {len(sect)} sector indices "
          f"(>= {MIN_SECTOR} members) | {covered} names sector-relative, {len(ohlcv)-covered} -> N50 fallback\n")

    provider = lambda t: sect.get(get_sector(t))          # noqa: E731 - None -> N50 inside prep

    base = backtest(prep_weekly_rank(ohlcv), mem)                                  # N50 denominator
    cand = backtest(prep_weekly_rank(ohlcv, index_provider=provider), mem)         # sector-relative

    d_sh, d_dd = abs(base["sharpe"] - REC_SHARPE), abs(base["dd"] - REC_DD)
    ok = d_sh < 0.02 and d_dd < 0.01
    print(f"[invariant] baseline Sharpe {base['sharpe']:+.3f} (rec {REC_SHARPE:+.3f}) | DD {base['dd']*100:.1f}% "
          f"-> {'OK reproduces 0094' if ok else 'MISMATCH'}\n")

    print(_row("baseline  (N50 CRS)     ", base))
    print(_row("overlay   (sector-rel)  ", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe base: 2017-18* {ba:+.2f} | 2019-21 {bb:+.2f} | 2022-26 {bc:+.2f}")
    print(f"    slice Sharpe over: 2017-18* {ca:+.2f} | 2019-21 {cb:+.2f} | 2022-26 {cc:+.2f}")

    d_sharpe = cand["sharpe"] - base["sharpe"]
    d_cagr = (cand["cagr"] - base["cagr"]) * 100
    d_dd_pp = (cand["dd"] - base["dd"]) * 100     # dd are negative; positive = overlay DD shallower (improved)
    lo, hi = _dsharpe_ci(base["ret"], cand["ret"])
    n_indep = len(base["ret"]) / 63.0
    print(f"\n  dSharpe {d_sharpe:+.3f} | dCAGR {d_cagr:+.2f}pp | dMaxDD {d_dd_pp:+.2f}pp (positive=shallower) "
          f"| Calmar {_calmar(base):.2f}->{_calmar(cand):.2f}")
    print(f"  trades {base['trades']}->{cand['trades']} | win {base['wr']*100:.0f}%->{cand['wr']*100:.0f}% "
          f"| dSharpe CI [{lo:+.3f}, {hi:+.3f}] | n_independent~{n_indep:.0f} "
          f"({'adequate' if n_indep>=20 else 'UNDERPOWERED'})")

    bar = {
        "dSharpe >= +0.10": d_sharpe >= 0.10,
        "2022-26 slice dCAGR >= 0 (proxy: slice Sharpe not worse)": (cc - bc) >= 0,
        "MaxDD not worse by >2pp": d_dd_pp >= -2.0,
        "dSharpe CI-low > 0": lo > 0,
    }
    print("\n  pre-committed bar (0096):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    verdict = ("SHADOW -> alt-denominator candidate to the forward wall" if all(bar.values())
               else "KILL / UNDERPOWERED - does not clear the 0096 bar")
    print(f"\n  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
