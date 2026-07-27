# Finding 0117 — The post-entry domain is HINDSIGHT-ONLY: all three cohorts fail in-flight identifiability (Stage 1; 0 trials)

**Type:** MEASUREMENT (train years 2019-01..2024-06 only; sealed set untouched; no Stage 2 proposed).
Scripts: `diag_postentry_stage1.py` (+ the forward-leg check), `diag_week_anchor.py`. Dataset: the banked
0116 context/label parquet + in-flight path features (bars strictly <= each decision time — firewall kept).
Prior exit-family verdicts stated per protocol: 0104/0105/0106/0109 all KILL — but those were
UNCONDITIONAL geometry; this study asked whether CONDITIONAL, path-informed decisions could do better.

## 1. Whipsaw vs false-touch — NOT distinguishable at stop time
noise_stop (n=391) vs false_touch (n=314) at the moment of the stop: **every candidate discriminator's
CI straddles zero** — MAE depth −0.12 [−0.70,+0.28], time-to-trough +4.9d [−3.3,+12.9], MAE speed,
gap-vs-grind share +0.03 [−0.05,+0.12], and weekly-structure-intact **48% vs 47%**. The whipsaw giveback
pool is huge in hindsight (**+753R** over 391 trades, mean +1.93R) and **entirely unreachable**: the stop
cannot tell which of its victims will recover. (0105's whipsaw lesson, now proven from the information
side: no smarter stop discriminator exists in this data.)

## 2. The pyramid / left-on-table premise — killed by the autocorrelation confound
exit_too_early winners are unmarked at day-10 (all CIs straddle; vol10's +0.002 is noise-scale).
The seductive headline IC(ret10 → final R) = **+0.356** (6/6 years) is **entirely the mechanical head
start**: the decision-relevant quantity, IC(day-10 strength → SUBSEQUENT leg R) = **−0.029**, per-year
{−0.11, −0.04, +0.02, −0.09, −0.00, −0.12} — zero-to-negative in 6/6 train years, no tercile gradient.
**Post-entry strength carries no forward information.** The "winners work immediately" forensic described
a head start, not a signal; an add at day-10 buys a leg with no expected edge at a worse cost basis.

## 3. Rotation — the bound is below the noise floor
Hindsight-perfect cut+rotate on the capped book's train losers: **+61R over 5.5y (~11R/yr)** — and that
requires knowing losers in advance; the same-week substrate queue's median alternative was **net negative**
(−2.5R sum). A realistic rule captures a fraction → ~1-3R/yr, under the ±10R/yr path-noise floor
(0109). The domain closes cheaply, exactly as the bound-first design intended.

## Bonus (free diagnostic): the weekly construction is anchor-robust
Rotating the week boundary (ISO Mon-Sun → Thu-Wed): Sharpe 1.132 → 1.079, trades 255 → 253, DD −42.4 →
−40.9. **dSharpe −0.053 = STABLE** — the edifice is not an artifact of the week anchor. A genuine trust
gain at zero cost.

## The completed information map (the program-level result)
With this, the ENTIRE trade lifecycle is measured: pre-entry (4 independent walls: bar-level ML, loser
forensics, Phase-1 levers, 0116 path-level), entry geometry (Phase-1/O-022), exit geometry
(0105/0106/0109 — unconditional), **post-entry conditional (this study — hindsight-only)**, and post-exit
(labels). **The price path carries no exploitable conditional information anywhere on this funnel beyond
the original signal + week-relative selection.** The book's R is earned by HOLDING through noise the
information cannot resolve — which is why every "manage it smarter" lever dies. Selection of what to
test next should leave the price path of this funnel alone.

## Stage-2 recommendation: NONE
Per the commissioning brief, a hindsight-only readout is a success that closes the territory. No
candidate survives to a pre-reg; no trial is warranted; n_trials stays 138.
