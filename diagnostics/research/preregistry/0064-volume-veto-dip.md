# 0064 — volume-vetoes-the-dip (sign-conditioned dip-volume veto)

**Date:** 2026-06-23
**Track:** entry-quality VETO (sidecar — no retrain) — frozen-ledger overlay then paired walk-forward.
**Status:** PRE-REGISTERED (frozen below). Source: the Siddharth Bhanushali price+volume video (owner reference).
**Plan:** `~/.claude/plans/some-need-very-complex-golden-thunder.md` (Edge-mining scope).
**Cost discipline:** ONE DSR trial for this cell (frozen single definition, NO sweep). `n_trials.json` is bumped **+1 at Phase D** (the walk-forward, where the DSR is computed); the Phase-C overlay uses a bootstrap CI, not a DSR, but still spends the cell's one trial — additional pullback-definition variants would each be a new trial, so the definition is frozen here.

## Hypothesis (precise)
A healthy pullback into an entry should be volume-**dry**; a pullback that comes **with** volume is churn/distribution → the entry is lower-quality. The frozen model sees only POOLED, point-in-time volume levels (`volume_price_divergence_20d`, `obv_trend_30d`, OBV/MoneyFlow); it does NOT see this **sign-conditioned interaction** (down-swing volume × the 20d norm). That different functional form is why this is a NEW cell, not a re-test of 0004 (volume-confirmed-breakout as a feature, KILLed) or 0010 (delivery%, a pooled level/near-miss KILL).

## The FROZEN signal (no sweep)
`src/data/pullback_volume.py::pullback_volume_ratio` (lookahead-safe, unit-tested incl. truncation-invariance). At bar t, over the trailing **5-bar** window ending at t: `ratio = mean(volume on down-close days) / (20d average volume)`; **NEUTRAL = 1.0** when there is no down-day in the window (not a pullback entry). `>1` = elevated dip volume (churn, veto-eligible); `<1` = dry (healthy). The SAME function feeds the Phase-C overlay (`.asof(entry_date)` on raw `ds.ohlcv`) and the Phase-D sidecar (per-stock series in `data_store`, on the cleaned OHLCV) — formula identical, so probe ↔ ship parity.

## Phase C — frozen-ledger overlay gate (the cheap, decisive test)
`diagnostics/run_volveto_overlay.py` runs the production backtest (`cfg0 = models/v1/config.json`, `REPRODUCIBLE_MODE=1`), annotates each trade with `pullback_volume_ratio` at entry, and (over only the **pullback** trades, ratio ≠ NEUTRAL) computes — via `diagnostics/_volveto_overlay_core.py` (unit-tested) — `ratio_vs_pnl` (Spearman + dry−churn bucket gap) and `dry_vs_churn` (bootstrap CI).

**PRE-COMMITTED PASS iff ALL:** Spearman(ratio, return) **≤ −0.05** (churn predicts worse) **AND** dry(lowest-ratio bucket) − churn(highest-ratio bucket) mean return **> 0** **AND** the dry−churn bootstrap **CI-low > 0**. This is the EXP-0/0062 overlay discipline, mirrored for the inverted veto hypothesis. **KILL on any miss** — the program ends here for ~one backtest (a straddling CI is a KILL, not a re-roll). The full per-trade ratio/return is dumped for a cheap local audit (no re-run).

## Phase D — production gate (only if Phase C PASSES)
Implement `pullback_volume_ratio` as a **SIDECAR** in `data_store._compute_stock_features` (AVAILABLE-only, NOT in `V1_FEATURES` — the `sweep_20d` contract → no retrain, frozen model untouched) + a **flag-gated admission override** (mirroring `sweep_override_enabled` in `models/v1/config.json`; golden-master byte-identical when off). Bump `n_trials.json` **+1 before** the run. Paired production walk-forward (book-with-veto vs book-without). **Ship iff ALL:**
- per-trade after-cost **CI-low > 0** on the paired difference,
- **DSR > 0.95** at the updated n_trials (empirical skew/kurtosis),
- **per-fold consistency** (≥2019 folds are the trustworthy window per the survivorship caveat),
- **orthogonality cross-check** — `return_correlation` of the veto signal vs `volume_price_divergence_20d` + delivery **< 0.30** (else the model already sees it → 0004 redundancy trap → KILL).

## Governance / what ships
PASS authorizes only research → a golden-master-safe flag-gated wiring → a shadow period → the forward wall (0003) before anything touches the ~10 users' signals. No live change without owner sign-off. Compliance-safe: this is a candidate change to a model-generated decision-support entry filter; no guarantee of outcomes.

## VERDICT (2026-06-23) — KILL, honored (program CLOSED)
Run **28016010288** (REPRODUCIBLE, 671 trades, 596 pullback, **0% skipped**). The Phase-C gate FAILED — and the signal is the **WRONG SIGN**:
- Spearman(ratio, return) = **+0.099** (needed ≤ −0.05 — POSITIVE, opposite to the hypothesis).
- dry−churn bucket gap = **−16.4** (needed > 0).
- dry (low ratio): mean ret **8.7%** / WR 66.4% vs churn (high ratio): **11.6%** / WR 72.5% → **churn BEATS dry** (mean_diff −2.84, CI [−14.99, +7.92]).
- Buckets: the most-"churn" bucket (ratio 1.14–4.71) was the **best** (20.7% / 77.5% WR); the most-"dry" (0.1–0.49) was the **worst** (4.3% / 59.7%).

"Volume vetoes the dip" is **reversed** for our momentum book: pullback-on-volume is not distribution — for a momentum name it is demand/accumulation, and those trades did better. Bhanushali's dry-pullback rule is a mean-reversion/buy-into-support heuristic that does not transfer to a momentum engine. **KILL honored: no Phase D, no sidecar.** The Bhanushali edge-mining program is CLOSED — the deep-dive's prediction held (the engine IS his method; the one orthogonal idea adds no edge and tested backwards). The funnel did its job: a clean, decisive kill for ~one backtest.

**NOTE (recorded, NOT pursued):** the reversed sign ("pullback-on-volume = mildly positive") is a DIFFERENT hypothesis. It is most likely **collinear** with the model's existing volume features (`volume_ratio`/`accumulation`/`volume_breakout` already flag high-volume bars the momentum model favors). Pursuing it would be a new cell needing its own pre-reg + a corr<0.30 check vs those features — flagged for the owner's judgment, not auto-pursued (one-shot KILL discipline + the correlated-cell rule).

## FOLLOW-UP (2026-06-23) — the reversed signal measured properly, then KILLed on the right angle
The 0064 KILL was of the dry-pullback hypothesis; the REVERSED signal (high-pullback-volume ratio≥1.14
beats: 20.7%/78% vs 7.5%/67%, ~7/9 years) was initially dismissed as "collinear, not pursued" WITHOUT
measuring — owner correctly flagged this as a lazy kill. Re-ran the overlay capturing per-trade
**confidence** (run 28019130664) for the control test "does it add edge BEYOND the model's selection":
- **Orthogonal to confidence** (corr(ratio,conf)=+0.07) — so it LOOKED like new info.
- **But it's a 2019 fat-tail mirage:** the 20.7% is 2019 (16 trades @ **+103%**); ex-2019 = **8.0% vs 5.7%
  = +2.3pp, CI [−0.26,+4.94] straddles 0**. The "+47% within the middle-confidence stratum" = **six 2019
  trades @ +264%**. In the TOP-confidence tercile high-vol **inverts** (−5.16pp, loses where it'd matter most).
- **VERDICT: KILL (earned, right angle).** Not a deployable edge — one fat-tail year, reverses at high
  conviction. LESSON (both directions): don't lazy-kill a lead (measure it), and don't promote an
  in-sample per-trade subset stat (it was a fat-tail artifact). Process fix adopted: explore-first →
  edge must be spread across years AND survive controls → OOS-validate, before belief.

## Provenance
Plan: the vectorbt + Bhanushali Edge-mining program. Reuses `_exp0_overlay_core` helpers (`_spearman`/`_wr_mean`) and the EXP-0 cloud-overlay pattern (`run_exp0_structure_overlay.py`). Caveat: raw `ds.ohlcv` split days (~16 F5 names) can momentarily distort the ratio in the overlay; the ratio is volume/volume (scale-invariant) and the effect on the dry-vs-churn contrast is immaterial; the Phase-D sidecar uses the cleaned OHLCV.
