"""First-passage base rates — does ANY profit-target / stop-loss pair carry an edge?

THE QUESTION. The owner proposes a swing book of +10% target / −3% stop / 15-day cap and asks why
we cannot reach 40% CAGR when others claim to.

THE THEOREM. For a driftless price with absorbing barriers at −a and +b, P(hit +b first) = a/(a+b).
With a=3, b=10 that is **3/13 = 23.08%**. The breakeven win rate for a 10:3 payoff is 10p = 3(1−p),
i.e. **p = 3/13 = 23.08%**. They are identical — by the optional stopping theorem, a martingale's
expected value at the stopping time equals its starting value REGARDLESS of where the barriers sit.
So the reward:risk geometry contributes exactly nothing, and every rupee of expectancy must come
from drift, i.e. from SELECTION.

WHY MEASURE IT ANYWAY. The theorem assumes a driftless walk. Real equities have positive drift and
fat tails, and three real effects push the other way: gaps overshoot the NEAR barrier (a −3% stop
fills at −4%; a +10% target does not fill at +13%), the time cap creates a third cost-only outcome
the theorem ignores, and ~0.5% round-trip friction is 17% of a 3% risk unit. Only measurement
settles the net.

WHAT IS REPORTED
  1. the unconditional first-passage rate for the proposed pair, against 23.08%
  2. the timeout share and the loss-side overshoot distribution
  3. a SURFACE over target x stop (and a horizon sweep), to show the result is general rather than
     a property of one cell
  4. conditional rates under our own signals — the direct test of "is our stock selection bad"

**NOTHING IS ADOPTED FROM THE SURFACE.** A target x stop grid is precisely the shape that turned a
21.95% in-sample cell into −5.06% out of sample yesterday. It is a robustness map: if some cell
looks good, that is the multiplicity talking. Per findings 0006/0010 the expectation is that the
surface is spiky, and a spike is evidence of noise, not of an edge.

CONVENTIONS, stated because they change the answer
  * entry at the SIGNAL BAR CLOSE (pure first-passage; execution lag is a separate question)
  * same bar touches both barriers -> STOP assumed first (conservative; matches pre-reg 0011)
  * a stop that gaps through fills at min(open, stop) -> losses can exceed 1R, as in life
  * CIs are CLUSTER-bootstrapped ON TICKER: forward windows overlap heavily, so per-observation
    CIs would be far too tight. Resampling whole tickers respects that dependence.

MEASUREMENT class. No trial is spent; `n_trials` stays 138.

    python scripts/diag_barrier_base_rate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_candidate_gate import build_panel, candidate_signals  # noqa: E402

START, END = "2017-01-01", "2026-06-30"
TARGET, STOP, HORIZON = 0.10, 0.03, 15          # the owner's proposal
COST_ROUND_TRIP = 0.005                          # ~0.25%/leg all-in, the house model
N_BOOT, SEED = 2000, 20260807

WIN, LOSS, TIMEOUT = 1, 2, 3


def first_passage(o, h, l, c, *, target: float, stop: float, horizon: int):
    """Vectorised first-passage. Returns (outcome[int8], realised_return[float]).

    ``outcome`` is WIN / LOSS / TIMEOUT / 0 (no full window available). ``realised_return`` is the
    signed return actually achieved — for a LOSS this uses ``min(open, stop_px)`` so a gap-through
    is recorded at its true depth rather than a clean −stop.
    """
    n = len(c)
    out = np.zeros(n, dtype=np.int8)
    ret = np.full(n, np.nan)
    tgt_px, stp_px = c * (1.0 + target), c * (1.0 - stop)
    pad = np.full(horizon, np.nan)
    hi_p, lo_p, op_p = (np.concatenate([a, pad]) for a in (h, l, o))
    idx = np.arange(n)

    for step in range(1, horizon + 1):
        j = idx + step
        live = (out == 0) & (j < n)
        if not live.any():
            break
        hj, lj, oj = hi_p[j], lo_p[j], op_p[j]
        hit_lo = live & np.isfinite(lj) & (lj <= stp_px)
        hit_hi = live & np.isfinite(hj) & (hj >= tgt_px) & ~hit_lo   # same bar -> stop first
        if hit_lo.any():
            out[hit_lo] = LOSS
            fill = np.minimum(oj[hit_lo], stp_px[hit_lo])
            ret[hit_lo] = fill / c[hit_lo] - 1.0
        if hit_hi.any():
            out[hit_hi] = WIN
            ret[hit_hi] = np.maximum(oj[hit_hi], tgt_px[hit_hi]) / c[hit_hi] - 1.0
    # unresolved but with a complete window -> timeout at the horizon close
    done = idx + horizon < n
    to = (out == 0) & done
    out[to] = TIMEOUT
    cl_p = np.concatenate([c, pad])
    ret[to] = cl_p[idx[to] + horizon] / c[to] - 1.0
    out[(out == 0) & ~done] = 0
    return out, ret


def scan(panel: pd.DataFrame, *, target: float, stop: float, horizon: int,
         mask: dict[str, np.ndarray] | None = None) -> pd.DataFrame:
    """Run first-passage per ticker. ``mask`` optionally restricts to signal bars."""
    rows = []
    for tkr, g in panel.groupby("ticker", sort=True):
        g = g.sort_values("date")
        o, h, l, c = (g[x].to_numpy(float) for x in ("open", "high", "low", "close"))
        if len(c) < horizon + 5:
            continue
        out, ret = first_passage(o, h, l, c, target=target, stop=stop, horizon=horizon)
        keep = out > 0
        if mask is not None:
            m = mask.get(tkr)
            if m is None:
                continue
            keep &= m[:len(out)] if len(m) >= len(out) else np.pad(m, (0, len(out) - len(m)))
        if not keep.any():
            continue
        rows.append(pd.DataFrame({"ticker": tkr, "outcome": out[keep], "ret": ret[keep]}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["ticker", "outcome", "ret"])


def summarise(df: pd.DataFrame, *, target: float, stop: float,
              cost: float = COST_ROUND_TRIP, n_boot: int = N_BOOT) -> dict:
    """Hit rate + net expectancy with a CLUSTER bootstrap on ticker."""
    if df.empty:
        return {}
    n = len(df)
    win = (df["outcome"] == WIN).to_numpy()
    loss = (df["outcome"] == LOSS).to_numpy()
    to = (df["outcome"] == TIMEOUT).to_numpy()
    resolved = win | loss
    theo = stop / (target + stop)

    net = df["ret"].to_numpy() - cost
    rng = np.random.default_rng(SEED)
    tickers = df["ticker"].to_numpy()
    uniq = np.unique(tickers)
    groups = {t: np.flatnonzero(tickers == t) for t in uniq}
    hit_b, ev_b = np.empty(n_boot), np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([groups[t] for t in pick])
        r = resolved[sel]
        hit_b[b] = win[sel][r].mean() if r.any() else np.nan
        ev_b[b] = net[sel].mean()
    return {
        "n": int(n), "n_tickers": int(len(uniq)),
        "hit_rate_resolved": round(float(win[resolved].mean()), 4) if resolved.any() else None,
        "hit_ci": [round(float(np.nanpercentile(hit_b, 2.5)), 4),
                   round(float(np.nanpercentile(hit_b, 97.5)), 4)],
        "theoretical": round(theo, 4), "breakeven": round(theo, 4),
        "win_share": round(float(win.mean()), 4),
        "loss_share": round(float(loss.mean()), 4),
        "timeout_share": round(float(to.mean()), 4),
        "gross_ev_pct": round(float(df["ret"].mean()) * 100, 4),
        "net_ev_pct": round(float(net.mean()) * 100, 4),
        "net_ev_ci_pct": [round(float(np.percentile(ev_b, 2.5)) * 100, 4),
                          round(float(np.percentile(ev_b, 97.5)) * 100, 4)],
        "mean_loss_pct": round(float(df["ret"][loss].mean()) * 100, 3) if loss.any() else None,
        "overshoot_frac": (round(float((df["ret"][loss] < -stop * 1.005).mean()), 4)
                           if loss.any() else None),
        "worst_loss_pct": round(float(df["ret"][loss].min()) * 100, 2) if loss.any() else None,
    }


def main() -> int:
    print("=== FIRST-PASSAGE BASE RATES — is any barrier pair an edge? ===\n")
    ohlcv, membership = corrected_universe(), load_membership()
    panel = build_panel(ohlcv, membership)
    print(f"  panel {len(panel):,} rows · {panel['ticker'].nunique()} names · "
          f"{panel['date'].min().date()} -> {panel['date'].max().date()}\n")

    # ── 1. the proposal, unconditional ──────────────────────────────────────
    print(f"=== 1. THE PROPOSAL: +{TARGET:.0%} target / −{STOP:.0%} stop / {HORIZON}d cap ===")
    base = scan(panel, target=TARGET, stop=STOP, horizon=HORIZON)
    s = summarise(base, target=TARGET, stop=STOP)
    print(f"  observations {s['n']:,} over {s['n_tickers']} names")
    print(f"  outcome mix : win {s['win_share']:.1%} · loss {s['loss_share']:.1%} · "
          f"TIMEOUT {s['timeout_share']:.1%}")
    print(f"  hit rate (of resolved) {s['hit_rate_resolved']:.2%}  CI {s['hit_ci']}")
    print(f"  THEORY / BREAKEVEN     {s['theoretical']:.2%}")
    print(f"  gross EV per trade {s['gross_ev_pct']:+.3f}%   net of {COST_ROUND_TRIP:.1%} costs "
          f"{s['net_ev_pct']:+.3f}%  CI {s['net_ev_ci_pct']}")
    print(f"  loss side: mean {s['mean_loss_pct']:+.2f}% (stop is −{STOP:.0%}), "
          f"{s['overshoot_frac']:.1%} overshot, worst {s['worst_loss_pct']:+.1f}%")

    # ── 2. the surface (REPORTED, never mined) ──────────────────────────────
    print(f"\n=== 2. SURFACE at {HORIZON}d — hit rate vs a/(a+b), and NET EV per trade ===")
    print("    (a robustness map; nothing here is adopted — see the module docstring)")
    tgts, stps = (0.04, 0.06, 0.08, 0.10, 0.15), (0.03, 0.05, 0.08, 0.12)
    print("    " + "stop:".ljust(10) + "".join(f"{st:>18.0%}" for st in stps))
    surface = {}
    for tg in tgts:
        cells = []
        for st in stps:
            d = scan(panel, target=tg, stop=st, horizon=HORIZON)
            r = summarise(d, target=tg, stop=st, n_boot=400)
            surface[f"t{tg}_s{st}"] = r
            cells.append(f"{r['hit_rate_resolved']:>7.1%}/{r['theoretical']:.0%}"
                         f"{r['net_ev_pct']:>+7.2f}%")
        print(f"    tgt {tg:>4.0%} " + "".join(f"{c:>18}" for c in cells))
    print("    cell = actual hit / theoretical hit , then NET EV per trade")

    print(f"\n=== 3. HORIZON SWEEP at +{TARGET:.0%}/−{STOP:.0%} ===")
    for hz in (10, 15, 30, 63):
        d = scan(panel, target=TARGET, stop=STOP, horizon=hz)
        r = summarise(d, target=TARGET, stop=STOP, n_boot=400)
        surface[f"h{hz}"] = r
        print(f"    {hz:>3}d  hit {r['hit_rate_resolved']:.2%} (theory {r['theoretical']:.2%})  "
              f"timeout {r['timeout_share']:.1%}  net EV {r['net_ev_pct']:+.3f}%")

    # ── 4. conditional on OUR signals — is selection the problem? ───────────
    print("\n=== 4. CONDITIONAL — does our selection lift the base rate? ===")
    cond = {}
    mom = {}
    for tkr, g in panel.groupby("ticker", sort=True):
        c = g.sort_values("date")["close"].to_numpy(float)
        r63 = np.full(len(c), np.nan)
        if len(c) > 63:
            r63[63:] = c[63:] / c[:-63] - 1.0
        mom[tkr] = r63
    allmom = np.concatenate([v[np.isfinite(v)] for v in mom.values()])
    q = np.nanpercentile(allmom, [10, 90])
    for name, mk in (("momentum top decile (63d)", {t: v >= q[1] for t, v in mom.items()}),
                     ("momentum bottom decile", {t: v <= q[0] for t, v in mom.items()})):
        d = scan(panel, target=TARGET, stop=STOP, horizon=HORIZON, mask=mk)
        r = summarise(d, target=TARGET, stop=STOP, n_boot=600)
        cond[name] = r
        print(f"  {name:<28} n {r['n']:>8,}  hit {r['hit_rate_resolved']:.2%} "
              f"CI {r['hit_ci']}  net EV {r['net_ev_pct']:+.3f}%")

    weekly = None
    try:
        from nq.data.weekly import build_weekly_panel
        weekly = build_weekly_panel({t: ohlcv[t] for t in panel["ticker"].unique() if t in ohlcv})
        sig = candidate_signals(ohlcv, panel, weekly)
        by = {t: set(pd.DatetimeIndex(g["date"]).normalize()) for t, g in sig.groupby("ticker")}
        mk = {}
        for tkr, g in panel.groupby("ticker", sort=True):
            dts = pd.DatetimeIndex(g.sort_values("date")["date"]).normalize()
            mk[tkr] = np.array([d in by.get(tkr, ()) for d in dts])
        d = scan(panel, target=TARGET, stop=STOP, horizon=HORIZON, mask=mk)
        r = summarise(d, target=TARGET, stop=STOP, n_boot=600)
        cond["validated candidate signal"] = r
        print(f"  {'validated candidate signal':<28} n {r['n']:>8,}  "
              f"hit {r['hit_rate_resolved']:.2%} CI {r['hit_ci']}  net EV {r['net_ev_pct']:+.3f}%")
    except Exception as e:                                   # noqa: BLE001
        print(f"  (candidate-signal cell skipped: {type(e).__name__}: {e})")

    print(f"\n  BAR: to reach 40% CAGR this book needs a 34-37% hit rate. "
          f"No-skill is {STOP/(TARGET+STOP):.2%}.")
    out = ROOT / "diagnostics" / "research" / "barrier_base_rate.json"
    out.write_text(json.dumps({"proposal": s, "surface": surface, "conditional": cond},
                              indent=2, default=str))
    print(f"  -> {out}")
    print("  standing counts: screens 19 · sealed opens 1 · n_trials 138 (measurement, unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
