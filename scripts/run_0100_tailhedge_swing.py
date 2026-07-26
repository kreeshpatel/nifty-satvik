"""Pre-reg 0100 - options-OI-triggered defined-risk tail hedge on the weekly-swing-0094 book.

The book leg is the FROZEN 0094 engine, run unchanged (its daily NAV curve is taken as-is), so the
engine invariant holds by construction. The hedge is a portfolio-level SIDECAR: a 1-month front-monthly
NIFTY put-spread armed when the OI-implied IV z-score > 2.0, priced from ACTUAL bhavcopy premiums
(data/_fo_oi_raw.parquet) and settled defined-risk at expiry against the spot path. Scored against the
pre-committed DD-overlay bar fixed in diagnostics/research/preregistry/0100-tailhedge-swing.md.

    python scripts/run_0100_tailhedge_swing.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.data.options_oi import OI_PIT_PATH, OI_RAW_PATH  # noqa: E402
from nq.validation.bootstrap import DEFAULT_BLOCK, block_bootstrap_metric  # noqa: E402
from nq.validation.dsr import cumulative_n_trials  # noqa: E402
from nq.validation.metrics import sharpe as sharpe_fn  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_sixstep import _row, _slices  # noqa: E402
from run_bhanushali_weekly_rank import backtest, prep_weekly_rank  # noqa: E402

# ── FIXED params (pre-reg 0100; not retunable) ──
Z_ARM = 2.0          # arm when atm_straddle_pct_z > this
OTM = 0.05           # short-put moneyness below spot (defines the risk & caps cost)
HEDGE_FRAC = 1.0     # protect full book notional: units = HEDGE_FRAC * NAV / spot
# 0094 run of record (models/bhanushali_weekly/config.json), NET, corrected universe
REC_SHARPE, REC_DD = 1.132, -0.424


def _spread_debit(pe_close, day, expiry, spot):
    """(debit, K1, K2) for the ATM/5%-OTM put-spread from ACTUAL PE closes, or (None,..) if unfillable.
    K1 = nearest listed strike <= spot; K2 = nearest listed strike <= spot*(1-OTM).
    """
    try:
        chain = pe_close.loc[(day, expiry)]           # Series: strike -> close
    except KeyError:
        return None, None, None
    if isinstance(chain, pd.Series) is False or chain.empty:
        return None, None, None
    ks = np.sort(chain.index.values.astype(float))
    le1 = ks[ks <= spot]
    le2 = ks[ks <= spot * (1 - OTM)]
    if not len(le1) or not len(le2):
        return None, None, None
    K1, K2 = float(le1.max()), float(le2.max())
    if K2 >= K1:
        return None, None, None
    d = float(chain.loc[K1]) - float(chain.loc[K2])
    return (d, K1, K2) if d > 0 else (None, K1, K2)


def build_hedge_pnl(book_curve, oi, raw):
    """Daily hedge cashflow Series (aligned to book_curve.index) + a per-cycle ledger. Pure: a function
    of the book NAV path, the PIT OI trigger, and actual bhavcopy premiums.
    """
    pe = raw[raw["otype"] == "PE"].copy()
    pe["date"] = pd.to_datetime(pe["date"]); pe["expiry"] = pd.to_datetime(pe["expiry"])
    pe_close = pe.groupby(["date", "expiry", "strike"])["close"].last().sort_index()
    z = oi["atm_straddle_pct_z"]; spot = oi["spot"]; fexp = pd.to_datetime(oi["front_expiry"])

    cf = pd.Series(0.0, index=book_curve.index)
    ledger, active = [], None
    for t in book_curve.index:
        # ── settle at/after expiry (first trading day >= the front-monthly expiry) ──
        if active is not None and t >= active["expiry"]:
            S_E = spot.asof(active["expiry"])
            payoff = float(np.clip(active["K1"] - S_E, 0, active["K1"] - active["K2"]))
            cf.loc[t] += payoff * active["units"]
            active.update(settle_date=t, S_E=float(S_E), payoff=payoff,
                          net_pts=payoff - active["debit"])
            ledger.append(active); active = None
        # ── arm when flat and the IV-stress signal is elevated ──
        if active is None and t in z.index and np.isfinite(z.loc[t]) and z.loc[t] > Z_ARM:
            E, S_t = fexp.get(t), spot.get(t)
            if pd.notna(E) and np.isfinite(S_t):
                debit, K1, K2 = _spread_debit(pe_close, t, pd.Timestamp(E), float(S_t))
                if debit is not None:
                    units = HEDGE_FRAC * float(book_curve.loc[t]) / float(S_t)
                    cf.loc[t] -= debit * units
                    active = dict(arm_date=t, expiry=pd.Timestamp(E), K1=K1, K2=K2, spot=float(S_t),
                                  debit=debit, units=units, z=float(z.loc[t]))
    return cf, pd.DataFrame(ledger)


def _curve_metrics(e, book_m):
    """Metrics dict for a NAV curve, compatible with _row/_slices (trade fields copied from the book)."""
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    m = dict(curve=e, ret=r, cagr=(e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1,
             sharpe=r.mean() / r.std() * np.sqrt(252) if r.std() else float("nan"),
             dd=(e / e.cummax() - 1).min(), mult=e.iloc[-1] / e.iloc[0])
    for k in ("trades", "tpy", "wr", "expR", "medhold", "p90hold"):
        m[k] = book_m[k]
    return m


def _calmar(m):
    return m["cagr"] / abs(m["dd"]) if m["dd"] else float("nan")


def _dsharpe_ci(base_ret, cand_ret, block=DEFAULT_BLOCK, n=5000, seed=12345):
    idx = base_ret.index.intersection(cand_ret.index)
    b = base_ret.reindex(idx).to_numpy(float); c = cand_ret.reindex(idx).to_numpy(float)
    N = len(b); rng = np.random.default_rng(seed); nblocks = int(np.ceil(N / block)); diffs = []
    for _ in range(n):
        starts = rng.integers(0, N - block + 1, size=nblocks)
        sel = np.concatenate([np.arange(s, s + block) for s in starts])[:N]
        diffs.append(sharpe_fn(c[sel]) - sharpe_fn(b[sel]))
    return tuple(float(x) for x in np.percentile(diffs, [2.5, 97.5]))


def main() -> int:
    print("=== pre-reg 0100: options-OI tail-hedge (put-spread sidecar) on the weekly-swing-0094 book ===")
    ohlcv = corrected_universe(); mem = load_membership()
    P = prep_weekly_rank(ohlcv)
    oi = pd.read_parquet(OI_PIT_PATH); oi.index = pd.to_datetime(oi.index)
    raw = pd.read_parquet(OI_RAW_PATH)
    print(f"corrected universe: {len(P)} names | OI series {oi.index.min().date()}..{oi.index.max().date()} "
          f"| trigger atm_straddle_pct_z>{Z_ARM}, {int(OTM*100)}%-wide put-spread, hedge_frac={HEDGE_FRAC}\n")

    base = backtest(P, mem)                                # book leg (hedge OFF)
    d_sh, d_dd = abs(base["sharpe"] - REC_SHARPE), abs(base["dd"] - REC_DD)
    ok = d_sh < 0.02 and d_dd < 0.01
    print(f"[invariant] book Sharpe {base['sharpe']:+.3f} (rec {REC_SHARPE:+.3f}) | DD {base['dd']*100:.1f}% "
          f"(rec {REC_DD*100:.1f}%) -> {'OK reproduces 0094' if ok else 'MISMATCH - stop'}\n")

    cf, led = build_hedge_pnl(base["curve"], oi, raw)
    hedged = base["curve"] + cf.cumsum()
    cand = _curve_metrics(hedged, base)

    print(_row("book only (hedge OFF)", base))
    print(_row("book + tail hedge    ", cand))
    ba, bb, bc = _slices(base); ca, cb, cc = _slices(cand)
    print(f"    slice Sharpe book : 2017-18* {ba:+.2f} | 2019-21 {bb:+.2f} | 2022-26 {bc:+.2f}")
    print(f"    slice Sharpe hedge: 2017-18* {ca:+.2f} | 2019-21 {cb:+.2f} | 2022-26 {cc:+.2f}")

    # ── hedge-cycle ledger ──
    if len(led):
        led["ret_x"] = led["net_pts"] / led["debit"]     # per-cycle return on premium (R multiple)
        won = (led["payoff"] > led["debit"]).sum()
        gross_debit = (led["debit"] * led["units"]).sum(); gross_pay = (led["payoff"] * led["units"]).sum()
        print(f"\n  hedge cycles: {len(led)} | premium-positive {won} ({100*won/len(led):.0f}%) | "
              f"total debit Rs{gross_debit:,.0f} -> payoff Rs{gross_pay:,.0f} (net Rs{gross_pay-gross_debit:,.0f})")
        print("  by year (cycles/net-R): " + " | ".join(
            f"{y} {int(g['ret_x'].count())}/{g['ret_x'].mean():+.1f}"
            for y, g in led.assign(yr=led["arm_date"].dt.year).groupby("yr")))

    d_sharpe = cand["sharpe"] - base["sharpe"]
    d_cagr = (cand["cagr"] - base["cagr"]) * 100
    d_dd_pp = (cand["dd"] - base["dd"]) * 100
    d_slice22 = cc - bc
    print(f"\n  dSharpe {d_sharpe:+.3f} | dCAGR {d_cagr:+.2f}pp | dMaxDD {d_dd_pp:+.2f}pp (positive=shallower) "
          f"| Calmar {_calmar(base):.2f}->{_calmar(cand):.2f}")
    print(f"  d(2022-26 slice Sharpe) {d_slice22:+.3f}")
    lo, hi = _dsharpe_ci(base["ret"], cand["ret"])
    n_indep = len(base["ret"]) / 63.0
    print(f"  dSharpe block-bootstrap 95% CI [{lo:+.3f}, {hi:+.3f}] | n_independent~{n_indep:.0f} "
          f"-> {'adequate' if n_indep >= 20 else 'UNDERPOWERED'}")

    bar = {
        "dMaxDD >= +3.0pp": d_dd_pp >= 3.0,
        "dSharpe >= -0.05": d_sharpe >= -0.05,
        "2022-26 slice not worse by >0.05": d_slice22 >= -0.05,
        "dCAGR >= -2.0pp": d_cagr >= -2.0,
    }
    print("\n  pre-committed bar (0100, DD-overlay class):")
    for k, v in bar.items():
        print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    verdict = ("SHADOW -> route the tail hedge to the forward wall" if all(bar.values())
               else "KILL / UNDERPOWERED - does not clear the 0100 bar")
    print(f"\n  n_trials (this run counted): {cumulative_n_trials()}")
    print(f"  VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
