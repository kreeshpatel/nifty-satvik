# forward/prereg_signal_quality.md — Per-Signal Quality Forward-Wall Pre-Registration

*Status: **PRE-REGISTERED**. Frozen by the owner 2026-08-17 BEFORE the forward data accrues.
Definitions and the decision rule below do not change between reviews (tighten-or-clarify only).*

**Class:** MEASUREMENT (forward evidence on the live book's own signals). **Spends no trial —
`n_trials` unchanged at 2.** Standing counts: screens 19 · sealed opens 1 · n_trials 2 (read from
`diagnostics/research/n_trials.json` + `diagnostics/research/label_screen_ledger.md`, not from here).

---

## 0. Why this wall exists, and the trap it avoids

Two grade-A signals in one week — **PTCIL** (bought 2026-08-07) and **CCL** (flagged 2026-08-14) —
passed the identical mechanical gate yet were plainly different trades: PTCIL a deep-touch, solid-green,
healthy-R setup; CCL a shallow-stall, doji, fragile-R one. The engine's own quality flags separated
them (`conviction` normal vs low). The open question is whether those flags **predict forward outcome**
— i.e. whether acting on them would build a stronger book.

The trap: gather many quality fields, then at the wall's end go looking for which one "worked". Across
K axes that is K bets, and the best-looking one is a lottery winner, not an edge — the exact
overfitting this programme corrects with the Deflated Sharpe Ratio and PBO (`nq/validation`, finding
0140). **The forward wall's whole purpose is to fix the hypotheses BEFORE the data exists**, so the
end read is confirmatory. This document is that fixing.

## 1. The family (FROZEN — four axes, no single primary)

Owner decision 2026-08-17: register all four as **one family**, judged with the multiplicity
correction at the wall — no single decision-driving axis. Each axis is a per-signal quality feature
recorded **at signal time** with a pre-committed directional hypothesis (higher forward R when…):

| # | Axis | Definition (frozen) | Hypothesis | Prior thread |
|---|---|---|---|---|
| Q1 | **body_ratio** | signal-week `\|close−open\| / (high−low)` | solid green (≥0.50) > doji (<0.50) | `research/preregistry_small_candle.md` (`min_body_frac` 0.50) |
| Q2 | **touch_depth** | **minimum** `dist_to_sma_pct` over the 8 weeks ending at the signal week (the *pullback low's* extension, NOT the signal-week ext) | deep (<5%) > shallow (5–10%) | `deep-near-sma-touch-edge` (+0.717R vs +0.094R) |
| Q3 | **signal_conviction** | engine composite flag as recorded | normal > low | — |
| Q4 | **crs_rank** | `crs_rank` at signal (higher = stronger RS) | top tercile > bottom tercile | — |

**Q2 subtlety, pre-committed:** touch depth is the *pullback low*, not the signal-week extension.
PTCIL signalled at 9.94% ext but *touched* 2.5% (the green week carried it up); CCL never went below
8.6%. The discriminator is the minimum ext over the trailing pullback, computed from the weekly panel /
OHLCV. Signal-week ext is recorded too, but Q2 is defined on the minimum.

No axis may be added, removed, or re-defined after this date. A fifth idea is a **new** pre-registration
with its own clock, not an amendment here.

## 2. The outcome and the dataset

- **Outcome metric:** forward **`r_multiple`** on each **closed** signal (`results/signals_history_weekly.json`,
  `r_multiple` / `exit_reason`). Secondary: `return_pct`, win (r>0), hold_days.
- **Dataset:** **every FRESH signal, all grades**, from its first-fresh appearance forward — read from
  the immutable weekly archives (`results/archive/YYYY-MM-DD/signals_today_weekly.json`), never a
  re-derivation. Forward-only: a signal enters the table at its signal week and its outcome fills in
  when it closes. The full-signal population (not just names actually bought) is the unit — self-reported
  personal buys are a chosen subset and are not the test set.
- **Inception:** 2026-08-17 (this pre-reg). Signals already FRESH before inception (e.g. PTCIL 08-07,
  CCL 08-14) are recorded as **seed** rows, labelled, and reported separately from the strictly-forward
  set so they can never quietly become in-sample.

## 3. The wall-end read (FROZEN procedure)

At the forward-wall review (the swing book's Oct-1 review and each quarter after, cumulative):

1. Build the quality→outcome table via `scripts/collect_signal_quality_forward.py` (reads only the
   immutable archives + `signals_history`).
2. For each axis Qi: the mean forward `r_multiple` in the hypothesised-strong bucket minus the weak
   bucket, with a bootstrap CI, **and** the per-year sign.
3. **Multiplicity correction over the family of four** — the axes are a config family, so the winner is
   judged through `nq.runner.research.adjudicate_family` (PBO on the four per-axis long-short return
   series) and a Bonferroni/Holm bar on the per-axis CIs. An axis "carries information" only if it
   survives the family correction, not on its raw CI.
4. Report **all four regardless** — a null on an axis is a finding worth keeping (it stops the idea
   being re-tried), never dropped.

## 4. Power — stated honestly, in advance

8 closed signals at inception (all `HIT_STOP`, avg r ≈ −1.5 — a genuinely rough start). Over a quarter
the closed count grows to roughly 30–60. Per backtest-rigor §E1 that is enough to **rank the axes by
per-trade forward R and see a directional separation**, and **not** enough for a Sharpe/ΔSharpe verdict
(needs 100+). Therefore:

- **UNDERPOWERED is a first-class outcome** and simply carries the wall another quarter (mirrors
  `prereg_swing` §4). No axis is killed for an inconclusive CI; no axis is adopted on a thin one.
- **This collection is EVIDENCE, not authorization.** A positive family result **does not** change the
  strategy. It justifies a **separate, pre-registered trial** of a specific quality gate (which *would*
  spend an `n_trials`), run through the full verdict machine on the corrected universe. The gate itself
  is never adopted off this forward table alone (small-sample in-sample fit is meaningless —
  `pursue-learning-bot-judge-oos`).

## 5. Integrity commitments

- **Definitions frozen** (§1). Thresholds (0.50 body, 5% touch, tercile) are tighten-or-clarify only; a
  relaxation voids this pre-reg and restarts its clock.
- **No peeking-driven change.** The engine's config, grading, and thresholds are frozen between reviews;
  nothing in the book reads this table.
- **Recorded-at-signal, never back-edited.** Quality flags come from the archived signal snapshot at the
  signal week; outcomes come from the append-only history. The collector rebuilds deterministically from
  immutable archives — it holds no editable state.
- **Spends no trial** (`n_trials` stays 2); this is forward measurement of signals the book already
  issues.

## 6. What a positive result authorizes (the next step, not this step)

If, at a review with adequate power, an axis (or a conjunction) survives the family correction with a
material forward-R separation and a consistent per-year sign: open a **new** pre-registration for a
quality-gate trial (e.g. "skip `conviction=low`" or "require `body_ratio ≥ 0.50`"), increment
`n_trials`, and run it through `evaluate_overlay` / the mechanized bar on the corrected universe. Only
that trial can change the live book. This document only decides *which questions the forward wall is
answering*.
