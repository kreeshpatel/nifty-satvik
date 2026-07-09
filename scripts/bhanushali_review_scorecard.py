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
from config import NSE_HOLIDAYS, RESULTS_DIR  # noqa: E402

INCEPTION = date(2026, 7, 4)                 # forward-watch paper inception (forward/prereg.md)
BOOK = "weekly-swing-0094-rank"
# Pre-committed gates (forward/prereg.md — DO NOT edit here; the doc is the authority)
READY_CLOSED, READY_QUARTERS = 40, 4         # §10.2 whichever first
PROMOTE_EXPECTANCY_R, PROMOTE_MAXDD = 0.10, -0.25   # §10.2 promote (both required)
KILL_SHARPE = 0.0                            # §10.2 kill if net Sharpe < this
HALT_MAXDD = -0.50                           # §4 mechanical halt
IST = timezone(timedelta(hours=5, minutes=30))


def _first_trading_day(y: int, m: int) -> date:
    d = date(y, m, 1)
    while d.weekday() >= 5 or d.isoformat() in NSE_HOLIDAYS:
        d += timedelta(days=1)
    return d


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
                    sharpe = float(r.mean() / r.std() * (252 ** 0.5))
                eq = df["total_value"].astype(float)
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
    days_live = (today - INCEPTION).days

    m = _forward_metrics()
    ready = m["n_closed"] >= READY_CLOSED or quarters_elapsed >= READY_QUARTERS

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
                f"{days_to_review} days to the {next_review} review")

    card = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
        "book": BOOK, "inception": INCEPTION.isoformat(), "days_live": days_live,
        "next_review": next_review.isoformat() if next_review else None,
        "days_to_review": days_to_review,
        "review_cadence": "first trading day of Jan/Apr/Jul/Oct (forward/prereg.md §8)",
        "forward": m,
        "gates": {
            "readiness": {"rule": ">=40 closed OR 4 quarters (§10.2)",
                          "n_closed": m["n_closed"], "quarters_elapsed": quarters_elapsed, "ready": ready},
            "promote": {"rule": "expectancy > +0.10R AND MaxDD shallower than -25% (§10.2)",
                        "expectancy_R": exp, "maxdd_pct": dd, "pass": promote_pass},
            "kill": {"rule": "net Sharpe < 0 (§10.2)", "sharpe": sh, "triggered": kill_trig},
            "halt": {"rule": "live MaxDD <= -50% (§4, mechanical)", "maxdd_pct": dd, "triggered": halt_trig},
        },
        "status": status,
        "headline": headline,
        "spec_note": ("The §10.2 registered proposal names practitioner Engine B + 4xATR; the live "
                      "forward book is weekly-swing-0094-rank. The Oct-1 review must reconcile which "
                      "spec is judged (forward/prereg.md §10.2). Gates are surfaced, never applied "
                      "between review dates; the only mechanical action is the §4 halt."),
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
    print(f"  forward: {m['n_closed']} closed | expectancy {exp if exp is None else f'{exp:+.2f}R'} | "
          f"win {m['win_rate_pct']} | Sharpe {sh if sh is None else f'{sh:+.2f}'} | MaxDD {dd}% | NAV {m['nav']:,.0f}")
    print(f"  [readiness] {'READY' if ready else 'ACCRUING'} ({m['n_closed']}/{READY_CLOSED} closed, "
          f"{quarters_elapsed}/{READY_QUARTERS} quarters)")
    print(f"  [promote §10.2] {passfail(promote_pass)}  (need expectancy>+0.10R AND MaxDD>-25%)")
    print(f"  [kill §10.2]    {trig(kill_trig)}  (net Sharpe<0)")
    print(f"  [halt §4]       {trig(halt_trig)}  (MaxDD<=-50%)")
    print(f"  STATUS: {status}")
    print(f"  {headline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
