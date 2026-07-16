# Stage 4 — sizing sleeves: does the zoo's per-trade edge survive the cap? (measurement, no trial)

> **⚠ CORRECTED 2026-07-16 — the original "sleeves cut DD −42→−34" conclusion was a BUG ARTIFACT.**
> A stop-contamination bug in `run_bhanushali_weekly_rank.py` (box/sr blocks wrote `_stop_arr` on
> touch weeks that also met a breakout condition, *before* the `& ~wsig` mask) inflated the touch
> baseline's DD to −42.4%. Fixed (masked-assign). The **correct** touch baseline is **−34.8% / Sharpe
> 1.03 / Calmar 0.61 / 22-26 slice 1.29**, and against it **no sleeve/zoo config improves the book** —
> config D is −33.9% DD (≈ baseline), CAGR 18.6% (< 21.2%), 22-26 slice 1.19 (< 1.29). **SLEEVES
> REJECTED. The current live touch-only book is the best config tested.** The corrected table + verdict
> are in the "RIGOR VERDICT" section; the numbers in sections below this banner are the PRE-FIX (wrong)
> values, retained only to show what the bug produced.


**Run 2026-07-16.** Faithful to the engine of record — reuses `backtest()` (capped Rs10L, CRS fills,
P2 exit); a "sleeve" = the same engine on a copy of P whose `entry_win` is filtered to one setup
family, own budget, curves summed. No frozen code edited. Continuous-slice sub-periods (not
fresh-capital). Reproduce: `python scripts/diag_sleeves.py`.

## Results (all under live P2 exit, Rs10L total)

| config | trades | Sharpe | CAGR | MaxDD | Calmar | 17-21 | **22-26** |
|---|---|---|---|---|---|---|---|
| A touch-only (baseline) | 167 | 0.82 | 18.2% | −42.4% | 0.43 | 0.75 | 0.92 |
| B all-setups SHARED cap | 211 | 1.20 | 29.0% | −39.7% | 0.73 | 1.41 | 0.97 |
| C sleeves ×6 (Rs10L/6) | 955 | 0.95 | 16.1% | −32.2% | 0.50 | 0.99 | 0.92 |
| **D sleeves touch+cup+dbl (Rs10L/3)** | 484 | 0.97 | 17.4% | **−33.6%** | 0.52 | 0.91 | **1.03** |

Per-family standalone (each Rs10L, 22-26 slice): box 1.00 · double_bottom 0.94 · cup 1.02 · touch
0.92 · ascending_base 0.64 · **trend_pullback 0.29 (weak, dropped)**.

## Findings

1. **The shared-cap all-setups book (B) is a regime artifact — reject as a headline.** Full-period
   Sharpe 1.20 looks like a huge win, but the split is **1.41 (2017-21) vs 0.97 (2022-26)** — on the
   continuous-slice 2022-26 gate it is only **+0.05** over baseline. The registry's box
   regime-sensitivity warning transfers: most of the "edge" is the 2017-21 bull.
2. **Sleeves are a real DRAWDOWN / robustness lever that HOLDS out-of-sample.** Config D (sleeve just
   touch + cup + double_bottom) cuts MaxDD **−42.4% → −33.6%**, lifts Calmar 0.43 → 0.52, and improves
   the 2022-26 slice **0.92 → 1.03**, at ~flat CAGR (18.2 → 17.4%). The diversification is genuine
   (distinct setups/tickers/times), not a summing artifact.
3. **This answers the program's core question.** The zoo's per-trade edge does NOT translate into a
   big portfolio RETURN boost under the cap (regime-sensitive) — but sleeve allocation across the best
   families DOES yield a durable **drawdown** improvement, which is the book's actual documented
   weakness (RESEARCH_PLAN_swing: "the real weakness is the −42% DD, not Sharpe").
4. **Drop trend_pullback and ascending_base from any sleeve** (22-26 Sharpe 0.29 / 0.64). The keeper
   families are touch + cup_handle + double_bottom (+ box as a standalone-strong option).

## Next — Stage 5

Config **D (touch+cup+double_bottom sleeves)** is the forward-wall candidate: a pre-registered
sizing-sleeve shadow book targeting DD, decided at the 2026-10-01 review — never an in-sample cfg flip
(the 22-26 +0.11 Calmar is real but modest; DSR/forward is the only certifier). This is exactly the
Phase-3 SLEEVE mechanism the swing plan anticipated ([[swing-setup-library]] "multi-setup engine only
pays off with sleeve sizing").

## CORRECTED RESULTS (post stop-fix) — sleeves REJECTED

| config | trades | Sharpe | CAGR | MaxDD | Calmar | 17-21 | 22-26 |
|---|---|---|---|---|---|---|---|
| **A touch-only (live book)** | 168 | 1.03 | 21.2% | **−34.8%** | 0.61 | 0.79 | **1.29** |
| B all-setups SHARED | 205 | 1.22 | 28.2% | −44.0% | 0.64 | 1.36 | 1.07 |
| C sleeves ×6 | 975 | 0.98 | 16.5% | −31.4% | 0.53 | 1.05 | 0.91 |
| D sleeves ×3 | 485 | 1.07 | 18.6% | −33.9% | 0.55 | 0.95 | 1.19 |

Per-family standalone (22-26 slice): touch **1.29** · cup 1.02 · box 1.00 · double_bottom 0.94 ·
ascending 0.64 · trend_pullback **−0.06** (DD −56.5%, genuinely bad — the contamination had hidden it).

**Corrected conclusion:** with honest stops, the touch-only LIVE book dominates on the OOS-relevant
2022-26 slice (1.29) and already sits at −34.8% DD / Calmar 0.61. No sleeve or shared-cap config beats
it; config D is worse on CAGR and the 22-26 slice at equal DD. The zoo's per-trade edge (Stage 1) does
NOT survive the cap even as sleeves — the per-trade≠portfolio wall holds, harder than before. **Ship
NOTHING; the live book is the best of everything tested.** (B's headline 1.22 is a 2017-21 artifact AND
has a WORSE −44% DD.)

## RIGOR VERDICT (pre-fix, on the contaminated baseline) — config D FAILED the promotion bar anyway

Run `scripts/diag_sleeve_rigor.py` (paired block-bootstrap, per-year walk-forward, DSR, cost check):

| test | result | verdict |
|---|---|---|
| ΔSharpe ≥ +0.10 & CI>0 | +0.148, 95% CI **[−0.131, +0.473]** | FAIL (not significant) |
| ΔMaxDD (the DD lever) | +0.088, CI **[−0.049, +0.132]** | FAIL (**DD gain not significant**) |
| ΔCalmar ≥ +0.05 | +0.089 | pass (barely) |
| ΔCAGR > 0 | −0.8% | FAIL |
| walk-forward ≥ 60% | 4/10 years (40%) | FAIL |
| DSR > 0.95 @ n=116 | **0.000** | FAIL |

Return-correlation D~A = **0.90** (≈ the same book reshuffled, not a diversifier). Cost drag 2.4pp/yr
(3× turnover). **The point-estimate DD improvement (−42→−34) does NOT survive significance testing** —
it is in-sample noise, exactly the failure mode the forward wall exists to catch. Same verdict class as
the rest of this program: directionally-nice, UNDERPOWERED, uncertifiable in-sample. **Do not change the
live config on this.** The only honest homes are (a) a forward-wall WATCHED shadow that logs live from
now (unbiased evidence in weeks, not an in-sample re-cut) or (b) an explicit owner-override accepting it
is a coin-flip. Recorded, not relitigated toward a pass.

## Caveats

- Post-hoc capital re-imposition on the engine's serialized fills (approximation, but engine-faithful
  mechanics). B's dilution/upgrade depends on the P2 exit (no-cap lets zoo wide-stop runners pay off).
- Nothing here changes live. Sleeve weights (equal) are un-optimized — deliberately, to avoid a
  knife-edge fit; the forward wall tests the concept, not a tuned weight vector.
