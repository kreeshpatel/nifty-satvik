"""TRADE-POPULATION CENSUS — characterise the SIGNAL, not the portfolio path.

Measurement class. Zero trials, zero screens, no rule proposed, no hypothesis generated. Every
number is a description of a population that already exists under the frozen configuration; nothing
here is a search over anything.

## Which population, and why not the substrate

`research/substrate/trades.parquet` is the obvious source and it is the WRONG one for this question.
It is built with `**P2_EXIT` (`no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5`) — the LIVE
Phase-2 exit — while the run of record (Sharpe 1.132 / 255) uses the frozen default ladder with the
13-week time cap. Comparing a funded set drawn from one engine against an unfunded set drawn from
another would attribute an exit-regime difference to the cash machine.

## Why the engine's own uncapped run is also not the population

`backtest(uncapped=True)` removes the cash test but still enforces ONE OPEN POSITION PER TICKER.
Measured: **81 of the capped book's 255 trades do not appear in the uncapped run at all**, and in
**all 81** cases the ticker was open in the uncapped book at that moment. It is not a superset of
the funded set, so "population minus funded" computed against it would have been wrong by a third.

The holdings rule is portfolio construction, not signal. Every entry window is therefore simulated
INDEPENDENTLY, overlaps included, by a simulator that is validated to reproduce all 3,045 rows of
the engine's uncapped ledger exactly before any statistic is published.

## What is compared

* **§1** full-population statistics, full period and 2019+ separately, per year;
* **§2** FUNDED (the 255) vs UNFUNDED (the 2,790 the cash gate never reached), on win rate,
  expectancy, extension band, CRS rank, price level, week-of-arrival queue depth, and hold time;
* **§3** adherence sensitivity by random sampling of the population — per-trade only, which cannot
  model cash-path effects and is labelled as such.

Outputs: `diagnostics/research/foundation_audit_2026Q3/trade_population_census.json`
and the per-trade table `trade_population.parquet`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
OUTDIR = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3"
OUT = OUTDIR / "trade_population_census.json"

STT = 0.001               # per leg, on gross notional — the inversion key for share count
SEED = 20260806           # fixed so §3 is reproducible; it seeds sampling only, never a search


def _shares_from_stt(row) -> float:
    """Recover the original share count from the reported STT.

    The ledger stores no share count, but STT is charged at 0.1% of every leg's gross, so the legs
    invert it exactly. A trade that booked its half sold 0.5x shares at `half_px` and 0.5x at
    `exit_px`; one that did not sold all shares at `exit_px`.
    """
    entry, exit_px = float(row["entry"]), float(row["exit_px"])
    half_px = row.get("half_px")
    if half_px is not None and half_px == half_px:
        legs = entry + 0.5 * float(half_px) + 0.5 * exit_px
    else:
        legs = entry + exit_px
    return float(row["stt_paid"]) / (STT * legs) if legs > 0 else float("nan")


def _ext_lookup(P) -> dict:
    """(ticker, entry-day timestamp) -> extension of the fill over the SIGNAL week's 44w SMA."""
    out = {}
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for _e0, win in s["entry_win"].items():
            days, _lo, _hi, _rk, sma_sig, _org = win
            for di in days:
                if di < len(dates):
                    out[(t, pd.Timestamp(dates[di]))] = float(sma_sig)
    return out


def _enrich(led: list, P, sma_at: dict) -> pd.DataFrame:
    D = pd.DataFrame(led)
    D["entry_date"] = pd.to_datetime(D["entry_date"])
    D["exit_date"] = pd.to_datetime(D["exit_date"])
    D["year"] = D["entry_date"].dt.year
    D["iso_week"] = D["entry_date"].dt.strftime("%G-W%V")
    D["shares"] = D.apply(_shares_from_stt, axis=1)
    D["gross_in"] = D["shares"] * D["entry"]
    D["net_pct"] = 100.0 * D["net_pnl"] / D["gross_in"]
    D["risk_pct"] = 100.0 * (D["entry"] - D["stop0"]) / D["entry"]
    D["sma_sig"] = [sma_at.get((t, d), np.nan) for t, d in zip(D["tkr"], D["entry_date"])]
    D["ext_pct"] = 100.0 * (D["entry"] / D["sma_sig"] - 1.0)
    D["hold_days"] = (D["exit_date"] - D["entry_date"]).dt.days
    return D


def _dist(x: pd.Series, nd: int = 3) -> dict:
    x = x.dropna()
    if not len(x):
        return {}
    qs = {f"p{int(q*100)}": round(float(x.quantile(q)), nd)
          for q in (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90)}
    return {"n": int(len(x)), "mean": round(float(x.mean()), nd),
            "sd": round(float(x.std(ddof=1)), nd), "min": round(float(x.min()), nd),
            **qs, "max": round(float(x.max()), nd)}


def _block(D: pd.DataFrame) -> dict:
    R, pct = D["R"], D["net_pct"]
    wins, losses = R[R > 0], R[R <= 0]
    payoff = (float(wins.mean()) / abs(float(losses.mean()))
              if len(wins) and len(losses) and losses.mean() != 0 else float("nan"))
    return {
        "N": int(len(D)),
        "win_rate": round(float((R > 0).mean()), 4),
        "avg_win_R": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loss_R": round(float(losses.mean()), 4) if len(losses) else None,
        "payoff_ratio": round(payoff, 4) if payoff == payoff else None,
        "expectancy_R": round(float(R.mean()), 4),
        "expectancy_net_pct": round(float(pct.mean()), 4),
        "median_R": round(float(R.median()), 4),
        "median_net_pct": round(float(pct.median()), 4),
        "sum_R": round(float(R.sum()), 2),
        "R_distribution": _dist(R),
        "net_pct_distribution": _dist(pct),
        "hold_weeks_distribution": _dist(D["held_weeks"].astype(float), nd=1),
        "hold_days_distribution": _dist(D["hold_days"].astype(float), nd=1),
        "exit_reason_mix": {k: int(v) for k, v in D["reason"].value_counts().items()},
    }


def _compare(a: pd.DataFrame, b: pd.DataFrame, cols) -> list[dict]:
    """Funded vs unfunded on each dimension, with a distribution-level test that assumes nothing
    about shape (Mann-Whitney) alongside the plain means."""
    from scipy.stats import mannwhitneyu
    rows = []
    for col, label in cols:
        x, y = a[col].dropna().astype(float), b[col].dropna().astype(float)
        if len(x) < 5 or len(y) < 5:
            continue
        try:
            u, p = mannwhitneyu(x, y, alternative="two-sided")
        except Exception:
            p = float("nan")
        rows.append({
            "dimension": label, "funded_n": int(len(x)), "unfunded_n": int(len(y)),
            "funded_mean": round(float(x.mean()), 4), "unfunded_mean": round(float(y.mean()), 4),
            "funded_median": round(float(x.median()), 4),
            "unfunded_median": round(float(y.median()), 4),
            "delta_mean": round(float(x.mean() - y.mean()), 4),
            "mannwhitney_p": (None if p != p else float(f"{p:.3g}")),
        })
    return rows


def _adherence(R: np.ndarray, pct: np.ndarray, ks=(50, 70, 90, 100), draws=4000) -> list[dict]:
    """Take a random k% of the signal population, many times; report the SPREAD.

    The mean of this distribution equals the population mean by construction (sampling without
    replacement is unbiased), so the centre carries no information and is reported only as an
    arithmetic check. The SPREAD is the finding: it is how far realised expectancy can sit from the
    population's on adherence noise alone, with no skill and no timing.
    """
    rng = np.random.default_rng(SEED)
    n = len(R)
    out = []
    for k in ks:
        m = max(1, int(round(n * k / 100.0)))
        if m >= n:
            out.append({"k_pct": k, "n_taken": n, "draws": 1,
                        "mean_R_of_draw_means": round(float(R.mean()), 4), "sd_of_draw_means": 0.0,
                        "p05_R": round(float(R.mean()), 4), "p50_R": round(float(R.mean()), 4),
                        "p95_R": round(float(R.mean()), 4),
                        "mean_net_pct_of_draw_means": round(float(pct.mean()), 4),
                        "p05_net_pct": round(float(pct.mean()), 4),
                        "p95_net_pct": round(float(pct.mean()), 4),
                        "_note": "k=100 takes the whole population: zero spread by construction"})
            continue
        mr = np.empty(draws)
        mp = np.empty(draws)
        for i in range(draws):
            idx = rng.choice(n, size=m, replace=False)
            mr[i] = R[idx].mean()
            mp[i] = pct[idx].mean()
        out.append({
            "k_pct": k, "n_taken": m, "draws": draws,
            "mean_R_of_draw_means": round(float(mr.mean()), 4),
            "sd_of_draw_means": round(float(mr.std(ddof=1)), 4),
            "p05_R": round(float(np.percentile(mr, 5)), 4),
            "p50_R": round(float(np.percentile(mr, 50)), 4),
            "p95_R": round(float(np.percentile(mr, 95)), 4),
            "mean_net_pct_of_draw_means": round(float(mp.mean()), 4),
            "p05_net_pct": round(float(np.percentile(mp, 5)), 4),
            "p95_net_pct": round(float(np.percentile(mp, 95)), 4),
        })
    return out



# ─────────────────────────────────────────────────────────────────────────────────────────────────
# THE PER-SIGNAL SIMULATOR — and why the engine's own uncapped run could not be the population
#
# `backtest(uncapped=True)` removes the cash test but still enforces ONE OPEN POSITION PER TICKER,
# so a signal on a name it is already holding is never activated. Measured: 81 of the capped book's
# 255 trades do not appear in the uncapped run at all, and in ALL 81 cases the ticker was open in
# the uncapped book at that moment (example: the capped book entered TATASPONGE on 2018-04-16 while
# the uncapped book was still holding a 2018-04-09 entry). The uncapped run is therefore NOT a
# superset of the funded set, and "population minus funded" would have been computed against a set
# that excludes a third of what it was supposed to contain.
#
# The holdings rule is portfolio construction, not signal. To characterise the SIGNAL, every entry
# window is simulated independently, overlaps included.
#
# The simulator re-implements the frozen exit ladder rather than calling the engine. That is a risk,
# and it is bought off by a hard validation: it must reproduce ALL 3,045 rows of the engine's own
# uncapped ledger EXACTLY — entry, exit date, exit price, reason, weeks held, R and net P&L. If it
# does not, this script raises and no number is published.
# ─────────────────────────────────────────────────────────────────────────────────────────────────

TRAIL_PCT = 0.04
CAP_WEEKS = 13
EQ0, RISK = 1_000_000.0, 0.02
STT_BROK = 0.0013
SLIP = {"LARGE": 0.0005, "MID": 0.0022, "SMALL": 0.0040}
ADV_LARGE, ADV_MID = 5.0e8, 5.0e7


def _cost(adv: float, notional: float) -> float:
    a = adv if np.isfinite(adv) else 0.0
    s = SLIP["LARGE"] if a >= ADV_LARGE else SLIP["MID"] if a >= ADV_MID else SLIP["SMALL"]
    if a > 0 and notional > 0.005 * a:
        s += 0.001
    return STT_BROK + s


def simulate_signal(s, i0_days, lo, hi):
    """One entry window, taken in isolation. Returns None when the window never fills."""
    o, h, c, ema20, weekend = s["o"], s["h"], s["c"], s["ema20"], s["weekend"]
    n = len(c)
    i0 = None
    for di in i0_days:                                  # first day of the window that fills
        if di < n and lo < o[di] < hi:
            i0 = di
            break
    if i0 is None:
        return None
    en, st = float(o[i0]), float(lo)
    if not (en > st):
        return None
    risk0 = en - st
    tp2 = en + 2.0 * risk0
    adv = float(s["adv20"][i0])
    sh = EQ0 * RISK / risk0

    weeks, half, trail, pending, half_px = 0, False, st, None, None

    def _close(px, reason, weeks_held):
        r_rest = (px - en) / risk0
        R = (0.5 * 2.0 + 0.5 * r_rest) if half else r_rest
        gi = sh * en
        cash_out = gi * (1 + _cost(adv, gi))
        proceeds = 0.0
        if half:
            hp = 0.5 * sh * half_px
            proceeds += hp * (1 - _cost(adv, hp))
        xp = (0.5 * sh if half else sh) * px
        proceeds += xp * (1 - _cost(adv, xp))
        return {"entry_pos": i0, "entry": round(en, 2), "stop0": round(st, 2),
                "exit_px": round(px, 2), "reason": reason, "held_weeks": weeks_held,
                "R": round(float(R), 3), "half_px": (None if half_px is None
                                                     else round(float(half_px), 2)),
                "net_pnl": round(proceeds - cash_out, 2), "shares": sh,
                "gross_in": gi, "adv20": adv, "risk0": risk0}

    for i in range(i0 + 1, n):
        if pending is not None:
            act, rs = pending
            px = float(o[i])
            if act == "half":
                half, half_px, pending = True, px, None
            else:
                return {**_close(px, rs, weeks), "exit_pos": i}
        if i in weekend:
            weeks += 1
            wc = float(c[i])
            if wc <= st:
                pending = ("full", "stop" + ("_half" if half else ""))
            elif not half and wc >= tp2:
                pending = ("half", "half")
            elif half:
                trail = max(trail, float(ema20[i]) * (1 - TRAIL_PCT))
                if wc < trail:
                    pending = ("full", "trail")
            if pending is None and weeks >= CAP_WEEKS:
                pending = ("full", "time")
    return {**_close(float(c[n - 1]), "eos", weeks), "exit_pos": n - 1}


def build_population(P, mem):
    """Every entry window, simulated in isolation. Membership is applied at the window's first day,
    exactly as the engine applies it at activation."""
    from nq.data.membership import ticker_in_index_on
    rows = []
    for t, s in P.items():
        dates = pd.DatetimeIndex(s["dates"])
        for _e0, win in s["entry_win"].items():
            days, lo, hi, rk, sma_sig, origin = win
            if not len(days) or days[0] >= len(dates):
                continue
            if mem is not None and not ticker_in_index_on(t, pd.Timestamp(dates[days[0]]).date(),
                                                          mem):
                continue
            r = simulate_signal(s, days, float(lo), float(hi))
            if r is None:
                continue
            r.update(tkr=t, entry_date=pd.Timestamp(dates[r["entry_pos"]]),
                     exit_date=pd.Timestamp(dates[r["exit_pos"]]), rank=float(rk),
                     sma_sig=float(sma_sig), origin=int(origin))
            rows.append(r)
    return pd.DataFrame(rows)


def validate_simulator(pop: pd.DataFrame, led_u: list) -> dict:
    """The simulator must reproduce the engine's uncapped ledger exactly, or nothing is published."""
    U = pd.DataFrame(led_u)
    U["entry_date"] = pd.to_datetime(U["entry_date"])
    key = ["tkr", "entry_date"]
    m = U.merge(pop, on=key, suffixes=("_eng", "_sim"), how="left")
    missing = int(m["R_sim"].isna().sum())
    checks = {}
    for col, tol in (("entry", 0.005), ("exit_px", 0.005), ("R", 0.0005), ("net_pnl", 0.05)):
        d = (m[f"{col}_eng"].astype(float) - m[f"{col}_sim"].astype(float)).abs()
        checks[col] = {"max_abs_diff": round(float(d.max()), 6),
                       "n_mismatch": int((d > tol).sum())}
    checks["reason"] = {"n_mismatch": int((m["reason_eng"] != m["reason_sim"]).sum())}
    checks["held_weeks"] = {"n_mismatch": int((m["held_weeks_eng"] != m["held_weeks_sim"]).sum())}
    checks["exit_date"] = {"n_mismatch": int((pd.to_datetime(m["exit_date_eng"])
                                              != pd.to_datetime(m["exit_date_sim"])).sum())}
    bad = missing + sum(v.get("n_mismatch", 0) for v in checks.values())
    return {"engine_rows": int(len(U)), "unmatched": missing, "checks": checks, "total_bad": bad}

def main() -> int:
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_path1 import corrected_universe

    OUTDIR.mkdir(parents=True, exist_ok=True)
    ohlcv = corrected_universe()
    mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    sma_at = _ext_lookup(P)

    led_c: list = []
    m_c = R94.backtest(P, mem, ledger=led_c, start="2017-01-01")
    led_u: list = []
    m_u = R94.backtest(P, mem, ledger=led_u, start="2017-01-01", uncapped=True)
    assert abs(m_c["sharpe"] - 1.132) < 0.01 and m_c["trades"] == 255, \
        f"record guard FAILED: {m_c['sharpe']:.4f} / {m_c['trades']}"

    C = _enrich(led_c, P, sma_at)

    # THE POPULATION — every entry window simulated in isolation, then hard-validated.
    pop = build_population(P, mem)
    val = validate_simulator(pop, led_u)
    assert val["total_bad"] == 0, f"simulator does not reproduce the engine: {val}"

    U = pop.copy()
    U["year"] = U["entry_date"].dt.year
    U["iso_week"] = U["entry_date"].dt.strftime("%G-W%V")
    U["net_pct"] = 100.0 * U["net_pnl"] / U["gross_in"]
    U["risk_pct"] = 100.0 * U["risk0"] / U["entry"]
    U["ext_pct"] = 100.0 * (U["entry"] / U["sma_sig"] - 1.0)
    U["hold_days"] = (U["exit_date"] - U["entry_date"]).dt.days

    assert U.groupby(["tkr", "iso_week"]).ngroups == len(U), "signal key is not unique"
    assert C.groupby(["tkr", "iso_week"]).ngroups == len(C)
    funded_keys = set(zip(C["tkr"], C["iso_week"]))
    U["funded"] = [k in funded_keys for k in zip(U["tkr"], U["iso_week"])]
    matched = int(U["funded"].sum())
    assert matched == len(C), (
        f"only {matched} of {len(C)} funded trades found in the population — the population is "
        "still not a superset and no funded/unfunded number may be published")

    depth = U.groupby("iso_week").size().rename("week_signal_count")
    U = U.join(depth, on="iso_week")
    U.to_parquet(OUTDIR / "trade_population.parquet", index=False)

    n_windows = sum(len(s["entry_win"]) for s in P.values())
    F, N = U[U["funded"]], U[~U["funded"]]
    U19, C19 = U[U["year"] >= 2019], C[C["year"] >= 2019]

    res = {
        "_class": "MEASUREMENT — trade-population census; zero trials, zero screens",
        "population_source": {
            "config": "frozen defaults, start=2017-01-01; uncapped=True removes only the cash test",
            "why_not_the_substrate": "research/substrate/trades.parquet is built with P2_EXIT "
                                     "(no_time_cap, 20wk trail, blow-off arm) — a different exit "
                                     "regime from the run of record, so it cannot answer a "
                                     "funded-vs-unfunded question about the 1.132 book",
            "record_guard": {"sharpe": round(float(m_c["sharpe"]), 4), "trades": int(m_c["trades"])},
        },
        "funnel": {
            "entry_windows_created": int(n_windows),
            "windows_in_index_and_fillable": int(len(U)),
            "signals_funded_capped": int(len(C)),
            "funded_share_pct": round(100.0 * len(C) / len(U), 2),
            "capped_cash_rejections": int(m_c["skipped_cash"]),
            "engine_uncapped_rows_for_reference": int(len(led_u)),
            "_note": "population = every entry window simulated in isolation, overlaps on a ticker "
                     "INCLUDED. The engine's uncapped run (shown for reference) suppresses a signal "
                     "on a name it already holds and is not a superset of the funded set.",
        },
        "simulator_validation": val,
        "match": {"funded_rows_matched_into_population": matched, "capped_rows": int(len(C)),
                  "_note": "join key = (ticker, ISO week of entry); asserted to be complete"},
        "section1_full_population": {
            "full_period_2017_2026": _block(U),
            "from_2019": _block(U19),
            "per_year": {str(y): _block(g) for y, g in U.groupby("year")},
            "per_year_funded": {str(y): {"N": int(len(g)),
                                         "expectancy_R": round(float(g["R"].mean()), 4),
                                         "win_rate": round(float((g["R"] > 0).mean()), 4)}
                                for y, g in C.groupby("year")},
        },
        "section2_funded_vs_unfunded": {
            "funded": _block(F), "unfunded": _block(N),
            "funded_2019plus": _block(U19[U19["funded"]]),
            "unfunded_2019plus": _block(U19[~U19["funded"]]),
            "dimensions": _compare(F, N, [
                ("R", "outcome R"), ("net_pct", "outcome net %"),
                ("ext_pct", "extension over signal-week 44w SMA (%)"),
                ("rank", "CRS rank (crs_dist)"), ("entry", "entry price level (Rs)"),
                ("week_signal_count", "signals arriving that ISO week (queue depth)"),
                ("held_weeks", "hold time (weeks)"), ("risk_pct", "stop width (% of entry)"),
            ]),
        },
        "section3_adherence": {
            "_limitation": "PER-TRADE sampling of the signal population. It cannot model cash-path "
                           "effects: which signals a smaller book could actually have funded, the "
                           "order they arrive in, or the capital they free. It answers only 'if you "
                           "took a random k% of these trades, how far can realised expectancy sit "
                           "from the population's?'",
            "population_used": "uncapped, full period",
            "seed": SEED,
            "draws": _adherence(U["R"].to_numpy(float), U["net_pct"].to_numpy(float)),
            "draws_2019plus": _adherence(U19["R"].to_numpy(float), U19["net_pct"].to_numpy(float)),
        },
    }
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps({k: res[k] for k in ("funnel", "simulator_validation", "match")},
                     indent=2))
    print("\nFULL POPULATION      ", {k: res["section1_full_population"]["full_period_2017_2026"][k]
                                      for k in ("N", "win_rate", "payoff_ratio", "expectancy_R",
                                                "expectancy_net_pct")})
    print("FUNDED               ", {k: res["section2_funded_vs_unfunded"]["funded"][k]
                                    for k in ("N", "win_rate", "payoff_ratio", "expectancy_R",
                                              "expectancy_net_pct")})
    print("UNFUNDED             ", {k: res["section2_funded_vs_unfunded"]["unfunded"][k]
                                    for k in ("N", "win_rate", "payoff_ratio", "expectancy_R",
                                              "expectancy_net_pct")})
    print("\nDIMENSIONS")
    for r in res["section2_funded_vs_unfunded"]["dimensions"]:
        print(f"  {r['dimension']:<46} funded {r['funded_mean']:>10.4f} | unfunded "
              f"{r['unfunded_mean']:>10.4f} | delta {r['delta_mean']:>9.4f} | p={r['mannwhitney_p']}")
    print("\nADHERENCE (full period)")
    for r in res["section3_adherence"]["draws"]:
        print(f"  k={r['k_pct']:>3}%  n={r['n_taken']:>4}  meanR {r['mean_R_of_draw_means']:.4f}  "
              f"sd {r['sd_of_draw_means']:.4f}  p05..p95 [{r['p05_R']:.4f}, {r['p95_R']:.4f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
