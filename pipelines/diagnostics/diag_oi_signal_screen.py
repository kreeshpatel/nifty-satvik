"""MEASUREMENT ONLY (0 trials — no PROMOTE/KILL decision): does any options-OI signal LEAD stress?

Finding 0100 killed a COINCIDENT IV-spike hedge (it lags — buys protection after the spike). Before
spending another trial we characterize, purely descriptively, the FORWARD relationship of each OI signal
to (a) Nifty and (b) the swing BOOK's future returns and future drawdowns, at several horizons. A useful
LEADING stress trigger would show: high signal_t -> deeply negative forward drawdown (Spearman < 0) AND
its top-decile days precede much worse drawdowns than average. Judged on DRAWDOWN/stress, never as a
return ranker (methodology-synthesis: PCR/OI is risk-context, not alpha).

    python scripts/diag_oi_signal_screen.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.options_oi import OI_PIT_PATH  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

HORIZONS = [5, 10, 21, 42, 63]


def _fwd_ret(p: pd.Series, h: int) -> pd.Series:
    return p.shift(-h) / p - 1.0


def _fwd_maxdd(p: pd.Series, h: int) -> pd.Series:
    """Worst drawdown over the NEXT h sessions (<=0; more negative = deeper stress ahead)."""
    a = p.to_numpy(float); n = len(a); out = np.full(n, np.nan)
    for i in range(n):
        j = min(i + h, n - 1)
        if j <= i:
            continue
        seg = a[i:j + 1]
        out[i] = (seg / np.maximum.accumulate(seg) - 1.0).min()
    return pd.Series(out, index=p.index)


def _ic(sig: pd.Series, tgt: pd.Series) -> float:
    d = pd.concat([sig, tgt], axis=1).dropna()
    if len(d) < 100:
        return np.nan
    return spearmanr(d.iloc[:, 0], d.iloc[:, 1]).statistic


def main() -> int:
    print("=== MEASUREMENT: do options-OI signals LEAD stress? (0 trials) ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    book = backtest(P, mem)["curve"]                       # daily book NAV
    oi = pd.read_parquet(OI_PIT_PATH); oi.index = pd.to_datetime(oi.index)

    idx = book.index.intersection(oi.index)
    book = book.reindex(idx); nifty = oi["spot"].reindex(idx)

    # ── candidate signals (levels + trailing transforms; all trailing-only / PIT) ──
    sig = pd.DataFrame(index=idx)
    sig["pcr_oi"] = oi["pcr_oi"].reindex(idx)
    sig["pcr_oi_z"] = oi["pcr_oi_z"].reindex(idx)
    sig["pcr_chg_oi"] = oi["pcr_chg_oi"].reindex(idx)
    sig["pcr_rise_5"] = oi["pcr_oi"].reindex(idx).diff(5)          # PCR accumulating (put build)
    sig["iv"] = oi["atm_straddle_pct"].reindex(idx)
    sig["iv_z"] = oi["atm_straddle_pct_z"].reindex(idx)           # the 0100 (coincident) signal
    sig["iv_rise_5"] = oi["atm_straddle_pct"].reindex(idx).pct_change(5)  # vol momentum
    sig["maxpain_gap"] = oi["max_pain_gap"].reindex(idx)          # spot above/below max-pain
    sig["tot_oi_rise_5"] = oi["tot_oi"].reindex(idx).pct_change(5)  # OI build rate
    # ── knowledge-import signals (2026-07-26 digest): S2 skew (best lead), S1 term slope, S3 VRP veto ──
    sig["put_skew"] = oi["put_skew"].reindex(idx)                 # S2 OTM-put richness (crash bid)
    sig["put_skew_z"] = oi["put_skew_z"].reindex(idx)
    sig["put_skew_rise5"] = oi["put_skew"].reindex(idx).diff(5)   # skew STEEPENING (the leading form)
    sig["iv_term_slope"] = oi["iv_term_slope"].reindex(idx)       # S1 front-next (>0 backwardation=stress)
    sig["iv_term_z"] = oi["iv_term_slope_z"].reindex(idx)
    sig["vrp_z"] = oi["vrp_z"].reindex(idx)                       # S3 protection richness (veto, relative)

    # ── forward targets ──
    tgt = {}
    for h in HORIZONS:
        tgt[(f"nifty_ret", h)] = _fwd_ret(nifty, h)
        tgt[(f"nifty_dd", h)] = _fwd_maxdd(nifty, h)
        tgt[(f"book_ret", h)] = _fwd_ret(book, h)
        tgt[(f"book_dd", h)] = _fwd_maxdd(book, h)

    # ── IC table: forward drawdown (the stress target) ──
    print("\nForward-DRAWDOWN Spearman IC  (want STRONG NEGATIVE: high signal -> deeper drawdown ahead)")
    print(f"  {'signal':<14} " + " ".join(f"nifDD{h:>2} bkDD{h:>2}" for h in HORIZONS))
    dd_scores = {}
    for s in sig.columns:
        cells = []
        best = 0.0
        for h in HORIZONS:
            icn = _ic(sig[s], tgt[("nifty_dd", h)]); icb = _ic(sig[s], tgt[("book_dd", h)])
            cells.append(f"{icn:+.2f} {icb:+.2f}")
            if np.isfinite(icb):
                best = min(best, icb)
        dd_scores[s] = best
        print(f"  {s:<14} " + "  ".join(cells))

    print("\nForward-RETURN Spearman IC  (want NEGATIVE: high signal -> weak forward return = bearish lead)")
    print(f"  {'signal':<14} " + " ".join(f"nifR{h:>2} bkR{h:>2}" for h in HORIZONS))
    for s in sig.columns:
        cells = [f"{_ic(sig[s], tgt[('nifty_ret', h)]):+.2f} {_ic(sig[s], tgt[('book_ret', h)]):+.2f}"
                 for h in HORIZONS]
        print(f"  {s:<14} " + "  ".join(cells))

    # ── event study: top-decile signal days -> forward 21d book drawdown vs unconditional ──
    print("\nEvent study: mean forward-21d BOOK drawdown | top-decile signal days vs all days")
    base_dd = tgt[("book_dd", 21)]
    uncond = base_dd.mean()
    print(f"  unconditional mean fwd-21d book DD: {uncond*100:+.2f}%")
    rows = []
    for s in sig.columns:
        d = pd.concat([sig[s], base_dd], axis=1).dropna()
        if len(d) < 200:
            continue
        thr = d.iloc[:, 0].quantile(0.90)
        cond = d[d.iloc[:, 0] >= thr].iloc[:, 1].mean()
        rows.append((s, cond, cond - uncond))
    rows.sort(key=lambda r: r[1])   # most negative (worst forward DD) first = best leading stress signal
    print(f"  {'signal':<14} {'top-decile fwd-DD':>18} {'vs uncond':>12}")
    for s, cond, delta in rows:
        flag = "  <- leads stress" if delta < -0.01 else ("  (coincident/none)" if delta > -0.003 else "")
        print(f"  {s:<14} {cond*100:>16.2f}% {delta*100:>+11.2f}pp{flag}")

    print("\nReadout: a LEADING trigger = strong negative forward-DD IC AND top-decile fwd-DD materially "
          "worse than unconditional. If the best is iv_z (the 0100 coincident signal) with no leader "
          "beating it, the OI-hedge-timing avenue is exhausted -> route to a CONTINUOUS/sleeve hedge, "
          "not another timed trigger.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
