"""ZOO SHADOW BOOK — observational logger for the combined-funnel candidate pool (pre-reg 0131).

**OBSERVATIONAL ONLY. TRADED BY NOBODY.** Writes `results/zoo_shadow_book.json` and nothing else.
It does not touch the certified swing paper book (`results/paper_portfolio_weekly.json`), the
hash-chained forward wall, the live cards, or any config the traded book reads. It is the same kind
of object as `run_blend_paper.py`: a stream that accrues evidence and decides nothing.

## What it is

The frozen engine with **one difference: a wider candidate pool.**

| | live / record book | this shadow book |
|---|---|---|
| candidate pool | `touch44` | `touch44` + `cup_handle` + `box` + `double_bottom` |
| CRS fill priority | strongest-first | **same** |
| exit ladder | frozen default (13-week cap) | **same** |
| risk %, cash gate, capital | 2%, cash-only, Rs10L | **same** |

Everything except the pool is held identical, so any divergence is attributable to the pool. Note
this uses the **frozen ladder, not `P2_EXIT`** — deliberately, because the STAGE1/STAGE4 numbers
that motivated the election carry a different exit and this removes that confound.

## What it may and may not be read as (pre-reg 0131 §4, binding)

The capped comparison is **underpowered by construction**: the measured resolution band is
+-0.302 dSharpe and the book's whole annual return is 1.617 sigma. So:

* **This is never a Sharpe race.** A dSharpe computed on this pair is reported only with its band
  attached and never as a verdict.
* The pre-committed reads are (1) population-level per-trade quality in **% of equity** (the arbiter)
  with R beside it, and (2) forward divergence of the two books' selections.
* First substantive read: **2027-04-01**, at >=2 quarters AND >=30 shadow-funded closed trades.
  2026-10-01 is a status check only.

## Hypothesis being logged against

**The pool improves, not the throughput** — capital binds, not signal supply (the census funded 255
of 6,245 signals, 4.08%, with the funded count flat while supply swung 280->984 a year).
Pre-committed falsifier: trade count rising >25% over the live book without per-trade quality rising
means the funnel bought throughput, not quality.

    python scripts/run_zoo_shadow_book.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "results" / "zoo_shadow_book.json"

# The elected pool (pre-reg 0131 §1). Frozen — this tuple is the whole configuration.
# origin ids: 0 touch (always on) | 1 box (box_breakout) | 6 cup_handle | 8 double_bottom (ZOO)
ELECTED_ZOO_ORIGINS = (6, 8)          # cup_handle, double_bottom
ELECTED_BOX = True                    # box arrives via its own flag, not the ZOO dict
EQ0 = 1_000_000.0
RISK = 0.02
SETUP_OF_ORIGIN = {0: "touch44", 1: "box", 6: "cup_handle", 8: "double_bottom"}


def _pool_kwargs() -> dict:
    """The ONE difference from the record. Everything else stays at signature defaults."""
    return {"box_breakout": ELECTED_BOX, "zoo_origins": ELECTED_ZOO_ORIGINS}


def _origin_at_entry(P, tkr: str, entry_date) -> int:
    """Which detector produced the window this fill came from."""
    s = P.get(tkr)
    if s is None:
        return -1
    dates = pd.DatetimeIndex(s["dates"])
    ts = pd.Timestamp(entry_date)
    if ts not in dates:
        return -1
    i = dates.get_loc(ts)
    for _e0, win in s["entry_win"].items():
        if i in set(win[0]):
            return int(win[5])
    return -1


def _boot_delta_mean(a: np.ndarray, b: np.ndarray, draws: int = 10_000, seed: int = 20260806):
    """CI on mean(a) - mean(b) for two disjoint trade sets. Trade counts are exact; per-trade
    MEANS are estimates, so the arbiter gets an interval and the trade count does not."""
    rng = np.random.default_rng(seed)
    ia = rng.integers(0, len(a), size=(draws, len(a)))
    ib = rng.integers(0, len(b), size=(draws, len(b)))
    d = a[ia].mean(axis=1) - b[ib].mean(axis=1)
    return (round(float(a.mean() - b.mean()), 4),
            round(float(np.percentile(d, 2.5)), 4),
            round(float(np.percentile(d, 97.5)), 4))


def _per_trade_block(L: pd.DataFrame, P) -> dict:
    """Per-trade quality, in BOTH units, split by detector. % of equity is the arbiter."""
    if not len(L):
        return {"n": 0}
    L = L.copy()
    L["origin"] = [_origin_at_entry(P, t, d) for t, d in zip(L["tkr"], L["entry_date"])]
    L["setup"] = L["origin"].map(SETUP_OF_ORIGIN).fillna("other")
    # the book sizes off mark-to-market equity, so price the trade on the fixed reference
    # equity to keep every trade commensurable (same convention as 0130)
    L["equity_pct"] = 100.0 * L["net_pnl"] / EQ0
    out = {"n": int(len(L)),
           "mean_R": round(float(L["R"].mean()), 4),
           "mean_equity_pct": round(float(L["equity_pct"].mean()), 4),
           "win_rate": round(float((L["R"] > 0).mean()), 4),
           "by_setup": {}}
    for setup, g in L.groupby("setup"):
        out["by_setup"][str(setup)] = {
            "n": int(len(g)),
            "mean_R": round(float(g["R"].mean()), 4),
            "mean_equity_pct": round(float(g["equity_pct"].mean()), 4),
            "win_rate": round(float((g["R"] > 0).mean()), 4),
        }
    return out



def _risk_block(m) -> dict:
    """MaxDD / CAGR / Calmar / worst calendar year from an arm's own equity curve.

    Added 2026-08-06 (H-bis). The first version of this logger recorded Sharpe and nothing else,
    which left the drawdown axis unreported — on precisely the family
    `research/losers_analysis/LOCKED_STRATEGY.md:64,73` preserves as a **drawdown-only option**
    (box/S-R sleeve: -32.5 vs -34.8 DD at a Sharpe cost, kept as a live/forward-wall DD option).
    Reporting only the axis that fell was an incomplete record.
    """
    e = m["curve"]
    yr = e.groupby(e.index.year).agg(["first", "last"])
    per_year = {str(y): round(float(r["last"] / r["first"] - 1.0) * 100, 3)
                for y, r in yr.iterrows()}
    worst = min(per_year.items(), key=lambda kv: kv[1]) if per_year else (None, None)
    dd = float(m["dd"])
    cagr = float(m["cagr"])
    return {"max_dd_pct": round(100.0 * dd, 3),
            "cagr_pct": round(100.0 * cagr, 3),
            "calmar": round(cagr / abs(dd), 4) if dd else None,
            "worst_year": worst[0], "worst_year_pct": worst[1],
            "n_losing_years": int(sum(1 for v in per_year.values() if v < 0)),
            "per_year_pct": per_year}


def _quality_delta(L_zoo: pd.DataFrame, L_live: pd.DataFrame) -> dict:
    """The ARBITER: per-trade % of equity, shadow minus live, with a bootstrap CI. R beside it."""
    if not len(L_zoo) or not len(L_live):
        return {}
    ze = (100.0 * L_zoo["net_pnl"] / EQ0).to_numpy(float)
    le = (100.0 * L_live["net_pnl"] / EQ0).to_numpy(float)
    de, dlo, dhi = _boot_delta_mean(ze, le)
    zr, lr = L_zoo["R"].to_numpy(float), L_live["R"].to_numpy(float)
    dr, rlo, rhi = _boot_delta_mean(zr, lr)
    return {
        "_arbiter": "% of equity per trade (UNIT_RESOLUTION.md); R reported beside it",
        "d_equity_pct_per_trade": de, "equity_ci95": [dlo, dhi],
        "equity_ci_excludes_zero": bool(dlo > 0 or dhi < 0),
        "d_R_per_trade": dr, "R_ci95": [rlo, rhi],
        "R_ci_excludes_zero": bool(rlo > 0 or rhi < 0),
    }


def build(start: str = "2017-01-01") -> dict:
    import run_bhanushali_weekly_rank as R94
    from nq.data.membership import load_membership
    from run_bhanushali_path1 import corrected_universe

    ohlcv = corrected_universe()
    mem = load_membership()

    # LIVE-EQUIVALENT ARM — the record's own pool, frozen defaults
    P_live = R94.prep_weekly_rank(ohlcv)
    led_live: list = []
    m_live = R94.backtest(P_live, mem, ledger=led_live, start=start)

    # SHADOW ARM — the same engine, wider pool. This is the ONLY difference.
    P_zoo = R94.prep_weekly_rank(ohlcv, **_pool_kwargs())
    led_zoo: list = []
    m_zoo = R94.backtest(P_zoo, mem, ledger=led_zoo, start=start)

    L_live = pd.DataFrame(led_live)
    L_zoo = pd.DataFrame(led_zoo)
    for D in (L_live, L_zoo):
        if len(D):
            D["entry_date"] = pd.to_datetime(D["entry_date"])

    live_keys = set(zip(L_live["tkr"], L_live["entry_date"].dt.strftime("%G-W%V"))) if len(L_live) else set()
    zoo_keys = set(zip(L_zoo["tkr"], L_zoo["entry_date"].dt.strftime("%G-W%V"))) if len(L_zoo) else set()

    n_live, n_zoo = len(L_live), len(L_zoo)
    throughput_delta_pct = round(100.0 * (n_zoo - n_live) / n_live, 2) if n_live else None

    return {
        "_what": "OBSERVATIONAL SHADOW BOOK — pre-reg 0131. Traded by nobody. Decides nothing.",
        "_binding": "pre-reg 0131 §4: this is NEVER a Sharpe race. A dSharpe on this pair may only "
                    "be quoted with the +-0.302 resolution band attached, never as a verdict. The "
                    "reads are per-trade quality in % of equity (arbiter) and forward divergence.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start": start,
        "pool": {"live": ["touch44"],
                 "shadow": ["touch44"] + [SETUP_OF_ORIGIN[o] for o in (1,) if ELECTED_BOX]
                           + [SETUP_OF_ORIGIN[o] for o in ELECTED_ZOO_ORIGINS]},
        "held_identical": ["CRS fill priority", "frozen exit ladder (13-week cap)", "risk 2%",
                           "cash-only capacity", "Rs10L capital"],
        "throughput": {
            "live_closed_trades": int(n_live),
            "shadow_closed_trades": int(n_zoo),
            "delta_pct": throughput_delta_pct,
            "falsifier_threshold_pct": 25.0,
            "_H": "the pool improves, not the throughput — capital binds, not supply",
            "throughput_falsifier_tripped": bool(
                throughput_delta_pct is not None and throughput_delta_pct > 25.0),
        },
        "selection_divergence": {
            "shadow_only_fills": int(len(zoo_keys - live_keys)),
            "live_only_fills": int(len(live_keys - zoo_keys)),
            "shared_fills": int(len(zoo_keys & live_keys)),
            "_note": "a shadow-only fill is a week where the wider pool won a seat the live pool "
                     "could not contest; this is the observable forward event",
        },
        "per_trade_quality": {"live": _per_trade_block(L_live, P_live),
                              "shadow": _per_trade_block(L_zoo, P_zoo),
                              "delta_shadow_minus_live": _quality_delta(L_zoo, L_live)},
        "capped_metrics_UNDERPOWERED": {
            "_warning": "REPORTED FOR COMPLETENESS ONLY. Resolution bands, both measured from "
                        "STAGE4's published paired block-bootstrap: +-0.302 dSharpe and +-0.0905 "
                        "dMaxDD. A difference inside its band is unresolvable and must not be read "
                        "as a result. Pre-reg 0131 §4 forbids treating any of this as a verdict.",
            "resolution_band_dsharpe": 0.302,
            "resolution_band_dmaxdd": 0.0905,
            "live_sharpe": round(float(m_live["sharpe"]), 4),
            "shadow_sharpe": round(float(m_zoo["sharpe"]), 4),
            "dsharpe": round(float(m_zoo["sharpe"] - m_live["sharpe"]), 4),
            "inside_resolution_band": bool(abs(m_zoo["sharpe"] - m_live["sharpe"]) < 0.302),
            "risk_axis": {
                "_why": "H-bis, 2026-08-06: the first version of this logger reported Sharpe only. "
                        "LOCKED_STRATEGY.md:64,73 preserves the box/S-R sleeve as a DRAWDOWN-ONLY "
                        "option (-32.5 vs -34.8 at a Sharpe cost), so reporting only the axis that "
                        "fell left the record incomplete. Completing it — no proposal.",
                "live": _risk_block(m_live),
                "shadow": _risk_block(m_zoo),
                "d_max_dd_pp": round(100.0 * (float(m_zoo["dd"]) - float(m_live["dd"])), 3),
                "d_calmar": round(float(m_zoo["cagr"]) / abs(float(m_zoo["dd"]))
                                  - float(m_live["cagr"]) / abs(float(m_live["dd"])), 4),
                "dd_gain_inside_resolution_band": bool(
                    abs(float(m_zoo["dd"]) - float(m_live["dd"])) < 0.0905),
            },
        },
        "next_substantive_read": "2027-04-01 (>=2 quarters AND >=30 shadow-funded closed trades); "
                                 "2026-10-01 is a status check only",
    }


def main() -> int:
    start = "2017-01-01"
    argv = sys.argv[1:]
    if "--start" in argv:
        start = argv[argv.index("--start") + 1]
    res = build(start)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(json.dumps({k: res[k] for k in
                      ("throughput", "selection_divergence", "capped_metrics_UNDERPOWERED")},
                     indent=2))
    print("\nper-trade quality (arbiter = % of equity):")
    for arm in ("live", "shadow"):
        b = res["per_trade_quality"][arm]
        print(f"  {arm:<7} n={b['n']:>4} meanR={b['mean_R']:+.4f} "
              f"mean_eq%={b['mean_equity_pct']:+.4f} win={b['win_rate']:.4f}")
        for su, v in sorted(b.get("by_setup", {}).items()):
            print(f"      {su:<15} n={v['n']:>4} meanR={v['mean_R']:+.4f} "
                  f"eq%={v['mean_equity_pct']:+.4f} win={v['win_rate']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
