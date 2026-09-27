# forward/prereg_swing.md — Swing-Book Forward-Wall Pre-Registration

**Status:** PRE-REGISTERED (locked before the decision review)
**Version:** 1.0 (registered 2026-07-13)
**Strategy:** Bhanushali weekly-swing, ranker of record `weekly-swing-0094` (CRS-strength fill).
**Anchor:** `0094` on the CORRECTED universe (`dataset-pin-20260701` ohlcv_sha `f8625a8f…` + delisted
backfill + `delisted_alias_map.json`), via `corrected_universe()`.
**Author/owner:** Kreesh Patel
**Companion:** the momentum wall (`forward/prereg.md`) — that book is decommissioned/WATCHED; this is the
live single-sleeve. This doc governs the swing book ONLY.

---

## 0. Why a forward wall for the swing book

The single-sleeve swing search is out of unbiased in-sample information, for the same reason the momentum
sleeve was (`forward/prereg.md §0`). At **n_trials = 114** the Deflated-Sharpe bar is high enough that any
new in-sample cut that "wins" is indistinguishable from a search-max. The 2026-07-13 volume thread
confirmed it three more ways (§7): every candidate that beat the baseline in-sample was a narrow peak, a
zero-spread IC, or an unrepresentative-population artifact. **The only remaining source of unbiased
information is forward data on a book that is not re-fit.**

This document fixes — **before the first decision review** — the rule that decides which grading the live
product runs. Thresholds here may be **tightened or clarified** with a dated amendment; they may **never be
relaxed retroactively**. Moving a goalpost after seeing forward data voids that criterion.

## 1. The in-sample reference distribution (what forward is judged against)

Reproduced NET after costs (STT 0.1%/leg + brokerage 0.03%/leg + tiered slippage), corrected universe,
2017-01-02 → 2026-06-29, via `python scripts/run_bhanushali_weekly_rank.py` (finding 0094 / 0038):

| Book | Sharpe | CAGR | MaxDD | Calmar | Win% | Trades/yr | DSR |
|---|--:|--:|--:|--:|--:|--:|--:|
| **base-swing** (all grades, fund strongest-first) | **1.132** | 24.7% | −42.4% | 0.58 | 59.2% | 27 | 0.894 **@ n_trials 114** |

*Dated clarification, 2026-08-09 (permitted by the tighten-or-clarify rule above; no threshold
changes).* **DSR 0.894 was deflated at n_trials = 114** — the count stated in §0 — and the two are
one fact, not two. This matters now because the counter was reset 138 → 0 → 2 on 2026-08-07 by owner
decision, while `scripts/run_bhanushali_weekly_rank.py:977` computes the run of record's DSR from
the **live** counter (`n_tr = cumulative_n_trials()`) and gates on `DSR > 0.95` at `:983`. Since
`expected_max_sharpe` is strictly increasing in the trial count, DSR is strictly decreasing in it —
so **re-running the certified configuration today, unchanged, yields a higher DSR and a more
flattering verdict than the one it was certified with.** The certification is therefore no longer
reproducible from the pipeline; it is reproducible only from this line. `tests/test_swing_certification_provenance.py`
holds it here.
| **A-only** (top-5 CRS per ISO week) | 1.003 | 21.2% | **−36.3%** | 0.58 | 54.9% | 26 | — |

Sub-period (continuous-slice) Sharpe — base / A-only: 2017-18 **1.17 / 0.75**, 2019-21 **1.05 / 1.30**,
2022-26 **1.19 / 0.90**. Bootstrap 95% Sharpe CI — base [0.47, 1.71], A-only [0.36, 1.54].

**Honest statement of what is and isn't claimed.** A-only is **not** an in-sample edge over all-grades —
it is **lower return at a shallower drawdown, same Calmar (0.58)**. It is a *defensive product variant*,
not a return improvement. The forward wall exists to answer two OOS questions that in-sample cannot:

1. **Does the CRS top-5 concentration hold its risk profile forward** — i.e. does A-only keep its
   shallower-DD / ~equal-Calmar shape on data it was never selected on, or does the concentration bite?
2. **Does CRS ranking carry any forward signal at all** (0094's open premise — in-sample its rank-IC was
   real, +0.08, but did not convert to a portfolio win; IC ≠ Sharpe)?

## 2. Books logged forward (hard cap: these two — no third without a recorded swap)

| Book | Status | Rule | Operational log |
|---|---|---|---|
| **base-swing** | WATCHED (reconstructable) | All grades, fund strongest-first from the ₹10L-equivalent cash gate. | Reconstructable from the **uncapped signal ledger** `results/signals_history_weekly.json` (every signal, all grades). |
| **A-only** | **PAPER (live product)** | Trade only the top-5-CRS-per-ISO-week names. | `results/paper_portfolio_weekly.json` (NAV) + `results/signals_history_weekly.json` (designation history). |

Both are written daily/weekly by `scripts/run_bhanushali_cron.py` (§F of `docs/SYSTEM.md`). The A-only book
is the one carrying the (paper) capital; base-swing is logged-not-traded and reconstructed from the same
signal ledger, so the two share ONE signal source per run (no divergent-panel risk).

## 3. Capital phase gate (mirrors the momentum wall §1)

A-only is **PAPER** now. It transitions to small real capital ONLY via a dated §10-style amendment once
the repo paper gate (`skills/portfolio-simulation`) is met: **≥ 30 closed trades AND ~2 months** of paper.
Phase-A paper measures signal continuation only; it does NOT clear execution-cost reality (real slippage /
MTF / own-behaviour-under-drawdown) — that is Phase-B, real-capital only.

## 4. The decision (pre-committed)

**When:** the quarterly reviews (first trading day Jan / Apr / Jul / Oct). Primary decision at the
**12-month review (2027-07-01)**; the **2026-10-01** review is a first read only (too few closed trades to
decide). Between reviews: **log and leave it alone** — no config or grading change (except the mechanical
halt, §5).

**What is decided:** which grading the live product runs — **A-only** vs **base-swing (all grades)**.

**Rule (frozen):**
- **Keep A-only** if, on forward closed trades, it holds its in-sample bargain: forward **MaxDD shallower
  than base-swing** AND forward **Calmar ≥ base-swing − 0.05**. (The A-only thesis is "shallower DD at ~equal
  risk-adjusted return"; it must keep *both* halves of that forward, not just give up return.)
- **Revert to base-swing** if A-only forward MaxDD is **not** shallower than base, OR forward Calmar falls
  **> 0.10 below** base. (Concentration that neither smooths the ride nor holds Calmar has no reason to exist.)
- **Insufficient evidence** (< 20 forward closed trades per book, or CIs overlapping on both DD and Calmar):
  **default to base-swing** — the certified run of record — and carry A-only one more quarter. A-only does not
  get the benefit of the doubt; it must *earn* its place against the higher-CAGR default.

All three thresholds are **tighten-only**. A relaxation voids this §4 and restarts its clock.

## 5. Mechanical halt (no discretion)

If the **live A-only book** draws down **−50%** from its logged peak NAV, **measured on the DAILY grid**
(clarified 2026-09-27, §11.3 — the grid was always daily in code; it is now part of the rule), halt new
entries, manage open positions to exit, and freeze until the next quarterly review. This is the only
between-review action.

## 6. Integrity commitments

- **Reproduce-before-trust.** Every number in a review readout must come from the committed pipeline
  (`run_bhanushali_weekly_rank.py` for the reference, the `*_weekly.json` logs for forward), never a chat
  transcript.
- **Sub-period gates use a continuous slice** of one full run (`nq.runner.research.evaluate_overlay`),
  never a fresh-capital re-run from the sub-window start.
- **No peeking-driven change.** Config, grading, universe, and thresholds are frozen between reviews.
- **The forward log is append-only.** The swing book currently logs via the `*_weekly.json` artifacts;
  hardening them to the momentum wall's hash-chained standard (`nq/paper/forward_wall.py`) is a tracked
  follow-up, not a blocker for registration (the decision rule above is what this doc pins).

## 7. Closed in-sample threads (pre-committed KILL — do not relitigate without new {data, feature,
sub-period, formulation})

The 2026-07-13 volume thread (finding 0097) is CLOSED. Three measurements, all rejected on the correct
population under `backtest-rigor`:

- **HVC as an A+ sub-grader** (split the traded A book by setup-week volume / trailing-L avg, L∈{10…150}):
  NULL and **wrong-signed** (high-volume A entries mildly *underperform*), every |t| < 2. The A pool
  (~26 trades/yr) is also below the sub-grade power floor. → grading stays CRS-only.
- **20-day momentum / volume as a RANKER** (roc20, volsurge, roc20×vol): real IC but **zero tradeable
  Q5−Q1 spread**; the combo goes negative. CRS remains the best-IC ranker and still doesn't convert to a
  portfolio win (IC ≠ Sharpe).
- **Volume FILTER on the raw pool** (keep entries with setup-week vol ≥ k× trailing-20d avg, k-sweep):
  the only cells that beat baseline are **narrow peaks** (Sharpe collapses > 0.15 one step either side),
  at **inconsistent thresholds across books** (all-grades 0.85 vs A-only 0.70), **non-monotone** — the
  `backtest-rigor §C1b` overfit signature. REJECT.

Root cause (all three): the 6-step filter + CRS + ADV≥5cr selection **already absorbs whatever volume was
proxying for**; layering volume on an already-elite pool adds nothing. These were measurements — **no trial
spent; n_trials stays 114.**

The 2026-07-14 **entry/exit research arc (finding 0098)** is CLOSED — ~20 configurations (near-SMA entry,
wide-candle reject, daily-uptrend gate, body-gain cap, trend-hold exit, 25/25/50 exit ladder, all-grades).
**Every one fails to improve returns**; the frozen `0094` book is the best config. Do not relitigate any of
them. Root lesson: the edge is *buying strength* and it resists every "make it safer" filter; "confirmation"
(daily gate) just delays entry into extended, wide-stop fills (it *caused* the HEG −22.8%).

## 7a. WATCHED overlay — max-stop-distance cap (DRAWDOWN lever only)

The one survivor of finding 0098. **Rule:** skip a fill when `(entry − stop)/entry > 15%` (stop = setup-week
low) — i.e. don't take a trade whose stop sits more than 15% below the entry (the HEG/wide-candle blow-up
pattern). **Status: WATCHED (logged, not traded).**

- **Thesis is DD, not return.** In-sample it consistently cuts MaxDD (−40% → −30/−32%) across every cap
  value — mechanically sound (removes wide-stop losers). But its **return response is NON-MONOTONE**
  (Sharpe 12%→0.955 / 15%→0.760 / 18%→0.938) — a `backtest-rigor §C1b` peak-not-plateau signature — so the
  return "win" is **noise and is NOT claimed**. Certifiable only on out-of-sample drawdown.
- **Param frozen by MECHANISM, not fit:** **15%** (a round "don't take stops wider than 15%" rule),
  deliberately NOT the in-sample-best 12%, to avoid fitting the peak. Tighten-only.
- **Decision (pre-committed):** at the 12-month review, **promote to the live cfg only if** forward MaxDD
  is shallower than the un-capped book by **≥3pp AND** forward Calmar is **not worse**. Otherwise it stays
  watched or is dropped. Never promoted on an in-sample number.

## 8. What would reopen the single-sleeve search (the bar for trial #115)

Nothing in the technical/volume/momentum/macro zoo already killed. A genuinely new lever means one of:
a new PIT-clean orthogonal feature (Jaccard-distinct from the killed set), a new data modality, or a new
sub-period with a mechanism. Absent that, **the forward wall — not a 115th in-sample cut — is the only
move.**

## 9. Amendment 2026-07-15 — live EXIT changed to the Phase-2 exit (owner-override; ADR-0008 / finding 0099)
The live cron (`scripts/run_bhanushali_cron.py`) now applies `P2_EXIT = {no_time_cap, wk20_trail_pct=0.04,
blowoff_arm_r=2.5}` to **both** `backtest()` calls, so **both forward-logged books now run the Phase-2 exit**
(no time cap + blow-off-bar exit @2.5R + 20-week backstop; the 20-day-SMA ratchet trail retained). This is an
**owner-override** (sole capital-at-risk): the change is a **defensive/selection variant** (in-sample Sharpe
1.132→1.034, CAGR 24.7→21.2%, **MaxDD −42.4→−34.8%, Calmar 0.58→0.61**, per-trade +28%, trades 255→168) that
**FAILS the standard ΔSharpe≥+0.10 gate** and touches the 0098-KILL exit area — so it did **not** travel the
forward-wall certification route; it was registered (trial #115) and adopted directly. See
`research/config_CHANGELOG.md` + ADR `docs/decisions/0008-swing-exit-change.md` + finding 0099.

Consequences for this wall:
- The **§1 in-sample reference distribution (0094 exit) is unchanged** — it stays the documented anchor and is
  reproducible offline with `P2_EXIT` OFF (`backtest(prep_weekly_rank(ohlcv))` = 1.132/255, byte-identical).
- The **§4 A-only vs base-swing GRADING decision continues**, now measured on the P2-exit books (both books
  shifted together, so the grading comparison is unaffected in kind).
- The forward log no longer carries a live 0094-exit shadow; the 0094 exit is the offline reference only. If a
  live 0094-exit shadow is later wanted for the wall, that is a recorded third book (a §2 swap).
- **Reversal:** flip `P2_EXIT` OFF in the cron → both live books revert byte-identical to the frozen 0094 exit.

---

## Amendment 2026-07-26 — register the `blend-hybrid` WATCHED book (a §2 recorded third book)

**What:** the swing-0094 × low-vol book at frozen-0081 ERC weights (quarterly inverse-vol). Registered as a
**WATCHED / observational** book — it does **not** carry paper capital (A-only stays the capital vehicle), so
the §2 two-**capital**-book cap is intact; this is a third *logged* book, recorded here per the "no third
without a recorded swap" rule.

**Why (finding 0107):** the 2026-07-26 sweep exhausted every entry/exit lever on the single swing sleeve
(body-null; ext_cap 0104; hard_stop 0105; widen 0106 — all KILL). The per-year lens showed the residual
weakness is regime (chop): swing fades in 2024 (+9.9%) / 2025 (−14.1%). The blend fixes it structurally —
Sharpe **1.15/1.06 → 1.23** (beats both sleeves), MaxDD −42→**−33**, and **0 losing years** (2025 −14.1→+5.6),
because low-vol earns +18-29% in the exact chop years the swing book bleeds (corr 0.54). This is the only
lever that survived, and it can't be tinkered — it must be a *sleeve combination*, forward-certified.

**Fixed spec (not retunable; ERC recipe frozen from 0081):**
- Sleeves: swing-0094 (A-only book NAV) + a low-vol 63d-hold sleeve.
- Weight: quarterly inverse-vol ERC (as-of prior day). Mean swing weight ≈ 0.37 in-sample. A fixed
  higher-swing weight (more CAGR / more DD) is an OWNER dial — if chosen, fix it HERE before logging.
- Certification: **forward-wall only.** In-sample is uncertifiable (low-vol = O-016; 0081 DSR 0.315). No
  in-sample config swap; the live A-only book is unchanged.

**Blocker (before it can log forward):** the daily wall computes no low-vol paper sleeve yet. The swing paper
book runs (`run_bhanushali_cron.py`); a **low-vol paper sleeve cron** is the missing infra. Until then the
blend is reproducible offline only (`scripts/run_blend_hybrid.py`, returns in
`research/exports/blend_hybrid_returns.csv`).

**Decision cadence:** resolved at the multi-sleeve fork of the quarterly review, on forward evidence — never
in-sample. Thresholds tighten, never relax.

## Amendment 2026-08-14 — owner fixes the barbell weight at 0.60 swing, and funds the sleeve cron

**Owner decision (the §7 "OWNER dial", now fixed before logging):** the blend logs at a **fixed 0.60 swing /
0.40 low-vol** weight, NOT the ERC default (~0.37). Chosen from the reproduced in-sample barbell curve
(`pipelines/research/run_blend_hybrid.py` + fixed-weight sweep): 0.60 gives **CAGR 21.4% · Sharpe 1.25 ·
MaxDD −36.4% · one −2% year (2025)**, versus 0.37 ERC (18.8% / 1.26 / −32.9% / zero down years). The owner
elected +CAGR into the upper half of the 18–22% target, accepting a deeper drawdown and one small down year.
This is the barbell dial the spec reserved for the owner; it does not retune the frozen ERC *recipe* — it
fixes the *weight input*. Certification stays **forward-wall only**; the live A-only book is unchanged; the
blend still carries **no paper capital** (observational logging only).

**Blocker cleared (was stale):** the logger `scripts/run_blend_paper.py` is ALREADY scheduled — the weekly
scanner cron runs it (`.github/workflows/cron-bhanushali-scanner.yml`, "Log the swing x low-vol blend
hybrid"), on fresh OHLCV, after the swing paper book writes `results/portfolio_history_weekly.csv`, and
commits `results/blend_hybrid_paper.json`. The only real change here is the **weight**: the logger blended
at dynamic ERC (~0.37–0.5); it now blends at the owner-fixed **0.60**. It stays observational (no paper
capital); empty until fresh post-inception bars accrue in both sleeves — valid, not an error.

---

## 11. Clarification 2026-09-27 — the four ambiguous gate definitions, ratified BEFORE the Oct-1 read

**Class: CLARIFICATION. No threshold moves.** §4's tighten-only rule is intact and its clock is not
restarted: every number below is the reading the code already implements, written down so the 2026-10-01
read cannot select a reading after seeing the data. Standing counts unchanged: **screens 20 · sealed
opens 3 · n_trials 2.**

Authority: `diagnostics/research/oct1_binder_decisions.md` §9.1–9.4, which states both readings for each
and weighs neither. This block picks one per item, in the conservative direction, and gives the reason.

**Why now, and why this is not self-serving.** As of the 2026-09-26 scan the book's net Sharpe reads
**−0.7310**, which trips the kill leg under **either** reading of §11.1. The definition is therefore
currently **non-binding on the outcome** — which is precisely the moment to fix it, because no choice
available here can flatter the result.

### 11.1 `KILL_SHARPE = 0.0` is the **as-coded, raw-return** Sharpe (rf = 0)

`mean/std × √252`, no risk-free subtraction (`nq/validation/metrics.py`). Kill means *below cash at 0%*,
not below the risk-free rate.

**Why.** Every verdict on the record was decided on raw-return Sharpe, where rf cancels in a ΔSharpe
comparison. Re-reading the one *absolute* gate as excess-return would move its threshold from 0.00 to
≈0.25–0.30 — i.e. it would **tighten a live kill trigger in the middle of a quarter, on a book that is
already tripping it**. Tightening a live risk control is a review decision with a stated rationale, never
a definition cleanup. If the owner wants the excess-return reading it is adopted at a review, prospectively.

### 11.2 CAGR is published on **calendar** years

Two committed denominators exist — calendar (`run_bhanushali_sixstep.py`) and trading-bar
(`run_corrected_anchor.py`) — and the same curve prints 24.7% and 25.21%. **Calendar years is the
publication standard for this book**, being the longer denominator and therefore the lower, more
conservative print.

**The live exposure this closes** is cross-document comparison: a book-vs-benchmark CAGR gap is only
valid when both sides use the same denominator. Any such gap quoted at a review states its convention.

### 11.3 MaxDD is measured on the **daily** grid, and the grid is now part of the halt rule

A coarser grid cannot see troughs between samples, so it can only **understate** a drawdown: the same
family publishes −42.4% daily against −33% monthly. §5 above now names the daily grid explicitly, so a
future change of series frequency cannot silently loosen a live risk control.

**Consequence for Calmar** (register row 18, which inherits 11.2 and 11.3): a Calmar is comparable only
between figures built on the **same** pair of conventions. A Calmar from a monthly DD and bar-year CAGR
is not comparable to one from a daily DD and calendar-year CAGR, and §4's Calmar test uses the latter.

### 11.4 The **≥30 closed** precondition is load-bearing, not advisory

`expectancy_R` and `win_rate` are computed over **closed trades only**. On a trend book losers stop out
fast while winners run for months, so both are **biased low by construction** in a young book and rise as
winners mature.

**Therefore: below 30 closed trades, expectancy and win rate are not informative quantities and are not
to be read as evidence — in either direction, on either book.** They are still published, because
suppressing them would be worse; they are published as uninformative. No re-computation on a
mark-to-market basis is proposed or implied.

### 11.5 WHICH BOOK each gate reads — added from finding 0146, and not in the binder

0146 established that the weekly scan runs three books off one engine and that the readout mixes them.
A gate cannot be ratified without naming its source book:

| gate | input | book |
|---|---|---|
| readiness (`≥40 closed OR 4 quarters`) | `n_closed` | **uncapped** tracker |
| `KILL_SHARPE < 0` (§11.1) | `sharpe` | **capped ₹10L** |
| §5 mechanical halt (§11.3) | MaxDD, daily | **capped ₹10L** |
| §4 decision (MaxDD shallower AND Calmar ≥ base − 0.05) | both NAV curves | **capped** A-only vs **capped** all-grades |
| §4 floor (`≥20 closed per book`) | `a_only_closed` **vs** `base_swing_closed` | **uncapped** vs **capped** — *not the same quantity* |

Two facts the review must carry, both measured in 0146 and neither resolved here:

- **§4's floor compares an uncapped closure count against a capped one.** It is the one gate that mixes
  books inside itself, and it short-circuits *before* the MaxDD/Calmar branches, so it is currently what
  decides §4. Whether §4 needs a dated amendment for that is an **owner decision**; this clarification
  only records that the two sides are different quantities.
- **`paper_portfolio_weekly.json` has mixed provenance:** `positions` is the capped A-only book while
  `total_trades` is the **uncapped** ledger's closure count. Anyone auditing the capital book from that
  file will read its closure count as 13 when the capital book has closed 2.

### What this block may never do

It ratifies readings; it changes no threshold, no grading, no config, and no book. Adopting the
excess-return Sharpe, repairing §4's floor, or altering the ≥30 precondition are all **live-rule changes**
and belong to a quarterly review with a stated rationale.
