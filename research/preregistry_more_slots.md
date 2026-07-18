# PRE-REGISTRATION — MORE SLOTS: lower flat risk so more names fit

*Status: **PRE-REGISTERED**, frozen 2026-07-16 BEFORE the run. No retuning (R4/R11). n_trials 120 -> 122.*

## Hypothesis

`FINDING_cash_starvation` established the book abandons **19,151 fill attempts for lack of cash** and
takes only **~2% of signal windows**. **Cash, not the signal, decides the book.** Cash is served
strongest-CRS-first, and CRS rises as a name extends — so the cheap early window loses the queue and the
name is only bought once expensive (MAXHEALTH: the 994.05 / +2.0%-ext window was fillable and worth
**+3.00R**; we filled 1173.30 / +19.4% for **−1.38R**).

The queue cannot be reordered — `near_sma` fill-priority is **KILLED at −0.80 Sharpe** because it
displaces the CRS-strongest names, which *are* the runners. **The CRS-strongest-first order is
load-bearing.**

So: don't change the queue — **add seats**. `notional per name = risk% ÷ R%`:

| config | risk% | R% | notional/name | names |
|---|---|---|---|---|
| BASE | 2.0 | 14.2 | 14% | ~7 |
| SPEC (R cap 10%) | 2.0 | 9.2 | **22%** | **~4-5** |
| **S1 (new)** | **1.3** | 9.2 | **14%** | **~7** |
| **S2 (new)** | **0.9** | 9.2 | **10%** | **~10** |

## Not a relitigation

Prior sizing work is **conviction TILTS** (0073/C3, 0020 — mean-preserved quintile scaling, KILLED) and
the Kelly analysis (0003) on the **momentum** book at 3% risk. **A flat risk-LEVEL change on the
weekly-swing book, motivated by slot count rather than edge-weighting, has no record.** New formulation
(R-registry rule 1). S1 doubles as the deconfounding arm `FINDING_small_candle` declined to run — it
holds notional at the base's natural 14% while R stays capped.

## Frozen spec

Both arms are **SPEC** (`ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20`) + live P2 exit,
all-grades, Rs10L, varying only `risk_pct`:

- **S1: `risk_pct=0.013`** — restores the base's ~14% notional per name.
- **S2: `risk_pct=0.009`** — ~10% per name, ~10 names.

Values are derived from the arithmetic above (`risk = 0.142 × target_notional`), **not swept**.

## Pre-declared measurements

Sharpe · CAGR · MaxDD · **2022-26 continuous slice** · trades · win% · meanR · median R% · notional/name ·
**skipped_cash** (the mechanism check) · mean hold · exit mix.

## Pre-declared expectation — the honest tension

- **Mechanism check:** `skipped_cash` MUST fall and trade count MUST rise. If they don't, the lever
  didn't do its job and the arm says nothing about the hypothesis (the `decouple` lesson —
  `FINDING_decouple.md` — where the mechanism check failed and the KILL was therefore uninformative).
- **CAGR will likely FALL.** Smaller positions earn less per trade; more trades must compensate. Not
  obviously a win.
- **Sharpe may RISE** — more names = more diversification = lower book vol.
- **The real risk is DILUTION.** The Monte-Carlo work put CRS at the **99-100th percentile** of selection
  skill; more seats means going **deeper down the CRS queue** into weaker names, pulling the book toward
  the pool mean (random null **0.74**). This is the whole question.

**KILL / UNDERPOWERED is a first-class outcome.**

## Gate

2022-26 continuous slice (R3) vs BASE **1.29** / SPEC **1.21** / null **0.74** (sd 0.24). DSR bar
acknowledged at trial 122. **Nothing ships in-sample (R11).**
