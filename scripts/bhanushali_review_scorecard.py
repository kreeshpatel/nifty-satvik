"""Weekly-swing forward-review scorecard — the Oct-1 promote/kill machinery (Track 1).

Reads the live weekly-swing paper book's forward record and renders a one-look panel of the
PRE-COMMITTED decision gates from forward/prereg.md, so the quarterly review is mechanical and
moving-the-goalposts is structurally impossible. It ENCODES ONLY pre-registered thresholds:

  * §10.2 Path-B sleeve (fixed 2026-07-03): readiness = >=40 closed trades OR 4 quarters;
    PROMOTE if net expectancy > +0.10R AND MaxDD shallower than -25%; KILL if net Sharpe < 0.
  * §8 cadence: decisions only on the first trading day of Jan/Apr/Jul/Oct.
  * §4 halt (mechanical, universal): live MaxDD <= -50% -> halt new entries, review in 5 days.

It NEVER invents a threshold, changes the book, or makes a decision — it surfaces state. Between
reviews: log and leave it alone. Writes results/weekly_review_scorecard.json + prints the panel.

    python scripts/bhanushali_review_scorecard.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import (  # noqa: E402
    NSE_HOLIDAYS, NSE_HOLIDAYS_COVERED_THROUGH, RESULTS_DIR,
    CalendarCoverageError, assert_calendar_covers,
)

INCEPTION = date(2026, 7, 4)                 # forward-watch paper inception (forward/prereg.md)
BOOK = "weekly-swing-0094-rank"
# Pre-committed gates (forward/prereg.md — DO NOT edit here; the doc is the authority)
READY_CLOSED, READY_QUARTERS = 40, 4         # §10.2 whichever first
PROMOTE_EXPECTANCY_R, PROMOTE_MAXDD = 0.10, -0.25   # §10.2 promote (both required)
KILL_SHARPE = 0.0                            # §10.2 kill if net Sharpe < this
HALT_MAXDD = -0.50                           # §4 mechanical halt
IST = timezone(timedelta(hours=5, minutes=30))

# Pre-committed gates for the OTHER decision this book faces — forward/prereg_swing.md §4, A-only vs
# base-swing grading. Frozen 2026-07-13, tighten-only; a relaxation voids §4 and restarts its clock.
# These are read here and never edited: the doc is the authority.
GRADING_FLOOR_CLOSED = 20        # "< 20 forward closed trades PER BOOK" -> insufficient evidence
GRADING_KEEP_CALMAR_TOL = 0.05   # keep A-only if forward Calmar >= base - 0.05 (and DD shallower)
GRADING_REVERT_CALMAR_GAP = 0.10 # revert if Calmar falls > 0.10 below base


def _first_trading_day(y: int, m: int) -> date:
    d = date(y, m, 1)
    while d.weekday() >= 5 or d.isoformat() in NSE_HOLIDAYS:
        d += timedelta(days=1)
    return d


def _is_verified(d: date) -> bool:
    """Is this review date SOURCED, or did the calendar run out and we skipped weekends only?

    NSE publishes its holiday list one year at a time, so every review date past
    ``NSE_HOLIDAYS_COVERED_THROUGH`` is a weekends-only guess: the right answer if that month's
    first weekday happens to be a trading day, silently wrong if it is a holiday. This scorecard
    is the thing the owner reads the review cadence off, so a guess must never be presented as a
    known date. It is flagged rather than raised — the cron must keep producing the card, and the
    fix (re-run ``scripts/build_nse_holidays.py`` once NSE publishes) is a data refresh, not a bug.
    """
    try:
        assert_calendar_covers(d, what="a review date")
        return True
    except CalendarCoverageError:
        return False


def _review_dates(y0: int, n: int = 6) -> list[date]:
    return sorted(_first_trading_day(y, m) for y in range(y0, y0 + n) for m in (1, 4, 7, 10))


def _forward_metrics() -> dict:
    """(n_closed, expectancy_R, win_rate, forward Sharpe, MaxDD, nav) from the weekly book files."""
    an = _read(RESULTS_DIR / "signal_analytics_weekly.json", {})
    pf = _read(RESULTS_DIR / "paper_portfolio_weekly.json", {})
    sharpe = maxdd = None
    curve_path = RESULTS_DIR / "portfolio_history_weekly.csv"
    if curve_path.exists():
        try:
            df = pd.read_csv(curve_path)
            if len(df) >= 2 and "total_value" in df:
                r = df["total_value"].astype(float).pct_change().dropna()
                if len(r) >= 2 and r.std():
                    # sqrt(252) is CORRECT here: portfolio_history_weekly.csv is a DAILY series —
                    # the `_weekly` suffix names the weekly-swing BOOK, not the sampling frequency
                    # (verified: median row gap 1.0 day). Do NOT "fix" this to sqrt(52) to match the
                    # filename; that would inflate the forward Sharpe by ~2.2x. Also note rf = 0
                    # (no risk-free subtraction), which matters for the absolute KILL_SHARPE gate
                    # below but cancels in any delta comparison. See DEFINITIONS_REGISTER §8.
                    sharpe = float(r.mean() / r.std() * (252 ** 0.5))
                eq = df["total_value"].astype(float)
                # MaxDD is GRID-DEPENDENT: a coarser grid cannot see the troughs between samples and
                # can only UNDERSTATE the drawdown. This is the daily grid (the conservative choice)
                # and the §4 mechanical -50% halt reads it, so the grid is load-bearing for a risk
                # control. Finding 0114 publishes -33% for the same book family at MONTHLY
                # granularity vs -42.4% daily — not a different book. DEFINITIONS_REGISTER §7.
                maxdd = float((eq / eq.cummax() - 1).min())
        except Exception:
            pass
    return {
        "n_closed": int(an.get("total_closed") or 0),
        "expectancy_R": (None if an.get("avg_r") is None else float(an["avg_r"])),
        "win_rate_pct": an.get("win_rate"),
        "sharpe": sharpe,
        "maxdd_pct": (None if maxdd is None else round(maxdd * 100, 1)),
        "nav": float(pf.get("total_value") or 0.0),
    }


def _window_metrics(nav: list[tuple[str, float]], lo: str, hi: str) -> dict | None:
    """CAGR / MaxDD / Calmar over a CONTINUOUS SLICE of one NAV curve.

    Never a fresh-capital re-run from ``lo``: that resets the equity peak and manufactures a pass
    (the phantom 0.762 defect). We slice the curve both books already produced and read the metrics
    off the slice, which is symmetric — each book's drawdown is measured within the same window,
    against its own running peak inside that window.
    """
    pts = sorted((d, float(v)) for d, v in nav if lo <= d <= hi)
    if len(pts) < 2 or pts[0][1] <= 0:
        return None
    yrs = (date.fromisoformat(pts[-1][0]) - date.fromisoformat(pts[0][0])).days / 365.25
    if yrs <= 0:
        return None
    cagr = (pts[-1][1] / pts[0][1]) ** (1.0 / yrs) - 1.0
    peak, dd = pts[0][1], 0.0
    for _, v in pts:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1.0)
    return {"cagr_pct": round(cagr * 100, 3), "maxdd_pct": round(dd * 100, 3),
            "calmar": (round(cagr / abs(dd), 4) if dd else None),
            "from": pts[0][0], "to": pts[-1][0], "n_points": len(pts)}


def _grading_panel(a_nav: list[tuple[str, float]], a_closed: int) -> dict:
    """forward/prereg_swing.md §4 — A-only vs base-swing, evaluated rather than asserted.

    Surfaces state; decides nothing. §4 is decided at a review date and its primary decision is
    2027-07-01, with 2026-10-01 a first read only.

    The comparison window is the INTERSECTION of the two records. base-swing logging began
    2026-08-08, five weeks after the A-only book's inception, because §2 registered the arm as
    reconstructable from the uncapped signal ledger and that ledger is Grade-A filtered, so it never
    accrued. §3 forbids backfilling, so the window is permanently truncated on the left and the only
    honest comparison is over what both books actually hold.
    """
    base = _read(RESULTS_DIR / "base_swing_forward.json", None)
    out: dict = {
        "rule": ("keep A-only if forward MaxDD shallower AND Calmar >= base - 0.05; revert if MaxDD "
                 "not shallower OR Calmar > 0.10 below base; < 20 closed per book -> insufficient "
                 "evidence, DEFAULT TO BASE-SWING and carry A-only (forward/prereg_swing.md §4)"),
        "authority": "forward/prereg_swing.md §4 (frozen 2026-07-13, tighten-only)",
        "decided_at": "2027-07-01 primary; 2026-10-01 is a first read only",
        "a_only_closed": a_closed, "floor_per_book": GRADING_FLOOR_CLOSED,
        # Disclosed rather than implied: §4's insufficient-evidence clause has a SECOND limb — "CIs
        # overlapping on both DD and Calmar" — and this panel does not compute bootstrap CIs. So a
        # KEEP or REVERT here is provisional on that check, which must be run before the verdict is
        # acted on. The floor and the two threshold branches are complete; the CI limb is not.
        "not_implemented": ("§4's CI-overlap limb of the insufficient-evidence clause. A KEEP or "
                            "REVERT verdict from this panel is provisional until block-bootstrap "
                            "CIs on forward MaxDD and Calmar are computed and checked for overlap."),
    }
    if base is None:
        out |= {"verdict": "INSUFFICIENT EVIDENCE -> default base-swing, carry A-only",
                "reason": "results/base_swing_forward.json absent — the comparator has not accrued",
                "base_swing_closed": None}
        return out

    b_nav = [(r["date"], r["equity"]) for r in base.get("nav", [])]
    b_closed = int(base.get("n_closed") or 0)
    out["base_swing_closed"] = b_closed
    if not a_nav or not b_nav:
        out |= {"verdict": "INSUFFICIENT EVIDENCE -> default base-swing, carry A-only",
                "reason": "one or both NAV curves are empty"}
        return out

    lo = max(a_nav[0][0], b_nav[0][0])
    hi = min(a_nav[-1][0], b_nav[-1][0])
    a_m, b_m = _window_metrics(a_nav, lo, hi), _window_metrics(b_nav, lo, hi)
    out |= {"common_window": {"from": lo, "to": hi}, "a_only": a_m, "base_swing": b_m}

    if a_m is None or b_m is None:
        out |= {"verdict": "INSUFFICIENT EVIDENCE -> default base-swing, carry A-only",
                "reason": "the common window is too short to measure"}
        return out
    if min(a_closed, b_closed) < GRADING_FLOOR_CLOSED:
        out |= {"verdict": "INSUFFICIENT EVIDENCE -> default base-swing, carry A-only",
                "reason": (f"{min(a_closed, b_closed)} closed trades in the thinner book, "
                           f"below the §4 floor of {GRADING_FLOOR_CLOSED} per book")}
        return out

    # Note the asymmetry, which is deliberate in the doc: A-only must EARN its place. It is not
    # enough to avoid the revert condition.
    shallower = a_m["maxdd_pct"] > b_m["maxdd_pct"]            # closer to zero == shallower
    d_calmar = (None if (a_m["calmar"] is None or b_m["calmar"] is None)
                else a_m["calmar"] - b_m["calmar"])
    out["maxdd_shallower"] = shallower
    out["calmar_delta"] = (None if d_calmar is None else round(d_calmar, 4))

    if d_calmar is None:
        out |= {"verdict": "INSUFFICIENT EVIDENCE -> default base-swing, carry A-only",
                "reason": "Calmar undefined for at least one book (no drawdown in the window)"}
    elif shallower and d_calmar >= -GRADING_KEEP_CALMAR_TOL:
        out |= {"verdict": "KEEP A-ONLY", "reason": "MaxDD shallower and Calmar within 0.05 of base"}
    elif (not shallower) or d_calmar < -GRADING_REVERT_CALMAR_GAP:
        out |= {"verdict": "REVERT TO BASE-SWING",
                "reason": ("MaxDD not shallower" if not shallower
                           else f"Calmar {abs(d_calmar):.4f} below base, past the 0.10 revert gap")}
    else:
        # Reachable: DD shallower, Calmar between 0.05 and 0.10 below base. Satisfies neither the
        # keep condition nor the revert condition as frozen. Surfaced, never silently resolved —
        # picking a side here would be inventing a threshold after seeing the data.
        out |= {"verdict": "UNDETERMINED BY §4 AS WRITTEN",
                "reason": (f"MaxDD shallower but Calmar {abs(d_calmar):.4f} below base — inside the "
                           "gap between the keep bound (0.05) and the revert bound (0.10). §4 "
                           "defines no outcome here; it needs an owner amendment, not a judgement "
                           "call at the review.")}
    return out


def _read(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except Exception:
        return default


def main() -> int:
    today = date.today()
    rev = _review_dates(INCEPTION.year)
    quarters_elapsed = len([d for d in rev if INCEPTION < d <= today])
    next_review = min([d for d in rev if d >= today], default=None)
    days_to_review = (next_review - today).days if next_review else None
    review_verified = next_review is not None and _is_verified(next_review)
    days_live = (today - INCEPTION).days

    m = _forward_metrics()
    ready = m["n_closed"] >= READY_CLOSED or quarters_elapsed >= READY_QUARTERS

    a_nav: list[tuple[str, float]] = []
    _curve = RESULTS_DIR / "portfolio_history_weekly.csv"
    if _curve.exists():
        try:
            _df = pd.read_csv(_curve)
            if {"date", "total_value"} <= set(_df.columns):
                a_nav = [(str(d)[:10], float(v))
                         for d, v in zip(_df["date"], _df["total_value"].astype(float))]
        except Exception:
            a_nav = []
    grading = _grading_panel(a_nav, m["n_closed"])

    exp, dd, sh = m["expectancy_R"], m["maxdd_pct"], m["sharpe"]
    promote_pass = (None if (exp is None or dd is None)
                    else (exp > PROMOTE_EXPECTANCY_R and dd > PROMOTE_MAXDD * 100))
    kill_trig = (None if sh is None else sh < KILL_SHARPE)
    halt_trig = bool(dd is not None and dd <= HALT_MAXDD * 100)

    if halt_trig:
        status = "HALT"
    elif not ready:
        status = "ACCRUING"
    elif kill_trig:
        status = "KILL (pre-committed)"
    elif promote_pass:
        status = "PROMOTE-ELIGIBLE (pre-committed)"
    else:
        status = "CONTINUE-WATCH"

    headline = (f"{m['n_closed']}/{READY_CLOSED} closed, {quarters_elapsed}/{READY_QUARTERS} quarters "
                f"-> {'evaluable' if ready else 'not yet evaluable'}; "
                f"{days_to_review} days to the {next_review} review"
                + ("" if review_verified else " [UNVERIFIED DATE - calendar coverage ends "
                                              f"{NSE_HOLIDAYS_COVERED_THROUGH}]"))

    card = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "book": BOOK, "inception": INCEPTION.isoformat(), "days_live": days_live,
        "next_review": next_review.isoformat() if next_review else None,
        "days_to_review": days_to_review,
        # False = the calendar ran out and this date skipped weekends only. Not a known date.
        "next_review_verified": review_verified,
        "holidays_covered_through": NSE_HOLIDAYS_COVERED_THROUGH,
        "review_cadence": "first trading day of Jan/Apr/Jul/Oct (forward/prereg.md §8)",
        "forward": m,
        "gates": {
            "readiness": {"rule": ">=40 closed OR 4 quarters (§10.2)",
                          "n_closed": m["n_closed"], "quarters_elapsed": quarters_elapsed, "ready": ready},
            "promote": {"rule": "expectancy > +0.10R AND MaxDD shallower than -25% (§10.2)",
                        "expectancy_R": exp, "maxdd_pct": dd, "pass": promote_pass,
                        # Stated, not silently reconciled: this gate mixes units. `expectancy_R`
                        # comes from signal_analytics_weekly.json, where R is computed on RAW
                        # prices, while `maxdd_pct` is read off the NET NAV curve. So the +0.10R
                        # limb is measured gross of the costs the -25% limb already pays, and the
                        # gate is easier to clear than a reader would assume. Recomputing
                        # expectancy net would change what a pre-committed threshold means, which
                        # is an amendment at a review date, not an edit here.
                        "_units": ("expectancy_R is GROSS (raw-price R); maxdd_pct and sharpe are "
                                   "NET (off the NAV curve). The two limbs of this gate are not in "
                                   "the same unit — see forward/prereg.md §10.2 and "
                                   "DEFINITIONS_REGISTER §8.")},
            "kill": {"rule": "net Sharpe < 0 (§10.2)", "sharpe": sh, "triggered": kill_trig},
            "halt": {"rule": "live MaxDD <= -50% (§4, mechanical)", "maxdd_pct": dd, "triggered": halt_trig},
        },
        # The OTHER pre-committed decision on this book. Kept separate from `gates` above because
        # those encode forward/prereg.md §10.2 (the momentum wall's doc) while this encodes
        # forward/prereg_swing.md §4 — see `spec_note`. Both are surfaced so the Oct-1 review can
        # reconcile which spec judges this book with the numbers in hand rather than in prose.
        "swing_grading": grading,
        "status": status,
        "headline": headline,
        "spec_note": ("The §10.2 registered proposal names practitioner Engine B + 4xATR; the live "
                      "forward book is weekly-swing-0094-rank. The Oct-1 review must reconcile which "
                      "spec is judged (forward/prereg.md §10.2). Gates are surfaced, never applied "
                      "between review dates; the only mechanical action is the §4 halt. The "
                      "`swing_grading` block encodes the OTHER doc — forward/prereg_swing.md §4 — so "
                      "both candidate specs are now computed rather than argued at the review."),
        "authority": "forward/prereg.md (the doc is the authority; this scorecard only reads it)",
    }
    (RESULTS_DIR / "weekly_review_scorecard.json").write_text(
        json.dumps(card, indent=2, default=str), encoding="utf-8")

    # human panel
    def passfail(v):
        return {True: "PASS", False: "FAIL", None: "n/a"}[v]

    def trig(v):
        return {True: "TRIGGERED", False: "no", None: "n/a"}[v]
    print(f"=== Weekly-swing forward-review scorecard ({BOOK}) ===")
    print(f"  inception {INCEPTION} | {days_live}d live | next review {next_review} ({days_to_review}d)")
    if not review_verified:
        print(f"  !! next review date is UNVERIFIED: NSE_HOLIDAYS covers through "
              f"{NSE_HOLIDAYS_COVERED_THROUGH}, so it skipped weekends only. Re-run "
              f"scripts/build_nse_holidays.py once NSE publishes the next year.")
    print(f"  forward: {m['n_closed']} closed | expectancy {exp if exp is None else f'{exp:+.2f}R'} | "
          f"win {m['win_rate_pct']} | Sharpe {sh if sh is None else f'{sh:+.2f}'} | MaxDD {dd}% | NAV {m['nav']:,.0f}")
    print(f"  [readiness] {'READY' if ready else 'ACCRUING'} ({m['n_closed']}/{READY_CLOSED} closed, "
          f"{quarters_elapsed}/{READY_QUARTERS} quarters)")
    print(f"  [grading §4] {grading['verdict']}")
    print(f"               {grading['reason']}"
          + (f" (A-only {grading['a_only_closed']} vs base {grading['base_swing_closed']} closed)"
             if grading.get("base_swing_closed") is not None else ""))
    print(f"  [promote §10.2] {passfail(promote_pass)}  (need expectancy>+0.10R AND MaxDD>-25%)")
    print(f"  [kill §10.2]    {trig(kill_trig)}  (net Sharpe<0)")
    print(f"  [halt §4]       {trig(halt_trig)}  (MaxDD<=-50%)")
    print(f"  STATUS: {status}")
    print(f"  {headline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
