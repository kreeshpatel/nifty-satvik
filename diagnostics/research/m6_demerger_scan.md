# M6 — demerger-suspect scan over the live swing cache

**Date:** 2026-07-29 · **Script:** [scripts/diag_m6_demerger_scan.py](../../scripts/diag_m6_demerger_scan.py)
· **Data:** [m6_demerger_scan.json](m6_demerger_scan.json) · Read-only; nothing quarantined.
**Counts unchanged: screens 11, sealed opens 1, n_trials 138.**

Constitution B-8: the swing path runs **no OHLCV cleaner** — `clean_ohlcv_for_features` and the
`demerger_suspect_names` quarantine guard are wired into the momentum path only. A value-leaving
demerger mid-hold appears as a huge red weekly bar that can drag the 44-week SMA, trigger a
spurious stop or runner `sma_break`, or manufacture a fake "touch" that fires an entry.

## Verdict: **CLEAR** — no suspect touches the live book or this week's cards

| Measure | Value |
|---|---|
| Names scanned (cache `f8625a8ff6abae06`) | 710 |
| Detector | ≥50% single-session drop within 263 bars, non-reverting (the existing momentum guard) |
| Suspects found | **2** — `SKFINDIA`, `VEDL` |
| Suspects in current holdings (4) | **none** |
| Suspects on this week's cards (19) | **none** |
| Suspects in the index snapshot | 2 |
| Committed demerger reference | ABFRL, RAYMOND, SKFINDIA, VEDL |

Both detected suspects are **already in the committed demerger reference**
(`data/corporate_actions_demergers.csv`), so the detector found nothing the repo did not already
know about, and neither name is in the book or on a card.

## Reading

The exposure is currently **latent, not live** — the same shape as B-1 before its fix. Two facts
keep it on the list rather than closing it:

1. The reference file is **manually curated**. ABFRL and RAYMOND are listed but were *not* flagged
   by the detector on this cache (their events fall outside the 263-bar lookback), so the reference
   is doing work the detector cannot. A future demerger that nobody adds to the CSV is invisible to
   both the swing path (no cleaner at all) and to any lookback-limited scan.
2. The swing engine has **no quarantine hook** to wire a guard into, unlike the momentum entry loop.
   Adding one is a live-path engine change — an owner decision, not a session fix.

Recommended disposition for the Oct-1 binder: run this scan as a standing weekly cron step
(read-only, seconds, zero risk) so a suspect entering the book or the cards is *flagged* even while
the quarantine decision stays open. Deciding whether the swing engine should also apply
`clean_ohlcv_for_features` is the larger, separate question — it would change every historical bar
the book has ever seen and therefore requires a golden regeneration and a re-anchor.
