# January 2027 review — dossier (DRAFT, facts only)

**Status: DRAFT for the owner's January review. Nothing here changes live trading, capital, a rule or a count.**
Standing counts: **screens 24 · sealed opens 4 · n_trials 3**. Every number below is quoted from a committed artifact,
whose path is given. Labels: [measured] = computed in the cited file; [inferred] = reasoning from those numbers.

Items placed on the agenda by the owner, 2026-11-19:
- the 60/40 fallback, recorded;
- the swing book, as a review item;
- 0001, as a review item.

No live change has been made.

---

## 1. 0001 (cross-sectional momentum)

**Alpha over beta**, weekly, net and gross of costs, pre-tax. Excess returns over 6.5%, OLS, Newey-West lag 8.
Regressor: the index fund (Nifty Midcap150 Momentum 50 TRI less 0.30% TER). [measured,
`diagnostics/research/explore/2026-11-19_0001_full_run_alpha.json`]

| period | net alpha / yr | net t | gross alpha / yr | gross t | beta |
|---|---|---|---|---|---|
| full run 2017-01..2026-06 | +1.49% | 0.44 | +3.21% | 0.93 | 0.906 |
| 2017-01..2019-02 | −17.80% | −2.56 | −16.48% | −2.32 | 0.621 |
| 2019-03..2024-06 | +8.01% | 1.87 | +9.90% | 2.31 | 0.958 |
| 2024-07..2026-06 | +3.97% | 1.03 | +5.46% | 1.40 | 0.956 |

**Beta to the momentum index**, regressing on the raw Nifty Midcap150 Momentum 50 TRI:
- full run 0.906, 2017–19 0.621, 2019–24 0.958, 2024–26 0.956;
- net alphas are 0.2–0.3pp lower than in the table above (full run +1.22%, t 0.36). [measured, same file]

**Deflated.** Bonferroni-equivalent hurdle for 141 lifetime trials: |t| ≥ **3.57**. The full-run net t is **0.44**:
**fails** (raw p 0.66). [measured, same file]

**Context.**
- Full-run CAGR is 21.73%, against 43% in the 2019–24 window.
- In 2019–24, a static mix matched to 0001's beta returned 32.7%.

[measured: `diagnostics/research/explore/2026-11-19_0001_full_run_alpha.json`;
`diagnostics/research/explore/2026-11-19_static_long_window_alpha.json`]

## 2. Swing book

| fact | value | source |
|---|---|---|
| Permutation p vs the label-shuffle (N1) / random-ranker (N2) placebos | **0.09 / 0.13** | [measured] `diagnostics/research/explore/2026-11-19_stress_suite_controls.json` |
| Net-of-cost alpha over the index fund, 2019-03..2024-06 | **−3.08% / yr, t −0.45** (beta 0.73) | [measured] `diagnostics/research/explore/2026-11-19_static_long_window_alpha.json` |
| After-tax CAGR standalone, 2019-03..2024-06, open positions taxed by their own holding period | **18.57%** (was 18.82%) | [measured] `diagnostics/research/explore/2026-11-19_after_tax_frontier.json`, `step2_swing_fix` |
| Harness validation (stress-suite placebos) | see §2a | `diagnostics/research/2026-11-19_stress_suite.md` |

The swing permutation p uses the placebos that failed the Amendment 1 baseline test, but the p-value is a different
statistic: the share of placebo seeds whose Sharpe is at least the strategy's. Amendment 1's error sat in the baseline,
not in the placebo Sharpe. [inferred]

### 2a. Harness result
Stress-suite placebo checks, swing only. Harness validation, not a verdict on swing.
[measured: `diagnostics/research/explore/2026-11-19_stress_suite_harness_step_a.json`,
`diagnostics/research/explore/2026-11-19_stress_suite_harness_step_b_n4.json`]

- **Step A, matched-fill baseline: fails.** Random entries run through swing's own exits earn +2.50pp a year (N1, z 4.27)
  and +2.23pp a year (N2, z 3.65) more than an exposure-matched equal-weight universe.
- **Step B (N4), random entries and random exits: passes.** Gap −1.47pp a year, z −1.74.
- **Reading** (fixed before the run): swing's exits carry the excess, a property of the strategy, not a harness bias.
  The harness is cleared for swing, and the shock table is released.

Swing's worst shock is S6 (a gap shock), with Sharpe 0.29. Every other shock keeps at least 83% of the unshocked Sharpe.
[measured: `diagnostics/research/explore/2026-11-19_stress_suite.json`]

## 3. Blend (70/30 0001/swing, vol-targeted)

| fact | value | source |
|---|---|---|
| Best point under the −25% cap, after tax, 2019-03..2024-06 | **18.36%** at 10% vol, arbitrage cash leg, p95 24.30 | [measured] `diagnostics/research/explore/2026-11-19_after_tax_frontier.json` |
| Best static point, same window | 65/35 index/arbitrage, **23.25%**, p95 24.73 (blend behind by 4.89pp) | same file |
| Rolling 3-year after-tax windows (excess Sharpe) won vs static 65/35 / vs the after-tax TRI | **0 of 28 / 0 of 28**. Only 1 non-overlapping 3-year window exists. | same file, `step5_mission_test` |
| Net-of-cost alpha over the index fund at 11% vol, 2019-03..2024-06 | +2.71% / yr, **t 0.75** (beta 0.54) | [measured] `diagnostics/research/explore/2026-11-19_static_long_window_alpha.json` |

## 4. Fallback (recorded 2026-11-19): 60/40 index fund / arbitrage fund

| fact | value | source |
|---|---|---|
| After-tax CAGR / p95 156w drawdown, 2017-01..2026-06 | **15.64% / 23.99**: the highest mix passing −25% (65/35 fails at 26.04) | [measured] `diagnostics/research/explore/2026-11-19_static_long_window_alpha.json` |
| Stress sub-period 2024-07..2026-06 (continuous slice) | 60/40: CAGR 2.54%, p95 **31.3** (fails). Only 40/60 and 45/55 pass on that slice; on fresh capital, mixes up to 50/50 pass | same file |
| Pre-tax anchor (owner fallback draft, daily-rebalanced 60% exposure, 2017–26) | 16.34% / 23.73, reproduced exactly | same file, `anchors` |

## 5. Options for the owner

| option | what it changes | what it costs |
|---|---|---|
| **(i) Core capital to 60/40; both sleeves paper-only** | Capital follows the measured best design under the cap. 0001 and swing keep running on paper and keep their 26-week forward clocks. | Gives up the blend's in-window upside (it led on gross return in 2019–24) for a design that led after tax in every measured window [inferred]. The 2024–26 stress slice says 60/40 can still breach −25% (p95 31.3). |
| **(ii) Retire swing; keep 0001 on paper** | The swing book stops; the blend can no longer be built as 70/30. 0001 continues as a forward challenger. | Loses the swing forward record. The evidence: alpha −3.08% (t −0.45) and permutation p 0.09/0.13; harness per §2a. 0001's own deflated test also fails (t 0.44 vs 3.57). |
| **(iii) Status quo** | No change. | The mission's own test is unmet: 0 of 28 rolling windows; after tax, the blend trails static by 4.89pp at the cap. Owner time continues on two books with no deflated evidence of edge [measured, §1–3]. |

## 6. Proposed gate for new candidates (draft for the owner's decision)

1. **Before any trial:** gross alpha over a beta-matched static mix (index fund + cash at the candidate's own beta),
   weekly, Newey-West lag 8, with **t ≥ 2 on the full available history**, not on a chosen window.
2. **Before capital:** whichever comes later of:
   - **(a)** the deflated hurdle, |t| ≥ 3.57 at 141 lifetime trials (Bonferroni-equivalent; the hurdle rises with the
     count);
   - **(b)** 26 weeks of forward paper.

Why: in 2019–24 alone, 0001 clears t ≥ 2 gross (2.31). Over its full run it does not (0.93). [measured, §1]
