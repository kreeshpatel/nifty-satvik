# 0138 — The validated rig, and what survives of 2026-08-06

**Date:** 2026-08-07 · **Class:** infrastructure + re-adjudication. **`n_trials` unchanged at 138.**
**Standing counts:** screens 19 · sealed opens 1 · n_trials 138.
**Verdict on the candidate:** **UNDERPOWERED** by the mechanized bar — 5 of 7 gates pass, the two
statistical gates fail. Not disproven; not certifiable on this data.

---

## 1. Why the rig was built

The 2026-08-06 session produced ~10 bespoke `scripts/diag_*.py` explorers, each with its own
portfolio loop, none routed through the tested engine, none covered by a golden, and none run
against `.claude/skills/backtest-rigor` §F. **Four defects surfaced, all by luck:**

| defect | consequence |
|---|---|
| pivot two periods stale (`resample().shift(1).reindex(ffill)` double-shift) | every pivot number wrong; a 19.28% headline collapsed to 9.15% |
| TRAIN/HOLDOUT were fresh-capital re-runs | violates `program-laws` §VIII; all sub-period figures phantom |
| 19 unadjusted splits in the universe | rediscovered by accident; documented since 2026-07-16 |
| weekly bars via `resample("W-FRI")` | the canonical grouping is ISO-week (`nq/data/weekly.py`) — whose docstring exists *because* "~10 swing scripts each re-derive weekly and drift" |

Root cause: `nq/engine/portfolio.py::simulate` hardcodes cross-sectional rank-gate selection and the
four `decide_exit` rules, so it **cannot express an event-driven signal book**. That gap is why each
script grew its own loop, and its own bugs.

## 2. What was built (357 → 441 tests)

| module | role |
|---|---|
| `nq/data/indicators.py` | TV-parity `rma`, `wilder_rsi`, `atr`, `supertrend`, `period_pivot`, `macd`, `stochastic`, `fresh`. 41 tests: hand-computed pivots, truncation invariance, and a pin that `rma` and `features.ema` must stay **different** (the frozen v1 EMA is α=2/(span+1) seeded at bar 0, not Wilder — the trap that produced the bug class) |
| `nq/engine/signal_book.py` | Event-driven simulator returning **`simulate`'s exact contract** `{equity_curve, trades, metrics}`. 17 tests over five hand-derivable trade archetypes |
| `nq/data/integrity.py` | Unadjusted-split detection, trade-spanning check, thin-universe floor. 19 tests |
| `nq/runner/research.py::adjudicate` | **The key refactor.** The mechanized bar split out of `evaluate_overlay`, so *any* engine emitting the contract inherits it. `evaluate_overlay` is now a thin wrapper; behaviour byte-identical |
| `tests/test_signal_book_parity.py` | Two-engine parity: a day-loop portfolio engine vs an independently written per-trade forward scan |

**The parity test found two defects before it ever went green** — which is the entire argument for
paying for it:

1. **`days_held` semantics.** Exits differed by one bar on 40% of trades. The engine was right
   (management runs before fills, so `days_held` counts ELAPSED sessions — `simulate`'s rule). Now
   pinned: **a stop breached on the entry bar itself does not fire.** That is a real optimism,
   inherited deliberately from the engine of record, and it is now a decision rather than an accident.
2. **Entry slippage was mine, in the engine.** `simulate` prices entries in TWO passes (size at the
   tier rate, re-price with the 0.5%-of-ADV impact once notional is known). `signal_book` did only
   the first pass — charging impact on exits but not entries, **understating round-trip friction on
   every large position**. Caught by a 9-paise disagreement between two implementations. Neither
   engine alone could have told us.

## 3. The candidate through the real bar

Weekly Supertrend(10,3) + EMA40w + monthly-pivot cross; stop 2×weekly ATR(14); target 2R; signal on
a completed ISO-week bar, entry next daily open, managed daily. Base arm = a **matched random-entry
null** (same signal count per name, same stop rule, random dates, fixed seed) — the right comparator
because `adjudicate`'s turnover gate assumes both arms trade.

| | CAGR | Sharpe | MaxDD | Calmar | trades | win |
|---|---|---|---|---|---|---|
| **CANDIDATE** | 17.62% | 0.955 | **−24.37%** | **0.72** | 281 | 48.4% |
| random null | 14.27% | 0.851 | −45.51% | 0.31 | 310 | 47.4% |
| **PASSIVE EW** | **17.97%** | **1.009** | −53.13% | 0.34 | — | — |

**Gates: 5 of 7 pass.**

| gate | | |
|---|---|---|
| `dSharpe_meaningful` | **FAIL** | ΔSharpe **+0.104**, CI **[−0.515, +0.658]** — straddles zero, point below the 0.30 noise floor |
| `dsr_gt_0.95` | **FAIL** | DSR **0.415** at n_trials=138 |
| `dCalmar_ge_0.05` | PASS | +0.41 |
| `subperiod_2022_positive` | PASS | +5.97pp, **sliced from the continuous curve** |
| `fold_pass_ge_60pct` | PASS | 0.625 / 8 folds |
| `turnover_le_30pct` | PASS | −0.093 |
| `n_eff_ge_20` | PASS | **37** |

**VERDICT: UNDERPOWERED.** `n_eff = 37` is the repo's own machinery confirming the ~36-independent-
window wall this programme keeps hitting (finding 0008). **The ΔSharpe CI is ±0.59 wide** — no edge
below roughly 0.6 Sharpe is resolvable on this data by any method.

Concentration (§C4): top-3 names **17.9%** of P&L — passes the 30% bar. Top-25 trades carry 97.6%.
Integrity: **0 of 281 trades span an unadjusted split**; universe floor held at 466 names minimum.

## 4. Re-adjudication of 2026-08-06

**WITHDRAWN**
- The **19.28% / Sharpe 1.129** weekly+quarterly-R1 headline — a pivot-bug artefact (0137 §0).
- **Every TRAIN/HOLDOUT absolute figure** of that session. They were fresh-capital re-runs, not
  continuous slices, and `program-laws` §VIII forbids exactly that. Relative rankings survive
  (identical treatment across cells); absolute sub-period claims do not.
- The stated **mechanism** by which RNAVAL corrupted results. A *uniformly* mis-scaled series is
  **scale-invariant for returns** — R-multiples and return-% are unaffected because ratios ignore
  units. What it corrupts is **position sizing** (`qty = cap × equity / price` reads an absolute
  price). The contamination is real; my account of its effect was wrong.

**REVISED — upward, against the prediction**
- The candidate on the validated rig is **better**, not worse: 15.77% → **17.62%** CAGR,
  0.850 → **0.955** Sharpe, −27.0% → **−24.37%** MaxDD. Correct ISO-week bars and the real cost
  model helped it. The stated expectation before running was that it would deteriorate.

**SURVIVES — and strengthened, now on one tested engine**
- **Passive ownership is the binding benchmark and the candidate does not clear it**: 17.97% / 1.009
  versus 17.62% / 0.955. Third independent framing of 0135 §5 / 0136 §4.
- **The drawdown edge is real**: −24.37% vs −53.13%, Calmar 0.72 vs 0.34. A Law VII trade —
  robustness bought with return — and the only durable property found across the whole arc.
- The structural conclusions of 0132/0134/0135/0136 (no timing edge on nine PIT fronts, no
  complementarity among the nine strategies, universe narrowing refuted) do not depend on the pivot
  and are unaffected.

**UNTESTED**
- The nine-strategy survey rankings have **not** been re-run on the validated rig. 0133's ordering
  and its random-control calibration remain provisional.
- The intraday half of the owner's table (11 of 22 positives) — still data-blocked.

## 5. Next setup

Nothing here promotes anything, and no further in-sample work on this candidate is warranted: the
windows are spent and §3 shows the resolution limit is ±0.59 Sharpe. The only instrument that can
still produce unbiased evidence is the **forward wall** (`forward/prereg.md`).

The remaining honest levers are unchanged and all structural: **long-short** (the only untested
source of negative correlation), **intraday data** (unblocks 11 strategies and the Bajaj 2-hourly
leg), and **longer history** (every dead end this arc died of n_eff ≈ 37).

## 6. Do not re-test unless

1. **Forward evidence** accumulates on a logged book.
2. **More independent observations** — a second market, or history predating 2017. Re-running the
   candidate on this window is refused: the CI half-width is 0.59 and the answer cannot change.
3. **A candidate that clears passive ownership**, which remains the binding gate.

## 7. Reproduction

`scripts/run_candidate_gate.py` — end-to-end: panel build, integrity assertions, candidate and null
signal generation, both arms through `signal_book`, `adjudicate`, concentration, passive benchmark.
Emits `diagnostics/research/candidate_gate.json`.
