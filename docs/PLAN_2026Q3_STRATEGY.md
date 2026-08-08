# Strategy plan — drafted overnight 2026-08-08/09, for owner review

**Status: DRAFT for approval. Nothing here has been run. No trial has been spent.**
Standing counts at drafting: **screens 19 · sealed opens 1 · n_trials 2**
(`diagnostics/research/n_trials.json`, `diagnostics/research/label_screen_ledger.md`).

This document exists because the owner asked for a plan that is "just waiting to be implemented",
together with a target of **30–40% yearly with no losing years**. §1 addresses the target directly,
because a plan built toward an unreachable number is worse than no plan. §2 onward is the work.

---

## 1. The return target, confronted

### 1.1 What the evidence says

The owner supplied two research compendia on 2026-08-08, now committed at
[`docs/references/external_literature.md`](references/external_literature.md). They are unambiguous:

> "The 30–40% claim is not achievable as a durable net CAGR. It appears only in bull-market windows
> …, in survivorship-biased or gross-of-cost backtests, or with leverage. Durable, honest, net
> figures cluster at 14–18%."

Our own best result agrees. Study **0001** — the strongest configuration this programme has
produced, and the first to beat passive ownership on return, Sharpe and drawdown simultaneously —
reports **21.73% CAGR, 18.16% after tax**, on a survivor-biased universe whose correction is
expected to move it *down*.

**Verdict: 30–40% net is not a target, it is a filter that would select for overfitting.** At
n_eff = 37 independent windows, a search over enough configurations will always surface one that
prints 35% in-sample. It would not survive contact with capital, and manufacturing it is the exact
failure the programme's entire apparatus exists to prevent.

### 1.2 "No losing years" is arithmetically incompatible with this asset class

Not an opinion — 0001's own committed Monte Carlo block (`research/0001-xsec-momentum/results.json`):

| | value |
|---|---|
| observed max drawdown | −37.17% |
| median resampled | −37.17% |
| p95 — *"a bad-but-plausible drawdown"* | **−51.76%** |
| p99 — *"the planning number"* | **−59.27%** |
| worst of 5,000 paths | −73.25% |
| percentile of the observed path | **0.513** |

The quoted labels are `nq/validation/montecarlo.py`'s own, not mine. Three things follow:

1. **The −37.17% headline is median luck, not a shallow-drawdown strategy.** The observed path sits
   at the 51st percentile of its own resampling. It was neither lucky nor unlucky.
2. **The repo already designates −59% as the planning number for this book.** A strategy planned
   against a −59% drawdown has losing years. Necessarily, and by construction.
3. **The true tail is worse than −59%**, because the same module states: *"a book that never met a
   2008 has no 2008 in its bootstrap… it widens the error bars on what was observed; it does not
   extend the observation."* Our window begins 2017-01.

The published band (−50% to −70%) and our own resampling therefore **agree**. The apparent conflict
between them was an artifact of comparing a single realised path to a distribution.

### 1.3 What is actually achievable, and what this plan targets

| | target | basis |
|---|---|---|
| Net CAGR (after cost, after tax) | **18–22%** | 0001 at 18.16% after tax today; the literature's "low-20s only for the best regime-managed, vol-targeted, quality-filtered combinations" |
| Planning drawdown | **−55% to −60%** | 0001's own p95/p99; the literature's −50/−70 |
| Losing years | **minimised, not eliminated** | 0001's 2018 regime slice is −9.60% — in the best book we have |
| Hard capital protection | **a halt that fires before ruin** | achievable engineering, see §3 |

**The honest opportunity is not in the return column.** It is that 0001 lost only −9.60% in the 2018
midcap crash where its random control lost −28.75%, and gained +51.26% in COVID against the
control's +28.33%. The edge this programme has found is *loss asymmetry*, and that is the same thing
the owner is asking for when they say "keep losing years to a minimum". That axis is real,
measurable, and open. The 30–40% axis is not.

### 1.4 The study already knew all of this. Nobody acted on it.

The overnight work above rediscovered what `research/0001-xsec-momentum/result.md` §3 — *"What does
NOT support this result"* — already states in its own words. Reproduced, because it is the most
important page in the repo and it has been sitting unread since 2026-08-07:

- **"PBO 0.452 is a coin flip, not a pass."** With 252 splits the standard error near 0.5 is ~0.031,
  so 0.452 sits **1.5 standard errors** from chance. Its conclusion: *"the family may carry edge,
  but the choice of top-30 / buffer-1.5 within the neighbourhood is not supported… the baseline's
  specific parameters should be treated as arbitrary within their neighbourhood."* **This is a
  direct argument against tuning 0001 further.**
- **"DSR 0.991 is close to uninformative at `n_trials = 2`."** At one trial there is essentially no
  deflation; the gate collapses to "is this Sharpe above zero". To be re-read once the counter
  reflects genuine accumulated testing.
- **"The planning drawdown is −59.3%, not −37.2%."**
- **"CAGR sits above the literature's honest band."** And its reconciliation is better than the
  survivorship story: *"the most likely reconciliation is the **window**: 2017-2026 excludes 2008,
  which is where the published −70% drawdowns and the CAGR drag come from. That is a real limitation
  of our sample, not evidence of superiority — the strategy has never met a 2008."*
- **"The win rate is 73%, and that is a construction artifact, not skill."** Of 2,951 trades,
  **2,045 (69.3%) are `rebalance_trim`** — equal-weight drift corrections, which book a gain by
  definition. Only **905** are genuine exits. Any hit-rate claim must be read off those 905 rows.

**So the correct framing of 0001 is not "a 21.73% strategy awaiting deployment". It is a
family-level edge, measured on a window containing no crisis, whose specific parameters are
unsupported and whose planning drawdown is −59%.** Everything in §2 is scoped accordingly.

### 1.5 Two open defects found overnight

**(a) Cost sensitivity reports no effect, and that is not credible.** `result.md` line 31 states
*"Cost sensitivity: unchanged at the 1.5× proxy (21.73% → 21.73%)"* — identical to two decimals. The
book turns over **311%/yr** at ~0.11% all-in per trade plus slippage; a 1.5× cost multiplier should
move CAGR by roughly 0.15–0.2pp, not 0.00. Either the multiplier is not reaching the cost model, or
the "proxy" is not what the label implies. **Must be resolved before any cost-sensitivity claim is
repeated.** Owner action: none — this is a code investigation, listed in §2.5.

**(b) The `cross_sectional_rank` tie-break divergence is inert, now measured.**
`nq/signals/cross_sectional_rank` takes pandas' default `"average"` while
`nq/data/eligibility.cross_sectional_rank` passes `"first"`, and the docstring falsely claimed they
matched. Measured on the pinned MID universe, 2017-01 onward: **0 exact NMS ties across 1,822 dates
and 198,949 scored rows; 0 dates where the top-30 selection differs.** The docstring is corrected
and now records both the measurement and the condition under which the divergence *would* bite — a
discrete or quantised score, where ties are normal rather than measure-zero. No code change needed;
no trial spent.

---

## 2. Workstreams

*(populated as the overnight research lands; each carries its own code-change map, test plan and
pre-commitment)*

**Three of the five workstreams were scoped on false premises. All three are corrected below, and
two of them shrank to almost nothing.** The common error: inferring "untested" from an absent
registry row without checking the source tree. Registry rows count *studies run*, not *code
present*.

### 2.1 Survivorship — **CLOSED, no work needed**

**0001 was already survivorship-corrected.** `pipelines/research/run_0001_xsec_momentum.py:115`
calls `corrected_universe()` (`scripts/run_bhanushali_path1.py:26`) — pinned cache + backfill +
alias map — and has since the study's first commit. The published 21.73 / 1.130 / −37.17 was never a
survivor-only number.

Measured differential (survivor-only vs the corrected run of record):

| | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| survivor-only | 21.37% | 1.121 | −35.70% |
| corrected (run of record) | 21.73% | 1.130 | −37.17% |
| **Δ survivorship** | **+0.36pp** | +0.009 | **−1.47pp** |

**Survivorship costs this book 1.5pp of drawdown, not the literature's 14pp**, and the mechanism is
sound: momentum ranking with a rank-45 buffer ejects failing names before they die. The same
correction moves *passive* by −4.83pp — 3.3× as much — because passive owns the corpse. Consistent
with 0025's "bias scales with holding period"; 0001's effective hold is 72.5 days.

**Owner action: none.** One optional tidy — commit a `--survivor-only` switch so the differential is
reproducible from the pipeline instead of a transcript (spec in the agent report; `pipelines/**`, no
depgraph regen). *Until then the 1.5pp figure is not citeable.*

### 2.2 The drawdown gap is path length, not bias — **one cheap measurement left**

With survivorship measured at 1.5pp and universe narrowness pushing the *wrong way* (narrower ⇒
deeper), the residual ~21pp of the gap to the literature's −55/−70% is sample period, in two parts:
the missing 2008 (untestable — earliest bar in the corrected store is 2016-01, only 27 names reach
it), and **max-drawdown being an order statistic in path length**: 18.5 years is 1.95× our exposure
to extremes, with zero bias involved.

That second part is testable *without any 2008 data*: add `path_days` to
`nq/validation/montecarlo.py:110-141` and resample the same corrected daily returns to **4,598
sessions** (18.58y × 247.5), then compare against BacktestIndia's −70.53%. Touches `nq/**` ⇒ depgraph
regen + full suite. Pre-committed reading, `path_days` set **once** at 4,598, no scanning:

| 18.5y bootstrap median MaxDD | reading |
|---|---|
| ≤ −55% | gap is path length; 0001 is consistent with the literature; nothing further owed |
| −45% to −55% | length explains most; name the 5–10pp residual openly as window/regime |
| > −45% | length does **not** close it — **defect signal**, route to `red-team` before citing 0001 again |

### 2.3 Clenow ranker — **the code already exists; the gap is wiring**

`nq/signals/__init__.py:132` `clenow_score`, `:166` `above_sma`, `:173` `max_gap`, four tests at
`tests/test_signals.py:224-266` including PIT truncation. Committed in `4b528ca`, never wired into a
study.

What is genuinely missing: a panel-level `clenow_qualified()` that maps disqualified names to **NaN,
not a low score** (the engine removes by `dropna()`; a sentinel would still sort into the top-30);
a `RANKER` flag defaulting to `"nms"`; and a new `pipelines/research/run_0002_clenow_ranker.py`.
The golden master cannot be reached by a ranker change — `tests/fixtures/rebalance_golden_panel.csv`
bakes in a pre-computed `rank` column and never imports `nq.signals`.

**Five defects in the existing code, fix before pinning anything:** `np.exp(slope)**periods - 1`
overflows to `inf` above slope ≈ 2.8 (use `np.expm1(slope*periods)`); `periods=250` vs the module's
`YEAR_DAYS=252` **re-orders** results because `× R²` is not monotone; `max_gap` measures
close-to-close, which is *not* Clenow's gap; `min_periods=45` fails open; and the Python loop (~960k
iterations) must be vectorised *before* any pin, never after.

**Do the screen before the trial.** Rank-IC of `clenow_q` vs forward-63d, and Spearman between the
Clenow and NMS orderings. **If the two rankers agree at ρ > ~0.8 the head-to-head is a coin flip
inside the ±0.59 band and the trial is not earned.** Screen costs zero trials.

### 2.4 Turnover conditioning — **largely answered, and against the claim**

`research/findings/0136-universe-buckets.md` already ran PIT turnover buckets per date: equal-weight
buy-and-hold earns **15.80 / 15.40 / 15.59%** across LARGE / MID / SMALL — **within 0.4pp, not the
claimed 10.9pp.** And `research/eng-02-membership-proxy.md` measured higher-turnover admissions
earning **+2.44pp more** forward-63d, which points the opposite way to BacktestIndia.

**The two external claims contradict each other** (BacktestIndia: low turnover wins; Medhat–Schmeling:
high turnover ⇒ momentum). The compendium presents them as aligned. Any test must therefore be a
**direction-agnostic quintile map**, never a confirmation — and it must clear each quintile's *own*
equal-weight buy-and-hold, which is 0136's binding bar and which nothing has cleared yet.

Note also `MIN_TURNOVER = ₹5cr` (`nq/universe/__init__.py:50`) already truncates the low end, so our
lowest bucket is **not** BacktestIndia's winning bucket.

### 2.5 Scaled turnover — the one genuinely new instrument

The "market cap isn't reconstructable" note at `pipelines/build/build_ff_india_factors.py:10-13` is
**stale**: `shares = net_profit / eps_ttm` from `fundamentals_pit_depth.pkl` gives 653 names at 98.4%
of rows. And mcap is not needed — `ΣPV / PS = ΣV / S`, so **scaled turnover = volume ÷ shares** and
price cancels. Near-orthogonal to rupee-turnover rank (Spearman ~0.21).

Honest limits: **85.8% PIT coverage** on MID name-days with non-random missingness (a coverage audit
is mandatory first); no free-float data anywhere in the repo, and Indian promoter holding of 40–75%
correlates with exactly the governance dimension the gate is meant to measure; group structures
over-state shares (RELIANCE +18%). **A better-banked alternative already exists**: delivery
percentage (`nq/data/delivery.py`, PIT-proven) already **passed screen #7** at conditional dR
**+0.363 [+0.13, +0.58]**, needs no shares estimate — but spans only 2019+.

Standing prior to record before testing: 0108's structural killers (removing momentum winners;
cash-redeploy inversion) are freshness-independent, and 0136's law is that universe narrowing is not
a return lever on this family. **The honest prior is that the +3.9pp does not replicate.**

### 2.6 Loss-limitation and bear-state machinery — the owner's real requirement

#### 2.6.1 Why "zero losing years" cannot be bought with an exposure rule — the decisive argument

Solving the two committed numbers (Sharpe 1.130, CAGR 21.73%) for the distribution: **σ ≈ 21.22%,
arithmetic mean ≈ 23.98%**, so **P(calendar year < 0) = Φ(−1.130) ≈ 12.9%** — about **1.3 losing
years per decade**, and P(zero in ten) ≈ 25%. Daily skew on the momentum base is **−0.639**
(`forward/prereg.md:36`), so the real tail is worse than Gaussian. To reach P ≤ 1% you would need
**47.1% CAGR at the current volatility, or 9.5% volatility at the current CAGR.**

Now the part that closes it. A gross-exposure multiplier `k_t` scales daily returns.

- A **constant** `k` scales mean and σ *together*. Sharpe is unchanged, so **P(year < 0) is exactly
  unchanged.** It shrinks the loss and the gain in the same proportion.
- A **time-varying** `k_t` changes P(loss) *only* through correlation between `k_t` and forward
  returns — that is, **only through timing skill.**

This programme has looked for that skill three times and not found it: **0134** (nine PIT market-state
variables, all null, every quintile CI overlapping), **0103** (regime-feature IC −0.09…+0.08; every
walk-forward switch loses out-of-sample to a static blend, 1.00/0.80/0.69 vs 1.18), and **0135's
clairvoyant bound** — perfect foresight of each year's sign was worth only **+6.56pp**, with every
real gate landing −0.7 to −3.4pp.

**So zero losing years is reachable only three ways: a timing edge looked for five times and not
found; a defined-risk tail hedge that pays a premium every year (0100/0102/O-023 — all killed); or
fitting to the two negative episodes in the sample.** Finding 0135 §6.1 names the last one outright:
*"The family has TWO negative years here. No timing rule can be fit or validated on two events."*
**That is what a literal reading of the request would produce.**

#### 2.6.2 The comparison the owner most needs to see

`research/findings/0135-*.md:77` — on the exact axis being asked for:

| 2017-2026 | CAGR | Sharpe | MaxDD | losing years |
|---|---|---|---|---|
| **NIFTY-50 buy-and-hold** | 11.98% | 0.787 | −38.4% | **1 / 10** |
| the surveyed strategy family | lower | lower | deeper | **4 / 10** |

**If the objective is literally "fewest losing years", the index is the incumbent to beat.** Same
finding, `:90`: gating the index halves its drawdown (−38.4% → −19.9%) at roughly half the CAGR
(11.98% → 6.35%). That is the real exchange rate between drawdown and return, measured on our data.

#### 2.6.3 What exists in code, and what is merely reported

| | state |
|---|---|
| **§4 mechanical halt** (live MaxDD ≤ −50%) | **Pre-registered and owner-approved, but only *reported***: `bhanushali_review_scorecard.py:39,132`. **No engine or cron blocks a fill on it.** |
| `kill_flags()` (`nq/paper/book.py:160`) | Built, hardcoded `"mode": "observe"`, read by nothing. **Contains no drawdown term at all.** |
| `vol_target_scalar` | Live on the momentum paper book only (O-009). De-gross only, never levers. |
| **`exposure_by_date`** (`nq/engine/rebalance_book.py:135,402`) | **Built, tested, and wired to nothing** — grep finds only the engine and its tests. Freed cash sits idle. |
| Swing live path | **No drawdown logic anywhere.** `LIVE_DISCIPLINE` is per-name caps, and its own comment says the notional cap is *"a GUARDRAIL… NOT a performance lever."* |
| `signals_today.json` regime block | Hardcoded stub `{"status":"UNKNOWN","vix":0,"breadth":0}`. Reads like machinery on the dashboard; isn't. |

#### 2.6.4 Three items to do regardless — zero trials, no pre-registration

1. **Wire the §4 halt.** Already owner-approved and pre-registered; currently only printed to a JSON
   nobody renders. Enforcing it in the cron is pure engineering and is the *only* part of "stop
   trading after large losses" that already has governance behind it.
2. **Emit a per-calendar-year table** from `run_0001_xsec_momentum.py` — three lines beside the
   per-regime block at `:175-183`, reusing `sub_slice`. **Nobody can currently state 0001's
   losing-year count**; only four regime slices are published. This turns "minimise losing years"
   from a slogan into a committed number.
3. **Sector-cap firing-rate census.** On a top-30 book drawn from a ~150-name band the cap may
   almost never bind. Measure the firing rate before writing any cap code.

#### 2.6.5 The one trial worth running: BREADTH_REG, re-run on the pinned universe

`diagnostics/research/preregistry/0070-crash-overlay.md`. A continuous breadth-and-trend exposure
throttle — explicitly designed *not* to repeat O-001's binary failure. It is **the only lever in the
whole corpus that improved 2018 AND 2020 AND 2025 at once**: best Calmar 0.668 vs 0.623, shallowest
DD −38.3 vs −41.9, CAGR cost **0.53pp**, ~95% deployed in calm years. It failed on exactly two gates,
both narrowly.

**And its own pre-registration says why to re-run it** (`:81-84`): it was measured on an *unpinned*
universe whose rebuild noise moved the 2020 floor by **3.7pp** — against a claimed effect of 3.6pp.
**A pinned re-run may show the entire result was build noise. That is the likely outcome, and it is
exactly why the trial is worth spending: right now nobody knows which it is.**

Why 0095's de-gross KILL does not transfer: 0095's mechanism was cash freed by de-grossing being
redeployed by a *strongest-first fill loop* into more, weaker signals (255→349 trades, expR
0.48→0.33). `simulate_rebalance_book` **has no fill loop** — exposure scales target weights and
freed cash sits idle (`:381` asserts cash ≥ 0). Law II carves this out explicitly.

**Implementation:** new `breadth_exposure()` in `nq/research/overlays.py` returning the
`{date: multiplier}` contract `exposure_by_date` already accepts; **no engine change at all**, so
`tests/test_rebalance_golden.py` stays byte-identical *by construction* rather than by a flag. One
pre-declared functional form, no sweep. Five tests, of which the load-bearing two are trailing-only
truncation invariance and *"the throttle actually fires"* — 0087's `wstall` fired 4 times in 9.5
years and that must not ship again.

**Order of operations, and the most likely stopping point:** run the **zero-trial clairvoyant
activation bound first**, per the standing law. That gate is **5/5 and has never passed**. If perfect
foresight of the throttle's activations is worth less than the ±10R/yr floor, **there is no trial —
record the bound and stop.** This step most likely kills the idea for free, which is why it goes
first.

If it survives: `n_trials` **2 → 3, committed before the run**; gates restated verbatim from 0070's
own so the re-run cannot be graded softer than the original (ΔCalmar ≥ +0.05 AND ΔSharpe CI-low >
−0.10 AND MaxDD ≤ 0.90×OFF AND ≥2 of {2018, 2020, 2022} improve AND CAGR cost ≤ 1.5pp); primary
metric **Calmar/MaxDD, not Sharpe** — it is a drawdown lever. **UNDERPOWERED is the modal outcome
and is stated up front**: the whole claimed effect (~3.6pp of MaxDD for 0.53pp of CAGR) sits inside
the ±0.59 band.

#### 2.6.6 A governance finding, surfaced in passing

**Pre-registration 0074** (Daniel–Moskowitz bear-state × realised-vol throttle) was committed on
2026-07-01 and `n_trials` was incremented 80 → 81 for it — **and it was never run**
(`research/OVERNIGHT_LOG.md:34`, "NOT RUN (judgment call) — DEFERRED"). A trial was charged against a
study that produced no evidence. It should either be run or formally withdrawn with the counter
noted; leaving it is a silent debit against every DSR computed since.

#### 2.6.7 The honest adversarial read on all of the above

The family record on this axis is brutal: **five regime-gate KILLs** (O-001, A5, 0056, 0086, 0090),
**both stop directions KILL** (0105 tighten, 0106 widen), **the zero-whipsaw disaster floor KILL**
(0109), **de-gross KILL on the swing book** (0095), and the **activation bound 5/5, never passed**.
0070's own conclusion is that the cheap-overlay programme has **plateaued at ~−38%**. The single
positive result in the entire family — O-009 — is on a book that is not this one.

**The realistic expectation for §2.6.5 is a null.** It is proposed not because it will work but
because it is the one candidate whose prior failure has a named, measurable, harness-level cause.

### 2.7 Code-correctness sweep
- The cost-sensitivity defect (§1.5a) — unresolved, blocking any cost-sensitivity claim.
- The five Clenow defects above.
- The stale SMB note at `build_ff_india_factors.py:10-13`.
- Remaining mutation-testable holes: `DE_MAX` free in (0.84, 1.6], `ADV_PERSISTENCE_WINDOW`
  unpinned, corporate-action threshold free in (0, 0.615), `_grade` cutoffs, live buy window.

---

## 2.8 Start here in the morning

Ordered by information per unit of multiplicity spent. Items 1–4 spend **no trial** and need no
pre-registration; nothing below item 5 should begin until 1–4 are done.

| # | Do | Cost | Why first |
|---|---|---|---|
| 1 | **Per-calendar-year table** for 0001 (§2.6.4) | ~3 lines | Nobody can state 0001's losing-year count today. Every claim about "minimising losing years" is currently unmeasurable. |
| 2 | **Wire the §4 halt** (§2.6.4) | engineering | Already owner-approved and pre-registered; today it is printed to a JSON nothing renders. This is the one piece of "stop trading after big losses" that already has governance behind it. |
| 3 | **Diagnose the cost-sensitivity defect** (§1.5a) | investigation | `21.73% → 21.73%` at 1.5× costs on a 311%/yr-turnover book is not credible. Blocks every cost-sensitivity claim until resolved. |
| 4 | **Clairvoyant activation bound for BREADTH_REG** (§2.6.5) | zero trials | The gate is 5/5 and has never passed. **Most likely outcome: the idea dies here for free.** |
| 5 | **Clenow ρ-screen** (§2.3) | zero trials | If Clenow and NMS agree at ρ > 0.8, the head-to-head is a coin flip inside the noise band and the trial is not earned. |
| 6 | **Path-length Monte Carlo** (§2.2) | zero trials, touches `nq/**` | Settles whether 0001's shallow drawdown is bias or sample length, without needing 2008 data. |
| 7 | Only if 4 survives: **BREADTH_REG trial**, `n_trials` 2→3 | one trial | The single lever that ever helped 2018, 2020 and 2025 at once, whose prior failure has a named harness-level cause. |

**Not recommended:** tuning 0001. Its own PBO (0.452, 1.5 SE from chance) says the specific
parameters are unsupported within their neighbourhood. Tuning is the one activity guaranteed to
spend trials and learn nothing.

**Owner decisions that no amount of research can substitute for:**
1. Accept the honest frontier of §1.3 (18–22% net, −55/−60% planning drawdown, losing years
   minimised not eliminated), or reject it and say what should change.
2. §2.6.6 — pre-registration 0074 charged a trial and was never run. Run it or withdraw it.
3. 2026-10-01: the veto arm (retire or fund the factor rebuild) and the scorecard reconciliation.

## 3. Sequencing principle

Measurements that spend no multiplicity come before trials that do. Under the 2026-08-08 owner
amendment, nothing may be killed without a run — so the scarce resource is no longer *permission to
close a path*, it is **trials on 37 independent windows**. Every trial deflates the bar for the next
one. The plan spends them in order of expected information, not expected return.
