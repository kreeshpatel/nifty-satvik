# January 2027 review — dossier (DRAFT, facts only)

**Status: DRAFT for the owner's January review. Nothing here changes live trading, capital, a rule or a count.**
Standing counts: **screens 25 · sealed opens 4 · n_trials 3**, read from `diagnostics/research/n_trials.json` and
`diagnostics/research/label_screen_ledger.md` on 2026-11-20. Every number below is quoted from a committed artifact,
whose path is given. Labels: [measured] = computed in the cited file; [inferred] = reasoning from those numbers.

**Last updated 2026-11-20.** First drafted 2026-11-19 at `forward/drafts/2027-01_review_dossier.md`, moved here. Added
since the first draft: the screen #25 stop-domain closure (§6), the cost and tax waterfall (§7), the tax Monte Carlo
(§8), the Phase 0 data state (§9), the cash-leg reconciliation and the index-leg tracking difference (§4). The owner
decisions are on one page: `forward/drafts/2027-01/decisions.md`.

> **Correction (2026-11-20, PR #219's close-out report):** `diagnostics/research/2026-11_phase0_closeout.md` §D said
> the long-window 60/40 study used "the index TRI less fees plus a modelled liquid fund". That is wrong for the
> long-window study. Its cash leg is the **real arbitrage-fund average** (Kotak 119771 + ICICI 120364, Direct-Growth NAVs
> from January 2013); the liquid model belongs to the earlier 2019–24 study (`explore_after_tax_comparison.py`). The
> figure **15.64% / p95 23.99 stands.** Using the forward record's single fund (119771) instead gives
> **15.67% / 23.97**. See §4. [measured: `pipelines/diagnostics/explore_static_long_window_alpha.py:135-150`;
> `diagnostics/research/explore/2026-11-20_cash_leg_reconciliation.json`]

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

**Index-leg caveat (new, §4b).** The regressor is the TRI less 0.30%. The real fund 150738 trails that model by about
1.05pp a year. Against the real fund, each alpha in this table would be higher by about beta × 1.05pp a year, if that
shortfall held before 2022 [inferred]. The
deflated verdict does not change: t 0.44 is far from 3.57.

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
| Live stops = backtested stops | same rule in code (`scripts/run_bhanushali_cron.py:596` → `_record_stop` at `:332`) | [measured] `diagnostics/research/explore/2026-11-19_stop_conformance_and_fall_discriminator.md`, Part 1 |
| Stop domain | **closed for this book by owner rule (screen #25 bound)**, §6 | same file |

The swing permutation p uses the placebos that failed the Amendment 1 baseline test, but the p-value is a different
statistic: the share of placebo seeds whose Sharpe is at least the strategy's. Amendment 1's error sat in the baseline,
not in the placebo Sharpe. [inferred]

### 2a. Stress suite: harness result and shocks
Stress-suite placebo checks, swing only. Harness validation, not a verdict on swing.
[measured: `diagnostics/research/explore/2026-11-19_stress_suite_harness_step_a.json`,
`diagnostics/research/explore/2026-11-19_stress_suite_harness_step_b_n4.json`]

- **Step A, matched-fill baseline: fails.** Random entries run through swing's own exits earn +2.50pp a year (N1, z 4.27)
  and +2.23pp a year (N2, z 3.65) more than an exposure-matched equal-weight universe.
- **Step B (N4), random entries and random exits: passes.** Gap −1.47pp a year, z −1.74.
- **Reading** (fixed before the run): swing's exits carry the excess, a property of the strategy, not a harness bias.
  The harness is cleared for swing, and the shock table is released.

Swing's worst shock is **S6 (a gap shock)**, with Sharpe 0.29. Every other shock keeps at least 83% of the unshocked
Sharpe. S6 is severe by construction (about 2.5 extra −8.46% gaps per name per year, on top of the real ones) and is
the worst shock for all three books; the owner kept it as recorded. [measured:
`diagnostics/research/explore/2026-11-19_stress_suite.json`; `diagnostics/research/2026-11-19_stress_suite.md`]

## 3. Blend (70/30 0001/swing, vol-targeted)

| fact | value | source |
|---|---|---|
| Best point under the −25% cap, after tax, 2019-03..2024-06 | **18.36%** at 10% vol, arbitrage cash leg, p95 24.30 | [measured] `diagnostics/research/explore/2026-11-19_after_tax_frontier.json` |
| Best static point, same window | 65/35 index/arbitrage, **23.25%**, p95 24.73 (blend behind by 4.89pp) | same file |
| Rolling 3-year after-tax windows (excess Sharpe) won vs static 65/35 / vs the after-tax TRI | **0 of 28 / 0 of 28**. Only 1 non-overlapping 3-year window exists. | same file, `step5_mission_test` |
| Net-of-cost alpha over the index fund at 11% vol, 2019-03..2024-06 | +2.71% / yr, **t 0.75** (beta 0.54) | [measured] `diagnostics/research/explore/2026-11-19_static_long_window_alpha.json` |
| 11% vol target with real NSE price bands (the 11% draft's condition precedent) | p95 **23.48** (base 23.35); condition met | [measured] `diagnostics/research/2026-11-18_robust_sizing.md` Part 3 |

**Frontier caveat (§4b).** Every static point in this table models the index leg as the TRI less 0.30%. With the real
fund's measured shortfall added, the static after-tax CAGRs fall by roughly 0.6–0.7pp at 60–65% index weight
[measured for 60/40 on 2017–26: 15.67 → 14.97, §4]. The blend still trails the static point at the cap [inferred:
4.89pp gap vs a ≈0.7pp shift].

## 4. Fallback (recorded 2026-11-19): 60/40 index fund / arbitrage fund

**Code path of the figure.** `pipelines/diagnostics/explore_static_long_window_alpha.py`:
- `:130-131` reads both arbitrage NAV series and asserts they start before the window ("proxy needed" otherwise);
- `:135-142` `prices_on`: index = TRI daily return less 0.30%/252; cash = the **equal average of the daily returns of
  Kotak 119771 and ICICI 120364**;
- `:150` `F.run("static", ..., cash=F.ARB)`: the arbitrage leg, not the liquid model (`AT.LIQ`);
- `:145` records `"liquid_proxy_used": false`.
[measured]

| fact | value | source |
|---|---|---|
| After-tax CAGR / p95 156w drawdown, 2017-01..2026-06, study of record (two-fund arbitrage average) | **15.64% / 23.99**: the highest mix passing −25% (65/35 fails at 26.04) | [measured] `diagnostics/research/explore/2026-11-19_static_long_window_alpha.json`, reproduced exactly in `2026-11-20_cash_leg_reconciliation.json` (`anchor`) |
| Same, cash leg = **119771 only** (the forward record's fund) | **15.67% / 23.97**; 55/45 14.96 / 21.82; 65/35 16.36 / 26.04 (fails) | [measured] `diagnostics/research/explore/2026-11-20_cash_leg_reconciliation.json` |
| Same, 119771 only **and** the index leg's measured fund shortfall (−1.05pp/yr) added. *Added after first look* | **14.97% / 24.22** (still passes); 65/35 15.59 / 26.35 | [measured] same file, `added_after_first_look_index_drag_sensitivity` |
| Stress sub-period 2024-07..2026-06 (continuous slice) | 60/40: CAGR 2.54%, p95 **31.3** (fails); 119771 only: 2.56% / 31.30. Only 40/60 and 45/55 pass on that slice; on fresh capital, mixes up to 50/50 pass | [measured] both files |
| Pre-tax anchor (owner fallback draft, daily-rebalanced 60% exposure, 2017–26) | 16.34% / 23.73, reproduced exactly | `2026-11-19_static_long_window_alpha.json`, `anchors` |
| Forward record | `forward/benchmark_60_40/` (funds 150738 + 119771, ₹20,00,000 notional, 5pp drift rebalance, hash-chained ledger); first row due Friday 2026-11-27 | `diagnostics/research/2026-11_phase0_closeout.md` §D |

**Independent re-derivation (rule 3).** A fresh blind replica, given only the written spec, gives 60/40 with 119771 alone
at **15.667% / p95 23.968** (original 15.67 / 23.97) and a fund − model difference of **−1.048pp** (original −1.05). The
difference is under 0.01% relative. [measured: `diagnostics/research/explore/2026-11-20_cash_leg_replica/RESULT.md`]

### 4b. Index leg: TRI less 0.30% vs fund 150738 [measured, `2026-11-20_cash_leg_reconciliation.json`, `index_leg`]

Common dates 2022-10-31..2026-11-13 (992). Tracking difference = fund return − comparison return.

| year | fund | TRI | TRI − 0.30% | fund − TRI | fund − model |
|---|---|---|---|---|---|
| 2022 (from 31 Oct) | −5.20% | −4.62% | −4.67% | −0.58pp | −0.53pp |
| 2023 | +49.84% | +52.48% | +52.04% | −2.64pp | −2.19pp |
| 2024 | +30.89% | +32.30% | +31.91% | −1.40pp | −1.01pp |
| 2025 | −4.20% | −3.46% | −3.75% | −0.74pp | −0.45pp |
| 2026 (to 13 Nov) | +3.15% | +3.79% | +3.52% | −0.64pp | −0.38pp |
| **annualised** | **16.27%** | **17.66%** | **17.32%** | **−1.40pp** | **−1.05pp** |

Daily tracking error 0.50% a year. The shortfall is larger in strong years (2023: −2.19pp against the model), which
fits a drag that is proportional to the return, such as cash held at rebalances, rather than a fixed fee [inferred].
**Every study that used "TRI less 0.30%" as the index fund overstates the real fund by about 1pp a year.** That
includes the frontier, the long window, the alpha regressions and the tax Monte Carlo [inferred from their method
sections]. Four years, one fund, one path.

## 5. Options for the owner

| option | what it changes | what it costs |
|---|---|---|
| **(i) Core capital to 60/40; both sleeves paper-only** | Capital follows the measured best design under the cap. 0001 and swing keep running on paper and keep their 26-week forward clocks. | Gives up the blend's in-window upside (it led on gross return in 2019–24) for a design that led after tax in every measured window [inferred]. The 2024–26 stress slice says 60/40 can still breach −25% (p95 31.3). With the real fund's shortfall, 60/40's expected after-tax CAGR is nearer 15.0% than 15.6% (§4). |
| **(ii) Retire swing; keep 0001 on paper** | The swing book stops; the blend can no longer be built as 70/30. 0001 continues as a forward challenger. | Loses the swing forward record. The evidence: alpha −3.08% (t −0.45) and permutation p 0.09/0.13; harness per §2a. 0001's own deflated test also fails (t 0.44 vs 3.57). |
| **(iii) Status quo** | No change. | The mission's own test is unmet: 0 of 28 rolling windows; after tax, the blend trails static by 4.89pp at the cap. Owner time continues on two books with no deflated evidence of edge [measured, §1–3]. |

**Lead quant's recommendation (recorded 2026-11-19): option (i).** The owner decides in January.

**Notes carried to January:**
- **0001 N2 harness check (Amendment 2).** The gap is −0.58pp a year at z −3.39. No N4 check was run on 0001, by
  owner decision. Source: `diagnostics/research/explore/2026-11-19_stress_suite_controls_a2.json`.

## 6. Stop domain: closed for the swing book by owner rule (screen #25) [measured]

Source: `diagnostics/research/explore/2026-11-19_stop_conformance_and_fall_discriminator.md`;
`diagnostics/research/explore/2026-11-19_results_stop_bound.json`. Counted as screen #25 by owner ruling (commit 93e902e).

- **Discriminator.** Two features' CIs excluded zero, (c) and (e). (e): a false touch is 2.4× as likely as a noise stop
  to have had a results meeting in the 5 sessions before the stop.
- **Hindsight bound for (e)**, 74 flagged stops held to the eventual exit: +116.3R total, **+21.1R a year**, but the
  per-year sign flips in **3 of 6 years**; one trade (CUMMINSIND, +85.8R) carries 74% of the total. The secondary
  reading (banked 21-session path) is −0.4R a year with 4 flips.
- **Owner's kill rule** (R/yr < 10, or sign flips in ≥ 2 of 6 years): **met**. Recorded as "stop domain closed for this
  book by owner rule (screen #25 bound)". It is a bound, not a KILL; re-opening needs a pre-registered run under the
  current harness (2026-08-08 amendment).
- No exploration-lane candidate comes from the stop domain.

## 7. Cost and tax waterfall, 2019-03..2024-06 (pp of CAGR) [measured, `diagnostics/research/explore/2026-11-19_blend_cost_tax.json`]

| book | gross | − engine costs | − expense ratios | − wrapper trading | − tax | = after-tax |
|---|---|---|---|---|---|---|
| blend 70/30 at 11% | 26.89 | 1.45 | 0.05 | 1.59 | 4.54 | **19.26** |
| 0001 alone | 45.59 | 2.83 | 0.00 | 0.05 | 6.78 | **35.92** |
| swing alone | 21.79 | 1.07 | 0.00 | 0.05 | 1.86 | **18.82** |
| static 65/35 | 25.55 | 0.00 | 0.31 | 0.00 | 2.22 | **23.02** |
| index fund at 11% | 25.80 | 0.00 | 0.32 | 0.04 | 5.04 | **20.41** |

- The blend starts with the highest gross of the fallback books and loses 7.6pp to after-tax, against 2.5pp for 65/35.
- Largest source: the wrapper layer (daily vol-target and 70/30 re-trading, 1.59pp, plus STCG on wrapper unit sales,
  ≈1.53pp) ≈ 3.1pp. 70% of the wrapper cost is trades over 2% of NAV; even a 2% no-trade band reaches at most 30% of it.
- Taxing net of transaction costs (Indian rules allow transfer expenses) would add about +0.26pp to the blend.
- The swing after-tax figure here is 18.82; the frontier's open-position fix makes it 18.57 (§2).
- Static rows use the TRI less 0.30% index model; see §4b.

## 8. Tax Monte Carlo (PR #214) [measured, `diagnostics/research/2026-11-19_tax_montecarlo.md`, `diagnostics/research/explore/2026-11-19_tax_montecarlo.json`]

Analysis, not tax advice; base rates `config/tax_india_fy2627.yaml` (CONFIRM WITH CA).

- **60/40, ₹20L, 2019-03..2024-06, law E, liquidated:** S0 p50 ₹29.75L (p5 26.18, p95 33.84). These draws assume 6–16%
  a year drift, far below the historical path's ₹57L.
- **Arbitrage vs liquid cash leg:** real spread +0.69pp a year (Kotak + ICICI arbitrage vs SBI + HDFC liquid,
  2019-03..2024-06); P(arbitrage beats liquid) **0.9995**, median +₹75k. This supersedes the earlier "coin flip, P 0.52".
  It depends on CA question 6 (§ decisions).
- **Harvest before 31 March:** P(gain > 0) 0.83 at a fixed pre-31-March date; a harvest that slips into April loses
  about a third of the gain.
- **Family split (3 PANs):** +₹81.1k median, P 0.989, **conditional on the split being legally valid** (CA questions 3
  and 4).
- **Company route:** −₹5.40L median, P(gain) 0.000 at zero owner surcharge; at 15–25% surcharge the company breaks even
  at a median ₹13.6 crore, without the final dividend only.

## 9. Company engine 0153: data state after Phase 0 [measured]

- **0153 is a DRAFT** awaiting signature (`diagnostics/research/preregistry/0153-company-engine.md`). Two dated owner
  notes (2026-11-20): known limits (PR #218), and **debt/equity is not a core L5 input** (it exists only from Sep-2022).
- **Results quarters still missing** after the NSE basis fallback: 1,145 of 16,941 PIT Nifty 500 member-quarters,
  2018-03..2026-06 (`diagnostics/replica/phase0/missing_member_quarters.json`).
- **BSE gap fill: not done.** api.bseindia.com returned Akamai 403 on 5 of 5 calls with backoff on 2026-11-20; the run
  stopped as the rule requires. Nothing fetched or merged (`diagnostics/research/explore/2026-11-20_bse_gap_fill_attempt.json`).
- **Where the gaps sit** (`diagnostics/replica/phase0/missing_gap_clusters.json`):
  - by position: 425 are before the company's first filed quarter, 607 are interior gaps (3.7% of interior quarters),
    101 are never-mapped symbols (5 companies), 12 after the last filed quarter;
  - by sector: financials miss 21.96% against 5.08% for non-financials; insurers dominate (ICICIPRULI 29, SBILIFE,
    ICICIGI, HDFCLIFE, GICRE, NIACL 28 each);
  - by size (adv60 tercile): 6.19% / 5.88% / 7.42%, least to most liquid, so **no small-company cluster**;
  - by filer speed (company median lag): ≤45d 6.02%, 46–60d 12.39%, >60d 28.38% (74 member-quarters).
  Insurers file outside the Ind-AS results taxonomy the parser reads [inferred]. An L1/L5 model that excludes
  financials, as the momentum book's universe treats them separately, loses few quarters [inferred].

## 10. Proposed gate for new candidates (draft for the owner's decision)

1. **Before any trial:** gross alpha over a beta-matched static mix (index fund + cash at the candidate's own beta),
   weekly, Newey-West lag 8, with **t ≥ 2 on the full available history**, not on a chosen window.
2. **Before capital:** whichever comes later of:
   - **(a)** the deflated hurdle, |t| ≥ 3.57 at 141 lifetime trials (Bonferroni-equivalent; the hurdle rises with the
     count);
   - **(b)** 26 weeks of forward paper.

Why: in 2019–24 alone, 0001 clears t ≥ 2 gross (2.31). Over its full run it does not (0.93). [measured, §1]

The exploration-lane draft (`forward/drafts/2027-01/exploration_lane_amendment.md`) uses this gate.
