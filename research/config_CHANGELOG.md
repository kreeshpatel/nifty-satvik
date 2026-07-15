# Config CHANGELOG — live-strategy configuration changes of record

Append-only. Each entry is a change to a LIVE strategy config (not a research measurement). Newest first.
Format: date — model — what changed — why — evidence — reversal.

---

## 2026-07-15 — weekly-swing (Bhanushali) — EXIT changed (Phase-2, owner-override)
- **Model:** `weekly-swing-0094-rank` → `weekly-swing-0094-rank-p2exit` (`models/bhanushali_weekly/config.json`).
- **What changed (EXIT only; entry, stop, sizing unchanged):** the 13-week time cap + 20-day-SMA trail were
  replaced by a **trend-following no-cap hold** (52-week backstop) **+ a blow-off-bar exit @2.5R MFE** (a week
  that makes a new high but closes in the lower third of its weekly range = exhaustion) **+ a 20-week-close −4%
  backstop**. Wired via `P2_EXIT = dict(no_time_cap=True, wk20_trail_pct=0.04, blowoff_arm_r=2.5)` passed to both
  `R94.backtest(...)` calls in `scripts/run_bhanushali_cron.py`. The `backtest()` DEFAULTS are left OFF so the
  frozen 0094 research run stays byte-identical (1.132/255).
- **Why:** a three-phase trade-by-trade AI forensic (5 text + 8 vision agents; an unbiased random 60-trade exit
  map) found the 13-week cap severed still-trending winners (45% of winners on the random map exited mid-trend,
  several ran 4–27R after) and givebacks topped on a blow-off bar. Owner-adopted for fewer/longer-held/higher-
  return trades (eases the capital-contention/selection bottleneck) at lower drawdown.
- **Effect (in-sample, corrected universe 2017–2026, ₹10L):** Sharpe 1.132→1.034, CAGR 24.7→21.2%,
  **MaxDD −42.4→−34.8%, Calmar 0.58→0.61**, per-trade meanR +0.481→+0.616 (+28%), trades 255→168, win 59→54%.
- **Discipline status:** this is a **defensive/selection variant that FAILS the standard ΔSharpe≥+0.10 promote
  gate** (it's −0.10) and it touches the exit area the registry closed as KILL (0098). It is adopted to LIVE by
  **owner-override** (sole capital-at-risk), NOT via the forward-wall certification route. Recorded honestly as
  such; the base-swing 0094 remains the WATCHED forward reference for comparison.
- **Evidence:** finding [0099](findings/0099-swing-p2exit-nocap-blowoff.md); pre-reg 0099; overlay_registry row
  0099; ADR `docs/decisions/0008-swing-exit-change.md`; per-year scorecard in
  `research/losers_analysis/FORENSIC_FINDINGS.md`; spec `research/losers_analysis/LOCKED_STRATEGY.md`.
- **Reversal:** set `P2_EXIT` OFF in `scripts/run_bhanushali_cron.py` (or remove `**P2_EXIT` from the two
  `backtest` calls) → live reverts byte-identical to the frozen 0094.
