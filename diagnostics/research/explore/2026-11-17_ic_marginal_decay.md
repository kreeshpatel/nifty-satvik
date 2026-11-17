# 2026-11-17 — Marginal IC decay of the two rankers (supersedes the cumulative version)

**Correction.** The earlier report `2026-11-17_ic_decay_halflife.md` (PR #206) measured **cumulative** forward
returns and concluded "IC rises with horizon, no decay, no half-life", with three reads drawn from that. A cumulative
return over a growing window mechanically inherits the trend the ranker is built from, so the rising curve was partly
the arithmetic of the window, not persistence of the signal. **That result and its three reads are withdrawn.** The
cumulative table is kept below, labelled as what it is, and the decay question is answered on the marginal measure.

**Mission line.** A ranker whose per-week information dies in a month and one whose lives for half a year call for
different re-ranking cadences and different holding periods; on the 70/30 blend that difference is return and
drawdown. This measures which it is. It changes nothing by itself.

**Tier:** EXPLORE, descriptive. No trial, no screen row, **no sealed read**, nothing live changed, nothing adopted.
Standing counts unchanged (read from the ledgers, not from here).
Reproduce: `python pipelines/diagnostics/explore_ic_marginal_decay.py` → `2026-11-17_ic_marginal_decay.json`.

---

## Rule 1 — method, before any result

| element | what was done |
|---|---|
| window | Fridays 2019-01-01..2024-06-30. Prices cut at 2024-06-30 and the cut **asserted** (`explore_ic_marginal_decay.py:109`). Sealed slice B never read. |
| universe | PIT Nifty-500 membership at each Friday, `nq.data.membership.load_membership()` + `run_bhanushali_weekly_rank.ticker_in_index_on` — the live swing rule. Cross-sections under **50 names** skipped. Median cross-section **498** names over **287** Fridays. |
| weekly close | daily `Close` resampled `W-FRI` `.last()`; the same Friday stamp carries price, rank and membership. |
| ranker 1 — `crs_dist` | `rs = weekly close / Nifty-50 weekly close`; `crs = rs / rs.rolling(40).mean() − 1`. Formula of record `scripts/run_bhanushali_weekly_rank.py:296-298`, `CRS_LEN=40` at `:46`. |
| ranker 2 — `sma200_slope_63` | `(SMA200 / SMA200.shift(63) − 1) × 100` on daily closes, read at the Friday. Formula of record `nq/data/features.py:113-115`. Momentum's ranker per finding 0001. |
| **cumulative IC(h)** | per Friday *t*: `Spearman(rank_t, close_{t+h}/close_t − 1)`. **Not a decay measure** — the window grows with *h*. Kept for continuity only. |
| **marginal IC(h)** | per Friday *t*: `Spearman(rank_t, close_{t+h}/close_{t+h−1} − 1)` — the return of **week t+h alone**. This is the decay measure. `explore_ic_marginal_decay.py:138-142` |
| **marginal-4w IC(h)** | per Friday *t*: `Spearman(rank_t, close_{t+h}/close_{t+h−4} − 1)` — the **4-week block ending at h**, sampled every 4th Friday so no two observations share a return window. Defined for h ≥ 4. The four offsets (0..3) are computed separately and pooled; the bootstrap draws whole blocks of Fridays, so the independence is not lost in the pooling. `explore_ic_marginal_decay.py:143-147` |
| dependence | consecutive weekly ICs are strongly dependent (overlapping cross-sections, autocorrelated ranks), so **every** band is a **moving-block bootstrap over Fridays: block 13 weeks, 2,000 draws, seed 20261117**. An iid interval would be several times too narrow. The marginal-4w variant removes return-window overlap but **not** rank autocorrelation, which is why it also gets a block bootstrap. |
| half-life | least squares of `ln(IC_h)` on *h* over horizons with `IC_h > 0`; half-life `= ln2 / −slope`. Fitted on the **marginal measures only**, never on the cumulative curve. Reported only if the slope is negative **and** ≥50% of bootstrap resamples also decay. |

## Rule 4 — anchor, reproduced in-run before any IC was computed

**Live A uncapped: total R = 650.2 over 525 trades** — expected 650.2 / 525, reproduced **650.2 / 525**, match.
(`diagnostics/research/2026-11_loss_diagnosis.json`; the run aborts on a mismatch beyond 0.1R.)
0001's **21.73% CAGR / 1.130 Sharpe / −37.17% MaxDD** is the cloud run of record and is **quoted, not reproduced
here** — it cannot be recomputed in this process.

## Rule 5 — scope

Horizons 1, 2, 4, 8, 13, 26 were asked for. **39 and 52 were added after the first look** at the cumulative curve,
because nothing had turned by 26 weeks, and they are carried here marked `*`. Counted honestly: 8 horizons × 3
measures × 2 rankers = **48 looks**, all descriptive, no trial budget spent.

---

## Marginal IC — the decay measure

**`crs_dist` (live swing ranker, 0094)**

| horizon | marginal IC | 95% band (block bootstrap) | obs IC > 0 | obs |
|---|---|---|---|---|
| 1w | +0.0222 | [+0.0039, +0.0439] | 58.0% | 286 |
| 2w | +0.0327 | [+0.0160, +0.0527] | 61.1% | 285 |
| 4w | +0.0330 | [+0.0167, +0.0539] | 62.2% | 283 |
| 8w | +0.0354 | [+0.0180, +0.0546] | 61.3% | 279 |
| 13w | +0.0364 | [+0.0155, +0.0525] | 63.1% | 274 |
| 26w | +0.0319 | [+0.0110, +0.0491] | 64.8% | 261 |
| 39w * | +0.0180 | [−0.0005, +0.0342] | 60.1% | 248 |
| 52w * | +0.0082 | [−0.0115, +0.0271] | 53.6% | 235 |

Half-life **32.4 weeks**, 95% CI **[11.4, 255.9]**; 89.7% of resamples decayed.

**`sma200_slope_63` (momentum ranker, 0001)**

| horizon | marginal IC | 95% band (block bootstrap) | obs IC > 0 | obs |
|---|---|---|---|---|
| 1w | +0.0412 | [+0.0201, +0.0631] | 61.2% | 286 |
| 2w | +0.0409 | [+0.0195, +0.0627] | 63.5% | 285 |
| 4w | +0.0402 | [+0.0201, +0.0636] | 63.6% | 283 |
| 8w | +0.0405 | [+0.0194, +0.0656] | 63.4% | 279 |
| 13w | +0.0412 | [+0.0158, +0.0631] | 63.5% | 274 |
| 26w | +0.0260 | [+0.0016, +0.0430] | 59.0% | 261 |
| 39w * | +0.0128 | [−0.0087, +0.0310] | 54.4% | 248 |
| 52w * | +0.0085 | [−0.0121, +0.0263] | 51.5% | 235 |

Half-life **21.6 weeks**, 95% CI **[9.0, 71.7]**; 98.9% of resamples decayed.

## Marginal IC on non-overlapping 4-week blocks

Returns measured over the 4-week block ending at *h*, Fridays sampled every 4th week so no two observations share a
return window.

| horizon | `crs_dist` | band | `sma200_slope_63` | band |
|---|---|---|---|---|
| 4w | +0.0424 | [+0.0108, +0.0767] | +0.0614 | [+0.0243, +0.1004] |
| 8w | +0.0462 | [+0.0203, +0.0828] | +0.0589 | [+0.0247, +0.1010] |
| 13w | +0.0550 | [+0.0201, +0.0882] | +0.0639 | [+0.0228, +0.1004] |
| 26w | +0.0525 | [+0.0153, +0.0803] | +0.0378 | [−0.0079, +0.0704] |
| 39w * | +0.0273 | [−0.0102, +0.0574] | +0.0082 | [−0.0313, +0.0407] |
| 52w * | −0.0036 | [−0.0379, +0.0300] | −0.0033 | [−0.0399, +0.0288] |

Half-lives: `crs_dist` **59.0 weeks** [8.4, 232.2], 86.2% of resamples decayed; `sma200_slope_63` **12.4 weeks**
[5.9, 83.1], 96.0%.

## Rule 2 — artifact check

| # | could the result be an artifact? | state |
|---|---|---|
| 1 | **cumulative vs marginal returns** — a growing window inflates IC with *h* | **this is the defect that killed the earlier version.** Ruled out here by construction: the decay statements come only from one-week and non-overlapping-4-week returns. |
| 2 | **overlapping windows / dependent observations** — consecutive weekly ICs share cross-sections and autocorrelated ranks, so an iid band would be far too narrow | **partly ruled out.** Every band is a 13-week moving-block bootstrap, and the 4-week variant removes return-window overlap entirely. Rank autocorrelation remains in both, so the bands are a lower bound on the true width. |
| 3 | **survivorship** | **ruled out.** Membership is point-in-time per Friday; a name that left the index stops being eligible on the date it left, and no name is added retroactively. Delisted names keep contributing until their data ends. |
| 4 | **look-ahead** | **ruled out by construction.** The rank at *t* uses only closes up to *t*; the return window starts at *t+h−1* ≥ *t*. The 200-day SMA slope and the 40-week CRS mean are both backward windows. |
| 5 | **the exponential model itself** — the curve is a **plateau then a fall**, not an exponential | **not ruled out, and it is the main caveat.** Fitting `e^(−λh)` across a flat region plus a drop gives a half-life that describes neither part. The confidence intervals say so: [11, 256] weeks for the swing ranker. The **shape** is the finding; the single half-life number is a weak summary of it. |
| 6 | **single window** — one 2019–2024 history containing one crash and one long trend | **not checked.** No sub-period split was run, and 2020 is inside the sample. |
| 7 | **cross-section composition** — IC is computed over ~498 names, while the book trades 5 | **not checked.** An IC over the whole index says nothing directly about the top-5 slice the book actually buys. |
| 8 | **ranker scale/ties** — Spearman on a near-continuous score | **ruled out as immaterial.** Both scores are continuous; ties are negligible at 498 names. |

## Conclusions — drawn only from marginal IC

1. **Each ranker's per-week information is flat, not decaying, out to about 13 weeks** [measured]. `crs_dist` holds
   +0.022 → +0.036 and `sma200_slope_63` holds +0.041 across 1 to 13 weeks, with bands excluding zero throughout. A
   13-week-old rank says about as much about *next week* as a fresh one does.
2. **Both die between 26 and 52 weeks** [measured]. At 39 and 52 weeks the bands include zero for both rankers on
   both marginal measures, and the non-overlapping 4-week measure is slightly negative at 52.
3. **The half-life is estimable but weak as a summary**: 21.6 weeks [9.0, 71.7] for momentum and 32.4 weeks
   [11.4, 255.9] for the swing ranker on the one-week measure; 12.4 and 59.0 weeks on the non-overlapping measure.
   The two rankers' intervals overlap heavily, so **this sample cannot say that one decays faster than the other**
   [measured]. The plateau-then-fall shape is better evidence than either number.
4. **Momentum's per-week IC is roughly twice the swing ranker's at every horizon inside 13 weeks** (+0.041 vs
   +0.022–0.036) [measured]. Both are measured on the live swing universe, so this compares the two scores on one
   universe, not the two books.

Nothing is proposed and nothing is adopted. Any rule built on this would need its own pre-registration and trial.

## Rule 3 — independent re-derivation

See the `rederivation` block in the JSON and the summary table in the PR: marginal IC at h = 1, 13 and 26 recomputed
by a fresh sub-agent from the written specification alone, with the implementation files withheld.

## Limitations

One window (2019-01-01..2024-06-30), one universe (PIT Nifty-500, median 498 names), so the momentum ranker's IC
*level* here is not its level on its own canonical universe — only the shape is comparable. 39 and 52 weeks were
added after the first look. The exponential fit is a poor model of a plateau-then-fall curve, and the half-life CIs
say so.
