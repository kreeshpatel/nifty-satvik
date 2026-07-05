# 0038 — CRS-strength fill ranking: the biggest single improvement of the arc (+0.90→+1.13 Sharpe, +18.7→+24.7% CAGR), and the adversarial probe says it's real

- **Status:** TRIAL (pre-reg [0094](../../diagnostics/research/preregistry/0094-weekly-crs-rank-fill.md),
  n_trials 111→112, params frozen before the run) + an ordering-probe measurement. **Verdict: UNDERPOWERED
  (DSR 0.894 — a hair under the 0.95 bar, the closest the program has ever come) — and per the pre-committed
  head-to-head rule, the ranked fill SHIPS to the live cron.**
- **Date:** 2026-07-05. Script `scripts/run_bhanushali_weekly_rank.py`; ledger
  `research/exports/bhanushali_weekly_rank_0094_trades.csv` (255 trades). Same cell as 0093-N50.

## What was tested (Level-0 ranking — zero trained parameters)
The live 0093+Nifty-50 signal set byte-identical; ONE change: when signals compete for limited cash,
fillable candidates are attempted in **descending CRS distance** (`RS/SMA40(RS) − 1` at the signal week)
instead of arbitrary dict order. Nothing added or dropped — only who gets the cash first.

## Result (corrected universe, real tiered costs)

| | trades | win | expR | CAGR | Sharpe | MaxDD | Calmar | CI-low | DSR |
|---|---|---|---|---|---|---|---|---|---|
| **0094 ranked fill** | 255 | **59.2%** | **+0.48** | **+24.7%** | **+1.132** | −42.4% | **0.58** | **+0.474** | **0.894** |
| 0093-N50 (arbitrary fill) | 247 | 52% | +0.30 | +18.7% | +0.900 | −42.5% | 0.44 | +0.274 | 0.745 |

Slices +1.17 / +1.05 / +1.19 (the most even ever). ΔSharpe +0.232, ΔCAGR +5.9pp, ΔDD ≈ 0. Only 2025 has a
negative mean-R year. Erratum-insensitive.

## The IC paradox and the adversarial probe (the important part)
Rank-IC within FILLED trades was **negative** (−0.124, p=0.049) — higher rank ≠ better outcome among the
chosen. Contradiction? The ordering probe answers it. Same engine, same signals, only the fill order:

| ordering | Sharpe | CAGR | win | expR |
|---|---|---|---|---|
| **DESC rank (as pre-registered)** | **+1.132** | **+24.7%** | 59% | +0.48 |
| dict order (live reference) | +0.900 | +18.7% | 52% | +0.30 |
| alphabetical | +0.770 | +15.5% | 55% | +0.36 |
| ASC rank (weakest first) | +0.683 | +13.1% | 52% | +0.29 |

Monotone in the direction the rank predicts (strongest-first best, weakest-first ~worst; arbitrary in the
middle) — the signature of real selection signal, not reshuffling luck. Resolution of the paradox: **the
rank's value is at the FILL MARGIN** (which names get funded at all — top-slice mean R 0.48 vs mixed 0.30),
while *within* the funded top slice residual ordering is noise (the slightly negative IC — classic range
restriction, the admissions-test effect). Two consequences: (a) the improvement is causal, not path luck —
though note the arbitrary-ordering noise floor is itself ±0.15 Sharpe wide, so treat the point estimate
with the usual humility; (b) **Level-2 trained rankers have limited headroom here** — the win is the cut,
not the fine ordering, and a model trained to order within the slice would be fitting the noisy part
(consistent with 0046's trained-ranker KILL).

## Verdict & disposition
**UNDERPOWERED at DSR 0.894 — one hair under certification, the strongest and most robust result the
program has produced.** CI [+0.474, +1.705] excludes zero decisively; slices are the most uniform of any
book; the mechanism survived an adversarial ordering probe. Per the pre-reg's pre-committed head-to-head
rule (better-or-equal → ships): **the ranked fill replaces arbitrary fill in the live weekly cron**, and
the live "buy this week" list now carries each signal's CRS rank so the owner funds strongest-first with
real capital too. Still not certified — the forward wall remains the only certifier — but this is the
right fill rule by both evidence and principle (deliberate beats arbitrary). Do NOT build a Level-2
trained ranker on this book without new evidence (the IC says the headroom isn't there); the open levers
remain the 13-week cap (exit-side) and the sizing/vol-target pair.
