# 0124 — Weinstein stage analysis, run as a WHOLE SYSTEM on the corrected universe

**Status:** PRE-REGISTERED
**Class:** **MEASUREMENT** — external-strategy shadow backtest, the 0022/0023/0024 (Bhanushali) precedent.
**No `n_trials` increment. No screen-ledger row. No config change. No forward-wall read.**
Standing counts at registration: **screens 12 · sealed opens 1 · n_trials 138.**

**Date registered:** 2026-07-31. **Owner:** Kreesh Patel. **Author:** research session.
**Universe:** corrected (`corrected_universe()` — pinned `dataset-pin-20260701` ohlcv sha `f8625a8f…`
+ delisted backfill + `delisted_alias_map.json`), PIT Nifty-500 membership, ADV ≥ ₹5cr.
**Window:** 2017-01-01 → 2026-06-29 (the pinned data span).

---

## §0 IMMUTABLE — what is being tested, and why it is not a relitigation

This tests a **complete, documented, real-world grammar as a whole system** — its own universe
qualification, its own trend line, its own trigger, its own stop, its own management and its own
exit — on our data. It does **not** strip components onto the incumbent 44-SMA touch funnel; that
path is the five-wall graveyard and stays closed.

**Grammar:** Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* (1988) — stage
analysis, stage-2 breakout entry, stage-3/4 exit.

### Collision register (the cite-and-narrow requirement, stated before the run)

| element | colliding verdict | why this is not relitigation |
|---|---|---|
| Market-stage rule ("don't buy in a bear market") | **O-001 regime/dual-momentum entry gate — KILLED for our base** | Kept **inside the grammar as taught**, exactly as regime-pause lives only inside the Path-B sleeve spec. It is **not** proposed for our base and no result here reopens O-001. |
| Stage-3/4 exit (weekly close below a flat/falling 30w SMA) | **0030 / pre-reg 0087 trend-death exit — KILL** (Sharpe −0.209, DD −37→−56, clipped winners mid-pause, freed no capital) | Different line (weekly 30w SMA close-below vs **daily EMA44** stall/deep), different funnel (Weinstein breakout vs six-step pullback), and here it is **constitutive** of the grammar, not an overlay bolted onto our book. The 0087 mechanism is recorded as an **adverse prior**, not a bar. |
| Volume ≥ 2× the 10-week average | **O-021 / 0097 volume thread — REJECT (all forms)** | 0097 rejected volume as an **overlay** on the 0094 funnel (sub-grader / ranker / pool filter), where "the selection already absorbs whatever volume proxied for". Here volume is **definitional**: Weinstein's breakout does not exist without it. Not the same object. |
| Relative-strength confirmation | our ranker of record `crs_dist` is the **same Mansfield construction at 40 weeks** (`run_bhanushali_weekly_rank.CRS_LEN=40`) | Disclosed overlap. We use Weinstein's own **52-week** Mansfield line for letter-faithfulness (quarantined research-only, the W89 precedent). Gate-1 measured that this leg is nearly free at a stage-2 breakout (86% / 97% survival) — it barely discriminates, and that is reported, not tuned away. |
| Breakout family generally | O-012 (`donchian_pos_126`), O-015/0079 (chart patterns lose as rankers) | Both are **cross-sectional ranker** verdicts at 63d on the momentum sleeve. This is a per-name breakout **system**, not a ranker. New formulation. |
| Pre-entry wall (Law I) | five walls, 0123 | Not engaged. We are **not** predicting which entry becomes a winner; we are testing whether a different grammar's entries are a different book. |
| ±10R/yr noise floor (Law VI) | 0109 | Law VI explicitly exempts **structural** changes (a second sleeve, a different book shape). A whole standalone grammar is that class. |

### The stated rationale that Gate-1 has already PARTIALLY REFUTED (recorded before the run)

G1 was picked as the census's most **pre-extension** grammar, on the reasoning that a stage-1 base
breakout buys the start of an advance. **Gate-1 measured it and the literal claim is false:**
median ext-vs-44w-SMA at the modelled entry is **17.54%**, and **0.0% of 211 signals** land in
E11's `<5%` band. What survives is only the **ordinal** claim — G1 is the least-extended *breakout*
funnel we have measured (17.5% vs cup 28.5, six-step 29.5, dbl 31.6, vcp 33.2, box 33.8, sr 37.9),
with only the incumbent touch (8.7%) closer to the line.

**Consequence, pre-committed:** this study proceeds as a **whole-system measurement**, not as a
test of the 0123 pre-extension re-open condition. **No outcome here may be reported as evidence
for or against that condition**, and a PROMISING verdict does not unlock perception/chart-structure
work under 0123. Saying so now is what stops it being said afterwards.

---

## §1 IMMUTABLE — the frozen spec (letter-faithful) and every ambiguity resolution

Weekly bars only. Parameters were frozen and published in `scripts/diag_g1_weinstein_gate1.py`
**before** any outcome was computed; this section restates them and they may not move.

| element | rule | source / interpretation |
|---|---|---|
| **Line** | 30-week SMA of the weekly close | His line. **Quarantined research-only** — our base's 44-week line is an SMA and is untouched (W89 precedent). |
| **Stage 1** | trailing **26 weeks** with (i) \|30w SMA drift\| ≤ **5%** and (ii) base range (high−low)/low ≤ **35%** | He gives no numbers. 26wk ≈ the "months-long" bases of his worked illustrations; 5% == "flat"; 35% is a **trading range**, deliberately looser than our 15% flat-base box. |
| **Ceiling** | the base's high over those 26 weeks | as taught |
| **Trigger** | weekly **close** above the ceiling | He teaches two buys — the breakout and the pullback-to-breakout. This models the **breakout**, his primary. **The pullback buy is not measured**; that is a stated limitation, not a finding. |
| **Stage-2 confirm** | close > 30w SMA **and** sma30[k] ≥ sma30[k−4] | "the MA has flattened out and is turning up" |
| **RS** | Mansfield = (close/index ÷ 52wk-SMA(close/index) − 1)×100 ≥ **0** and rising over **4 weeks** | Mansfield's construction. Index = **Nifty-50** — the house index of record for CRS, and the only series spanning the window (the N500 TRI starts 2017-09; a 52wk RS SMA would push the study to ~2018-09). |
| **Volume** | breakout-week volume ≥ **2.0×** the trailing **10-week** mean | "significant volume increase" has no number in the book; 2×/10wk is his charts' rule of thumb. |
| **One per base** | no re-signal within **26 weeks** on the same name | one stage-2 entry per stage-1 base, as taught |
| **Initial stop** | the **base low** | as taught ("below the last significant support") |
| **Management** | ratchet the stop up to each new confirmed higher swing low; **partial sell (½) into strength** at the first stage-3 warning | as taught. "Stage-3 warning" resolved mechanically as: a weekly close below the prior 4-week low **while** price is still above the 30w SMA. |
| **Exit** | **stage 4** — weekly close below the 30w SMA with sma30[k] ≤ sma30[k−4] | as taught |
| **M-rule** | no NEW entries while the Nifty-50 weekly close is below its own 30-week SMA | Weinstein's market-stage rule, **inside the grammar only** (see §0). |
| **Costs** | house tiered: STT 0.1%/leg + brokerage 0.03%/leg + ADV-tiered slippage (`config.SLIPPAGE`) | the engine-of-record cost model, unchanged |
| **Sizing (capped book)** | ₹10L, 2% equity risk per fill, cash-gated, fills ordered by Mansfield RS strongest-first | house convention; RS-strongest-first is Weinstein's own leader preference, and mirrors the incumbent's CRS-strongest-first fill |

**Nothing above is swept. There is no parameter grid in this study.** A single value per knob,
chosen from the source, recorded before the run.

---

## §2 IMMUTABLE — what will be reported (both views, in this order)

**Diagnostic-first law: per-trade UNCAPPED first, capped book second.**

1. **PER-TRADE, UNCAPPED** (every signal fills; R is capital-independent): trade count, R
   distribution (mean/median/PF/win%), hold profile, **median risk %**, **stop-out rate**,
   per-year meanR and per-year N.
2. **CAPPED ₹10L BOOK**: Sharpe, CAGR, MaxDD, Calmar, worst calendar year, turnover, trades/yr —
   and **sub-periods on a CONTINUOUS SLICE of one full run**, never a fresh-capital re-run from
   the sub-window start (the phantom-gate law; base 2022-26 Sharpe 0.762 phantom vs 0.570 correct).
3. **Correlation** of the capped book's daily returns to **both** incumbent sleeves
   (`research/exports/third_sleeve_returns.csv`: `swing`, `lowvol`), plus the 3-sleeve quarterly
   inverse-vol ERC blend vs the incumbent swing+lowvol pair (1.22 / −33% / worst yr +5.6%).
4. **Where its R concentrates** — its own ext / stop-distance / tail anatomy, matched-cell, never a
   one-sided list.
5. **The Bhanushali trichotomy**, explicitly: **return engine / risk discipline / nothing.**

---

## §3 IMMUTABLE — pre-committed bars, guards, and kill criteria

### The bar it must beat (stated in advance, per the owner)

- **Bar A — RETURN ENGINE:** standalone capped book, **2022-26 continuous-slice Sharpe ≥ 1.29**
  (the incumbent touch book's slice, STAGE4-corrected) **and** full-period Sharpe > 0.
- **Bar B — A SEAT UNDER 0115's BLEND LOGIC:** ρ to **both** `swing` and `lowvol` **< 0.55**
  (0115's two failures ran 0.57–0.64; the incumbent pair itself is 0.54) **and** positive standalone
  Sharpe **and** the 3-sleeve ERC blend beats swing+lowvol on Sharpe **without** breaking its
  zero-losing-year property.
- Clearing **neither** ⇒ **KILL**, unless it clears the risk-discipline profile below.
- **RISK DISCIPLINE (Law VII):** fails Bar A but delivers a materially shallower MaxDD or a better
  worst year at materially lower CAGR. This is **owner risk-preference territory: logged for the
  review, never promoted in-sample, never relitigated toward a pass.**

### Guard 1 — the wide-stop mirage (E6 signature), pre-committed

Gate-1 measured the modelled stop distance: **median 24.74%** (IQR 21.6–27.5%, max 36.1%). That is
squarely the geometry that produced the killed S/R "1.381 / Calmar 1.11" mirage (median risk 33%):
**a stop that rarely triggers inflates both win rate and R.** Pre-commitment: the readout must
report median risk %, stop-out rate and meanR together, and **a high-win-rate / low-meanR /
low-stop-out profile is to be reported as the mirage signature, not as an edge** — regardless of
how the headline Sharpe looks. No post-hoc stop retune is permitted; the base-low stop is what
Weinstein teaches and it is frozen.

### Guard 2 — the power imbalance, pre-committed

Gate-1's per-year counts are severely uneven: **2018–21 ≈ 12 signals/yr vs 2022–26 ≈ 36/yr**
(49 vs 162 member+liquid signals), and 2017 is warmup-truncated (a 52-week RS SMA on data starting
2017-01 means most names cannot signal before ~2018-01). Pre-commitment: the 2017-21 sub-period is
**underpowered by construction**; a failure there is **not** on its own a KILL, and a 2022-26 pass
alone is **not** certification. Both are reported with their N.

### Guard 3 — leakage

All features are trailing-only and computed from weekly bars closing at or before the signal week.
The entry is the signal week's close. A result **worse** than the incumbent is not a leak; a result
**better** than the incumbent is guilty until cleared (`skills/leakage-audit`), and Guard 1 is the
first place to look.

### Kill criteria (explicit)

**KILL** if: Bar A fails **and** Bar B fails **and** no risk-discipline profile is present; or the
per-trade edge is shown to be a Guard-1 mirage; or the trade count collapses below ~10/yr on the
member+liquid universe once the M-rule is applied.

**KILL ends the thread** with a finding (`research/findings/0124-*.md`, with the mandatory
root-cause readout and a named "do not re-test unless" clause) and an `overlay_registry.md` row.
**PROMISING** routes to a **watched-book / forward-wall proposal for the next quarterly review**
(2026-10-01) — the only certifier. **No component is extracted onto the base regardless of outcome.**

**UNDERPOWERED and KILL are first-class outcomes. No parameter moves after this line.**

---

## §4 Gate-1 artifacts (already committed, pre-run)

- `scripts/diag_g1_weinstein_gate1.py` → `diagnostics/research/g1_weinstein_gate1.{md,json}`,
  ledger `research/exports/g1_weinstein_signals.csv` (294 raw signals; **211** member + ADV≥₹5cr;
  **22.5/yr**; 174 distinct names).
- `scripts/diag_ext_band_census.py` → `diagnostics/research/ext_band_census.{md,json}` — the
  companion measurement that refuted the pre-extension premise and supplied the comparison set.

## §5 Reproduce

    python scripts/diag_ext_band_census.py       # the companion ext census
    python scripts/diag_g1_weinstein_gate1.py    # Gate-1: counts + ext at entry
    python scripts/run_weinstein_0124.py         # Phase 2: per-trade uncapped + capped book

---

## OUTCOME (appended 2026-07-31, after the run — nothing above this line was touched)

**VERDICT: KILL.** Full readout: [`research/findings/0124-weinstein-stage-analysis.md`](../../../research/findings/0124-weinstein-stage-analysis.md).
Registry row appended. **Counts unchanged: screens 12 · sealed opens 1 · n_trials 138.**

| pre-committed test | result | outcome |
|---|---|---|
| **Bar A** — 2022-26 continuous slice Sharpe ≥ 1.29, full-period Sharpe > 0 | slice **0.861**; full **0.259**, boot CI **[−0.58, +1.03]** | **FAIL** |
| **Bar B.1** — ρ < 0.55 to both incumbent sleeves | **0.381** (swing) / **0.344** (lowvol) | **PASS** (the lowest ever measured here) |
| **Bar B.2** — positive standalone Sharpe | +0.259 | pass (trivially) |
| **Bar B.3** — 3-sleeve ERC beats swing+lowvol without breaking zero-losing-years | Sharpe **1.182 → 1.005**; worst year **+3.8% → −2.5%**; losing years **0 → 2** | **FAIL** |
| **Risk discipline (Law VII)** — materially shallower DD or better worst year at lower CAGR | blend DD −29.7% → −21.0%, but −0.177 Sharpe **and** a worse worst year | **partial — not claimed** |
| **Guard 1** — wide-stop mirage (E6 signature) | win 39.4% (low, not inflated), meanR +0.077; the ratchet makes the stop a real trailing stop | **did not fire** |
| **Guard 2** — 2017-21 underpowered by construction | fired, then overtaken: 2017-21 is **5/5 negative years**, and 2024/25/26 are negative too | **noted; not the explanation** |
| **Guard 3** — leakage | result far worse than incumbent; leaks inflate | **clear** |

**Trichotomy: NOTHING** — not a return engine, not a clean risk discipline.

**The §0 pre-registered honesty clause held:** Gate-1 refuted the pick's pre-extension premise
*before* the run (0.0% of 211 signals below 5% ext; median 17.54%), it was recorded there, and
accordingly **no result here is reported as evidence for or against 0123's re-open condition.**

**Bankable asset carried forward:** ρ 0.34–0.38 to both incumbent sleeves — the first genuinely
orthogonal long-only equity return stream the programme has produced. It failed on edge, not on
correlation, which completes 0115's law from the missing side. Recorded for the Oct-1 binder.

**Re-open condition:** see the finding's "Do NOT re-test unless" clause (new data / a new ENTRY
geometry that shifts the ext-at-entry distribution / genuine forward data). Parameter re-tuning,
a grafted tighter stop, and running with the M-rule off are refused as relitigation.
