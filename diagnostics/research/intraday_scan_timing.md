# Has the 14:30 shadow scan ever run at 14:30? (MEASUREMENT, no trial)

`cron-intraday-scan.yml:11` schedules `0 9 * * 1-5` — 09:00 UTC, which is 14:30 IST. The schedule is correct. What follows is when the job actually fired.

| date | ran (UTC) | delay | IST | session fraction | forming setups | after close? |
|---|--:|--:|--:|--:|--:|:--:|
| 2026-08-05 | 11:11 | **131m** | 16:40 | 1.0 | 0 | **YES** |
| 2026-08-06 | 11:11 | **132m** | 16:41 | 1.0 | 0 | **YES** |
| 2026-08-07 | 09:48 | **49m** | 15:18 | 0.968 | 0 | no |

**Runs measured: 3. Fired within 15 minutes of schedule: 0. Fired after the market had already closed: 2. Worst delay: 132 minutes.**

## Reading

A `session_fraction` of 1.0 means the session was already over when the scan ran — there was no partial candle to read, only the completed one. The scan's entire premise is that you see the setup forming with about an hour of session left; at 16:40 IST there is nothing to act on and nothing forming that the daily bar will not show anyway.

GitHub Actions `schedule` events are queued rather than guaranteed. They drift under load, most of all at the top of the hour, and GitHub documents that they may be delayed or dropped. A cron expression is a request, not an appointment. **A time-critical market-hours job cannot live on it.**

Consequence: `results\intraday_scan\confirmation_log.csv` **has never accrued a single row**. The partial-to-final survival rate — the statistic the scan's own docstring says decides whether same-day entries are ever proposed as a real trial — cannot accrue, because a partial state is never captured.

## Alternatives, in order of cost

1. **Move it to a machine that holds a time.** `deploy/DROPLET_KITE_REFRESH.md` already documents a droplet used for the Kite session refresh — itself a time-sensitive job, and presumably moved there for this reason. A `cron` entry fires within seconds. Cheapest fix, on infrastructure that exists.
2. **A Fly.io scheduled machine.** The backend already runs there.
3. **Schedule earlier to absorb the drift** (e.g. 07:30 UTC). Crude: if it fires on time you get a 13:00 IST snapshot rather than 14:30, and if it drifts you are back where you started. A stopgap, not a fix.
4. **Stop accruing it forward and backtest it instead.** This is the one that changes the problem rather than the plumbing. If the 14:30 state cannot be captured reliably going forward, it can still be RECONSTRUCTED historically from an intraday bar store — every 14:30 in 2017-2026, thousands of observations, testable this quarter rather than in several years. **The intraday store is therefore not an alternative to the 14:30 scan; it is the only way to answer the question the scan was built to ask.** That makes the Kite delisted-name probe (`pipelines/diagnostics/probe_kite_intraday_survivorship.py`) the gating step for this too, not just for new strategy families.

Reproduce: `python pipelines/diagnostics/diag_intraday_scan_timing.py`
