"""MEASUREMENT (no trial): has the 14:30 shadow scan ever actually run at 14:30?

`scripts/run_intraday_scan.py` exists to see a setup FORMING before the close — it reads today's
partial daily candle at 14:30 IST, roughly an hour before the 15:30 close, so there is still time to
act. Its confirmation log is meant to accrue the partial-to-final survival rate, and its own docstring
says that statistic "decides whether same-day entries are ever proposed as a real (pre-registered)
trial".

`.github/workflows/cron-intraday-scan.yml:11` schedules it correctly: `0 9 * * 1-5`, and 09:00 UTC is
14:30 IST with no DST to worry about. The schedule is right. The firing is not.

GitHub Actions `schedule` events are queued, not guaranteed. They drift under load — especially at
the top of the hour — and GitHub documents that they may be delayed or dropped entirely. This
measures the drift against the artifacts the job actually committed.

    python pipelines/diagnostics/diag_intraday_scan_timing.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / "results" / "intraday_scan"
OUT = ROOT / "diagnostics" / "research" / "intraday_scan_timing.md"

SCHEDULED_UTC_HOUR = 9          # cron-intraday-scan.yml:11 -> 14:30 IST
CLOSE_UTC = dt.time(10, 0)      # NSE closes 15:30 IST


def main() -> int:
    files = sorted(p for p in SCANS.glob("*.json") if p.stem[:2] == "20")
    if not files:
        print("no scan artifacts committed yet")
        return 0

    rows, after_close, ever_on_time = [], 0, 0
    for p in files:
        j = json.loads(p.read_text(encoding="utf-8"))
        ran = dt.datetime.fromisoformat(j["generated_utc"])
        sched = ran.replace(hour=SCHEDULED_UTC_HOUR, minute=0, second=0, microsecond=0)
        delay = (ran - sched).total_seconds() / 60.0
        closed = ran.timetz().replace(tzinfo=None) >= CLOSE_UTC
        after_close += closed
        ever_on_time += delay <= 15
        rows.append({"date": p.stem, "ran_utc": ran.strftime("%H:%M"), "delay_min": round(delay),
                     "ist": j.get("ist", "")[-5:], "session_fraction": j.get("session_fraction"),
                     "n_forming": j.get("n_forming"), "after_close": closed})

    conf = SCANS / "confirmation_log.csv"
    md = ["# Has the 14:30 shadow scan ever run at 14:30? (MEASUREMENT, no trial)", "",
          "`cron-intraday-scan.yml:11` schedules `0 9 * * 1-5` — 09:00 UTC, which is 14:30 IST. "
          "The schedule is correct. What follows is when the job actually fired.", "",
          "| date | ran (UTC) | delay | IST | session fraction | forming setups | after close? |",
          "|---|--:|--:|--:|--:|--:|:--:|"]
    for r in rows:
        md.append(f"| {r['date']} | {r['ran_utc']} | **{r['delay_min']}m** | {r['ist']} | "
                  f"{r['session_fraction']} | {r['n_forming']} | "
                  f"{'**YES**' if r['after_close'] else 'no'} |")

    worst = max(r["delay_min"] for r in rows)
    md += ["", f"**Runs measured: {len(rows)}. Fired within 15 minutes of schedule: "
               f"{ever_on_time}. Fired after the market had already closed: {after_close}. "
               f"Worst delay: {worst} minutes.**", "",
           "## Reading", "",
           "A `session_fraction` of 1.0 means the session was already over when the scan ran — there "
           "was no partial candle to read, only the completed one. The scan's entire premise is that "
           "you see the setup forming with about an hour of session left; at 16:40 IST there is "
           "nothing to act on and nothing forming that the daily bar will not show anyway.",
           "",
           "GitHub Actions `schedule` events are queued rather than guaranteed. They drift under "
           "load, most of all at the top of the hour, and GitHub documents that they may be delayed "
           "or dropped. A cron expression is a request, not an appointment. **A time-critical "
           "market-hours job cannot live on it.**",
           "",
           f"Consequence: `{conf.relative_to(ROOT)}` "
           f"{'exists' if conf.exists() else '**has never accrued a single row**'}. The "
           "partial-to-final survival rate — the statistic the scan's own docstring says decides "
           "whether same-day entries are ever proposed as a real trial — cannot accrue, because a "
           "partial state is never captured.",
           "",
           "## Alternatives, in order of cost", "",
           "1. **Move it to a machine that holds a time.** `deploy/DROPLET_KITE_REFRESH.md` already "
           "documents a droplet used for the Kite session refresh — itself a time-sensitive job, and "
           "presumably moved there for this reason. A `cron` entry fires within seconds. Cheapest "
           "fix, on infrastructure that exists.",
           "2. **A Fly.io scheduled machine.** The backend already runs there.",
           "3. **Schedule earlier to absorb the drift** (e.g. 07:30 UTC). Crude: if it fires on time "
           "you get a 13:00 IST snapshot rather than 14:30, and if it drifts you are back where you "
           "started. A stopgap, not a fix.",
           "4. **Stop accruing it forward and backtest it instead.** This is the one that changes "
           "the problem rather than the plumbing. If the 14:30 state cannot be captured reliably "
           "going forward, it can still be RECONSTRUCTED historically from an intraday bar store — "
           "every 14:30 in 2017-2026, thousands of observations, testable this quarter rather than "
           "in several years. **The intraday store is therefore not an alternative to the 14:30 "
           "scan; it is the only way to answer the question the scan was built to ask.** That makes "
           "the Kite delisted-name probe "
           "(`pipelines/diagnostics/probe_kite_intraday_survivorship.py`) the gating step for this "
           "too, not just for new strategy families.",
           "",
           "Reproduce: `python pipelines/diagnostics/diag_intraday_scan_timing.py`"]
    OUT.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"{'date':12s} {'ran':>9s} {'delay':>7s} {'IST':>7s} {'sess':>6s} {'forming':>8s}  after close")
    for r in rows:
        print(f"{r['date']:12s} {r['ran_utc']:>9s} {r['delay_min']:>6}m {r['ist']:>7s} "
              f"{r['session_fraction']:>6} {r['n_forming']:>8}  {'YES' if r['after_close'] else 'no'}")
    print(f"\nruns {len(rows)} | on time (<=15m) {ever_on_time} | after close {after_close} | "
          f"worst delay {worst}m")
    print(f"confirmation_log.csv: {'exists' if conf.exists() else 'NEVER ACCRUED A ROW'}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
