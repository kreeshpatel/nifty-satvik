# 0076 — Uncapped target + ATR-proportionate trailing: does letting winners run behind a vol-scaled trail beat the flat exit?

- **ID:** 0076 (Stage-D exit machinery; Entry-Signal Arc successor to 0071). Owner-approved 2026-07-02.
- **Registered:** 2026-07-02, BEFORE the run. **TRIAL** (PROMOTE/KILL decision), 4 grid arms →
  **cumulative_n_trials 82 → 86, incremented BEFORE the run** per the discipline.
- **Anchor / data:** pinned `baseline_v1` (`dataset-pin-20260701`, sha `f8625a8f…52142`), frozen cfg,
  corrected universe, 2017-01-01..2026-06-30. Byte-reproducible.
- **Supersedes-context:** re-opens the 0071 "let-winners-run" lead with (a) a **genuinely new
  formulation** (ATR-proportionate trailing WIDTH — 0071 only varied the target, holding the flat
  4.27% trail fixed), and (b) a **corrected sub-period gate**: 0071's WEAK-SHADOW downgrade used a
  fresh-capital per-half re-run (phantom base 2022-26 Sharpe 0.762 / DD −40.0). The correct
  continuous-slice base is **0.570 / −46.3**; on it the loosen-target family is UNDERPOWERED, not a
  bull artifact (see [[subperiod-gate-continuous-slice]]).

## Hypothesis
Removing the +22.52% target un-truncates the momentum right tail (base clips 17.7% of trades at
exactly +22.5%; uncapped surfaces 95 trades >+22.5%, top +125%), and replacing the flat 4.27%
trailing stop with a width that scales to each name's ATR (`trail_atr_mult × atr_pct`) protects the
open profit proportionally to the name's own volatility — improving Sortino/Calmar AND cutting the
2022-26 drawdown, and surviving the correctly-sliced 2022-26 gate that flat-trail variants only
marginally clear. Falsifier: ΔSharpe CI straddles 0, OR DSR ≤ 0.95, OR the 2022-26 (continuous-slice)
ΔCAGR ≤ 0, OR the best arm is a lone spike between failing neighbours (overfit) → UNDERPOWERED/KILL.

## Candidate (grid; frozen path byte-identical when off)
`cfg["target_pct"]=999` (OFF sentinel) + `cfg["trail_atr_mult"] ∈ {2.0, 2.5, 3.0, 3.5}`. The trailing
stop width becomes `trail_atr_mult × atr_pct_63` (per name) instead of the flat `trailing_pct=4.27`;
`trailing_activate_pct=4.0` unchanged. Implemented in `nq.engine.exits.decide_exit` (reads
`cfg["trail_atr_mult"]` + `position["atr_pct"]`), wired through `portfolio.simulate`'s `exit_cfg`.
**Inert when `trail_atr_mult` is absent** (frozen cfg) → golden master byte-identical (verified by
`tests/test_stage2_golden.py`). Median `atr_pct_63` ≈ 2.75%, so the grid brackets ~5.5%–9.6% flat-
equivalent trail widths (the flat-8% in-sample lead ≈ 2.9×).

## Method
Per arm: paired 63-day block bootstrap (n=5000) of ΔSharpe **and ΔSortino** (candidate − base) + DSR
(candidate) at n_trials=86, via `nq.runner.research.evaluate_overlay` (authoritative 7-gate verdict,
continuous-slice sub-period) plus `bootstrap_delta(·, sortino)` for the ΔSortino CI.
`scripts/run_atr_trail_overlay.py` on the pinned universe. Report all four arms (grid shape is the
overfit tell), the exit-reason mix, and the 2017-21 / 2022-26 split.

## Decision rule (pre-committed) — the 7-criterion promotion bar
PROMOTE-CANDIDATE only if ALL: ΔSharpe CI-low > 0 AND point > 0.30 (NOISE_FLOOR) AND DSR > 0.95,
then ΔCalmar ≥ +0.05, 2022-26 (sliced) ΔCAGR > 0, ≥2019 fold-pass ≥ 60%, turnover ≤ +30%, mechanism
one sentence. Positive point but CI-low ≤ 0 → UNDERPOWERED. Else KILL. A PROMOTE here is EVIDENCE
only — a frozen-cfg exit change is the heavy path (walk-forward re-derivation of the mult + golden
regen + owner sign-off), never a live flip off this in-sample run.

## Skeptical prior (state it)
0071 found target-loosening improves the full-period point estimate but is **UNDERPOWERED** (ΔSharpe
CI straddles 0 at ~34 windows, DSR 0.27); 0034 **KILLED** partial scale-out (clips winners, −0.125).
Priors say the DSR at 86 trials is a steep hurdle and the wider-trail edge may again be
uncertifiable at this sample. The one genuinely new element vs 0071 is the ATR-proportionate trail:
in-sample it turned the flat-trail lead regime-consistent (uncapped+trail8: full/bull/live Sharpe
1.02/1.05/0.98, live DD −46.3→−34.9) where flat-6% vs -8% vs -12% was non-monotonic — i.e. flat % is
a fitted point and ATR-scaling is the robustness fix. UNDERPOWERED is a first-class, expected outcome;
do NOT retune the mult toward a pass.
