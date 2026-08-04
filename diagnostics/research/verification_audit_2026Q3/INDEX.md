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

## Remaining scope

### Tier A — PENDING

| item | note |
|---|---|
| **A1 baseline_v1 anchors** (0.667 / 15.46 / −46.26) | needs the long-horizon engine run on the pinned OHLCV |
| **A2 corrected-anchor table** (0.737 + alias-aware + backfill arms) | `scripts/run_corrected_anchor.py` |
| **A3 swing record 1.132 / 255 + golden** | `run_bhanushali_weekly_rank.py` + `test_r94_golden.py` / `test_stage2_golden.py` |
| **A4 two-sleeve ERC blend** (1.22 / −33%) | `research/exports/third_sleeve_returns.csv`; independent ERC re-derivation |

### Tier B — PENDING (standing-law receipts)

0118 (+0.363) · 0120 (−0.383) · the four activation bounds (rotation ≈+11R clairvoyant, tiebreak
−1.29, deferral −15.72, hugger 1.92 / 0.0-identity) · 0123 nulls + instrument stats (κ 0.867,
truncation probe) · 0124 Weinstein · 0125 power arithmetic · 0126 / 0127.

### Tier C — PENDING (auditor-selected spot checks, five findings, method-diverse)

---

## Cross-cutting arithmetic checks — PENDING

Sharpe annualisation consistency (√52 weekly vs √252 daily — **verify no book mixes them**);
CAGR↔Sharpe↔vol mutual consistency; per-year tables summing to totals; R-definition consistency
across scripts (same risk denominator, same fill convention); CI method appropriateness
(bootstrap iid vs overlapping windows — **flag, do not fix**).

## Discrepancy ledger

**Empty so far** — and an empty ledger is itself a reportable result, not an absence of work.
One **audit-script error** is recorded above (A6 scoping); it is not a repo discrepancy.

## Guards in force

- Any discrepancy that could move a standing verdict → **STOP on that item**, report both numbers
  and the mechanism, owner decides. **Never silently correct a finding.**
- **Fishing guard:** anything interesting noticed goes to `PARKING_LOT.md` **unanalysed**. This audit
  validates old answers and is forbidden from generating new questions in the same pass.
- No retunes, no threshold edits, no golden re-records without a stated diff and sign-off.
