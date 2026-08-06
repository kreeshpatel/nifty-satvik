# Structural Defect Map — one register, six sources

**Living document. Started 2026-08-06.** Class: **CONSOLIDATION.** This document itself spends
nothing — zero trials, zero screens, zero recomputation. **Standing counts: screens 16 · sealed
opens 1 · n_trials 138** (authority `label_screen_ledger.md`; `n_trials.json`). Screens moved
15 → 16 in the same session for **finding 0130**, which is a separate measurement with its own
pre-registration and ledger row — not for this map.
Fishing guard in force: anything noticed while consolidating goes to
`verification_audit_2026Q3/PARKING_LOT.md` unanalysed.

**Every cost figure below is quoted from a committed source, with the link.** Nothing is estimated.
Where a cost has never been measured the cell reads **`UNMEASURED — see [test]`** and names the test
that would produce it. No number in this document was computed for it.

---

## Why this file exists

The knowledge is dense and it is scattered across **six registers, each organised by a different
axis**:

| register | organising axis |
|---|---|
| `system_constitution.md` §2/§3/§4 | live-vs-certified divergence, convention menu, outright bugs |
| `system_constitution.md` appendices S / S2 | scheduler layer |
| `verification_audit_2026Q3/EXECUTIVE_SUMMARY.md` | reproducibility / provenance |
| `DEFINITIONS_REGISTER.md` | what a metric means |
| `skills/program-laws/FALSIFIERS.md` | whether a law can be overturned |
| `oct1_binder_decisions.md` | what the owner must decide |

A repo-wide search confirms no consolidated register existed. Restating those lists would add
nothing. **The four things this document does that none of them does** are §A cross-register
linkage, §B the roll-up with a total, §C a severity ordering that spans registers, and §D the
assembled statement of what the evidence cannot rule out.

---

## §A. Cross-register linkage — one fact, five entries

Nothing today connects these. They are one structural fact seen five ways, and reading any one of
them alone understates it.

> **THE FACT.** Position size is `shares = sizing_eq × 2% ÷ (entry − stop)`
> ([`run_bhanushali_weekly_rank.py:868`](../../scripts/run_bhanushali_weekly_rank.py)), so **notional
> is inversely proportional to stop width**. In the run of record the caps are at signature defaults
> (`max_notional_pct=None`, `max_positions=0` inert at `:843`), leaving **cash as the only capacity
> constraint** (`:876`). The book therefore selects on stop width before it selects on anything else
> — and R, the unit every verdict is written in, has stop width in its denominator.

| # | alias | register | what it says |
|---|---|---|---|
| 1 | **D3** | constitution §2 | live runs `LIVE_DISCIPLINE` (`cron:86`) + config P; the certified 1.132 never ran that config |
| 2 | **binder §6** | `oct1_binder_decisions.md` | R is not a comparable unit in the live book — the cap binds on 53.4% of trades |
| 3 | **binder §7/§8** | same | rupee-weighted collection: `<5%` band weight **0.621**, realised-R recovery **0.829** |
| 4 | **census §2** | `TRADE_POPULATION_CENSUS.md` | the funded set is systematically selected — stop width 13.73% vs 6.79%, p=1.1e-89 |
| 5 | **definitions row 1** | `DEFINITIONS_REGISTER.md` | R is an open DOOR precisely because its denominator varies |

**The asymmetry that makes it worse, and which no register states:** the *record* is uncapped
risk-parity (cash-only), while *live* runs `LIVE_DISCIPLINE` with a 20% notional cap. **The two
books carry different selection biases.** The record over-selects wide stops because notional is
unbounded; live truncates the same axis from the other end. D3 is usually read as "a different exit
config"; it is also a different *selection* config, and that half has never been written down.

**Scale-invariance — the part that is easy to get wrong.** Because risk-parity notional is a fixed
*fraction* of equity, a bigger book does not fix this. Doubling capital doubles both the affordable
notional and the position size demanded by a tight stop. The exclusion is a property of the sizing
rule, not of the ₹10L figure.

Two further linkages, stated once:

- **Survivorship (D1) × no time cap (G6).** Finding 0025 measured survivorship bias **scaling with
  holding period** (−0.04 Sharpe tight-stop vs **−0.18** wide-stop swing configs). The live book has
  **no time cap at all**, which is the configuration where the bias was largest. Two registers carry
  the halves; neither multiplies them.
- **Mutability (D2, closed) × the gates (I4).** The archive now makes recomputation attributable,
  but `bhanushali_review_scorecard.py` still reads the **mutable working copy** (binder §0). The
  divergence is closed; the gate still points at the wrong artifact.

---

## §B. The open-item roll-up — the first total ever taken

| source | items | open |
|---|---|---:|
| constitution §2 DIVERGENT | D1, D3, D4, D6, D7, D8, D9 | **7** |
| constitution §4 outright broken | B-2-substance, B-3, B-4 | **3** |
| constitution §3 convention menu | M3, M4, M5, M8, M9, M10, M11, M12, M13, M14 | **10** |
| appendix S scheduler flags | S-F1 … S-F7 | **7** |
| appendix S2 scheduler flags | S2-F4 (S2-F5 **closed this session**; S2-F3 is a standing method rule) | **1** |
| verification discrepancy ledger | D2, D4-remainder | **2** |
| definitions doors | rows 1, 5, 6, 7, 8, 11, 15, 18 | **8** |
| falsifiers not armed | Law II, Law III (contingent) — Law VIII flagged for demotion | **2** |
| | **TOTAL OPEN** | **40** |

**41 as enumerated when this map was planned; 40 after S2-F5 closed on 2026-08-06** (`f9edf71`,
PR #66 — the golden's curve key repinned to 8 significant figures). **The DIVERGENT row count of 7 is
no longer a discrepancy: the constitution's header was corrected 9 → 7 on 2026-08-06, so this total
and its source now agree.**

**Update 2026-08-06 — finding 0130.** SEL-1/2/3 move OPEN → TRADEOFF (the funding bias is now priced
at −10.83% of equity/yr, a saving). They were never counted in the roll-up above, which counts only
the six source registers' own open items, so **the total is unchanged at 40**.

**Owner decisions vs work items.** The split matters because it is the difference between "October
must choose" and "someone must do it".

| | items | count |
|---|---|---:|
| **Owner decision** (governance / quarterly-review class) | D1, D3, D4, D6, D7, D8, D9 · B-2-substance · 8 definitions doors · Law II, Law III · S-F1, S-F2 · S2-F4 · M10 | **21** |
| **Work item** (no decision needed, just unbuilt) | B-3, B-4 · M3, M4, M5, M8, M9, M11, M13, M14 · S-F3, S-F4, S-F5, S-F6, S-F7 · D2, D4-remainder · M12 (inert while display-only) | **19** |

**De-duplication note, because the roll-up would otherwise double-count.** The binder's §6–§10 are
not separate items: §6/§7/§8 are the same fact as definitions row 1 and row 11, §9's four sub-items
are definitions rows 5/6/7/8, and §10 is the demerger convention (§4 of this map). The binder is the
**routing destination** for these items, not an additional register of them. Counting it separately
would inflate the total by roughly ten.

---

## §C. Severity ordering across registers

Ranked by **what a defect invalidates**, not by size. A defect that breaks the instrument outranks
one that moves a number, because the second is measurable and the first makes measurement
meaningless.

| # | defect | measured cost | class | source |
|---|---|---|---|---|
| **1** | **The capped book cannot certify an improvement** | the ±10R/yr floor = **1.20 annual σ**; an overlay must add **74.4%** of the book's entire annual return to clear it | INHERENT | §2 below |
| **2** | **Funding bias — the funded set is not its own population** | 0 of 1,249 tightest-stop signals funded in 9.5y; **48×**/**111×**; **priced 2026-08-06 as a SAVING of −10.83% of equity/yr** (finding 0130) | **TRADEOFF** | census §2; finding 0130 |
| **3** | **D1 survivorship × no time cap** | −0.18 Sharpe class (0025, wide-stop configs — the largest-bias configuration, which is this one) | FIXABLE (backfill exists, unapplied to live) | constitution D1 |
| **4** | **D3 live ≠ certified config** | config P **fails** the 2022-26 continuous slice at **0.91** vs the 1.29 bar, with **−39.5% DD** (`cron:44-77`) | TRADEOFF (owner override, recorded) | constitution D3 |
| **5** | **D4 no fill feedback** | **UNMEASURED — see** a reconciliation of owner fills vs the modelled ledger; no instrument exists (ADR-0011 removed the broker link) | OPEN | constitution D4 |
| 6 | Vendor adjustment seams | backtest **−23.89R = −1.28%** of book R (4 trades); live = 1 suppressed candidate (TRENT) to ~2026-11-06 | GUARDED (monotonicity guard; TRENT accepted to Oct-1) | `FOUNDATION_AUDIT.md` F-1 |
| 7 | Demerger convention split | 22 back-adjusted / 15 cliffs; **30 of the 418** `<5%` core-cell trades at **+1.292R** vs the cell's +0.717 — excluding them moves the cell to +0.672 (**6.2%** of the core edge) | OPEN (binder §10) | binder §10 |
| 8 | Paper gate resting on 4 closed trades | expectancy and win rate not informative below the pre-committed **≥30 closed** | GUARDED (precondition is load-bearing) | binder §9.4 |
| 9 | Unmodelled statutory cost | **≈4.8 bps** round-trip (exchange, SEBI, stamp, GST, DP) — smaller than the slippage term already charged | TRADEOFF (quantified, no change proposed) | audit A8 |
| 10 | Concentration under pure risk-parity | **UNMEASURED — see** the sizing-exclusion bound's tail leg (disaster-class exposure per arm) | OPEN | this map §3 |

Items 1 and 2 are the two that should change how October reads everything else. Item 1 is not new —
it is **Law VI quantified**, and it is stated as such in §2.

---

## §D. What the evidence base cannot rule out

Assembled from the per-document statements that already exist (census §4, `FOUNDATION_AUDIT.md`'s
can/cannot section and its addendum, `verification_audit_2026Q3/INDEX.md`'s pending Tier A/B/C
scope). Nothing here is new; it has simply never been in one paragraph.

> **The arithmetic is sound and the selection is not characterised.** Every number the 2026Q3 audit
> could re-derive independently came back right, often to the digit, and the programme rebuilds from
> a clean clone in under five minutes. What remains open is different in kind. **On the data:** the
> pin is exchange-true at quarterly resolution (0 of 17,801 name-days above raw) but intra-quarter
> vintage seams away from a year boundary are sampled rather than enumerated, pre-2019 corporate
> actions are outside the census, rights issues are not in the split/bonus/demerger record, and two
> seams (HBLENGINE 2024-12-24, TRENT 2019-03-18) have no diagnosis. **On the engine:** one trade has
> been hand-reconciled end to end, on the `time` branch only; `stop`, `trail`, `half` and `eos` are
> pinned by golden masters but never hand-computed. **On the book:** no counterfactual book has ever
> been run, so the cost of the funding bias is unknown in either direction, and the excluded
> tight-stop cohort's +0.972R is a population figure a book could not have realised. **On the
> record:** `baseline_v1` has no producer script and the blind adversarial replication's report is
> **not in this repo** — both are corroborated-but-not-self-reproducible. **On the forward wall:**
> three of eight laws have no live falsifier today, and the wall's own log had no scheduled producer
> as of the last scheduler audit (S-F1). **And on every in-sample verdict:** §2's power arithmetic
> means the capped book was never capable of certifying an improvement, so a KILL recorded there is
> evidence about the instrument at least as much as about the idea.

---

# The register

Schema: `ID · defect · mechanism · measured cost · class · resolution path · source`.
Classes: **INHERENT** (property of strategy or market) · **TRADEOFF** (deliberate, priced) ·
**FIXABLE** (known fix, unapplied) · **GUARDED** (found, defended, residual stated) ·
**OPEN** (cost unmeasured — names the test) · **CLOSED** (retained for history).

---

## 1. Selection & capacity

| ID | defect | mechanism | measured cost | class | resolution path | source |
|---|---|---|---|---|---|---|
| SEL-1 | **The funded book is not a representative sample of its own signal population** | notional ∝ 1/stop-width; cash is the only capacity constraint (`R94:876`) | stop width 13.73% vs 6.79% (p=1.1e-89); ext 18.50% vs 9.10% (p=1.9e-84); **priced 2026-08-06: the bias is a SAVING of −10.83% of equity/yr, CI [−26.33, +4.74]** | **TRADEOFF** (priced) | closed — finding 0130 | census §2; finding 0130 |
| SEL-2 | **Zero of the 1,249 tightest-stop signals were ever funded** | their median notional is **₹704,900** against a ₹1,000,000 book — one position consumes 70% of capital | +0.972R vs +0.224R **in R**; letting them in earns **10.83% of equity/yr LESS** (0130) — they are best in R because R over-weights tight stops | **TRADEOFF** (priced) | closed — finding 0130 | census §2; finding 0130 |
| SEL-3 | **Funding probability varies 48× by stop width and 111× by extension band** | same mechanism; ext and stop width correlate **+0.577** | 0.32% → 15.45% (stop width); 0.36% → 40.08% (ext band); the selection it produces is **net favourable** (0130) | **TRADEOFF** | closed — finding 0130 | census §2; finding 0130 |
| SEL-4 | **Scale does not fix it** | risk-parity notional is a fixed *fraction* of equity, so more capital scales both sides | n/a — structural | **INHERENT** | only a different sizer changes it (governance class) | this map §A |
| SEL-5 | **Throughput is set by capital, not by signal supply** | cash gate | population 6,245 → funded **255** (**4.08%**); **19,504** cash rejections; signal counts swing 280→984/yr while funded stays 15–36 | **INHERENT** | — | census §1 |
| SEL-6 | **Live under-collects what the research measures** | the 20% notional cap binds on 53.4% of live trades, under-sizing exactly the narrow-stop cohort the research calls the core | `<5%` band live weight **0.621**; realised-R recovery **0.829** (1907.3R → 1581.9R) | **TRADEOFF** (priced guardrail) | binder §7/§8 | binder §7, §8 |
| SEL-7 | **Record and live carry *different* selection biases** | record is uncapped risk-parity; live truncates the same axis with `max_notional_pct=0.20` (`cron:86`) | **UNMEASURED — see** a like-for-like selection comparison of the two configs | **OPEN** | D3's Oct-1 door | this map §A |

**The consequence, stated plainly:** the 1.132 bar is partly the cash machine. Every rejection ever
measured against it inherits this selection.

---

## 2. Statistical power — Law VI, quantified

**This is not a new discovery. It is [`program-laws`](../../skills/program-laws/SKILL.md) Law VI
expressed in the book's own units**, and 0109 derived the ±10R/yr floor on this same 4–5-name
cash-constrained book, so the two are internally consistent by construction rather than by
coincidence.

Verified from `trade_population_census.json` / `trade_population.parquet` (no new computation — the
funded rows are the record's own 255):

| quantity | value |
|---|---:|
| funded trades | 255 over 9.4867 years |
| funded `sum_R` | **+127.46 R** |
| **book annual return** | **+13.44 R/yr** |
| per-trade σ (R) | **1.6023** |
| trades per year | 26.88 |
| **book annual σ** | **σ√n = 1.6023 × √26.88 = 8.307 R** |

From which, directly:

| statement | value |
|---|---:|
| the ±10R/yr floor, in the book's own annual sigma | **1.204 σ** |
| the book's annual return, in the same sigma | **1.617 σ** above zero |
| **an overlay must add this share of the book's entire annual return to clear the floor** | **74.4%** |

**The honest consequence.** An instrument whose noise floor is 1.2σ, on a book whose entire signal
is 1.6σ, cannot resolve anything smaller than three-quarters of itself. **The capped book was never
capable of certifying an improvement.** That explains the 4-for-4 activation-bound failures (0117
rotation, 0119 tiebreak, 0121 deferral, 0129 event-sizing) more economically than their four
individual mechanisms do — the mechanisms are real and separately established, and they were also
never going to be measurable here.

Certification can therefore only come from **the 6,245-signal population** or **forward evidence**.

**A third route, and where it is not.** The 2026Q3 audit records a blind adversarial replication
whose Sharpe confidence interval would be a third independent line to the same statement. **That
report is not in this repo** (`SESSION4_BLIND_REPLICATION.md` says so explicitly — filed as intake
from the owner's summary, never confirmed here), so no CI from it is cited in this map. Two routes
are in-repo; the third is owner-held and is listed in §7 as a provenance gap rather than as evidence.

| ID | defect | measured cost | class | source |
|---|---|---|---|---|
| POW-1 | **In-sample certification on the capped book is impossible** | floor = 1.204σ; book = 1.617σ; overlay must add 74.4% of annual R | **INHERENT** | this section |
| POW-2 | Paper gate currently rests on **4 closed trades** | expectancy/win-rate uninformative below the pre-committed ≥30 | **GUARDED** | binder §9.4 |
| POW-3 | Per-trade adherence noise alone spans **±58%** of expectancy at k=50% | p05–p95 = +0.17 to +0.64 R against +0.41 | **INHERENT** | census §3 |
| POW-4 | `n_trials = 138` deflates every future DSR | permanent; cannot be un-spent | **INHERENT** | `n_trials.json` |

---

## 3. Risk

| ID | defect | mechanism | measured cost | class | source |
|---|---|---|---|---|---|
| RSK-1 | **Stops do not hold** — gap-through / disaster class | the default ladder decides at the weekly close and fills at the next open; a gap prints through | 0109's disaster-floor was **KILLed** (a strictly positive per-trade floor still lost at book level, 17 exits reshuffled the cash path) | **INHERENT** | 0109 / program-laws §V |
| RSK-2 | **Concentration under pure risk-parity** | no `max_positions`, no notional cap in the record | **UNMEASURED — see** the bound's tail leg: disaster-class (R ≤ −1.5) exposure per arm. A 20% position with a 2.84% stop and a 16% position with a 12.62% stop have different gap-through costs | **OPEN** | this map |
| RSK-3 | **Lumpiness** — the book is a tail | population median trade **−0.317R**; 4 of 10 years negative in R at population level; **45.2%** of signals stop out | **INHERENT** | census §1 |
| RSK-4 | **The longest-hold decile earns 64.3% of total R** | no time cap live (G6); mean R rises monotonically with hold (−1.72R at 0–4w → +18.71R at >104w) | reinstating a 52-week cap would truncate the book's entire positive expectancy (M2 **reversed** its own provisional recommendation) | **TRADEOFF** | `m2_hold_age.md` |
| RSK-5 | Concentration is recorded as a **feature**, not a bug | `docs/decisions/0009` §68; `max_positions` REJECTED as knife-edge overfit | 0.24-Sharpe swings per one-position change | **TRADEOFF** | `LOCKED_STRATEGY.md:62` |

---

## 4. Measurement

| ID | defect | measured cost | class | source |
|---|---|---|---|---|
| MSR-1 | **8 open definitions doors** — R, win rate, CAGR, MaxDD, Sharpe, the ±10R floor, `expectancy_R`, Calmar | each changes what a gate means; none changes a past verdict (all decided on deltas, where the convention cancels) | **OPEN** ×8 | `DEFINITIONS_REGISTER.md` rows 1, 5, 6, 7, 8, 11, 15, 18 |
| MSR-2 | **R is heterogeneous** — stop width spans **7×** | the same rupee move prints a different R; funded vs unfunded differ by +6.94pp in stop width, so their R gap and their % gap measure different things | **OPEN** (binder §6–8) | binder §6/§7/§8 |
| MSR-3 | **The ±10R/yr floor is a blended unit** | derived empirically in R on a book whose R denominators vary 7× | **OPEN** | definitions row 11 |
| MSR-4 | **Demerger convention applied both ways** | 22 back-adjusted / 15 cliffs; **AARTIIND is in both**; 243/4,321 substrate trades (5.6%), 7.5% of sum R; 30 of the 418 `<5%` core-cell trades at +1.292R → excluding them moves the cell +0.717 → **+0.672** (**6.2%**) | **OPEN** (binder §10) | binder §10 |
| MSR-5 | **CAGR has two committed denominators** | 24.7% vs 25.21% on the same curve (calendar years vs bar-years) | **OPEN** | definitions row 6 |
| MSR-6 | **MaxDD is grid-dependent** | −42.4% daily vs −33% monthly, same book family; the −50% mechanical halt reads the daily grid, apparently incidentally | **OPEN** | definitions row 7; parking lot #2 |
| MSR-7 | **`KILL_SHARPE` threshold of 0 means "underperforms cash"**, not the risk-free rate | an excess-return reading would sit near 0.25–0.30 | **OPEN** | definitions row 8 |
| MSR-8 | **≈4.8 bps statutory cost unmodelled** | exchange + SEBI + stamp + GST + DP; smaller than the slippage the engine does charge | **TRADEOFF** (quantified, no change proposed) | audit A8 |

---

## 5. Data

| ID | defect | mechanism | measured cost | class | source |
|---|---|---|---|---|---|
| DAT-1 | **13 vendor adjustment seams** | the vendor applies a corporate action's adjustment only from **1 January of the ex-date's year**, leaving earlier history unadjusted; a fresh single-call download reproduces all 13, so rebuilding does not heal them | backtest **−23.89R = −1.28%** of book R across 4 trades (3 already on the record; **CONCOR −1.438R new**) | **GUARDED** — `nq/data/adjustment_guard.py` asserts monotonicity on every refresh | `FOUNDATION_AUDIT.md` addendum C-1 |
| DAT-2 | **TRENT seam accepted until 2026-10-01** | seam 2026-01-01 ×1.50; suppresses TRENT from the live candidate pool | `close_above_sma` reads **False** as served vs **True** corrected; self-resolves ~2026-11-06; no open position affected | **TRADEOFF** (ADR-0013, dated expiry, escalation trigger armed) | ADR-0013 |
| DAT-3 | **Two seams undiagnosed** | HBLENGINE 2024-12-24 (×1.0336, **inside the trusted period**), TRENT 2019-03-18 (×1.0214) | no corporate action in the NSE record explains either | **OPEN** | `adjustment_guard.KNOWN_SEAMS` |
| DAT-4 | **Survivorship — the pin is survivor-only** | 103/813 PIT members missing from the pinned cache; the backfill exists and is **not** applied to the live universe (D1) | bias **scales with holding period**: −0.04 Sharpe tight-stop, **−0.18** wide-stop; this book has no time cap | **FIXABLE** (backfill landed 2026-07-03; re-anchor is governance class) | 0025; D1 |
| DAT-5 | **Fundamentals coverage 67/104** | D/E recovered for 67 of 104 backfilled names | 21 passed the solvency gate, 46 rejected on real balance sheets | **GUARDED** | `review_2026Q4/01_reanchor.md` |
| DAT-6 | **`fundamentals_pit_depth.pkl` has no rebuilder** | in neither git nor any release | recovery risk only | **OPEN** (D4 remainder) | audit ledger D4 |

---

## 6. Operational

| ID | defect | measured cost | class | source |
|---|---|---|---|---|
| OPS-1 | **6–7 DIVERGENT rows still open** (see §B's flag) | D1 flatters the backtest; D4/D8 flatter the live record; D6/D7/D9 are card-vs-book seams | **UNMEASURED** except D1 | mixed | constitution §2 |
| OPS-2 | **B-2 substance — no time cap of any kind** | the docstring was fixed; the missing cap was not | M2 **reversed** the provisional fix: a 52-week cap would cut the only profitable cohort | **TRADEOFF** (binder recommends adopting an explicit no-cap policy) | constitution §4 |
| OPS-3 | **M5 — the stop never moves after tp1** | post-2R givebacks ride to the full initial stop | **UNMEASURED — see** the free diagnostic already specified: among trades that booked tp1 then exited `stop_part`/`sma_break`, the R lost below breakeven (a column pass on the existing ledger) | **OPEN** | menu M5 |
| OPS-4 | **M10 — the NSE holiday calendar runs out** | `config.py:165` `NSE_HOLIDAYS` holds **35 entries, 2025-02-26 → 2026-12-25**. There is **no 2027 entry**. | 2027 Jan/Apr review dates cannot be computed; the "first trading day" anchor for the quarterly wall silently mis-places | **FIXABLE** — the only open item with a near-term clock | menu M10; verified in `config.py` |
| OPS-5 | **S-F1 — the forward-wall log has no scheduled producer** | `run_paper_cron.py` → `wall_cron.update_wall` is invoked by no workflow, while CLAUDE.md calls the wall "the only certifier … logged daily" | it runs **never** | **OPEN** (owner: dormant by intent, or schedule it?) | appendix S.6 |
| OPS-6 | **S2-F4 — cron commits are authored as the owner, not a bot** | a runner-authored commit cannot be distinguished from a hand-made one by author line | weakens S2-F3's firing-evidence cross-check | **OPEN** (one-line workflow fix; owner door because it changes the commit record's appearance) | appendix S2.9 |
| OPS-7 | **S-F2 / S-F3 — the health banner is miscalibrated and unsurfaced** | 26h/48h daily thresholds against a weekly book → reads STALE on a healthy book; the `scheduler_health` block is produced but the backend does not read it | a false alarm nobody reads is worse than no alarm | **OPEN** | appendix S.6 |
| OPS-8 | Gates read the **mutable working copy** | D2's archive is built and the scorecard still points at the live file | **UNMEASURED** — drift is now attributable but the gate is not pointed at a named snapshot | **FIXABLE** | binder §0 |

### Closed, retained for history

| ID | what it was | how it closed |
|---|---|---|
| CLS-1 | **The silent `git add`** — five instances; the judge log was destroyed weekly | whitelisted; guarantee written as the standing rule (S2.14) |
| CLS-2 | **Record mutability (D2)** | write-once dated snapshots + drift log (`7e016b9`) |
| CLS-3 | **Dead-man blindness (S2-F6)** | heartbeat now reads the Actions run log, not the artifact |
| CLS-4 | **B-1 absent-bar positions** | `stale_absent_days`; census found **zero instances ever**, so the fix landed with a provably zero diff |
| CLS-5 | **D5 card ≠ book prices** | card prices off `_record_stop()`; pinned as a relationship, not a snapshot |
| CLS-6 | **S2-F5 flaky golden** | curve key repinned to 8 significant figures (`f9edf71`) — see §7's reconciliation note |

---

## 7. Provenance gaps

| ID | gap | status | source |
|---|---|---|---|
| PRV-1 | **`baseline_v1` has no producer script** | **OPEN** — only consumers of `baseline_v1.json` exist; corroborated by the blind session but not reproducible from the repo alone | audit ledger D2 |
| PRV-2 | **`fundamentals_pit_depth.pkl` has no rebuilder or release attachment** | **OPEN** | audit ledger D4 remainder |
| PRV-3 | **The blind adversarial replication's report is not in this repo** | filed as **intake, unconfirmed**; its findings (F1–F4) are recorded from the owner's summary, and **its Sharpe CI is therefore not citable here** | `SESSION4_BLIND_REPLICATION.md` |

---

## 8. NOT defects — the closed graveyard

Kept short and citing [`skills/program-laws`](../../skills/program-laws/SKILL.md) §IX, so this file
stays a defect register rather than an invitation to relitigate. **None of these is an open item.
Re-proposing any of them requires the collision rule — name which of {new data, new feature source,
new sub-period, new formulation} you bring, or the ledger has already answered.**

- **The five pre-entry walls** — bar-level ML, loser forensics, path shape, formula chart structure,
  perception (0123, κ=0.867 validated, flat).
- **Exit geometry, both directions** — 0105 tighten, 0106 widen, 0109 disaster floor. The 0094 stop
  is a robust optimum unmovable either way.
- **Regime / entry gating** — O-001, 0056, 0086, 0090, 0103.
- **Post-entry conditional management** — 0117 (day-10 IC −0.029; the +0.356 is a mechanical head
  start).
- **The technical/indicator zoo at 63d** — O-015/0079. IC ≠ portfolio Sharpe.
- **Event deferral** — 0121, 94% lapse rate, −15.72 R/yr.
- **Third sleeves** — STAGE4; 0115; 0124 killed a genuinely orthogonal one (ρ 0.34–0.38) with no edge.
- **`max_positions`** — knife-edge overfit, 0.24-Sharpe swings per one-position change.
- **`fill_order="near_sma"`** — E11, displaces CRS leaders, −0.80 Sharpe.

---

## Contradictions found while consolidating — flagged, not resolved

Per the fishing guard and the audit's standing rule, these are reported with both readings and left
for the owner. **No register was edited to make them agree.**

1. ~~**The constitution's DIVERGENT header says "9 → 6 open"; the section lists seven open rows**~~ **— RESOLVED 2026-08-06 by the owner: the header was the error and is corrected to "9 → 7 open"; no row's status changed. Original text retained below.**

   **The constitution's DIVERGENT header said "9 → 6 open"; the section lists seven open rows**
   (D1, D3, D4, D6, D7, D8, D9 — D2 and D5 are struck through). 9 − 2 = 7. Either one row is
   considered closed without being struck (D9 is described as "trivial"), or the header is a
   miscount. **Reading A:** 6 open, D9 informally closed. **Reading B:** 7 open, header stale. This
   map counts **7** and says so; the count changes the §B total by one.
2. **Standing counts differ across documents by date, not by disagreement.** The constitution's
   footer says screens 11; `review_2026Q4/00_INDEX.md` says 12; the verification
   `EXECUTIVE_SUMMARY.md` says 14; `program-laws` and `label_screen_ledger.md` say **15**. The
   ledger is the authority and all four are simply dated snapshots — flagged so a reader does not
   treat the older ones as a live count.
3. **The plan that commissioned this map quotes the book's annual return as 13.46 R/yr;
   recomputation from the census gives 13.436 R/yr.** A rounding slip, not a discrepancy; this map
   uses **13.44** throughout and every derived figure (1.204σ, 1.617σ, 74.4%) is computed from the
   unrounded value.
4. **M10's scope was stated as uncertain and is now settled.** The plan noted "a scan found entries
   as late as 2027-01-01". Verified directly: `NSE_HOLIDAYS` has **35 entries ending 2026-12-25**
   with **no 2027 entry at all**. The row above states the verified fact.

---

## Cross-references

- `system_constitution.md` — §2 DIVERGENT, §3 menu, §4 broken, appendices S / S2
- `verification_audit_2026Q3/` — `EXECUTIVE_SUMMARY.md`, `INDEX.md`, `GUARD_AUDIT.md`, `PARKING_LOT.md`
- `DEFINITIONS_REGISTER.md` · `oct1_binder_decisions.md` §0–§10
- `foundation_audit_2026Q3/` — `FOUNDATION_AUDIT.md`, `TRADE_POPULATION_CENSUS.md`, `LIVE_REPAIR_DECISION.md`
- `skills/program-laws/{SKILL,FALSIFIERS}.md` — the laws and their falsifiers
- `label_screen_ledger.md` — the counts authority (screens 15) · `n_trials.json` (138)
