# Verification audit 2026Q3 — tracking index

**Class: VERIFICATION.** Zero trials, zero new screens, no new hypotheses.
**Counts: screens 14 · sealed opens 1 · n_trials 138 — identical at start and at every commit.**
Sealed 2024H2+ **not re-opened** (re-verification uses committed artifacts).
Judge log **not read** (chain-verified by hash only; no verdict deserialised).

**Multi-session by design. Progress commits per tier.** This index is the state of the audit;
every item carries a status and, once run, an evidence link.

Status vocabulary: **PASS** · **DISCREPANCY** (both numbers + mechanism, owner decides) ·
**IRREPRODUCIBLE** (script absent / won't run / needs undocumented inputs — itself a finding) ·
**PENDING**.

---

## Session 1 (2026-07-31) — Tier A live-money items

Evidence: `tierA_live_results.json` · script `scripts/audit_tierA_live_2026Q3.py`

| item | pass 1 mechanical | pass 2 independent | pass 3 arithmetic | status |
|---|---|---|---|---|
| **A7 NAV / ledger identity** | n/a (artifact) | ✅ re-derived from JSON | ✅ 3 identities | **PASS** |
| **A6 D5 card arithmetic** | n/a (artifact) | ✅ recomputed every printed field | ✅ | **PASS** |
| **A5 band census** (+0.717 / +0.094 / +2.088) | ✅ | ✅ from substrate, no census import | ✅ | **PASS — exact** |
| **A8 cost model vs NSE** | n/a | ✅ hand-computed line items | ✅ | **MEASURED — gap quantified, see below** |

### A7 — NAV identity **PASS**

`cash 87,924.20 + Σ positions 925,495.47 = 1,013,419.67` vs stated `total_value 1,013,421.36`.
**Residual −₹1.69 on ₹1.01M (1.7 ppm).**

The residual is **fully explained by 2-dp share rounding in the stored artifact**, and the tolerance
is **derived from the stored precision** (`0.005 × price + 0.005` per position), not relaxed to fit.
Every position is inside its own bound; per-position P&L and P&L-% re-derive independently.
`n_positions` matches. **This is a rounding artifact of the JSON representation, not a ledger leak.**

### A6 — D5 card arithmetic **PASS** (2 FRESH cards, as-of 2026-07-31)

For every FRESH buy card: `risk > 0` ✓ · `stop == entry_low` ✓ · `entry ∈ [low, high]` ✓ ·
`target == entry + 2×risk` ✓ (R:R exactly 2.000) · tranche percentages sum to 100.000 ✓ ·
`ext_pct_over_sma44` re-derived from the committed SMA panel to **0.00 delta** ✓ ·
`record_would_skip_as_extended` reproduces the cron's rule `entry > sma44 × (1+cap)` ✓.

**Audit-script error recorded (pass 1 of this item):** the first pass scoped the extension check to
all `tier == "signal"` rows and flagged 15 mismatches. Those rows are **held positions**
(`ACTIVE` / `HIT_STOP`), and the ext/skip block is a **pre-buy** decision aid the cron emits only at
issue — their absence is correct. Scoping to `status == "FRESH"` clears it. **Recorded because a
false positive in an audit is as damaging as a missed defect**, and the correction is part of the
evidence, not a footnote.

### A5 — band census **PASS, exact**

Re-derived from `research/substrate/trades.parquet` with plain masks, importing nothing from
`diag_ext_band_census.py`:

| cell | published | re-derived | delta |
|---|---:|---:|---:|
| `<5%` deep core | +0.717 (N=418) | **+0.717 (N=418)** | 0.000 / 0 |
| `5-10%` band | +0.094 (N=615) | **+0.094 (N=615)** | 0.000 / 0 |
| sub-line `<0%` | +2.088 (N=39) | **+2.088 (N=39)** | 0.000 / 0 |

Double-entry satisfied: two independent code paths, identical to three decimals and exact on N.

### A8 — cost model vs NSE reality **MEASURED** (not a pass/fail; a quantified gap)

Hand-computed round-trip friction on a ₹1L delivery leg, itemised:

| line item | ₹ |
|---|---:|
| STT (0.1% × 2 legs) | 200.00 |
| brokerage (0.03% × 2) | 60.00 |
| exchange txn (~0.00297% × 2) | 5.94 |
| SEBI (0.0001% × 2) | 0.20 |
| stamp (0.015%, buy only) | 15.00 |
| GST 18% on charges | 11.91 |
| DP (flat, sell side) | 15.34 |
| **total** | **308.39 = 30.84 bps** |

**Engine models 26.00 bps** (STT + brokerage) **plus ADV-tiered slippage and √-impact on top.**

**The statutory gap the engine does not name is ≈4.8 bps round-trip** — exchange, SEBI, stamp, GST
and DP. It is **materially smaller than the slippage term the engine does charge** (5–40 bps by
tier), so the engine is not obviously under-costing; but the omission was previously unquantified and
is now a known number. **No change proposed** — recording the gap is the deliverable.

---

## Session 2 (2026-07-31) — annualisation, alpha decomposition, anchor robustness

Evidence: `session2_annualization_anchor.json` · `session2_alpha_decomposition.json`
Scripts: `scripts/audit_annualization_anchor_2026Q3.py` · `scripts/audit_alpha_decomposition_2026Q3.py`

| item | status |
|---|---|
| **1. Annualisation sweep** | **PASS — CONSISTENT** |
| **2a. 0114 re-verification** | **PASS — claims stand, and are narrower than remembered** |
| **2b. Alpha decomposition** (new Tier-A) | **DELIVERED** |
| **3. Rebalance-anchor robustness** | **PASS — stable, not a knife-edge** |
| **A4 two-sleeve ERC blend** | **DISCREPANCY — producer IRREPRODUCIBLE** ⛔ |

### 1 — Annualisation sweep: CONSISTENT

The constant alone proves nothing; the test is the constant applied to the right **frequency**. For
each load-bearing book, all four candidate conventions were computed and compared to the published
figure:

| book | published | daily×√252 | weekly×√52 | daily×√52 (mixed) | weekly×√252 (mixed) | reproduced by |
|---|---:|---:|---:|---:|---:|---|
| swing sleeve | 1.15 | **1.153** | 1.139 | 0.524 | 2.531 | daily×√252 ✅ |
| low-vol sleeve | 1.06 | **1.057** | 1.023 | 0.480 | 2.271 | daily×√252 ✅ |

`third_sleeve_returns.csv` is confirmed **daily** (median day-gap 1.0). **No book reproduces under a
mixed convention** — the mixed forms are off by 2.2×, far outside any rounding. `nq/validation/metrics.py`
and `nq/engine/portfolio.py` both pin `TRADING_DAYS = 252` and are applied to daily series.
**Site inventory:** ~50 `sqrt(252)` call sites across `scripts/diag_*`, all operating on daily engine
curves; `diag_pbo_cscv.py:57` uses `sqrt(12)` on the **monthly** PBO matrix (correct for its input);
`nq/data/options_oi.py:215` uses `sqrt(21)` for a 21-day realised-vol feature (not a book Sharpe).
**No mixing found.**

### 2a — 0114 re-verified: its claims stand, and are narrower than they are often quoted

0114 compared the swing book's **monthly, after-tax NET** returns to **investable ETF NAVs** and
reported after-tax CAGR margins (+3.5pp vs LowVol-30, +1.1pp vs AlphaLowVol-30, +4.3pp vs Nifty-50,
all at a 10% execution haircut). It records the niftyindices TRI endpoint as **WAF-blocked on
2026-07-27** and argues ETF NAVs are the more honest investable benchmark.

**It never computed beta or alpha.** Anyone citing 0114 for "the book's alpha" is over-reading it.
Item 2b is therefore **additive**, not a contradiction.

### 2b — Alpha decomposition vs Nifty-500 **TRI** (new Tier-A item)

Daily OLS `r_book = α + β·r_bench`, α annualised ×252, **risk-free = zero (stated, not hidden)**.

| book | β | R² | **α / yr** | SE | t | 95% CI | book CAGR | bench CAGR | +α years |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|
| swing sleeve | 0.885 | 0.43 | **+13.92%** | 5.80 | 2.40 | [+2.6, +25.3] | 25.67% | 12.62% | 7/10 |
| low-vol sleeve | 0.617 | 0.56 | **+6.13%** | 3.10 | 1.98 | [+0.1, +12.2] | 14.16% | 12.62% | 7/10 |
| **swing+lowvol EW** | **0.751** | 0.61 | **+10.03%** | 3.41 | **2.94** | **[+3.3, +16.7]** | 20.31% | 12.62% | **9/10** |

**The honest sentence:** *over 8.8 years, the two-sleeve structure earned **+10.0% ± 3.4 a year over
the Nifty-500 total-return index** (95% CI +3.3 to +16.7) at **beta 0.75**, positive in **9 of 10
calendar years**.*

**Four things that shrink it, all stated:**
1. **Zero risk-free overstates.** At an Indian RF of ~6.5%, α falls by `(1−β)·RF` ≈ **1.6pp → ~8.4%/yr**
   for the pair (swing → ~13.2%, low-vol → ~3.6%). Sensitivity, not a restated headline.
2. **These are sole-ranker sleeve panels, not the capped ₹10L book of record.** Strategy alpha, not
   tradable-book alpha.
3. **In-sample and pre-haircut** — before 0113's ~⅓ selection haircut and the 0025 survivorship debt
   (known to inflate in this direction).
4. The single largest α year is **2026, a stub half-year** whose annualised figure is unreliable.

Applying (1)+(3) lands near 0114's after-tax ETF margins, so the two lenses are **consistent**.

### 3 — Rebalance-anchor robustness: STABLE

Quarterly ERC re-implemented from its stated rule and the anchor shifted 0–6 weeks:

| offset | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sharpe | 1.248 | 1.254 | 1.261 | 1.261 | 1.263 | 1.258 | 1.266 |
| MaxDD % | −32.57 | −32.53 | −32.47 | −32.46 | −32.40 | −32.45 | −32.40 |

**Sharpe spread 0.018; DD spread 0.17pp; zero losing years at every anchor; worst year 4.9–5.4%.**
**The 1.22/−33% is a property of the sleeves, not of the calendar.** → binder line.
**Flagged to the breadth-50 §4 stub:** its spec inherits this question and should state its own
rebalance anchor explicitly.

### A4 — ⛔ DISCREPANCY: the blend's producer is IRREPRODUCIBLE

**No committed script produces 0115's 1.22 / −33%.** A repo-wide search for `third_sleeve` in `*.py`
returns **only this audit's own scripts** and `run_weinstein_0124.py`. The *input*
(`third_sleeve_returns.csv`) is committed and 0115 documents how the sleeves were built; the **blend
arithmetic on top of it is not in the repo**. Pass 1 (mechanical replication) cannot be performed.

**Independent re-derivation lands at Sharpe 1.248 / DD −32.6 vs published 1.22 / −33%** — same
direction, ~+0.03 Sharpe and ~0.4pp shallower DD. **Root cause of the divergence: the rebalance rule
is under-specified in the finding** (0115 says "quarterly inverse-vol ERC" without naming the vol
lookback; this audit used trailing 252d).

**Does it move a standing verdict? No** — the verdict is "the swing × low-vol pair is the structure
of record", and 1.248 supports it at least as strongly as 1.22. **Reported, not corrected**; the
published number stands until the owner decides. **Recommended remedy: commit the producer script**
so the Oct-1 binder cites a reproducible number.

---

## Session 3 (2026-07-31) — 0115 remedy, disaster drill, A1/A2/A3, falsification register

Evidence: `DISASTER_DRILL.md` · `research/exports/two_sleeve_blend.json` ·
[`skills/program-laws/FALSIFIERS.md`](../../../skills/program-laws/FALSIFIERS.md)

| item | status |
|---|---|
| **1. 0115 remedy** — producer committed, lookback recovered | **CLOSED — D1 remedied** |
| **2. Clean-clone disaster drill** | **DONE — 4m37s; 4 gaps found** |
| **A3 swing record 1.132 + goldens** | **PASS — exact in a clean clone** |
| **A2 corrected-anchor table** | **PASS** (minor CAGR divergence recorded) |
| **A1 baseline_v1 anchors** | **IRREPRODUCIBLE — no producer script** |
| **4. Falsification register** | **DONE — 4 armed / 3 contingent / 1 to demote** |

**0115 remedy.** The vol lookback was recovered as **126d** by asking which value reproduces the
*published* triple, not which maximises anything. Reproducible figure **Sharpe 1.237 / MaxDD
-33.04% / worst year +5.62%** vs published 1.22 / -33% / +5.6% — **DD and worst-year agree within
rounding**; the residual **+0.017 Sharpe is unexplained and was not tuned away**. Producer:
`scripts/build_two_sleeve_blend.py`. Anchor stability re-confirmed at the recovered lookback (Sharpe
spread 0.023, zero losing years at every anchor). 0115 carries a dated addendum with the published
triple preserved as as-measured-then; breadth-50 §4 carries the inherited-question note.

**Disaster drill.** Full reconstruction from `git clone` + releases only, in **4 min 37 s**. The
pinned `ohlcv.pkl` sha256 **`f8625a8f…` matches CLAUDE.md exactly**; goldens (22) and the full suite
(218) pass identically to the working tree; A2 reproduces and with it A3's **Sharpe 1.132 / MaxDD
-42.4% exactly**. Four gaps found — see `DISASTER_DRILL.md`: the documented `pip install` fails on
Python 3.13, two artifacts exist in neither git nor either release, and **baseline_v1 has no producer
script**.

**Falsification register** (new, beside `program-laws`): **ARMED** — Laws IV, V, VI, VII.
**CONTINGENT** — Laws I, II, III (judge API key unset; breadth-50 Oct-1 sign-off; habit ledger
unbuilt). **Law VIII flagged for demotion to PROTOCOL** — procedural commitments are not empirical
claims, so no market measurement can overturn them. **Finding: three of seven empirical laws,
including the two most-cited, have no live falsifier today.**

---

## Session 5 (2026-08-05) — CLOSEOUT

Evidence: `EXECUTIVE_SUMMARY.md` · `ANCHOR_MANIFEST.md` · `SESSION4_BLIND_REPLICATION.md`

| item | status |
|---|---|
| **0. Judge stream** | **D5 FOUND AND FIXED** — key was set and the Aug-1 run judged 17 cards at $4.00, but `.gitignore` discarded every one; whitelisted (PR #64), scanner re-dispatched |
| **1. G4 / anchor manifest** | **STANDARD WRITTEN** — `ANCHOR_MANIFEST.md`; `baseline_v1` producer designation **still open (D2)** |
| **2. G1 python pin** | **FIXED** — `<3.13` → `<3.14`; CI stays pinned to 3.12 |
| **2. G2 substrate rebuild** | **CLOSED — exercised end-to-end, 100 s**, reproduces all three band-census cells exactly |
| **2. G3 fundamentals depth** | **OPEN** — no rebuilder, no release attachment |
| **3. Blind-replication intake** | **FILED** as session 4 — intake only, not independently confirmed |
| **4. Executive summary** | **DONE** |

**Law I moved CONTINGENT → ARMED** as a direct result of item 0: its falsifier existed on paper and
was being deleted weekly in practice.

---

## Remaining scope

### Tier A — PENDING

| item | note |
|---|---|
| ~~A1 baseline_v1 anchors~~ | **session 3 — IRREPRODUCIBLE, no producer script (D2)** |
| **A2 corrected-anchor table** (0.737 + alias-aware + backfill arms) | `scripts/run_corrected_anchor.py` |
| ~~A3 swing record + goldens~~ | **session 3 — PASS, exact in a clean clone** |
| ~~A4 two-sleeve ERC blend~~ | **done session 2 — DISCREPANCY (irreproducible producer)** |

### Tier B — PENDING (standing-law receipts)

0118 (+0.363) · 0120 (−0.383) · the four activation bounds (rotation ≈+11R clairvoyant, tiebreak
−1.29, deferral −15.72, hugger 1.92 / 0.0-identity) · 0123 nulls + instrument stats (κ 0.867,
truncation probe) · 0124 Weinstein · 0125 power arithmetic · 0126 / 0127.

### Tier C — PENDING (auditor-selected spot checks, five findings, method-diverse)

---

## Cross-cutting arithmetic checks — PENDING

~~Sharpe annualisation consistency~~ — **done session 2, CONSISTENT, no mixing found**;
CAGR↔Sharpe↔vol mutual consistency; per-year tables summing to totals; R-definition consistency
across scripts (same risk denominator, same fill convention); CI method appropriateness
(bootstrap iid vs overlapping windows — **flag, do not fix**).

## Discrepancy ledger

| # | item | published | re-derived | mechanism | moves a verdict? |
|---|---|---|---|---|---|
| **D2** | A1 baseline_v1 anchors | 0.667 / 15.46 / -46.26 | — | **no producer script exists**; only consumers of `baseline_v1.json` | **Unverifiable, not wrong.** Same class as D1. Remedy: commit the producer. |
| **D3** | clean-clone install | `pip install -e .` documented | **fails** on Python 3.13.5 (`pyproject` pins `<3.13`) | code still runs via `sys.path.insert`; CI pins 3.12 so is unaffected | **Latent**, not active. |
| **D4** | recovery artifacts | — | `trades.parquet`, `fundamentals_pit_depth.pkl` in neither git nor either release | rebuildable (former) / no named rebuilder (latter) | Recovery risk. |
| ~~D1~~ **REMEDIED s3** | A4 two-sleeve ERC blend | Sharpe **1.22** / DD **−33%** | **1.248** / **−32.6%** | producer script **not in the repo**; rebalance vol-lookback **under-specified** in 0115 | **No** — the verdict ("the pair is the structure of record") is unchanged and marginally stronger. Reported, not corrected. |

One **audit-script error** is also recorded (session 1, A6 scoping); it is not a repo discrepancy.

## Guards in force

- Any discrepancy that could move a standing verdict → **STOP on that item**, report both numbers
  and the mechanism, owner decides. **Never silently correct a finding.**
- **Fishing guard:** anything interesting noticed goes to `PARKING_LOT.md` **unanalysed**. This audit
  validates old answers and is forbidden from generating new questions in the same pass.
- No retunes, no threshold edits, no golden re-records without a stated diff and sign-off.
