# Pre-registration registry

One file per experiment, named `NNNN-short-slug.md`, written and committed
**before** the experiment is run. See `../HOLDOUT.md` for the binding rules.

## Required fields

- **ID** — zero-padded sequence number (matches filename).
- **Registered** — date the pre-registration was committed (must precede the run).
- **Hypothesis** — the falsifiable claim, with the *predicted* direction/magnitude.
- **Holdout** — which holdout this is tested on (`forward-wall` or `unseen-universe`).
  Dev folds are NOT a valid confirmation holdout.
- **Primary metric** — exactly ONE. Everything else is secondary/diagnostic.
- **Decision rule** — the pass/fail/inconclusive thresholds, fixed in advance.
- **n_trials (cumulative)** — total model/strategy variants tried across the whole
  program up to and including this one. Feeds the Deflated Sharpe Ratio deflation.
- **Status** — `PENDING` → `RUNNING` → `COMPLETE`. Set at registration; results
  appended in a separate "Result" section, never by editing the fields above.

## Discipline reminders

- The pre-registration text above the `## Result` line is immutable once committed.
- A result can only KILL or weakly SUPPORT a hypothesis — never "bless" it.
- Report every metric with a bootstrap CI; a Sharpe only counts if DSR > 0.95 at
  the current `n_trials`.
- Costs honest (brokerage + STT + slippage + ADV floor) or the result is void.

## Index

| ID | Slug | Holdout | Status |
|----|------|---------|--------|
| 0001 | different-universe-oos | unseen-universe | COMPLETE — SUPPORT (weak; +4.1%/trade on 145 unseen tickers, survivorship-caveated) |
| 0002 | sector-rotation-activation | unseen-universe + forward-wall | COMPLETE — signal EXISTS (momentum t=2.75) but KILL as a per-stock feature (OOS +0.14%/trade noise, WR/Sharpe down — redundant w/ per-stock momentum). Real edge needs a sector-rotation ALLOCATION OVERLAY, not the model |
| 0003 | forward-wall-live-expectancy | forward-wall | PENDING — accumulating (the decisive live test) |
| 0004 | chart-structure-features | unseen-universe → forward-wall | COMPLETE — INCONCLUSIVE (features used: 4/5 earn importance, but OOS expectancy delta +0.10%/trade, within noise → as-features approach KILLed; pivots to 0005 + structure-as-separate-track) |
| 0005 | signal-persistence-latch | unseen-universe → forward-wall | COMPLETE — KILL (latch −2.84%/trade vs snapshot; latch-only entries 51% WR / +1.25% = bleed. Gate strictness is protective; low conf is information) |
| 0006 | earnings-proximity-gate | unseen-universe → forward-wall | COMPLETE — DATA-LIMITED/no-support (yf earnings coverage 37%; on covered subset near-earnings did BETTER not worse → gate would drop good trades) |
| 0007 | target-calibration-headroom | unseen-universe → forward-wall | COMPLETE — INCONCLUSIVE/KILL (live shrink_target is the best of a 6-point sweep; B2 optimism already correctly handled; no headroom) |
| 0008 | sector-rotation-overlay | unseen-universe → forward-wall | CLOSED — INCONCLUSIVE (unseen smallcaps unmapped → coverage-limited; tilt Sharpe 2.86→2.79, no benefit). Sector edge = standalone rotation product, not a picker enhancement |
| 0010 | delivery-pct-feature | unseen-universe → forward-wall | COMPLETE — **KILL (reproducible).** Delivery-% (orthogonal conviction) ADDED to 82f candidate, reproducible same-window (2020+) vs 79f baseline: makes the model WORSE — Sharpe 1.12→0.84 (−0.28), WR −5.6pp, composite −0.02, 2/5 folds, DSR 0.005. Overfits the short 2020+ window (helps 2022/23, breaks 2025/26). First VALID run after fixing PR #66 (train() ignored config active_features → all feature experiments were no-ops). The orthogonal-feature ceiling pattern (0002/0004/0008): new data adds noise, not edge |
| 0011 | triple-barrier-win-label | unseen-universe → forward-wall | COMPLETE — **KILL** (per-trade near-miss + walk-forward gate REJECT). Path-aware `tb_hit_14d` (hit +4% BEFORE 2×ATR stop): per-trade OOS +4.42% vs +3.74% (**+0.68%**, +4pp WR, 266 vs 343 trades) — strongest near-miss but sub-CI. Briefly adopted as training default (bdf74e5) then the **production walk-forward gate REJECTed it** (3/9 fold Sharpe wins, −0.38 Sharpe, −26.5pp CAGR — selectivity wins choppy yrs but bleeds CAGR in trend yrs 2020/2021). **REVERTED to hit_4pct** (0c5d82f). Surfaced+fixed a real gate bug (per-fold filter dropped tb_hit → would REJECT all candidates; 908b3bc). Lesson: more-correct label ≠ better model; portfolio gate > per-trade OOS |
| 0011b | triple-barrier-7pct-threshold | unseen-universe → forward-wall | COMPLETE — KILL (gate-starvation): +7% win bar → only n=12 trades clear the 0.92 gate (+10.5%/100%WR is an n=12 mirage, Sharpe fell). Settles the threshold: **+4% is right, don't raise it.** n≥30 floor caught the small-sample trap |
| 0012 | balanced-program (master) | unseen-universe → forward-wall | RUNNING — results-focused program master: baseline LOCKED (baseline_wf_2026_06, mean Sharpe 1.36 / std 1.85). BALANCED scorecard (trades/WR/return/drawdown; composite>0 + floors + DSR>0.95). Phases: 0013 (KILL), 0014 mean-reversion sleeve (next). DSR n_trials ledger at 18 |
| 0013 | vol-managed-exposure | walk-forward (sizing-only; unseen-universe N/A) → forward-wall | COMPLETE — **KILL** (all 4 configs). Regime/vol gross-exposure overlay: effect within noise (mean Sharpe ±0.08, DSR 0.19–0.28 ≪0.95), no config wins ≥70% folds vs off. **Redundant with the live BEAR block** (entries already gated out of BEAR → nothing left to re-scale); **2025 unchanged** (its losses are in CHOPPY/BULL = a SIGNAL problem, not exposure). Redirects program to Phase 2 (MR sleeve) + Phase 3 (orthogonal alpha) for the non-BEAR bad years |
| 0014 | mean-reversion-sleeve | unseen-universe → forward-wall | COMPLETE — **KILL (reproducible).** Non-reproducible runs gave a favorable-noise "strongest signal" (6/10→8/10 swing); the DECISIVE reproducible sweep = 5/10 folds, mean Sharpe +0.025 (flat), DSR 0.05. +37% trades but no risk-adj edge; 2025 got WORSE. Both bad-year levers (P1 exposure, P2 MR) KILLed → 2025-type losses not fixable by portfolio construction. RULE: reproducible-only verdicts (noise nearly promoted a worthless sleeve). _Original (withdrawn) framing:_ **STRONGEST signal of the program.** Rules-based MR sleeve (CHOPPY-only oversold bounce), per-row merged w/ momentum. Fires exactly in the bad years: **2025 Sharpe −1.44→−0.67 (+0.77), WR +9.1pp**; 2023 +0.44; 2022 +0.26; 2019 +0.23. Aggregate: mean Sharpe 1.26→1.36, **std 1.89→1.68** (consistency↑), **trades +37% (→130/yr, clears 120)**, WR +0.8pp; **balanced composite +0.115 (best yet)**. KILL on `sharpe_wins` 6/10 (needs 7) — diversification trade-off dilutes good years (2017/2020/2024). Floor calibrated for momentum upgrades, not variance-reducing sleeves. Two no-op gate bugs found+fixed first (PR #60 adx/rsi, #61 min_predicted_return). → 0015 refines. n_trials→19 |
| 0015 | mr-thin-book-gating | unseen-universe → forward-wall | COMPLETE — **INCONCLUSIVE** (refinement adds nothing) + KEY METHOD FINDING. thin3/thin5 ≈ plain mr (all PROMOTE here: composite +0.095–0.098, 7–8/10). But the SAME un-gated mr scored 6/10 in v3 (KILL) vs 8/10 here (PROMOTE) — the `sharpe_wins` verdict swings ±2 on NON-REPRODUCIBLE model-fit noise. AGGREGATE signal robust across both runs (composite +0.10–0.12, trades +33%, mean Sharpe +0.12, consistency↑, bad years lifted); per-fold VERDICT unstable. → decisive verdict needs a REPRODUCIBLE sweep (added to mr-sleeve.yml). n_trials 21 |
