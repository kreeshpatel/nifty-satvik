"""Track P2 — is the position-weighting axis resolvable at all on a five-name weekly book?

SPEC: `diagnostics/research/estimation_bound/SPEC.md`, committed before this file existed. Every
constant, constraint and reading rule below is copied from it, not chosen here.

The study re-splits the same money between the same names on the same days. Seats, entries and exits
are untouched, and each scheme is held to the engine's own exposure, so nothing here can answer a
question about leverage or cash — that is 0095's axis and it is already killed on this book.

Reproduce: `python pipelines/diagnostics/diag_estimation_bound.py --run-date YYYY-MM-DD`
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from nq.brain import estimation as EST  # noqa: E402
from nq.brain import io as BIO  # noqa: E402

# ── copied from SPEC.md ─────────────────────────────────────────────────────────────────────────────
HIST_START, HIST_END = "2019-01-01", "2024-06-30"      # ends before the sealed slice
CORR_WINDOW = 63
NAV_MEDIAN_TOL, NAV_MAX_TOL = 0.005, 0.030             # the reconstruction gate, fixed before the run
MIN_NAMES = 2                                          # a weighting question needs at least two names
SCHEMES = ("actual", "equal_notional", "inverse_vol", "min_variance",
           "max_sharpe_plugin", "max_sharpe_clairvoyant", "max_return_clairvoyant")
# Only the scheme the SPEC froze may set the ceiling. `max_return_clairvoyant` was added while
# coding and is reported for contrast only — an addition made after the fact must not be eligible to
# loosen a gate in the pass direction.
CLAIRVOYANT = {"max_sharpe_clairvoyant"}
NOT_PRE_REGISTERED = {"max_return_clairvoyant"}

OUT_BASE = ROOT / "diagnostics" / "research" / "estimation_bound"


# ────────────────────────────────────────────────────────────────────────── population A
def build_population() -> dict:
    """Population A — the live configuration, 2019-01-01..2024-06-30, exactly as 0142 built it."""
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_sixstep import RISK, _cost_leg
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe
    from diag_excursions_null import demerger_dates
    import diag_portfolio_risk as P1

    ohlcv = corrected_universe()
    cut = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(HIST_END)] for t, df in ohlcv.items()}
    cut = {t: df for t, df in cut.items() if len(df) > 60}
    P = R94.prep_weekly_rank(cut, **LIVE_PREP)
    events = R94.build_demerger_events(cut, load_demerger_rows(), **LIVE_PREP)
    led: list = []
    plog: list = []
    # The corporate-action HOLD is OFF, as in 0142 §A1 and for its stated reason: with no owner to
    # resolve a frozen position in a 5.5-year reconstruction it never resolves.
    out = R94.backtest(P, None, ledger=led, start=HIST_START, return_state=True,
                       a_grade=R94.grade_a_entries(P), **LIVE_DISCIPLINE, **LIVE_EXIT,
                       **LIVE_STALENESS, demerger_events=events, position_log=plog)
    ledger = pd.DataFrame(led)
    curve = pd.Series(out["curve"], dtype=float)
    curve.index = pd.DatetimeIndex(curve.index).normalize()
    curve = curve[~curve.index.duplicated(keep="last")].sort_index()

    BIO.assert_unsealed(pd.to_datetime(ledger["entry_date"]))

    # The log carries names the TRADE ledger cannot: a position still open at the window end never
    # closed, so it has no ledger row, yet it occupied a seat and a slice of the book every session.
    names = sorted(set(ledger["tkr"].unique()) | {r["tkr"] for r in plog})
    closes = pd.DataFrame({t: pd.Series(np.asarray(P[t]["c"], dtype=float),
                                        index=pd.DatetimeIndex(P[t]["dates"]).normalize())
                           for t in names if t in P}).sort_index()
    closes = closes[~closes.index.duplicated(keep="last")].reindex(curve.index)
    adv = {t: float(np.nanmedian(np.asarray(P[t]["adv20"], dtype=float))) for t in names if t in P}
    dem = demerger_dates()
    rets = P1._returns_panel({t: df for t, df in cut.items() if t in names}, dem)
    rets = rets.reindex(curve.index)

    # Control universe: the 30 highest-turnover names in the SAME universe, through the SAME filters.
    liq = {}
    for tk, df in cut.items():
        if df is None or len(df) < 300 or "Volume" not in df:
            continue
        v = (df["Close"].to_numpy(float) * df["Volume"].to_numpy(float))
        liq[tk] = float(np.nanmedian(v)) if len(v) else float("nan")
    top = [tk for tk, _ in sorted(liq.items(), key=lambda kv: -(kv[1] if kv[1] == kv[1] else -1))[:30]]
    control_rets = P1._returns_panel({tk: cut[tk] for tk in top}, dem).reindex(curve.index)

    positions = pd.DataFrame(plog)
    positions["date"] = pd.DatetimeIndex(positions["date"]).normalize()

    # A held name that printed no bar this session must be marked at its LAST TRADED price, as the
    # engine marks it. Leaving the raw NaN and summing with fillna(0) marks it to ZERO, which drives
    # any replayed book to a -100% drawdown — the defect that made the first run of legs 2-3 garbage.
    marks = closes.ffill()
    # ...and where the engine HELD a name it recorded the exact price it marked at, including the
    # B-1 absent-bar mark. Using the engine's own mark means notional / mark == the engine's share
    # count, so replaying the engine's own weights produces no trade and therefore no phantom cost.
    engine_marks = positions.pivot_table(index="date", columns="tkr", values="mark_px", aggfunc="last")
    marks = marks.combine_first(engine_marks.reindex(index=marks.index, columns=marks.columns))
    marks.update(engine_marks.reindex(index=marks.index, columns=marks.columns))

    return {"curve": curve, "ledger": ledger, "positions": positions, "marks": marks, "closes": closes, "rets": rets, "adv": adv,
            "control_rets": control_rets,
            "cap_notional": LIVE_DISCIPLINE["max_notional_pct"], "risk": RISK,
            "cost_leg": _cost_leg, "eq0": float(curve.iloc[0])}


# ────────────────────────────────────────────────────────────────── the weight reconstruction
def positions_from_log(pop: dict) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Daily notional per name, straight from the engine's own position ledger.

    Added after the ledger-only rebuild below failed its pre-registered gate by 34% of NAV. This is
    not a reconstruction: it is what the engine held, recorded as it held it.
    """
    pos = pop["positions"]
    notional = (pos.pivot_table(index="date", columns="tkr", values="notional", aggfunc="sum")
                .reindex(pop["curve"].index).fillna(0.0))
    book = pos.groupby("date")[["cash", "equity"]].first().reindex(pop["curve"].index)
    return notional, book["cash"].ffill().fillna(pop["eq0"]), book["equity"].ffill().fillna(pop["eq0"])


def reconcile_log(pop: dict, notional: pd.DataFrame, cash: pd.Series, equity: pd.Series) -> dict:
    """The SPEC's gate, now applied to the engine log: cash + Σ notional must be the engine's NAV."""
    rebuilt = cash + notional.sum(axis=1)
    rel = (rebuilt / equity - 1.0).abs().replace([np.inf, -np.inf], np.nan).dropna()
    curve_rel = (equity / pop["curve"] - 1.0).abs().dropna()
    out = {
        "source": "engine position_log (scripts/run_bhanushali_weekly_rank.py)",
        "median_abs_rel_error": round(float(rel.median()), 9),
        "max_abs_rel_error": round(float(rel.max()), 9),
        "log_equity_vs_curve_max_abs_rel_error": round(float(curve_rel.max()), 9),
        "tolerance": {"median": NAV_MEDIAN_TOL, "max": NAV_MAX_TOL},
        "n_sessions": int(len(rel)),
    }
    out["passed"] = bool(rel.median() <= NAV_MEDIAN_TOL and rel.max() <= NAV_MAX_TOL
                         and curve_rel.max() <= NAV_MAX_TOL)
    return out


def reconstruct(pop: dict) -> tuple[pd.DataFrame, dict]:
    """Daily notional per held name, from the engine's own sizing rule.

    `shares = sizing_equity × 2% ÷ (entry − stop)`, capped at `max_notional_pct` of sizing equity, and
    the sizing equity on day d is the NAV marked at the close of d−1 — which is what the engine uses,
    not a choice made here.
    """
    curve, ledger, closes = pop["curve"], pop["ledger"], pop["closes"]
    sessions = curve.index
    prev_eq = curve.shift(1)
    notional = pd.DataFrame(0.0, index=sessions, columns=list(closes.columns))
    flows: list[dict] = []          # every cash movement, so NAV can be rebuilt exactly
    holes: list[str] = []

    for t in ledger.itertuples(index=False):
        tkr = t.tkr
        if tkr not in closes.columns:
            holes.append(f"{tkr}: no price column")
            continue
        d0 = pd.Timestamp(t.entry_date).normalize()
        d1 = pd.Timestamp(t.exit_date).normalize()
        en, st = float(t.entry), float(t.stop0)
        eq = float(prev_eq.get(d0, np.nan))
        if not np.isfinite(eq) or en <= st or en <= 0:
            holes.append(f"{tkr} {d0.date()}: no sizing equity or non-positive risk")
            continue
        sh = eq * pop["risk"] / (en - st)
        sh = min(sh, eq * pop["cap_notional"] / en)
        a = pop["adv"].get(tkr, float("nan"))
        gross = sh * en
        flows.append({"date": d0, "cash": -gross * (1 + pop["cost_leg"](a, gross))})

        span = sessions[(sessions >= d0) & (sessions <= d1)]
        held = pd.Series(sh, index=span, dtype=float)
        half_date = getattr(t, "half_date", None)
        if half_date is not None and pd.notna(half_date):
            hd = pd.Timestamp(half_date).normalize()
            held[held.index >= hd] = sh * 0.5
            hp = float(t.half_px) * sh * 0.5
            flows.append({"date": hd, "cash": hp * (1 - pop["cost_leg"](a, hp))})
        px = closes[tkr].reindex(span)
        notional.loc[span, tkr] += (held * px).fillna(0.0)
        # the exit fills at the exit price and the position leaves the book that day
        xp = float(t.exit_px) * float(held.iloc[-1])
        flows.append({"date": d1, "cash": xp * (1 - pop["cost_leg"](a, xp))})
        notional.loc[d1, tkr] -= float(held.iloc[-1]) * float(px.iloc[-1]) if np.isfinite(px.iloc[-1]) else 0.0

    cash_flow = (pd.DataFrame(flows).groupby("date")["cash"].sum()
                 .reindex(sessions).fillna(0.0)) if flows else pd.Series(0.0, index=sessions)
    return notional, {"cash_flow": cash_flow, "holes": holes}


def validate_reconstruction(pop: dict, notional: pd.DataFrame, meta: dict) -> dict:
    """The gate the SPEC set before the run: the rebuilt NAV must track the engine's own curve."""
    nav = pop["eq0"] + meta["cash_flow"].cumsum() + notional.sum(axis=1)
    rel = (nav / pop["curve"] - 1.0).abs()
    rel = rel[np.isfinite(rel)]
    invested = (notional.sum(axis=1) / pop["curve"])
    verdict = {
        "median_abs_rel_error": round(float(rel.median()), 6),
        "max_abs_rel_error": round(float(rel.max()), 6),
        "tolerance": {"median": NAV_MEDIAN_TOL, "max": NAV_MAX_TOL},
        "n_sessions": int(len(rel)),
        "holes": meta["holes"][:20],
        "n_holes": len(meta["holes"]),
        # a long-only book funded by cash cannot be more than fully invested; if the rebuild says it
        # is, the rebuild is wrong, and by how much says where
        "reconstructed_invested_fraction": {"median": round(float(invested.median()), 4),
                                            "max": round(float(invested.max()), 4)},
    }
    verdict["passed"] = bool(rel.median() <= NAV_MEDIAN_TOL and rel.max() <= NAV_MAX_TOL)
    return verdict


def _open_at_end_census(pop: dict) -> dict:
    """Positions the TRADE ledger never had: open at the window end, so never closed, so never logged.

    They still occupied a seat and a slice of the book every session, so a ledger-based rebuild of the
    book omits them entirely — cash never debited, NAV too high. Measured, because the tranche story
    alone would take credit for error this also produces.
    """
    pos, led = pop["positions"], pop["ledger"]
    logged = set(pos["tkr"].unique())
    closed = set(led["tkr"].unique())
    missing = sorted(logged - closed)
    if not missing:
        return {"names": [], "held_name_days": 0}
    sub = pos[pos["tkr"].isin(missing)]
    total_by_day = pos.groupby("date")["notional"].sum()
    miss_by_day = sub.groupby("date")["notional"].sum().reindex(total_by_day.index).fillna(0.0)
    share = (miss_by_day / total_by_day).replace([np.inf, -np.inf], np.nan).dropna()
    late = share[share.index >= pd.Timestamp("2023-01-01")]
    return {"names": missing, "n_names": len(missing), "held_name_days": int(len(sub)),
            "share_of_notional_overall_median": round(float(share.median()), 4),
            "share_of_notional_from_2023_median": round(float(late.median()), 4) if len(late) else None}


def diagnose_reconstruction(pop: dict, notional: pd.DataFrame, meta: dict) -> dict:
    """Why it failed, measured rather than asserted.

    The live exit is config P's SCALED exit — 60% of the position at +2R, 20% at +3R, the rest running
    to an SMA break. The ledger records one `half_date`/`half_px` and the final exit, so from the
    ledger alone a position's share count after its first tranche is unknown. The claim is testable:
    the rebuild should track the engine until the first tranche fires and drift afterwards, and the
    drift should be upward, because unrecorded sales leave shares on the books that were in fact sold.
    """
    led = pop["ledger"]
    nav = pop["eq0"] + meta["cash_flow"].cumsum() + notional.sum(axis=1)
    err = (nav / pop["curve"] - 1.0)
    reasons = led["reason"].value_counts().to_dict()
    # reasons that can only be reached through the tranche ladder
    tranche_reasons = {"targets", "target3", "stop_part", "pattern", "blowoff_half", "wk20_half",
                       "stop_half"}
    tranche_rows = led[led["reason"].isin(tranche_reasons)]
    first_tranche = (pd.to_datetime(led["half_date"]).min() if led["half_date"].notna().any()
                     else pd.NaT)
    before = err[err.index < first_tranche] if pd.notna(first_tranche) else err.iloc[:0]
    after = err[err.index >= first_tranche] if pd.notna(first_tranche) else err
    return {
        "cause": ("the ledger records at most ONE half-exit per trade, and the live exit sells in "
                  "more than one tranche. Config P (run_bhanushali_cron.P_EXIT, read not remembered): "
                  "tp1_frac 0.40 at +2R, tp2_frac 0.0 at +3R (so nothing sells at +3R), pattern_frac "
                  "0.40 armed at +2.5R, and a 20% runner to the SMA break. The ledger's half_px/"
                  "half_date cannot express which tranche fired, let alone two"),
        "exit_reason_mix": reasons,
        "trades_with_a_tranche_reason": int(len(tranche_rows)),
        "trades_total": int(len(led)),
        "first_recorded_half_exit": str(first_tranche.date()) if pd.notna(first_tranche) else None,
        "median_abs_error_before_first_tranche": (round(float(before.abs().median()), 6)
                                                  if len(before) else None),
        "median_abs_error_after": round(float(after.abs().median()), 6) if len(after) else None,
        "error_is_upward_share": round(float((after > 0).mean()), 4) if len(after) else None,
        # A SECOND, INDEPENDENT CAUSE, disclosed because the "error is upward" evidence above does
        # NOT discriminate between them — both leave shares on the books that are not really there.
        "second_cause_open_at_window_end": _open_at_end_census(pop),
        "remedy": ("the engine's own daily position ledger (added 2026-09-25, commit 881a5ec, "
                   "off by default). Note the earlier wording 'unrecoverable without an engine "
                   "change' was too strong: tranche SIZES are algebra on the committed config, and "
                   "it is the tranche DATES that the ledger does not pin down."),
    }


# ────────────────────────────────────────────────────────────────────────── the schemes
def held_frame(ledger: pd.DataFrame, sessions: pd.DatetimeIndex, names: list[str]) -> pd.DataFrame:
    """Who was held on each session — from entry and exit dates only.

    This needs no share count, which is why leg 1 survives a failed weight reconstruction.
    """
    held = pd.DataFrame(False, index=sessions, columns=names)
    for t in ledger.itertuples(index=False):
        if t.tkr not in held.columns:
            continue
        a, b = pd.Timestamp(t.entry_date).normalize(), pd.Timestamp(t.exit_date).normalize()
        held.loc[(sessions >= a) & (sessions <= b), t.tkr] = True
    return held


def rebalance_sessions(held: pd.DataFrame) -> list[pd.Timestamp]:
    """The engine's own trading days: every session on which the held set changes.

    Rebalancing only when the engine itself trades creates no turnover the book did not already have,
    which is the conservative reading of the SPEC's weekly rebalance.
    """
    changed = held.ne(held.shift(1)).any(axis=1)
    changed.iloc[0] = True
    return list(changed.index[changed])


def _weights(scheme: str, names: list[str], d: pd.Timestamp, rets: pd.DataFrame,
             closes: pd.DataFrame, nxt: pd.Timestamp | None, cap: float,
             actual: np.ndarray) -> tuple[np.ndarray, dict]:
    n = len(names)
    diag: dict = {}
    if scheme == "actual":
        return actual, diag
    if scheme == "equal_notional":
        return EST._apply_cap(EST.equal_weights(n), cap), diag

    win = rets.loc[:d, names].iloc[-CORR_WINDOW:].dropna(axis=1, how="all")
    win = win.reindex(columns=names).dropna(axis=0, how="any")
    vols = win.std(ddof=1).to_numpy(float)
    if scheme == "inverse_vol":
        return EST.inverse_vol_weights(vols, cap), diag

    x = win.to_numpy(float)
    if len(x) >= 10:
        delta, cov = EST.ledoit_wolf_shrinkage(x)
    else:                                   # too little history to shrink: fall back to the sample
        delta, cov = float("nan"), np.cov(x, rowvar=False) if len(x) > 1 else np.eye(n) * 1e-6
    diag["lw_delta"] = delta
    cov = np.atleast_2d(cov)

    if scheme == "min_variance":
        return EST.min_variance_weights(cov, cap), diag
    if scheme == "max_sharpe_plugin":
        return EST.max_sharpe_weights(win.mean().to_numpy(float), cov, cap), diag

    # clairvoyant: perfect foresight of the NEXT holding period's return, honest risk model
    if nxt is None:
        return actual, diag
    fwd = (closes.loc[nxt, names].to_numpy(float) / closes.loc[d, names].to_numpy(float)) - 1.0
    fwd = np.nan_to_num(fwd)
    if scheme == "max_return_clairvoyant":
        return EST.max_return_weights(fwd, cap), diag
    return EST.max_sharpe_weights(fwd, cov, cap), diag


def run_scheme(scheme: str, pop: dict, notional: pd.DataFrame,
               rebal: list[pd.Timestamp], costs: bool = True) -> tuple[pd.Series, dict]:
    """Re-split the same money between the same names, at the engine's own exposure."""
    curve, closes, rets = pop["curve"], pop["marks"], pop["rets"]
    sessions = curve.index
    invested = notional.sum(axis=1)
    exposure = (invested / curve).clip(0.0, 1.0)     # the engine's own invested fraction of NAV
    rebal_set = set(rebal)
    nxt_of = {d: (rebal[i + 1] if i + 1 < len(rebal) else None) for i, d in enumerate(rebal)}

    cash = pop["eq0"]
    shares = pd.Series(0.0, index=closes.columns, dtype=float)
    nav_path, deltas, turnover = [], [], 0.0
    for d in sessions:
        px = closes.loc[d]
        mark = float((shares * px).fillna(0.0).sum())
        nav = cash + mark
        if d in rebal_set:
            names = [t for t in notional.columns if notional.at[d, t] > 0 and np.isfinite(px.get(t, np.nan))]
            target = pd.Series(0.0, index=closes.columns, dtype=float)
            if len(names) >= 1:
                actual_w = notional.loc[d, names].to_numpy(float)
                actual_w = actual_w / actual_w.sum()
                cap = float(min(1.0, max(pop["cap_notional"] * nav / max(invested.get(d, np.nan), 1e-9),
                                         1.0 / len(names))))
                if len(names) >= MIN_NAMES:
                    w, diag = _weights(scheme, names, d, rets, closes, nxt_of.get(d), cap, actual_w)
                    if diag.get("lw_delta") == diag.get("lw_delta") and "lw_delta" in diag:
                        deltas.append(diag["lw_delta"])
                else:
                    w = actual_w
                total = float(exposure.get(d, 0.0)) * nav
                target[names] = w * total / px[names].to_numpy(float)
            unusable = ~np.isfinite(px.reindex(target.index).to_numpy(float))
            target[unusable] = shares[unusable]          # cannot trade what has no price
            trade = (target - shares).fillna(0.0)
            for t, dsh in trade[trade != 0].items():
                value = abs(float(dsh) * float(px[t]))
                if not np.isfinite(value) or value <= 0:
                    continue
                cost = value * pop["cost_leg"](pop["adv"].get(t, float("nan")), value) if costs else 0.0
                cash -= float(dsh) * float(px[t]) + cost
                turnover += value
            shares = target
            nav = cash + float((shares * px).fillna(0.0).sum())
        nav_path.append(nav)

    nav_s = pd.Series(nav_path, index=sessions, dtype=float)
    daily = nav_s.pct_change().dropna()
    stats = {
        "sharpe": round(EST.sharpe(daily.to_numpy(float)), 4),
        "cagr_pct": round(float((nav_s.iloc[-1] / nav_s.iloc[0]) ** (252 / len(nav_s)) - 1) * 100, 2),
        "max_dd_pct": round(float((nav_s / nav_s.cummax() - 1).min()) * 100, 2),
        # against the RUNNING book, not the opening ₹1M: on a book that compounds 6x, normalising by
        # eq0 turns ordinary churn into five-figure nonsense (red-team read, 2026-09-25).
        "turnover_x_book": round(turnover / float(nav_s.mean()), 1),
        "mean_lw_delta": round(float(np.mean(deltas)), 4) if deltas else None,
    }
    return nav_s, stats


# ────────────────────────────────────────────────────────── leg 1: how much is estimable
def estimability(pop: dict, held: pd.DataFrame, rebal: list[pd.Timestamp],
                 window: int = CORR_WINDOW) -> dict:
    rets = pop["rets"]
    rows = []
    for d in rebal:
        names = [t for t in held.columns if held.at[d, t]]
        if len(names) < MIN_NAMES:
            continue
        win = rets.loc[:d, names].iloc[-window:].dropna(axis=1, thresh=window // 2)
        # COMPLETE CASES ONLY. Padding a missing session with 0.0 is not a missing observation, it is
        # a fabricated one: it pulls correlations toward zero and would inflate the very shrinkage
        # number this leg reports.
        win = win.dropna(axis=0, how="any")
        if win.shape[1] < MIN_NAMES or len(win) < window // 2:
            continue
        x = win.to_numpy(float)
        q = win.shape[1] / len(win)
        corr = np.corrcoef(x, rowvar=False)
        delta, _ = EST.ledoit_wolf_shrinkage(x)
        lo, hi = EST.marchenko_pastur_edges(q)
        eig = np.linalg.eigvalsh(corr)
        rows.append({"date": d, "n_names": win.shape[1], "q": q,
                     "mp_noise_share": EST.mp_noise_share(corr, q), "lw_delta": delta,
                     # 1 - noise_share is NOT signal: an eigenvalue can also be pushed BELOW the bulk,
                     # which the fixed trace forces and which exploits nothing. Only modes ABOVE the
                     # upper edge are structure a weighting scheme could act on, so they are reported
                     # separately (red-team read, 2026-09-25).
                     "eig_above_upper_edge": float(np.mean(eig > hi)),
                     "eig_below_lower_edge": float(np.mean(eig < lo))})
    df = pd.DataFrame(rows)

    # how long a pair is actually held together, against the 63 sessions its correlation is read from
    overlaps = []
    cols = list(held.columns)
    for i, a in enumerate(cols):
        ha = held[a]
        if not ha.any():
            continue
        for b in cols[i + 1:]:
            n = int((ha & held[b]).sum())
            if n > 0:
                overlaps.append(n)
    ov = pd.Series(overlaps, dtype=float)

    def cell(s: pd.Series) -> dict:
        return {"n": int(s.notna().sum()), "median": round(float(s.median()), 4),
                "mean": round(float(s.mean()), 4), "p10": round(float(s.quantile(0.10)), 4),
                "p90": round(float(s.quantile(0.90)), 4)}

    return {
        "window_sessions": window,
        "rebalances_measured": int(len(df)),
        "n_names": cell(df["n_names"]) if len(df) else None,
        "q_shape_ratio": cell(df["q"]) if len(df) else None,
        "mp_noise_share": cell(df["mp_noise_share"]) if len(df) else None,
        "eig_above_upper_edge": cell(df["eig_above_upper_edge"]) if len(df) else None,
        "eig_below_lower_edge": cell(df["eig_below_lower_edge"]) if len(df) else None,
        "lw_shrinkage_delta": cell(df["lw_delta"]) if len(df) else None,
        "pair_joint_holding_sessions": (cell(ov) | {"corr_window": CORR_WINDOW,
                                                    "share_under_window": round(float((ov < CORR_WINDOW).mean()), 4)}
                                        ) if len(ov) else None,
    }


def shrinkage_null(shapes: list[tuple[int, int]], reps: int = 30, seed: int = 20260925) -> dict:
    """What delta* does on PURE NOISE, so nobody reads it as a noise statistic. It is not one.

    delta* is (pi - rho) / (gamma * T), and gamma is the squared distance from the sample matrix to
    the CONSTANT-CORRELATION target. It goes to 1 whenever a single average correlation is nearly an
    adequate summary — on iid noise that is true at ANY sample size, so delta* is ~1.0 even at
    T = 2000, where estimation noise is negligible. Published without this row, "delta* = 0.98"
    invites exactly the wrong inference, which is the one this study originally drew.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for n, tt in shapes:
        vals = [EST.ledoit_wolf_shrinkage(rng.standard_normal((tt, n)))[0] for _ in range(reps)]
        out[f"iid_noise_N{n}_T{tt}"] = round(float(np.median(vals)), 4)
    return out


def estimability_control(pop: dict, rebal: list[pd.Timestamp], window: int,
                         n_names: int = 8, reps: int = 20, seed: int = 20260925) -> dict:
    """The same statistics on a matched set of LIQUID names — the control the SPEC forgot to ask for.

    Without it, "delta* is 0.98 on this book" has no scale: it could be a property of the estimator on
    any 8 Indian equities, of the outlier filter, or of small-cap staleness. Same rebalance dates,
    same returns panel and the same filters; only the names change.
    """
    rets = pop["control_rets"]
    cols = [c for c in rets.columns]
    if len(cols) < n_names:
        return {"n_names_available": len(cols)}
    rng = np.random.default_rng(seed)
    deltas, noise, above = [], [], []
    for _ in range(reps):
        names = list(rng.choice(cols, size=n_names, replace=False))
        d_rep, n_rep, a_rep = [], [], []
        for d in rebal:
            win = rets.loc[:d, names].iloc[-window:].dropna(axis=0, how="any")
            if len(win) < window // 2:
                continue
            x = win.to_numpy(float)
            q = win.shape[1] / len(win)
            corr = np.corrcoef(x, rowvar=False)
            d_rep.append(EST.ledoit_wolf_shrinkage(x)[0])
            n_rep.append(EST.mp_noise_share(corr, q))
            a_rep.append(float(np.mean(np.linalg.eigvalsh(corr) > EST.marchenko_pastur_edges(q)[1])))
        if d_rep:
            deltas.append(np.median(d_rep)); noise.append(np.median(n_rep)); above.append(np.median(a_rep))

    def cell(v):
        return {"mean_of_rep_medians": round(float(np.mean(v)), 4), "sd": round(float(np.std(v, ddof=1)), 4)}
    return {"n_liquid_names": len(cols), "reps": reps, "names_per_rep": n_names,
            "lw_shrinkage_delta": cell(deltas), "mp_noise_share": cell(noise),
            "eig_above_upper_edge": cell(above)}


# ────────────────────────────────────────────────────────────────────────── main
def per_year_sharpe(nav: pd.Series) -> dict[str, float]:
    out = {}
    for yr, g in nav.groupby(nav.index.year):
        if len(g) > 30:
            out[str(yr)] = round(EST.sharpe(g.pct_change().dropna().to_numpy(float)), 3)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-date", default=str(date.today()))
    args = ap.parse_args(argv)

    counts = json.loads((ROOT / "diagnostics" / "research" / "n_trials.json").read_text(encoding="utf-8"))
    pop = build_population()
    notional, log_cash, log_equity = positions_from_log(pop)
    recon = reconcile_log(pop, notional, log_cash, log_equity)

    # The ledger-only rebuild is kept as an EXHIBIT, not as a fallback: it is the measurement that
    # established the engine could not answer a portfolio-level question about itself, and it is the
    # justification of record for the owner-authorised position_log change on 2026-09-25.
    rec_notional, rec_meta = reconstruct(pop)
    exhibit = validate_reconstruction(pop, rec_notional, rec_meta)
    exhibit["diagnosis"] = diagnose_reconstruction(pop, rec_notional, rec_meta)

    summary: dict = {
        "spec": "diagnostics/research/estimation_bound/SPEC.md",
        "class": "MEASUREMENT — zero trials, no screen row, nothing adopted",
        "run_date": args.run_date,
        "window": f"{HIST_START}..{HIST_END}",
        "n_trials_at_run": counts["cumulative_n_trials"],
        "constants": {"corr_window": CORR_WINDOW, "schemes": list(SCHEMES),
                      "dsharpe_half_width": EST.DSHARPE_HALF_WIDTH,
                      "nav_tolerance": {"median": NAV_MEDIAN_TOL, "max": NAV_MAX_TOL}},
        "n_trades": int(len(pop["ledger"])),
        "position_source": recon,
        "ledger_only_rebuild_exhibit": exhibit,
    }

    # Leg 1 needs the held SET and the price panel only — no share counts — so it is computed whether
    # or not the weight reconstruction passed its gate.
    held = (notional > 0)
    rebal = rebalance_sessions(held)
    summary["rebalances"] = len(rebal)
    summary["estimability"] = estimability(pop, held, rebal)
    # Sensitivity of an ESTIMATOR to sample length, not a sweep: nothing is selected on an outcome,
    # and it answers the question leg 1 provokes — would simply looking back further fix this?
    summary["estimability_by_window"] = {str(w): estimability(pop, held, rebal, window=w)
                                         for w in (63, 126, 252)}
    summary["matched_liquid_control"] = {str(w): estimability_control(pop, rebal, window=w)
                                        for w in (63, 126, 252)}
    summary["shrinkage_null"] = shrinkage_null([(8, 63), (8, 252), (8, 2000)])

    if not recon["passed"]:
        # The SPEC's instruction, unchanged: do not proceed with an approximated book and do not
        # widen the tolerance. With the engine log as the source this should be unreachable — if it
        # fires, the engine's own ledger disagrees with its own NAV, which is a defect, not a limit.
        summary["result"] = ("POSITION SOURCE FAILED RECONCILIATION — legs 2 and 3 are BLOCKED. The "
                             "engine's position log does not add up to the equity it reports.")
        summary["schemes"] = "BLOCKED — see position_source"
        _write(summary, args.run_date, None)
        print(json.dumps(summary["position_source"], indent=2, default=str))
        return 1

    navs, stats = {}, {}
    # THE CONTROL, AND WHAT IT IS A CONTROL FOR.
    # Re-splitting the book by the engine's OWN weights must give back the engine's book. It does not
    # give back the engine's NAV exactly, and the reason is not a mystery: the replay buys every
    # position itself and pays a full cost stack, while the engine's curve has ALREADY paid those
    # costs inside the notional the replay starts from. The charge lands twice. That is a testable
    # explanation rather than an excuse, so it is tested — with costs switched off the replay must
    # meet the pre-registered NAV tolerance. Every scheme then runs WITH costs through the same
    # machinery, so the double charge is common to all of them and cancels in a difference.
    actual_nav, actual_stats = run_scheme("actual", pop, notional, rebal)
    free_nav, _ = run_scheme("actual", pop, notional, rebal, costs=False)
    with_costs = (actual_nav / pop["curve"] - 1.0).abs().replace([np.inf, -np.inf], np.nan).dropna()
    no_costs = (free_nav / pop["curve"] - 1.0).abs().replace([np.inf, -np.inf], np.nan).dropna()
    engine_sharpe = EST.sharpe(pop["curve"].pct_change().dropna().to_numpy(float))
    summary["replay_check"] = {
        "what": ("the control must reproduce the engine's book; the NAV gap must be explained, not "
                 "tolerated. Costs off is the test of the explanation."),
        "with_costs": {"median_abs_rel_error": round(float(with_costs.median()), 6),
                       "max_abs_rel_error": round(float(with_costs.max()), 6)},
        "costs_off": {"median_abs_rel_error": round(float(no_costs.median()), 6),
                      "max_abs_rel_error": round(float(no_costs.max()), 6)},
        "tolerance": {"median": NAV_MEDIAN_TOL, "max": NAV_MAX_TOL},
        "engine_sharpe": round(float(engine_sharpe), 4),
        "control_replay_sharpe": actual_stats["sharpe"],
        "control_minus_engine_sharpe": round(float(actual_stats["sharpe"] - engine_sharpe), 4),
        "disclosed": ("the control replay sits below the engine by the double-charged cost stack. "
                      "That bias is COMMON to every scheme and cancels in ΔSharpe, which is what is "
                      "reported; no scheme is compared to the engine curve directly."),
    }
    summary["replay_check"]["explanation_holds"] = bool(
        no_costs.median() <= NAV_MEDIAN_TOL and no_costs.max() <= NAV_MAX_TOL)
    # THE EXPLANATION WAS TESTED AND IT FAILED. Switching costs off makes the gap WORSE, so the cost
    # double-charge is not the cause; what remains is that the engine fills at entry and exit PRICES
    # while a mark-to-mark replay trades at the session's mark. That difference does not go away, so
    # this check is reported as a measured limitation of the replay rather than as a gate:
    #   * the PRE-REGISTERED gate is that the engine's weights be recoverable, and the position log
    #     satisfies it exactly (0.0 error) — that gate blocks, and it passed;
    #   * this check was added DURING the run and cannot retroactively become a pass/fail criterion;
    #   * what it licenses is a comparison BETWEEN schemes inside one replay, never a comparison of
    #     any scheme to the engine's own curve. Every ΔSharpe below is within-replay.
    # It also supplies the number that decides the study: the control's own fidelity error, in Sharpe
    # units, is the floor below which this instrument cannot see a difference at all.
    summary["replay_check"]["instrument_floor_sharpe"] = abs(
        summary["replay_check"]["control_minus_engine_sharpe"])
    summary["replay_check"]["interpretation"] = (
        "A ΔSharpe smaller than the control's own deviation from the engine (0.055) is invisible to "
        "this replay, and a ΔSharpe smaller than 0.59 is invisible to this DATA. Both thresholds are "
        "reported so a reader can see which one binds.")

    for scheme in SCHEMES:
        nav, st = run_scheme(scheme, pop, notional, rebal)
        navs[scheme], stats[scheme] = nav, st
        st["per_year_sharpe"] = per_year_sharpe(nav)
    base = stats["actual"]["sharpe"]
    for scheme in SCHEMES:
        d = stats[scheme]["sharpe"] - base
        stats[scheme]["delta_sharpe_vs_actual"] = round(float(d), 4)
        stats[scheme]["resolvable"] = EST.resolvable(d)
    summary["schemes"] = stats

    ceiling = max(stats[s]["delta_sharpe_vs_actual"] for s in CLAIRVOYANT)
    best_plugin = max(stats[s]["delta_sharpe_vs_actual"] for s in SCHEMES
                      if s not in CLAIRVOYANT | NOT_PRE_REGISTERED | {"actual"})
    # LEGS 2 AND 3 ARE WITHHELD, NOT REPORTED AS A BOUND.
    # The SPEC's gate was imperative: if the daily book cannot be differenced against the engine's own
    # curve within the stated tolerance, the diagnostic stops and does not widen the tolerance. The
    # engine position log satisfies the WEIGHT half of that gate exactly, but `position_source` is an
    # identity, not a test — the log's `equity` and `curve` are the same variable written twice, so it
    # cannot fail and proves nothing about the replay. The substantive check is `replay_check`, and it
    # fails at median 2.2% / max 7.2% against 0.5% / 3.0%, with its own stated explanation falsified
    # by its own costs-off test. Publishing a ceiling on that basis would be a threshold moving after
    # the result arrived, on the one gate the SPEC wrote as an instruction.
    summary["bound"] = {
        "status": "WITHHELD — no ceiling and no plug-in ΔSharpe is established by this study",
        "why": ("the scheme replay does not reproduce the engine's own book within the pre-registered "
                "tolerance, and the shortfall is unexplained: with costs switched off it gets WORSE "
                "(3.2% vs 2.2% median), so the cost-double-charge explanation is falsified. What "
                "remains is that the engine fills at entry and exit PRICES while the replay trades at "
                "session marks. That is a design flaw in the replay, not a limit of the data."),
        "what_it_would_take": ("a new pre-registration whose replay fills at the engine's own trade "
                               "prices, with the fidelity tolerance fixed before the run and a stated "
                               "rule for a positive-but-unresolvable plug-in, which this SPEC's "
                               "reading table does not cover."),
        "half_width_for_reference": EST.DSHARPE_HALF_WIDTH,
        "withheld_numbers": {
            "clairvoyant_ceiling_delta_sharpe": round(float(ceiling), 4),
            "best_plugin_delta_sharpe": round(float(best_plugin), 4),
            "control_replay_fidelity_sharpe_error": summary["replay_check"]["instrument_floor_sharpe"],
            "NOT_A_RESULT": ("recorded for reproducibility and for whoever writes the follow-up "
                             "pre-registration. These may not be cited as a measured bound."),
        },
        "pre_registered_sign_prediction_that_FAILED": (
            "the SPEC predicted the sign of equal-notional from 0130 (notional sizing, −10.83% of "
            f"equity per year). In this replay it is +{stats['equal_notional']['delta_sharpe_vs_actual']:.3f} "
            "ΔSharpe, i.e. the opposite sign. Since the replay itself fails its fidelity check the "
            "disagreement resolves nothing either way — but a failed pre-registered prediction is "
            "recorded, not quietly dropped."),
    }
    summary["spec_deviations"] = [
        ("The 126- and 252-session windows are not in the SPEC, and its 'do not re-test unless' clause "
         "refuses 'a different lookback'. They are descriptive sensitivity of an estimator, nothing is "
         "selected on an outcome, and the direction is unflattering — but it is a deviation and it is "
         "recorded here rather than annotated in a code comment."),
        ("Leg 1's NaN handling was changed from zero-fill to complete-case AFTER a first set of numbers "
         "existed. Zero-fill pulls correlations toward zero, which makes the constant-correlation "
         "target more adequate and INFLATES δ*, so the change moved toward the less flattering option; "
         "it is disclosed because the ordering, not the direction, is what matters."),
        ("`max_return_clairvoyant` is not in the SPEC's frozen six-scheme set. It is reported for "
         "contrast and is excluded from setting the ceiling."),
        ("'Rebalance weekly on the engine's own decision day' is implemented as 'every session the held "
         "set changes' — about 20 events a year, far less than weekly, hence conservative on turnover."),
        ("The SPEC's reading table has no row for a positive-but-unresolvable plug-in ΔSharpe. Nothing "
         "is read off that gap: legs 2-3 are withheld on the fidelity gate instead."),
        ("Leg 1's window count is overlapping (consecutive windows share ~60 of 63 sessions) and the "
         "programme's floor is n_eff = 37 independent 63-day windows. The medians are descriptives; "
         "nothing inferential is hung on the count."),
    ]
    _write(summary, args.run_date, pd.DataFrame(navs))
    print(json.dumps(summary["bound"], indent=2))
    return 0


def _write(summary: dict, run_date: str, navs: pd.DataFrame | None) -> None:
    out = OUT_BASE / run_date
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    if navs is not None:
        navs.to_csv(out / "nav_by_scheme.csv.gz", compression="gzip")
    print(f"estimation bound -> {out}")


if __name__ == "__main__":
    raise SystemExit(main())
