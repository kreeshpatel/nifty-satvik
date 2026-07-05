# 0094 — CRS-strength fill ranking on the live weekly book (Level-0, no training)

- **ID:** 0094. **Status: PRE-REGISTERED** (spec frozen before the run; no retuning).
- **Registered:** 2026-07-05, BEFORE the run. **TRIAL, 1 frozen config** → cumulative_n_trials 111 → 112.
- **Anchor / data:** identical cell to 0093-N50 (corrected universe, PIT, tiered costs, 2017–2026, ₹10L,
  pinned Nifty-50). Script `scripts/run_bhanushali_weekly_rank.py`.

## Why this trial exists
The live book (0093 + Nifty-50, finding 0037) is capacity-bound: a typical week fires ~10–25 signals but
cash funds only a few. Today the engine fills them in **arbitrary dict order** — effectively alphabetical.
Finding 0029 showed the family's profit lives in a handful of trades, so WHICH signals get the cash is a
first-order lever the current engine leaves to chance. Owner direction: build a ranking system; per the
trust-ladder decision, start at **Level 0 — a fixed, a-priori formula with zero fitted parameters** (the
0046 precedent killed a TRAINED ranker; this is allocation-order only, no ML, different book — not a
relitigation).

## The FROZEN spec (one delta from the live 0093-N50 config)

| Param | Frozen value |
|---|---|
| Signal set / entry / stop / exits / sizing / universe / costs | **exactly 0093 + Nifty-50** (live config: 44w-SMA + slope≥3%/13w + quality green + loose 7% band + CRS>SMA40 vs Nifty-50; in-range open entry; half@2R, 20-SMA −4% trail, week-low stop, 13w cap, weekly-close/Monday exits; 2% risk) |
| **Rank (new)** | `crs_dist = RS / SMA40(RS) − 1` computed at the signal week's close (RS = wclose / Nifty-50) — how far the RS line sits above its own 40-week SMA |
| **Fill order (new)** | each session, all fillable entry candidates are attempted in **descending crs_dist** (was: dict order). Ties → ticker A-Z. Signal set unchanged — nothing is added or dropped, only WHO gets the cash first. |

Pre-declared diagnostics: (a) **rank-IC** — Spearman correlation of crs_dist vs realized trade R across all
filled trades (does the formula actually order outcomes? this decides whether a Level-2 trained ranker is
ever worth building); (b) fills changed vs 0093-N50 (how many trades differ); (c) per-year.

## Primary metric + decision rule
Primary = corrected-universe NET Sharpe. Family gates (DSR@112 > 0.95 AND CI-low > 0 AND slices > 0 →
PROMOTE; Sharpe > 0 → UNDERPOWERED; else KILL). **Head-to-head vs 0093-N50 (+0.900 / +18.7% / −42.5%)
decides the live fill rule:** better-or-equal → the ranking ships to the live cron (it is a strict
improvement in principle — deliberate over arbitrary); clearly worse → arbitrary fill stays and the rank-IC
readout tells us whether ranking research continues at all.

## Skeptical prior (honest)
For: allocation among already-taken signals is the one untested first-order lever; profit concentration
(0029) says selection matters; zero fitted params = minimal overfit surface. Against: 0046's trained ranker
carried no signal on the base book, and C2 found conviction IC weak (0.056) — cross-sectional ordering may
be noise here too; the alphabetical fill may be an accidental (lucky) portfolio, and any reordering
reshuffles the cash-constrained path (0085's lesson: path-dependence swamps small changes). Expect: modest
|Δ|, UNDERPOWERED; the rank-IC diagnostic is the durable learning either way.

---

## RESULT (appended 2026-07-05 after the run of record — spec above untouched)

| | trades | win | expR | CAGR | Sharpe | MaxDD | CI-low | DSR |
|---|---|---|---|---|---|---|---|---|
| **0094 ranked fill** | 255 | **59.2%** | **+0.48** | **+24.7%** | **+1.132** | −42.4% | **+0.474** | **0.894** |
| 0093-N50 reference (same run) | 247 | 52% | +0.30 | +18.7% | +0.900 | −42.5% | +0.274 | 0.745 |

Slices +1.17/+1.05/+1.19. ΔSharpe +0.232, ΔCAGR +5.9pp, ΔDD ≈ 0. Rank-IC within filled trades −0.124
(p=0.049). **Adversarial ordering probe:** DESC +1.132 > dict +0.900 > alphabetical +0.770 > ASC +0.683 —
monotone in the rank's direction → real selection signal at the fill margin, not reshuffling luck; the
negative within-slice IC = range restriction (the value is the cut, not the fine ordering → limited
Level-2 headroom, consistent with the 0046 trained-ranker KILL).

**VERDICT: UNDERPOWERED (DSR 0.894 — one hair under the bar, the program's strongest result).** Per the
pre-committed head-to-head rule (better-or-equal → ships): the ranked fill REPLACES arbitrary fill in the
live weekly cron; the live signal list carries `crs_rank` and is served strongest-first (top-5 = grade A).
Forward wall remains the only certifier. See finding 0038.
