# Config CHANGELOG — live-strategy configuration changes of record

Append-only. Each entry is a change to a LIVE strategy config (not a research measurement). Newest first.
Format: date — model — what changed — why — evidence — reversal.

---

## 2026-07-16 — weekly-swing (Bhanushali) — LIVE EXIT switched to config P (owner-override; product build Phase A)
- **Model:** `weekly-swing-0094-rank-p2exit-disc` -> `weekly-swing-0094-rank-P`
  (`models/bhanushali_weekly/config.json`; `P_EXIT` in `scripts/run_bhanushali_cron.py`).
- **What changed (EXIT only; entry, stop, sizing unchanged):** the P2 trend exit (no-cap hold + blow-off
  @2.5R + 20wk trail) is replaced by config P — a THREE-TRANCHE scaled exit: 40% @ +2R (intraweek limit),
  40% on the blow-off exhaustion pattern (new-high week closing lower-third, armed +2.5R), 20% runner to a
  weekly close below the 44-week SMA.
- **Why:** owner decision to ship P and build the product (per-user memory, Research UI, guidance) around
  it. P maximises the fat tail.
- **Evidence (A-only book, in-sample):** full Sharpe 1.055 -> 1.227, CAGR 20.2 -> 27.2%, MaxDD -31.2 ->
  -39.5%, max winner 16.7R -> 40.8R, trades 184 -> 130, **2022-26 gate 1.04 -> 0.91**.
- **Honesty:** OWNER-OVERRIDE against the research recommendation. P fails the 2022-26 gate, runs a
  -39.5% DD (against the owner's own drawdown priority), and is WORSE from a cold start than the prior LIVE
  book (COLD_START_DIST.md: 1yr median +9% vs +17%). In-sample at trial 129; no DSR gate passes it. Adopted
  for its amplified fat tail; the owner accepts the drawdown and regime risk.
- **Cards:** now carry `pattern` (entry structure), `exit_plan` (the 3 tranches with price levels +
  plain-English do-this), and `exit_stage` (which tranches have booked). Held-card exit messages are
  P-aware (pattern / sma_break / stop).
- **Guards:** frozen 0094 research run byte-identical 1.132/255 (`backtest()` defaults OFF);
  `test_stage2_golden` 3 passed; cron smoke-tested offline (exit 0, held cards carry exit_stage).
- **Reversal:** swap `**P_EXIT` -> `**P2_EXIT` at the two `backtest()` call sites and revert `model_version`.
- **Refs:** ADR `docs/decisions/0010-swing-config-P.md`; `research/substrate/FINDING_pattern_exit.md`;
  `research/substrate/COLD_START_DIST.md`.

---

## 2026-07-16 — weekly-swing (Bhanushali) — DISCIPLINE config added (owner-override on risk appetite)
- **Model:** `weekly-swing-0094-rank-p2exit` → `weekly-swing-0094-rank-p2exit-disc`
  (`models/bhanushali_weekly/config.json`; `LIVE_DISCIPLINE` in `scripts/run_bhanushali_cron.py`).
- **What changed (entry SELECTION + stop + sizing bound; the exit is untouched):**
  - `ext_cap=0.20` — skip any fill priced **>20% above the signal-week 44w SMA**. Pure selection; the stop
    is untouched. The rule-faithful half.
  - `max_risk_pct=0.10` — stop = `max(signal-week low, entry × 0.90)`. **This LIFTS the stop off the candle
    low** when the low is further — a deliberate deviation from the taught rule, per the owner.
  - `max_notional_pct=0.20` — no name above 20% of sizing equity. **Guardrail against single-name blowup,
    NOT a diversification benefit** (see evidence).
- **Why:** owner review of live trades against charts — *"i dont care even if it gave good returns, then our
  book is badly traded … max 20 percent is fine, if more than 10 percent then our R is distorted"*. Median R
  of 13.7% made a −2R exit a −27% move; holds ran 19 weeks; fills landed 20-40% over the SMA (KNRCON +40.1%).
- **Evidence (A-ONLY book = what actually trades; parity-checked vs the recorded 1.004/171 — PASS):**
  Sharpe **1.004 → 1.055**, CAGR 20.9 → 20.2%, **MaxDD −36.4 → −31.2% (+5.2pp)**, trades 171 → 184,
  **median R 13.7 → 9.1%**, **mean hold 19.1 → 12.4wk**, win 54 → 51%, **2022-26 slice 1.17 → 1.04** (the one
  negative). Pre-registered `research/preregistry_owner_discipline.md` BEFORE the run (R4); trial 115→116.
- **Honesty:** **NOT an edge claim and NOT certified.** +0.05 full-sample vs −0.13 on the 22-26 slice —
  opposite signs = noise; the book is chaotic under fill perturbation (G1 0.47 / G2 0.42 / G1+G2 0.97). At
  cumulative trial **122 no DSR gate passes** this, and none is claimed — it fails no gate because it was
  never submitted as an improvement. It ships for the **risk-appetite** properties (R ≤ 9.1%, holds −35%,
  DD −5.2pp), which are structural, not statistical.
- **Corrections recorded:** (1) the owner's stated mechanism was inverted — notional = `risk% ÷ R%`, so a
  wide stop makes positions *small*; capping R **concentrated** the book 14% → 22%/name, hence the notional
  cap. (2) That concentration is a **feature**: `FINDING_more_slots` (trials 120→122) measured 4-5 names
  **1.21** > 7 **0.97** > 10 **0.81** → the null 0.74. An earlier draft called it "the real cost of the R
  cap"; that was wrong.
- **Guards:** frozen 0094 research run **byte-identical 1.132/255** (all levers default OFF); full suite
  **120 passed**.
- **Reversal:** delete `**LIVE_DISCIPLINE` from the two `backtest()` call sites in
  `scripts/run_bhanushali_cron.py` and revert `model_version`.
- **Refs:** ADR `docs/decisions/0009-swing-discipline-config.md`; `research/substrate/FINDING_owner_discipline.md`;
  `research/substrate/FINDING_more_slots.md`.

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
