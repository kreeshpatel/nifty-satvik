# 0151 — h5-30: the live exit with three caps off and a 30% per-name cap (CONFIRM)

**Status: PRE-REGISTERED and SIGNED (2026-11-13). Next: the counter increment (C1), then checks C2–C4, then the run.**
**Amended 2026-11-13 (before any sealed number), by the owner:** one arm; the arm switched from h5 (notional cap
off) to **h5-30** (notional cap at 30%); P5 at 30%. The train-window result for h5-30 is in §3 and was shown to the owner
before signing.
**Tier:** 3 · CONFIRM (`docs/PROCESS_TIERS.md`): a cap and grading change to the live book.
**Written:** 2026-11-13, before any sealed-slice number for any h5 variant exists.
**Counter:** `n_trials` 2 → 3 and `family_level_count` 2 → 3 (one arm). The increment is a separate commit, made after
this file is committed and the owner has signed §9, and before the run. **Sealed opens:** 3 → 4 on the run (row S4).
Standing counts at registration: screens 24 · sealed opens 3 · n_trials 2.

## 1. Hypothesis

On the sealed validation slice (2024-07-01..2026-06-30), the live book with the extension cap, the Grade-A gate and the
stop-width cap removed, and the per-name notional cap raised from 20% to 30% (**h5-30**), has a higher Sharpe than the
live book at no materially deeper drawdown, with the same signals, exit, costs and
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

| switch | live (control) | h5-30 |
|---|---|---|
| `ext_cap` | 0.20: no entry more than 20% above the 44-week SMA | `None` |
| `grade_gate` | on: Grade A only (top 5 by CRS per ISO week) | off: all grades, funded strongest-CRS-first |
| `max_notional_pct` | 0.20: one position ≤ 20% of sizing equity | **0.30**: one position ≤ 30% of sizing equity |
| `max_risk_pct` | 0.10: stop raised to entry × 0.90 when the candle low is further | `None`: stop at the candle low |

This is the lab config `{"ext_cap": None, "grade_gate": False, "max_notional_pct": 0.30, "max_risk_pct": None}`
(`H5_30` in `pipelines/diagnostics/explore_ensemble_jan_candidates.py`). No other value is run.

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

  Every one of those numbers is train-window and has been looked at.
- **h5-30 on the train window** (owner request 2026-11-13, the same 20 paired paths, reported 2019-03-01..2024-06-30,
  `2026-11-13_ensemble_jan_candidates.json`):

  | | median | 5th pct | 95th pct | paths better |
  |---|---|---|---|---|
  | ΔSharpe vs live | **+0.34** | −0.10 | +0.59 | 18 of 20 |
  | ΔMaxDD, pp (+ = shallower) | +4.5 | −3.0 | +15.1 | 16 of 20 |
  | ΔCAGR, pp | +11.3 | −3.9 | +16.6 | — |

  Medians: h5-30 Sharpe 1.61 / CAGR 38.1% / MaxDD −32.6%, against live 1.25 / 26.1% / −37.5%. Its median gain is
  larger than uncapped h5's (+0.27), but **it does not clear the house robustness bar**: its 5th percentile is below
  zero, where uncapped h5's (+0.12) was above. 2 of 20 paths are worse than live. This is disclosed before the sealed read.
  This is the first trial on any h5 variant.
- **Grading collides with an existing forward decision.** `forward/prereg_swing.md` §4 reserves the A-only vs
  all-grades choice for the forward record (primary read 2027-07-01; "between reviews, no config or grading change").
  §12 records that under `max_notional_pct = 0.20` the two §4 books have held identical positions, so §4 cannot
  currently decide. h5-30 raises that same cap. **This trial cannot change the live grading or caps by itself.** A PROMOTE
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
8 windows give a statistical half-width near **1.3 Sharpe**. The hoped-for effect (+0.34 in-sample) is far below that.
**This read cannot confirm the magnitude of h5-30's edge; it can only refute it** by showing a sign flip, a drawdown
blow-out, or a gain that rests on one trade, as S1 refuted 0116. The bars are written for that job.

## 5. Pre-committed outcome table

Path-level quantities are paired (h5-30 minus live, same draw) on the sealed continuous slice. The "unperturbed run" is one
extra run of each book with zero cost jitter and start 2019-01-01.

| outcome | condition, fixed now | what happens |
|---|---|---|
| **STOP (no read)** | **G0** fails: before the sealed slice is read, the same script on the train slice 2019-03-01..2024-06-30 gives a median paired ΔSharpe outside **+0.34 ± 0.10** (h5-30's registered train number) | harness drift; the sealed read is not spent, and the cause is found first |
| **PROMOTE** | **all of**: **P1** median ΔSharpe > 0 **and** ≥ 15 of 20 paths > 0; **P2** median ΔMaxDD ≥ −5.0pp (h5-30 at most 5pp deeper); **P3** on the unperturbed run, ΔSharpe is not negative on **both** halves (2024-07-01..2025-06-30 and 2025-07-01..2026-06-30, each a continuous slice); **P4** on the unperturbed run, h5-30's sealed-slice net P&L minus its single largest winning trade's net P&L still exceeds live's sealed-slice net P&L; **P5** on the unperturbed run, no h5-30 position exceeds **31%** of equity at entry (weight = `notional / equity` on the position's first `position_log` row). The cap is 30% of the prior close's equity at the fill price; the first row is marked at the entry day's close, so 1pp covers that day's move (train-window maximum 30.5%). A larger figure means the cap failed. | evidence for adoption at the 2027-01-01 review; red-team before any write-up; adoption only through §7 |
| **UNDERPOWERED** | median ΔSharpe > 0 and P2, P4 and P5 hold, but P1's 15-of-20 or P3 fails | record; adopt nothing; offer h5-30 as a forward-logged comparator (needs a §2 swap in `forward/prereg_swing.md`) |
| **KILL** | median ΔSharpe ≤ 0, **or** P2, P4 or P5 fails | registry row; h5-30 is not retuned or re-run on the sealed slice, and no other h5 variant is opened on it |

Reported regardless of outcome: each book's sealed Sharpe, CAGR, MaxDD and trade count bands; the per-half numbers;
the largest position weight; h5-30's share of sealed P&L from positions above 20% of equity; per-trade mean R
(degenerate-stop rule applied). The 30% figure was set by the owner on 2026-11-13, first as a pass bar on uncapped h5
(amending the drafted 60%), then as the arm's own cap.

## 6. What would make this wrong

- **Falsifier.** h5-30's train-window gain came from concentration: a few tight-stop names sized up to 30% that
  happened to run. P4 tests that directly; P5 checks the cap held. A pass with most sealed P&L from oversized positions is a fragile
  pass, and §5's reporting line makes it visible.
- **The leak most likely to fake a pass.** A data path that lets 2024H2+ prices into signal construction for the
  train-slice G0 check, or a fresh-capital slice in place of the continuous one. The script asserts the continuous
  slice (NAV indexed from the full run's start) and uses the same price pin as every ensemble.
- **Survivorship.** PIT membership is on for both books.
- **Regime.** The slice is one 2-year market. A PROMOTE says h5-30 survived one refutation attempt in one regime, nothing more.

## 7. Route on PROMOTE (no live change from this file)

1. Red-team the run (`red-team` agent) before any write-up.
2. `/verdict` writes `research/findings/0151-*.md` and seals this pre-registration.
3. The owner decides at the **2027-01-01** quarterly review, or earlier by owner override. Adoption requires:
   - a dated amendment to `forward/prereg_swing.md` re-scoping §4 (grading) and §12 (funding cap), owner-written;
   - an effective-date gate in `scripts/run_bhanushali_cron.py`, so history is not re-priced;
   - a golden re-pin (`/re-anchor`).
4. Cards must state position size in rupees, because h5-30 positions can be up to 1.5 times today's 20% cap.

## 8. Checks before the run (each recorded in the run's output)

- **C1** `n_trials` incremented in its own commit after this file, then the run.
- **C2** the ext-band census population (`pipelines/diagnostics/diag_ext_band_census.py`) date-checked for rows on or
  after 2024-07-01; any found are disclosed in the S4 ledger row.
- **C3** sealed-open row **S4** appended to `diagnostics/research/label_screen_ledger.md` before the read.
- **C4** G0 passes before any sealed number is computed.

## 9. Owner sign-off (required before C1)

Decided by the owner on 2026-11-13, before any sealed number:
- [x] **One arm.** `n_trials` 2 → 3.
- [x] **The arm is h5-30** (§2): extension cap, Grade-A gate and stop-width cap off; per-name notional cap 30%.
      Switched from uncapped h5 after the train window showed uncapped h5 opened 4 of 87 positions above 30% (largest
      49.2%), which would almost certainly have failed the 30% bar.
- [x] **Concentration limit 30%**, checked as P5 with a 1pp measurement tolerance (§5).

Shown to the owner before signing (train window only, nothing sealed read):
- h5-30's 20-path result (§3): median +0.34 Sharpe, 18 of 20 paths better, **5th percentile −0.10, so it does not clear
  the robustness bar that uncapped h5 cleared**;
- its unperturbed concentration: 97 positions, the largest 30.5% of equity at the entry day's close and 32.5% on any
  day, against live's 22.0% and 27.9%.

Final sign-off:
- [x] **Final sign-off on this plan as written, and on spending sealed open S4.** Signed by the owner in chat on 2026-11-13 ("sign 0151"), after seeing the h5-30 train result.

## 10. Reproduction

`python pipelines/diagnostics/confirm_0151_h5_30.py`, written and committed with the C1 counter commit (it implements
exactly §2 and §5 and nothing else). Data: `data/ohlcv.pkl` at the anchor pin (sha `f8625a8f`), PIT membership from
`nq.data.membership`. Interpreter: Python 3.13 (pin ≥3.12,<3.14). The engine commit is the one carrying the C1 counter
increment.
