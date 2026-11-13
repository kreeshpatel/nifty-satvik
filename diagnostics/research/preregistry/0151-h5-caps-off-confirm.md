# 0151 — h5: the live exit with the four entry and sizing caps off (CONFIRM)

**Status: PRE-REGISTERED, awaiting the owner's final sign-off (§9) before the counter increments.**
**Amended 2026-11-13 (before any sealed number):** one arm confirmed; P5 changed from 60% to 30%; the train-window
concentration measurement is disclosed in §9.
**Tier:** 3 · CONFIRM (`docs/PROCESS_TIERS.md`): a cap and grading change to the live book.
**Written:** 2026-11-13, before any sealed-slice number for h5 exists.
**Counter:** `n_trials` 2 → 3 and `family_level_count` 2 → 3 (one arm). The increment is a separate commit, made after
this file is committed and the owner has signed §9, and before the run. **Sealed opens:** 3 → 4 on the run (row S4).
Standing counts at registration: screens 24 · sealed opens 3 · n_trials 2.

## 1. Hypothesis

On the sealed validation slice (2024-07-01..2026-06-30), the live book with its four entry and sizing caps removed
(**h5**) has a higher Sharpe than the live book at no materially deeper drawdown, with the same signals, exit, costs and
membership. The comparator is the live configuration itself, run on the same paths.

## 2. The two books, every parameter fixed here

Both books run `R94.backtest` through `nq.lab.runs.engine_kwargs`. Shared settings:
- `LIVE_PREP` signals;
- the live scaled exit, config P (40% at +2R, 40% on the blow-off pattern armed at +2.5R, 20% runner to a weekly close
  below the 44-week SMA);
- `LIVE_STALENESS`;
- demerger events;
- PIT Nifty-500 membership (`load_membership()`);
- ₹10L starting capital;
- 2% risk per trade (`RISK`);
- costs as coded.

The books differ on exactly four switches:

| switch | live (control) | h5 |
|---|---|---|
| `ext_cap` | 0.20: no entry more than 20% above the 44-week SMA | `None` |
| `grade_gate` | on: Grade A only (top 5 by CRS per ISO week) | off: all grades, funded strongest-CRS-first |
| `max_notional_pct` | 0.20: one position ≤ 20% of sizing equity | `None`: size set by risk alone, bounded by cash |
| `max_risk_pct` | 0.10: stop raised to entry × 0.90 when the candle low is further | `None`: stop at the candle low |

This is the lab config `{"ext_cap": None, "grade_gate": False, "max_notional_pct": None, "max_risk_pct": None}`
(`REVERTED` in `pipelines/diagnostics/explore_ensemble_breakeven_d6.py`). No other value is run.

**Window.** One full run per path from the path's start date in early 2019 to 2026-06-30. Every gate below reads the
**continuous slice** 2024-07-01..2026-06-30 of that one run, never a fresh-capital re-run from 2024-07-01 (CLAUDE.md;
the phantom-0.762 lesson). Paths are the 20 standard draws (`nq.lab.ensemble.draw_perturbations(20, DEFAULT_SEED)`:
cost jitter ±10bp, start within the first 20 trading days of 2019), the same draws for both books, paired.

## 3. Registry confrontation

- **Where h5 comes from.** It is run (h5) of the 2026-10-23 live-switch ablation (PR #159, EXPLORE): Sharpe 1.68 vs
  1.03 on one path. It held as robust to path noise in three train-window ensembles:
  - +0.13 on 2 paths (2026-11-02);
  - +0.27 [+0.12, +0.71] on 20 paths (2026-11-03);
  - +0.27 again on 20 paths (2026-11-12, `2026-11-12_ensemble_s1_throttle.json`).

  Every one of those numbers is train-window and has been looked at. This is the first trial on h5.
- **Grading collides with an existing forward decision.** `forward/prereg_swing.md` §4 reserves the A-only vs
  all-grades choice for the forward record (primary read 2027-07-01; "between reviews, no config or grading change").
  §12 records that under `max_notional_pct = 0.20` the two §4 books have held identical positions, so §4 cannot
  currently decide. h5 lifts that same cap. **This trial cannot change the live grading or caps by itself.** A PROMOTE
  is evidence for a quarterly review, and adoption needs an owner-written dated amendment to `forward/prereg_swing.md`
  that re-scopes §4 (§7 below).
- **The caps have their own history.**
  - `max_risk_pct` and the notional cap: FINDING_owner_6040_poscap, and 0130, which priced the stop-width funding bias
    as a −10.83%/yr equity saving, CI [−26.3, +4.7]).
  - `ext_cap`: the deep near-SMA touch work (ext < 5% carries the edge).

  None of these is a KILL of removing all four together on the live exit, and none was measured under the current
  harness with PIT membership and the scaled exit together. This trial brings **a new sub-period**, the sealed slice,
  which none of them read for this question.
- **Sealed-slice cleanliness.** Opens S2 and S3 spoiled the slice for rules about profit-target distance, R-multiple
  targets, stop-width bands and descent kinematics. `max_risk_pct` is a stop-width rule. Its outcome on the sealed
  slice was not read by S2 or S3, but the bands it governs were. This is disclosed as a limitation: a PROMOTE does
  not certify the risk-cap leg in isolation. The ext-band census population must be date-checked for sealed rows before
  the run (§8, check C2).

## 4. Resolution, stated plainly

The sealed slice is about 2 years, roughly 8 independent 63-day windows. At the measured n_eff ≈ 37 → half-width 0.59,
8 windows give a statistical half-width near **1.3 Sharpe**. The hoped-for effect (+0.27 in-sample) is far below that.
**This read cannot confirm the magnitude of h5's edge; it can only refute it** by showing a sign flip, a drawdown
blow-out, or a gain that rests on one trade, as S1 refuted 0116. The bars are written for that job.

## 5. Pre-committed outcome table

Path-level quantities are paired (h5 minus live, same draw) on the sealed continuous slice. The "unperturbed run" is one
extra run of each book with zero cost jitter and start 2019-01-01.

| outcome | condition, fixed now | what happens |
|---|---|---|
| **STOP (no read)** | **G0** fails: before the sealed slice is read, the same script on the train slice 2019-03-01..2024-06-30 gives a median paired ΔSharpe outside **+0.27 ± 0.10** | harness drift; the sealed read is not spent, and the cause is found first |
| **PROMOTE** | **all of**: **P1** median ΔSharpe > 0 **and** ≥ 15 of 20 paths > 0; **P2** median ΔMaxDD ≥ −5.0pp (h5 at most 5pp deeper); **P3** on the unperturbed run, ΔSharpe is not negative on **both** halves (2024-07-01..2025-06-30 and 2025-07-01..2026-06-30, each a continuous slice); **P4** on the unperturbed run, h5's sealed-slice net P&L minus its single largest winning trade's net P&L still exceeds live's sealed-slice net P&L; **P5** on the unperturbed run, no h5 position exceeds **30%** of equity at entry (weight = `notional / equity` on the position's first `position_log` row) | evidence for adoption at the 2027-01-01 review; red-team before any write-up; adoption only through §7 |
| **UNDERPOWERED** | median ΔSharpe > 0 and P2, P4 and P5 hold, but P1's 15-of-20 or P3 fails | record; adopt nothing; offer h5 as a forward-logged comparator (needs a §2 swap in `forward/prereg_swing.md`) |
| **KILL** | median ΔSharpe ≤ 0, **or** P2, P4 or P5 fails | registry row; h5 is not retuned or re-run on the sealed slice |

Reported regardless of outcome: each book's sealed Sharpe, CAGR, MaxDD and trade count bands; the per-half numbers;
the largest position weight; h5's share of sealed P&L from positions above 20% of equity; per-trade mean R
(degenerate-stop rule applied). P5's 30% limit was set by the owner on 2026-11-13 (amending the drafted 60%) because h5
sizes by risk alone: at 2% risk, a 4% stop means 50% of equity in one name.

## 6. What would make this wrong

- **Falsifier.** h5's train-window gain came from concentration: a few tight-stop names sized far past 20% that
  happened to run. P4 and P5 test that directly. A pass with most sealed P&L from oversized positions is a fragile
  pass, and §5's reporting line makes it visible.
- **The leak most likely to fake a pass.** A data path that lets 2024H2+ prices into signal construction for the
  train-slice G0 check, or a fresh-capital slice in place of the continuous one. The script asserts the continuous
  slice (NAV indexed from the full run's start) and uses the same price pin as every ensemble.
- **Survivorship.** PIT membership is on for both books.
- **Regime.** The slice is one 2-year market. A PROMOTE says h5 survived one refutation attempt in one regime, nothing more.

## 7. Route on PROMOTE (no live change from this file)

1. Red-team the run (`red-team` agent) before any write-up.
2. `/verdict` writes `research/findings/0151-*.md` and seals this pre-registration.
3. The owner decides at the **2027-01-01** quarterly review, or earlier by owner override. Adoption requires:
   - a dated amendment to `forward/prereg_swing.md` re-scoping §4 (grading) and §12 (funding cap), owner-written;
   - an effective-date gate in `scripts/run_bhanushali_cron.py`, so history is not re-priced;
   - a golden re-pin (`/re-anchor`).
4. Cards must state position size in rupees, because h5 positions can be several times today's.

## 8. Checks before the run (each recorded in the run's output)

- **C1** `n_trials` incremented in its own commit after this file, then the run.
- **C2** the ext-band census population (`pipelines/diagnostics/diag_ext_band_census.py`) date-checked for rows on or
  after 2024-07-01; any found are disclosed in the S4 ledger row.
- **C3** sealed-open row **S4** appended to `diagnostics/research/label_screen_ledger.md` before the read.
- **C4** G0 passes before any sealed number is computed.

## 9. Owner sign-off (required before C1)

Decided by the owner on 2026-11-13, before any sealed number:
- [x] **One arm:** h5 exactly as registered in §2 (all four switches off together). No Grade-A-gate variant.
      `n_trials` 2 → 3.
- [x] **P5 concentration bar: 30%** of equity in one name at entry (amended from the drafted 60%).

Still open, and the sealed slice is not opened until it is signed:
- [ ] **Final sign-off on this plan as written, and on spending sealed open S4.** It cannot be undone.

**Disclosed before the read: P5 will probably bind.** Measured on the train window only (2019-01-01..2024-06-30,
unperturbed run, nothing sealed read), h5 opened **4 of 87 positions above 30%** of equity at entry, the largest at
**49.2%**. The live book's largest was 22.0%, with none above 30%. At that rate (about 4.6% of positions), a sealed slice
of about 30 positions has roughly a 3-in-4 chance of containing at least one, so h5 as registered is likely to KILL on
P5 whatever its Sharpe. The owner may, before signing, replace the arm with **h5 capped at 30% notional**
(`max_notional_pct = 0.30`, the other three switches off). That is still one arm, and it turns P5 from a likely
failure into a rule the book obeys by construction.

## 10. Reproduction

`python pipelines/diagnostics/confirm_0151_h5.py`, written and committed with the C1 counter commit (it implements
exactly §2 and §5 and nothing else). Data: `data/ohlcv.pkl` at the anchor pin (sha `f8625a8f`), PIT membership from
`nq.data.membership`. Interpreter: Python 3.13 (pin ≥3.12,<3.14). The engine commit is the one carrying the C1 counter
increment.
