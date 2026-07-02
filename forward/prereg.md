# forward/prereg.md — Forward-Wall Pre-Registration

**Status:** PRE-REGISTERED (locked before first live row)
**Version:** 1.2 (v1.0 2026-07-02; v1.1 + v1.2 amendments 2026-07-02 — see §10)
**Registered:** 2026-07-02
**Anchor:** `baseline_v1` / `dataset-pin-20260701` (ohlcv_sha256 `f8625a8f…52142`)
**Author/owner:** Kreesh Patel
**Companion trials:** 0076 (exit, UNDERPOWERED), 0077/0078 (residual momentum, REJECT), veto-0.1 cascade (`scripts/diag_veto01_cascade.py`, §6).

---

## 0. Purpose & integrity commitment

The in-sample program is exhausted: at a moderate edge (~2× random) on ~34 independent 63-day windows with 91 trials spent, no overlay can clear a Deflated-Sharpe gate, and every additional in-sample trial deflates the bar further. The **only** remaining source of unbiased information is out-of-sample forward data on a book that cannot be re-fit.

This document fixes — **before any live row exists** — every decision threshold that governs the wall: when to halt, when to conclude the edge has degraded, when to promote a watched variant, and when the strategic fork (multi-sleeve build) is authorized. **Thresholds set here may be tightened or clarified with a dated amendment; they may never be relaxed retroactively.** Any relaxation voids the pre-registration for the affected criterion, which must then be treated as a fresh registration with its own start date. The point is to make "moving the goalposts after seeing the data" structurally impossible.

## 1. What is traded vs. watched — and the two-phase capital gate

**All three books begin in PAPER (Phase A).** The base transitions to small real capital only in Phase B, and only via a dated §10 amendment once the repo's **pre-committed paper gate is met** (`skills/portfolio-simulation`: **≥ 30 closed trades AND ~2 months** of paper). As of registration the paper book is ~2 days old with 0 closed trades, so Phase B has not begun — and a document whose purpose is to make goalpost-moves impossible must itself honor that pre-committed gate rather than vault it.

- **Phase A (now):** all books paper. Measures **signal continuation** — does the live signal keep producing returns in the backtest's distribution (§5), and do the shadows beat base on unbiased forward data (§6)? Real slippage/financing/own-behaviour are NOT yet measured.
- **Phase B (after the paper gate clears, by dated amendment):** base → small real capital. Adds **execution-cost reality** (§3.3) — realized slippage, MTF/financing, and own-behaviour-under-drawdown, which paper cannot. Phase A paper results do **not** clear the execution-risk question; only Phase B does.

| Book | Status | Rule |
|---|---|---|
| **base** | **PAPER (Phase A)** → small real capital (Phase B, dated amendment, gate-conditioned) | Frozen `frozen_cfg` — `sma200_slope_63`, top-15, ATR-stop 3.67×, target 22.52%, trail 4.0→4.27%, hold 10–63d, 3% risk, 15% cap, 5% ADV. |
| **veto-0.1** | WATCHED (shadow, logged not traded) | Base ranking, exclude bottom-decile residual-momentum names from the eligible set. Reshuffle-luck null (§6). |
| **drift-degross** | WATCHED (shadow, logged not traded) | Base book, gross-exposure multiplier = 1.0 if trailing-63d base return ≥ 0, else 0.5. **Never backtested — pure forward watch (zero in-sample contamination, by design).** One parameter, no fitting. |

**Hard cap: two shadow books.** A wall with many watched variants is multiple testing relocated to the forward sample. No third shadow is added without retiring one and recording the swap here.

## 2. Frozen references

- **Config:** the `frozen_cfg` block of `export_manifest.json` @ `dataset-pin-20260701`. Any byte-difference in the live config vs. this hash invalidates the wall.
- **Backtest reference metrics (the distribution live is judged against):** Sharpe 0.667 · Sortino 0.836 · CAGR 15.46% · after-tax CAGR 12.758% · MaxDD −46.26% · Calmar 0.33 · daily skew −0.639 · ann. vol 27.1%. *(All re-verified against `research/exports/daily_returns.csv` on 2026-07-02.)*

## 3. Log-integrity rules (enforced in code, not convention)

> **IMPLEMENTATION STATUS (2026-07-02): BUILT & TESTED.** `nq/paper/forward_wall.py` implements the chain below; `tests/test_forward_wall.py` (5 tests, green) is the acceptance criterion — a mutated **or** reordered historical row makes `append_row` refuse the next write, and back-dating is rejected. Built while the log was empty (no history to migrate or re-hash). (v1.0/v1.1 recorded this as aspirational; v1.2 built it — see §10.)

**Pinned contract — the doc is the authority; a code change that diverges from this is a break:**
- **Hash:** `row_hash = SHA-256( prior_row_hash ‖ "|" ‖ canonical_payload )`, hex digest.
- **Genesis seed** (the `prior_row_hash` of the first row): `SHA-256(b"nifty-satvik/forward-wall/genesis@dataset-pin-20260701")` = `f5a0223bea985252683bfbb51d9d845f9c50bda499017381884127192aa209ee`. Anchors the chain to the pinned dataset.
- **Canonical payload** (fixed order, deterministic formatting; the written CSV cells ARE these strings, so read-back re-hashes identically with no float round-trip drift): `date(YYYY-MM-DD) | base_ret(.8f) | base_equity(.2f) | base_npos(int) | veto_ret | veto_equity | veto_npos | drift_ret | drift_equity | drift_npos`.
- **Log path:** `results/forward_wall.csv` (columns = the payload fields + `row_hash`).

1. The live log is **append-only**, **ONE atomic row per trading day carrying all three books hashed together** — a partial write (one book logged, another missed) cannot open a silent hole, because there is one row and one hash, not three independent chains.
2. The harness **refuses to write** if the recomputed chain over existing rows does not match — retroactive edits **and reorderings** are structurally blocked (position-sensitive: each hash binds its predecessor).
3. Live fills use realized executions (real slippage/financing), not modelled costs — **Phase B only** (Phase A paper cannot measure these). Slippage and own-behaviour-under-drawdown are themselves untested model inputs; the wall measures them once real capital is live.
4. No back-dating. A row's date must be strictly after the last; a missed day is a gap, never reconstructed.

## 4. Risk halt (mechanical, no discretion)

**Trigger:** live max drawdown breaches **−50%** (a margin beyond the −46.26% backtest max — i.e., the point at which the backtest no longer bounds the realized risk and the model's risk assumptions are violated).

**Action:** halt **new entries** immediately; **hold** existing positions; convene a mandatory review within **5 trading days**.

*Rationale for "halt-not-liquidate":* momentum drawdowns recover V-shaped; an automatic liquidation at −50% crystallizes the bottom (the exact failure mode flagged for portfolio DD-stops). The halt stops *adding* risk and forces a human decision; it does not pre-commit to selling. The review may then hold, reduce, or exit on regime evidence.

**A −35% or −40% live DD is NOT a halt condition** — it is inside designed-for experience (worst realized 12m return −29%; 31% of days spent >20% underwater; rolling-12m Sharpe has legitimately reached −0.98). Firing there would sell normal pain.

## 5. Edge-degradation review (evidence, evaluated only at quarterly dates)

The wall must separate *"a bad stretch the backtest also produced"* from *"the live edge is gone."* Thresholds are the backtest's own rolling-12-month distribution (derivation in Appendix).

| Flag | Condition (trailing 252 live trading days) | Action |
|---|---|---|
| **Green** | 12m Sharpe ≥ −0.53 **and** 12m return ≥ −29% | Normal. Continue. |
| **Yellow** | 12m Sharpe < −0.53 (empirical 5th pctile) **or** 12m return below the 25th-pctile cone | Log "underperforming, within designed range." No action. Watch. |
| **Red** | 12m Sharpe < **−0.99** (block-bootstrap 5th pctile) **or** 12m return < **−29%** (bootstrap 5th ≈ worst realized) | **Formal degradation review.** Document a decision: continue / reduce size / suspend. |

Red means live is worse than ~95% of what an intact edge produces over any 12-month window — out-of-distribution, not just unlucky. Red is a *review* trigger, not an auto-halt (that's §4); the two are independent.

## 6. Shadow-book promotion (watched → traded)

A shadow is promotable **only if all** hold, evaluated **only at a quarterly review date**:

1. **Duration:** ≥ **18 months** of forward data **and** ≥ **8 non-overlapping** 63-day windows.
2. **Forward-only dominance:** beats base on **both** after-tax Calmar **and** Sortino, computed on **forward data only** (never backtest+forward blended).
3. **Beats the null:** block-bootstrap ΔSortino on forward daily returns has a 95% CI **excluding 0**. (This will take a long time to achieve — that is correct, not a bug.)

**Pre-committed null for veto-0.1 (reproducible — `scripts/diag_veto01_cascade.py`, pinned universe).** Its in-sample edge decomposes to reshuffle luck + path-dependent compounding, NOT a "vetoed names were bad" mechanism. Reproduced cascade (base 1279 trades +24.4L → veto-0.1 1266 trades +29.8L; **net +5.5L**):

| component | trades | PnL | win |
|---|---|---|---|
| **removed** (base trades on names veto vetoed) | 665 | **+7.8L** | 58% |
| **replacement** (veto-only, freed-slot re-picks) | 652 | **+10.1L** | 55% |
| **shared_delta** (sizing/exit on 614 shared keys) | 614 | **+3.1L** | — |
| recon (repl − removed + shared) | | +5.5L = net ✓ | |

The removed names were **profitable in base** (+7.8L, 58% win) — the veto did not cut losers, it displaced winners with replacements that happened to out-earn them (+10.1L), plus a +3.1L shared-sizing/compounding residue. **Expectation: the edge reverts forward.** Promotion requires beating *that* expectation on unbiased data. If it beats base forward anyway, that is a genuine discovery.

**drift-degross** carries no in-sample prior (never run); its forward record is its only evidence, judged on the same three criteria.

## 7. Shadow-book demotion (watched → dropped)

At any quarterly review, a shadow that **underperforms base on forward-only Sortino over a trailing ≥12-month window** is dropped from the watch and the retirement recorded here. A dropped shadow is not re-enrolled without a new dated registration.

## 8. Review cadence

- Reviews occur on the **first trading day of Jan / Apr / Jul / Oct**.
- **All** promotion, demotion, degradation, and fork decisions happen **only** on these dates. Between dates: monitoring and logging only — no config changes, no size changes (except the mechanical §4 halt).
- No looking at the equity curve "because it looks interesting" and acting. Fixed dates defeat outcome-conditioned peeking.

## 9. Multi-sleeve fork trigger

At the **first review on/after 12 months of live data**:

- **If base is Green (edge intact, no Red in the trailing period):** the multi-sleeve defensive-sleeve build (low-vol/quality sleeve + portfolio-level ERC combination) is **authorized as the next research project.** Note: this is a *full new-strategy certification* — the second sleeve must itself be a validated positive-edge strategy — not a config change. "Diversification is a free lunch" applies to the *combination*, not to skipping certification of the sleeve.
- **If base is Yellow/Red:** do **not** start the multi-sleeve build. Fixing or reassessing the core comes first; a diversifying sleeve on a broken core diversifies nothing.

## 10. Amendment protocol

Amendments are appended below with date, author, and rationale. Tightening/clarification only. Any relaxation of a §4–§9 threshold voids the pre-registration for that criterion and restarts its clock.

*(amendments below this line)*

- **2026-07-02 — v1.1 (Claude Code, per owner).** All tightenings/clarifications; no relaxation of any §4–§9 threshold.
  1. **§1 base TRADED → PAPER (Phase A).** v1.0 committed base to small real capital in its first section, which would have vaulted the repo's pre-committed `portfolio-simulation` paper gate (≥30 closed trades / ~2 months) — the exact class of pre-registration this doc exists to honor. Base now begins PAPER; the real-capital transition (Phase B) is gated on the paper gate and requires its own dated amendment. Added the Phase A (signal-continuation) vs Phase B (execution-cost reality) distinction so paper results are not misread as clearing the execution-risk question.
  2. **§3 marked NOT-YET-BUILT.** Verified 2026-07-02 that the hash-chain + 3-book log harness does not exist in code (no `row_hash` in `nq/paper`; only the legacy single-book NAV log). Recorded as a build prerequisite before the first live row.
  3. **§6 null made auditable.** The veto-0.1 cascade figures (previously transcript-only) were reproduced from the pinned pipeline (`scripts/diag_veto01_cascade.py`) and embedded (removed +7.8L / replacement +10.1L / shared +3.1L / net +5.5L, exact recon). The null now cites a committed, reproducible basis.
  4. **Appendix pins the rejected −18.8% figure** so a future reviewer does not "correct" the Red-return line to it.
- **2026-07-02 — v1.2 (Claude Code, per owner).** Built the §3 integrity harness that v1.1 recorded as unbuilt — clarification/addition only, no threshold relaxed. `nq/paper/forward_wall.py`: one atomic 3-book row, a single SHA-256 chain off the pinned genesis seed, `append_row` refuses on any chain mismatch, reorder, or back-dating. `tests/test_forward_wall.py`: tamper-rejection, reorder-break, no-backdating, atomic-three-books, genesis-pin — 5 green (the acceptance criterion). Pinned the genesis seed (`f5a0223b…09ee`), the hash construction, and the canonical field order into §3 as the contract. Done while the log was empty (no history to migrate/re-hash) — the cheapest possible time.

---

## Appendix — threshold derivation (from `baseline_v1`, `daily_returns.csv`)

Computed on the pinned net daily series (2017-09-14 → 2026-06-29), so the wall judges live data against the same book that produced them. *(Re-verified 2026-07-02: rolling-12m Sharpe min −0.982 / 5th −0.530 / 25th −0.086 / median 0.434 / max 3.754; worst-realized 12m −29.1%; 31% of days >20% underwater; MaxDD −46.26%, ann vol 27.1% — all reproduce the figures below.)*

- **Rolling-252d Sharpe (overlapping windows):** min **−0.984** · 5th pctile **−0.532** · 25th −0.087 · median 0.435 · max 3.761.
- **Block-bootstrap synthetic-12m Sharpe (block=21, 5000 draws):** 5th pctile **−0.987** · 1st pctile −1.690 · median 0.759.
- **Bootstrap cumulative-return cone [5th / 25th / median]:** 6m −25.3 / −4.6 / +8.8% · 12m **−28.7** / −2.5 / +18.3% · 18m −30.3 / +0.4 / +26.2% · 24m −29.5 / +4.5 / +36.5%.
- **Worst realized 12m return:** −29.1%. **Days >20% underwater:** 31%.

The empirical 5th pctile (−0.53 Sharpe) is the Yellow line; the block-bootstrap 5th (−0.99) — worse than 95% of resampled 12m windows — is the Red line. The −50% halt sits beyond the −46.26% backtest max by design.

**Why the Red-return line is −29% and not −18.8% (pinned to prevent a well-meaning future edit).** The **overlapping-realized** 12m-return 5th percentile is **−18.8%** — milder, because overlapping windows are autocorrelated and undercount tail uncertainty. The Red line deliberately uses the more conservative **block-bootstrap cone 5th (−28.7%)**, which coincides with the **worst realized 12m (−29.1%)**. A reviewer who "corrects" −29% to the realized-overlap −18.8% would be *loosening* the line on a statistical artifact — do not. The −18.8% figure is recorded here solely so the rejection is explicit.
