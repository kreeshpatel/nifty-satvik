# 2026-09-15 snapshot — a mid-week run; its six stop exits are artifacts

Added 2026-09-15, owner-approved. The snapshot itself is left byte-for-byte as written (write-once, constitution D2); this note sits beside it.

**What this snapshot is.** A manual dispatch of `cron-bhanushali-scanner` on **Tuesday** 2026-09-15. It was run to publish the B′ demerger credit for HEG (PR #98) ahead of the Saturday scan.

**What in it is wrong.** The engine then treated the last bar of every ISO week as that week's close. That included the week still in progress, so Tuesday's close was scored as a weekly close. Six held names closed that Tuesday just under their stops, and the snapshot records each of them as `HIT_STOP` / `EXIT_REQUIRED` ("Weekly close below the stop — SELL the remaining position at Monday's open"):

| ticker | Tue close | stop |
|---|---|---|
| ASTERDM | 741.25 | 745.05 |
| LTF | 296.80 | 297.50 |
| NESTLEIND | 1362.00 | 1374.89 |
| HINDALCO | 958.70 | 981.35 |
| JSWSTEEL | 1229.20 | 1250.40 |
| PHOENIXLTD | 1833.60 | 1876.00 |

The rule is a weekly close below the stop. None of these was one. **Do not read them as exits, stops or losses.** The same defect was latent in the earlier mid-week dispatches (2026-08-04, 2026-08-13).

**What in it is right.** HEG's B′ re-basing: credit ₹1,39,521, entry 244.07, stop 219.67. It does not depend on the week being closed.

**The fix and the record of truth.**
- The fix is prod-fix `complete_weeks_only` (`LIVE_PREP` in `scripts/run_bhanushali_cron.py`, `week_closed_at` in `scripts/run_bhanushali_weekly_rank.py`). The last bar of an open week no longer decides any weekly exit, and a week cut short by NSE holidays still counts as closed.
- The cron was re-run the same day on the fixed engine. That snapshot is `2026-09-15__rerun-*`, and it supersedes this one for every purpose.
- The first full-week record after this is the Saturday 2026-09-19 scan.
