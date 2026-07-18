# The `<0%` bucket — the last unexplored structure, CLOSED (measurement, no trial)

**Run 2026-07-16.** The final open thread: entries filled BELOW the signal-week 44w SMA showed the
largest, most OOS-persistent effect in the dataset (train +1.91R / holdout +2.70R). Investigated and
closed. Live config untouched.

## What these trades are

The touch signal requires the week to CLOSE above the SMA — so a fill *below* it means the **entry week
gapped/traded down through the SMA** and the fill landed near the bottom of the entry window. Since the
stop is the signal-week low, `entry ≈ stop` → risk → 0 → the R-multiple explodes.

## Partly an artifact — but not entirely

| risk% band | N | meanR | implied notional / equity @2% risk |
|---|---|---|---|
| **<2% (untradeable)** | 6 | 5.91 | **2.37x the whole book in ONE position** |
| 2-4% | 9 | 2.61 | 0.69x |
| 4-8% | 11 | 1.43 | 0.34x |
| >8% | 9 | 1.15 | 0.21x |

- Full bucket: N=35, meanR **2.43**. The 6 sub-2%-stop trades (incl. INOXINDIA **28.5R on a 0.606%
  stop**) are sizing artifacts — at 2% risk they demand 2.37x equity in one name.
- **Cleaned (risk >= 2%): N=29, meanR 1.71 — still 4.6x the rest of the pool (0.37).** So a real
  effect survives the artifact removal.

## Why it is nevertheless unusable — four independent reasons

1. **Recency concentration:** **46% of the bucket is 2026** — a *partial* year that is only **11%** of the
   touch pool (a 4x over-representation) — and 2026 carries the highest meanR (+3.71).
2. **Unresolved trades:** 3 of the 2026 entries exit on `eos` (marked-to-market at the sample end, not a
   realized outcome), inflating the recent number.
3. **Ex-2026 it is a coin flip:** per-year meanR 2019 −1.11 · 2020 +2.93 · 2022 +1.75 · 2023 −0.10 ·
   2025 +0.76.
4. **It cannot be manufactured.** The fill requires price to gap down through the SMA in the entry week —
   that happens *to* you; it is not a lever. Limit-order manufacture was already REJECTED (Phase-1 E1).

## And the exploiting mechanism is already measured — it fails

Allocating toward this bucket **is** the H2 bucket-prior variant (`CRS_DISSECTED.md` §5): it ranks
`<0%`/`0-5%` first and scored **22-26 = 0.84 with MaxDD −61.7%** against the baseline's 1.29 / −34.8%.
CRS itself picks only **1 of these 35** (0.6% of its fills) — and that abstention is correct.

## Verdict

**CLOSED — dead end, as expected but now on evidence.** The effect is small-N, artifact-inflated,
recency-concentrated, partly unresolved, unmanufacturable, and the one mechanism that would harvest it is
already known to be catastrophic. **No further work.** This was the last unexplored structure in the swing
book; every avenue is now closed.
