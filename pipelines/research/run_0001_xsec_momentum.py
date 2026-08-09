"""Pre-reg 0001 — cross-sectional momentum on Indian midcaps, end to end.

Runs exactly the configuration frozen in ``research/0001-xsec-momentum/prereg.md``. Nothing in this
file may deviate from that document; if a parameter here disagrees with the pre-registration, the
pre-registration wins and this file is the bug.

    python pipelines/research/run_0001_xsec_momentum.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from nq.engine.portfolio import elapsed_years  # noqa: E402
from nq.engine.rebalance_book import RebalanceConfig, rebalance_dates, simulate_rebalance_book  # noqa: E402
from nq.runner.research import adjudicate  # noqa: E402
from nq.signals import SKIP_DAYS, YEAR_DAYS, nse_momentum_score, vol_adjusted_return  # noqa: E402
from nq.universe import build_universe, screen_report  # noqa: E402
from nq.validation.montecarlo import resample_equity_curve, suggest_block_days  # noqa: E402
from nq.validation.pbo import cscv_pbo  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
BAND = "MID"
SEED = 20260807
BOOK = dict(top_n=30, buffer_mult=1.5, max_position_pct=5.0, cadence="M")
OUT = ROOT / "research" / "0001-xsec-momentum"


def add_signals(u: pd.DataFrame) -> pd.DataFrame:
    """MR12 / MR6 per name, then the NSE score cross-sectionally among ELIGIBLE names only."""
    parts = []
    for tkr, g in u.groupby("ticker", sort=True):
        g = g.sort_values("date").copy()
        c = g["close"].to_numpy(float)
        g["mr12"] = vol_adjusted_return(c, YEAR_DAYS - SKIP_DAYS, skip=SKIP_DAYS)
        g["mr6"] = vol_adjusted_return(c, 126 - SKIP_DAYS, skip=SKIP_DAYS)
        parts.append(g)
    p = pd.concat(parts, ignore_index=True)
    p.loc[~p["eligible"], ["mr12", "mr6"]] = np.nan          # score only what we could trade
    p = nse_momentum_score(p)
    p["rank"] = np.where(p["eligible"] & p["nms"].notna(), p["nms"], np.nan)
    return p


def random_control(p: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Same universe, same cadence, same slots — random ranks that PERSIST within a rebalance period.

    The first version drew a fresh random number for every (ticker, date), which re-shuffled the
    ranking daily. That control could never benefit from the hold buffer, so it churned its whole
    book at every rebalance and paid roughly double the candidate's turnover cost. Comparing against
    it measures "persistent selection vs churning selection", not "ranking vs no ranking" — and the
    turnover gate then passes for the wrong reason.

    Drawing one random score per (ticker, month) gives the control the same persistence structure as
    the candidate, so the only difference left is whether the RANKING carries information.
    """
    rng = np.random.default_rng(seed)
    q = p.copy()
    period = pd.PeriodIndex(q["date"], freq="M")
    keys = pd.Index(q["ticker"].astype(str) + "|" + period.astype(str))
    uniq = keys.unique()
    scores = pd.Series(rng.random(len(uniq)), index=uniq)
    # rankable exactly where the candidate is rankable, so the two arms face the same opportunity set
    q["rank"] = np.where(p["rank"].notna(), keys.map(scores), np.nan)
    return q


def passive_equal_weight(p: pd.DataFrame) -> dict:
    """Own the whole rankable band, equal weight, daily rebalance — the economic benchmark."""
    e = p[p["rank"].notna()] if "rank" in p.columns else p[p["eligible"]]
    r = e.pivot_table(index="date", columns="ticker", values="close").sort_index().pct_change()
    daily = r.mean(axis=1).fillna(0.0)
    eq = (1 + daily).cumprod()
    # Calendar time, the SAME denominator the engine uses (nq.engine.portfolio.elapsed_years).
    # This computed `len(eq) / 252.0` independently of the engine, so when the engine moved to
    # calendar annualisation on 2026-08-07 the benchmark silently did not — leaving the pre-reg's
    # "must clear equal-weight passive ownership" gate comparing two different conventions, with the
    # benchmark flattered by ~0.4pp relative to the candidate.
    yrs = elapsed_years([{"date": str(d)[:10], "equity": float(v)} for d, v in eq.items()], len(eq))
    return {"cagr_pct": round((eq.iloc[-1] ** (1 / yrs) - 1) * 100, 3),
            "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 3),
            "max_drawdown_pct": round((eq / eq.cummax() - 1).min() * 100, 2),
            "note": "equal-weight, daily rebalance -> carries a rebalancing premium"}


def run(p: pd.DataFrame, **over) -> dict:
    cfg = RebalanceConfig(**{**BOOK, **over})
    return simulate_rebalance_book(p, cfg=cfg, start=START, end=END, initial_capital=1_000_000.0)


def sub_slice(curve: list[dict], lo: str, hi: str) -> float | None:
    """CAGR over a slice of ONE continuous curve — never a fresh-capital re-run."""
    pts = [(pd.Timestamp(e["date"]), float(e["equity"])) for e in curve]
    s = [(d, v) for d, v in pts if pd.Timestamp(lo) <= d <= pd.Timestamp(hi)]
    if len(s) < 2 or s[0][1] <= 0:
        return None
    yrs = (s[-1][0] - s[0][0]).days / 365.25
    return round(((s[-1][1] / s[0][1]) ** (1 / yrs) - 1) * 100, 2) if yrs > 0 else None


def main() -> int:
    print("=== PRE-REG 0001 — cross-sectional momentum, Indian midcaps ===")
    print(f"    frozen in research/0001-xsec-momentum/prereg.md · n_trials incremented to 1\n")

    ohlcv, mem = corrected_universe(), load_membership()
    u = build_universe(ohlcv, mem, start=START, end=END)
    rep = screen_report(u)
    print(f"  universe: {rep['rows']:,} rows · {rep['eligible_rows']:,} eligible "
          f"· {rep['mean_eligible_per_day']} names/day (min {rep['min_eligible_per_day']})")
    print(f"  bands/day: {rep['mean_per_band']}")
    print(f"  screens removed — liq {rep['liq_ok_fail']:,} · hist {rep['hist_ok_fail']:,} "
          f"· price {rep['price_ok_fail']:,} · circuit {rep['circuit_ok_fail']:,}")

    p = add_signals(u)

    # Restrict the RANK to the band, never the ROWS.
    #
    # Filtering rows to `eligible` deletes a name's prices the moment it leaves the band — and band
    # membership churns constantly at the rank-100/101 boundary. The engine then cannot price a sale,
    # holds the position blind, and force-closes it 10 sessions later at a stale mark: 380 of 2807
    # trades (13.5%) exited that way. Keeping every price row and NaN-ing the rank means an
    # ineligible name simply drops out of the target and is sold at the next open at a real price,
    # which is what actually happens when a stock leaves an index.
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    band = p[keep].copy()
    band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                            band["nms"], np.nan)
    rankable = band[band["rank"].notna()]
    print(f"  {BAND} band: {band['ticker'].nunique()} names ever · "
          f"{rankable.groupby('date')['ticker'].nunique().mean():.0f} rankable/day "
          f"({band.groupby('date')['ticker'].nunique().mean():.0f} priced/day)\n")

    cand = run(band)
    ctrl = run(random_control(band))
    passive = passive_equal_weight(band)

    print("=== ARMS (one continuous run, 2017-2026) ===")
    for tag, bt in (("CANDIDATE", cand), ("RANDOM CTRL", ctrl)):
        m = bt["metrics"]
        print(f"  {tag:<12} CAGR {m['cagr_pct']:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
              f"MaxDD {m['max_drawdown_pct']:>7.2f}%  Calmar {m['calmar']:>5.2f}  "
              f"trades {m['n_trades']:>5}  turnover {m['turnover_per_year']:>5.1f}")
    print(f"  {'PASSIVE EW':<12} CAGR {passive['cagr_pct']:>7.2f}%  "
          f"Sharpe {passive['sharpe']:>6.3f}  MaxDD {passive['max_drawdown_pct']:>7.2f}%")

    print("\n=== PRIMARY GATE (adjudicate vs the random control) ===")
    v = adjudicate(ctrl, cand, end=END, initial_capital=1_000_000.0)
    for k, g in v["gates"].items():
        print(f"  {'PASS' if g else 'FAIL':<5} {k}")
    print(f"\n  dSharpe {v['dSharpe']:+.3f} CI {v['dSharpe_ci']} · n_eff {v['n_eff_windows']}")
    print(f"  DSR {v['dsr_candidate']:.4f} @ n_trials {v['n_trials']} (post-reset — the GATE)")
    print(f"  DSR {v['dsr_candidate_lifetime']:.4f} @ n_trials {v['n_trials_lifetime']} "
          f"(lifetime — every trial ever run on this history)")
    print("  The lifetime figure is the statistically defensible one: the DSR exists to deflate by")
    print("  the search that actually happened, and the pre-reset trials were run on this same data.")
    print(f"  VERDICT: {v['verdict']}")

    # Until 2026-08-10 this block varied `max_position_pct` (5.0 -> 3.33) and merely LABELLED the
    # arms 1.0x and 1.5x: the multiplier was never passed to the engine. `max_position_pct` reaches
    # exactly one line -- the target-weight cap -- and no cost path, and at 3.33% it binds only when
    # the book holds exactly 30 names (the average is 31.25). Both arms were the same run, which is
    # why both printed 21.73%. The prereg makes surviving 1.5x costs a HARD deployability condition,
    # so that gate had never been evaluated. `cost_mult` now scales the actual friction terms.
    print("\n=== COST SENSITIVITY (deployable only if it survives 1.5x) ===")
    print("  cost_mult scales brokerage+STT AND slippage (tier rate + the >0.5%-ADV impact adder).")
    cost_rows = []
    for mult in (1.0, 1.5):
        m = run(band, cost_mult=mult)["metrics"]
        cost_rows.append({"cost_mult": mult, "cagr_pct": m["cagr_pct"], "sharpe": m["sharpe"],
                          "max_drawdown_pct": m["max_drawdown_pct"], "n_trades": m["n_trades"]})
        print(f"    {mult:.1f}x  CAGR {m['cagr_pct']:>7.2f}%  Sharpe {m['sharpe']:>6.3f}  "
              f"MaxDD {m['max_drawdown_pct']:>7.2f}%  trades {m['n_trades']:>5}")

    # Self-check: the 1.0x arm must reproduce the candidate exactly. If it does not, the multiplier
    # is reaching something other than cost and the stress below means nothing.
    inert = cost_rows[0]["cagr_pct"] == cand["metrics"]["cagr_pct"]
    if not inert:
        print("  ** cost_mult=1.0 did NOT reproduce the candidate — the hook is not cost-only **")

    drag = cost_rows[0]["cagr_pct"] - cost_rows[1]["cagr_pct"]
    survives = cost_rows[1]["cagr_pct"] > passive["cagr_pct"]
    print(f"\n  1.5x costs remove {drag:.2f}pp of CAGR "
          f"({cost_rows[0]['cagr_pct']:.2f}% -> {cost_rows[1]['cagr_pct']:.2f}%).")
    print(f"  {'PASS' if survives else 'FAIL'}  still clears passive EW "
          f"({passive['cagr_pct']:.2f}%) under stress — the prereg's own ownership gate, "
          f"re-evaluated at 1.5x rather than a new threshold.")
    cost_sensitivity = {"arms": cost_rows, "cagr_drag_pp": round(drag, 3),
                        "passive_cagr_pct": passive["cagr_pct"],
                        "clears_passive_at_1_5x": survives,
                        "one_x_reproduces_candidate": inert,
                        "note": ("cost_mult scales LEG_COST and the full _slip charge. Before "
                                 "2026-08-10 this gate varied max_position_pct instead and was "
                                 "therefore never evaluated; both arms were the same run.")}

    print("\n=== PER-REGIME (continuous slices of the one curve) ===")
    for lo, hi, tag in (("2018-01-01", "2018-12-31", "2018 midcap crash"),
                        ("2020-01-01", "2020-12-31", "2020 COVID"),
                        ("2022-01-01", "2022-12-31", "2022 drawdown"),
                        ("2024-01-01", "2026-06-30", "2024-26 correction")):
        c = sub_slice(cand["equity_curve"], lo, hi)
        r = sub_slice(ctrl["equity_curve"], lo, hi)
        print(f"    {tag:<22} candidate {c if c is not None else 'n/a':>8}%   "
              f"control {r if r is not None else 'n/a':>8}%")

    print("\n=== PBO across the parameter neighbourhood (adopts NOTHING) ===")
    grid, cols = [], []
    for n in (20, 30, 50):
        for b in (1.0, 1.5, 2.0):
            bt = run(band, top_n=n, buffer_mult=b)
            eq = pd.Series({e["date"]: e["equity"] for e in bt["equity_curve"]})
            grid.append(eq.pct_change().fillna(0.0).to_numpy())
            cols.append(f"n{n}_b{b}")
    M = np.column_stack(grid)
    pbo = cscv_pbo(M, n_blocks=10)
    print(f"  configs {pbo.n_configs} · splits {pbo.n_splits} · PBO {pbo.pbo:.3f} "
          f"({'informative' if pbo.selection_is_informative else 'NOT informative'})")
    print(f"  median logit {pbo.median_logit:+.3f}")

    # What is the book actually DOING? A turnover number does not distinguish "changed its mind
    # about a name" from "nudged an equal weight back into line", and the two have very different
    # implications for whether the selection logic is carrying the result.
    mix = Counter(t["reason"] for t in cand["trades"])
    print("\n=== TRADE MIX (turnover is not all selection) ===")
    for reason, n in mix.most_common():
        print(f"    {reason:<18} {n:>5}  ({n / len(cand['trades']) * 100:.1f}%)")

    print("\n=== MONTE CARLO — equity-curve block bootstrap (the planning drawdown) ===")
    mc_out = None
    try:
        mc = resample_equity_curve(cand["equity_curve"], n_paths=5000, seed=SEED)
        mc_out = {"block_days": mc.block, "observed": mc.dd_observed, "median": mc.dd_median,
                  "p95": mc.dd_p95, "p99": mc.dd_p99, "worst": mc.dd_worst,
                  "observed_pctile": mc.dd_observed_pctile, "prob_loss": mc.prob_loss}
        print(f"  block {mc.block} sessions, read off the ACF of |daily return| (volatility")
        print(f"  clustering is what produces drawdowns; raw returns are near-uncorrelated)")
        print(f"  observed {mc.dd_observed*100:>7.2f}%  median {mc.dd_median*100:>7.2f}%  "
              f"p95 {mc.dd_p95*100:>7.2f}%  p99 {mc.dd_p99*100:>7.2f}%")
        print(f"  observed sat at the {mc.dd_observed_pctile*100:.0f}th percentile · "
              f"P(end below start) {mc.prob_loss:.1%}")
        if mc.dd_observed_pctile <= 0.01:
            print("  ** the observed path is still outside the distribution — treat the observed")
            print("     drawdown, not p99, as the planning number")
    except ValueError as e:
        print(f"  skipped: {e}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps({
        "candidate": cand["metrics"], "control": ctrl["metrics"], "passive": passive,
        "verdict": v, "pbo": {"pbo": pbo.pbo, "n_configs": pbo.n_configs,
                              "median_logit": pbo.median_logit},
        "monte_carlo": mc_out, "trade_mix": dict(mix),
        "cost_sensitivity": cost_sensitivity,
        "universe": rep}, indent=2, default=str), encoding="utf-8")
    print(f"\n  -> {OUT / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
