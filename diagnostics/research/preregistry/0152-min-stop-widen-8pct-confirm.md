# 0152 — Widen a stop tighter than 8% of entry to 8% (CONFIRM)

**Status: PRE-REGISTERED, awaiting the owner's signature. Nothing has been run on sealed slice B for this question.**
**Tier:** 3 · CONFIRM (`docs/PROCESS_TIERS.md`): a change to how the live book sets its stop and therefore its size.
**Written:** 2026-11-17, before any sealed-slice number for this rule exists.
**Counter:** `n_trials` 3 → 4 and `family_level_count` 3 → 4 (one arm). The increment is a separate commit, made after
this file is committed and the owner has signed §9, and before the run. **Sealed opens:** 4 → 5 on the run (row S5).
Standing counts at registration: screens 24 · sealed opens 4 · n_trials 3.

## 1. Hypothesis

On the sealed validation slice (2024-07-01..2026-06-30), the live book with a **minimum stop distance of 8% of entry,
applied by widening the stop rather than skipping the trade**, has a higher Sharpe than the live book at no materially
deeper drawdown, with the same signals, exit, costs and membership. The comparator is the live configuration itself,
run on the same paths.

## 2. The two books, every parameter fixed here

Both books run `R94.backtest` through `nq.lab.runs.engine_kwargs`. Shared: `LIVE_PREP` signals, the live scaled exit
(config P), `LIVE_DISCIPLINE` (ext_cap 0.20, max_risk_pct 0.10, max_notional_pct 0.20), `LIVE_STALENESS`, demerger
events, PIT Nifty-500 membership, ₹10L, 2% risk per trade, costs as coded.

They differ on exactly one thing:

| | live (control) | the arm |
|---|---|---|
| `min_stop_pct` | 0.0 (off) | **0.08** |
| `min_stop_mode` | — | **"widen"** |

In the engine (`scripts/run_bhanushali_weekly_rank.py`, merged off-by-default in PR #191): after the signal-week low
and the existing 10% cap have set the stop, a stop closer to entry than 8% is **moved down to exactly 8%**. The trade
is still taken. Risk sizing then divides by the wider distance, so the position is smaller. No trade is skipped and no
other lever changes. `min_stop_atr20` stays 0.

**What this does to the book, stated plainly:** the live cap already refuses a stop further than 10% from entry. An 8%
floor therefore squeezes every stop into an 8–10% band, so in effect the book moves to a near-fixed stop distance.

**Window.** One full run per path from the path's start date in early 2019 to 2026-06-30. Every gate below reads the
**continuous slice** 2024-07-01..2026-06-30 of that one run, never a fresh-capital re-run (CLAUDE.md). Paths are the 20
standard draws (`nq.lab.ensemble.draw_perturbations(20, DEFAULT_SEED)`: cost jitter ±10bp, start within the first 20
trading days of 2019), the same draws for both books, paired.

## 3. Registry confrontation, and everything already looked at

**Where this comes from.** The 2026-11-13 stop-floor study (`diagnostics/research/explore/2026-11-13_stop_floor_and_confirmation.md`,
PR #191), run at the owner's request after the loss diagnosis.

**Every stop-distance setting examined on the train window before this pre-registration — 14 settings, one study:**

| mode | settings |
|---|---|
| skip the trade when the stop is tighter than | 6%, 7%, 8%, 9% of entry; 1.0×, 1.5×, 2.0× the 20-session ATR |
| widen the stop to | 6%, 7%, 8%, 9% of entry; 1.0×, 1.5×, 2.0× the 20-session ATR |

All 14 were scored on a single capped path and on the per-trade book. Three were then run on the 20 paired paths
(widen to 6%, 7% and 8%), and two more earlier the same day (widen to 1.5× and 2.0× ATR), so **five settings have a
20-path number and 14 have a single-path number**. This arm is the best of them. That is selection, and it is why the
bars below are stricter than "better than live".

**The train-window result for this arm** (20 paired paths, reported 2019-03-01..2024-06-30,
`2026-11-13_ensemble_widen_stop.json`): median ΔSharpe **+0.37 [p5 +0.12, p95 +0.70]**, better on **20 of 20** paths;
median ΔMaxDD **+3.1pp shallower** [−3.8, +16.1]; median ΔCAGR **+8.6pp**. Per trade it is roughly neutral: total R 639
against 650, mean R per closed trade +0.68 against +0.62, and 9 of the 169 big winners lost.

**The effect rises with the level** (6% +0.04, 7% +0.21, 8% +0.37), which is the opposite of the spike seen when the
first profit target was moved to +1R and then collapsed a quarter-R away. 9% and 10% have **not** been run on 20 paths.
This pre-registration tests 8% only; no other level may be adopted from this run.

**Prior verdicts this must confront.**
- **Exit geometry is closed** (0105 tighten, 0106 widen, 0109 disaster floor — all KILL). 0106 widened *every* stop by
  a multiplier and killed on Sharpe 1.132 → 0.785. This is a different rule: a **floor on the tightest stops only**,
  which leaves the median trade untouched, and it is measured on the current scaled exit with PIT membership, which
  0106 was not. Quoted as `KILL (pre-scaled-exit epoch, base book) — not re-tested under the current harness`.
- **The funding channel.** The gain is in the capital book, not per trade: a wider stop means a smaller position for
  the same 2% risk, so more seats get funded. That is the same channel as h5, and **h5-30 failed on this slice**
  (finding 0151). A pass here would be the same mechanism passing where h5-30 failed, which is a reason for suspicion,
  not confidence. Gate P4 exists for it.
- **Law VI (the ±10R/yr noise floor)** and **Law VII (robustness is bought with return)** both apply.

**Sealed-slice cleanliness.** Opens S2 and S3 spoiled the slice for rules about **stop-width bands**, among others
(label ledger, sealed-open rows). This rule is a stop-width rule. **This is the central limitation of this trial and it
is disclosed before the run:** the slice has already been read for stop-width questions by the 2026-07-31 ext-band
census, so a PROMOTE here is weaker evidence than a first read would be. The owner is signing with that known.

## 4. Resolution, stated plainly

The sealed slice is about 2 years, roughly 8 independent 63-day windows, giving a statistical half-width near **1.3
Sharpe**. The hoped-for effect (+0.37 in-sample) is far below that. **This read cannot confirm the size of the edge; it
can only refute it.** The bars are written for that job.

## 5. Pre-committed outcome table

Paired (arm minus live, same draw) on the sealed continuous slice. The "unperturbed run" is one extra run of each book
with zero cost jitter and start 2019-01-01. **Owner-set bars, fixed 2026-11-17.**

| outcome | condition, fixed now | what happens |
|---|---|---|
| **STOP (no read)** | **G0** fails: on the train slice 2019-03-01..2024-06-30 the same script gives a median paired ΔSharpe outside **+0.37 ± 0.10** | harness drift; the sealed read is not spent, and the cause is found first |
| **PROMOTE** | **all five**: **P1** better than live on **≥ 15 of 20 paths**; **P2** median paired ΔSharpe **≥ +0.10**; **P3** median paired ΔMaxDD **≥ −3.0pp** (at most 3 points deeper); **P4** big winners (closed trades at or above +2R in the live arm, inside the slice) lost by the arm **≤ 5%** of the live arm's count in the slice; **P5** on the unperturbed run, ΔSharpe is **not negative in both** halves (2024-07-01..2025-06-30 and 2025-07-01..2026-06-30, each a continuous slice) | evidence for adoption at the 2027-01-01 review; red-team before any write-up; adoption only through §7 |
| **UNDERPOWERED** | median ΔSharpe > 0 and P3, P4 and P5 hold, but P1 or P2 fails | record; adopt nothing |
| **KILL** | median ΔSharpe ≤ 0, **or** P3, P4 or P5 fails | registry row; the rule is not retuned, and no other floor level is opened on this slice |

A quantity exactly on a bar passes (≥ and ≤ are inclusive). "Big winners lost" counts live-arm trades at or above +2R
whose counterpart in the arm closes below +2R or is absent; both arms take the same signals, so this measures the
widened stop and the smaller size, not selection.

Reported regardless of outcome: each book's sealed Sharpe, CAGR, MaxDD, trade count and mean R per closed trade; the
per-half numbers; how many stops the floor actually moved and by how much; the share of sealed P&L from trades whose
stop was widened.

## 6. What would make this wrong

- **Falsifier.** The train gain is a funding artefact: smaller positions let more names in, and 2019–24 rewarded being
  more invested. In a falling market the same rule buys more of a falling book. The slice contains exactly that market,
  which is what makes it the right test.
- **The leak most likely to fake a pass.** A fresh-capital slice in place of the continuous one, or 2024H2+ prices
  reaching the train-slice G0 check. The script asserts the continuous slice and uses the same price pin as every
  ensemble.
- **Regime.** One 2-year market. A PROMOTE says the rule survived one refutation attempt in one regime.

## 7. Route on PROMOTE (no live change from this file)

1. Red-team the run before any write-up.
2. `/verdict` writes `research/findings/0152-*.md` and seals this pre-registration.
3. The owner decides at the **2027-01-01** review. Adoption requires an **effective-date gate** in
   `scripts/run_bhanushali_cron.py` (history is rebuilt from inception every scan, so without it the live record would
   be silently re-priced), a golden re-pin (`/re-anchor`), and a card change: the stop shown to the owner moves, so the
   card must print the widened stop and the smaller position size.

## 8. Checks before the run (each recorded in the run's output)

- **C1** `n_trials` incremented in its own commit after this file, then the run.
- **C2** sealed-open row **S5** appended to `diagnostics/research/label_screen_ledger.md` before the read, repeating the
  §3 disclosure that the slice has already been read for stop-width bands.
- **C3** G0 passes before any sealed number is computed.

## 9. Owner sign-off (required before C1)

- [ ] Spend sealed open S5 on this rule, knowing the slice has already been read for stop-width questions (§3).
- [ ] The five bars in §5 as written.
- [ ] One arm only: widen to 8% of entry. No other level and no skip variant may be opened on this slice.

## 10. Reproduction

`python pipelines/diagnostics/confirm_0152_min_stop.py`, written and committed with the C1 counter commit (it
implements exactly §2 and §5 and nothing else, modelled on `confirm_0151_h5_30.py`). Data: `data/ohlcv.pkl` at the
anchor pin (sha `f8625a8f`), PIT membership from `nq.data.membership`. Interpreter: Python 3.13 (pin ≥3.12,<3.14).
