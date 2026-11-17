# 2026-11-17 — Institutional positioning (FII / DII) against the book's trades

**Tier:** EXPLORE, descriptive. Dataset A only — entries 2019-01-01..2024-06-30, prices cut at 2024-06-30 and the cut asserted. No trial, no screen row, **no sealed read**, nothing live changed. Standing counts unchanged. It adopts nothing: any rule out of it needs its own pre-registration and its own trial.

## The instrument is not the one the backlog spec assumed

The spec asked for NSE's daily FII/DII **cash** net buy/sell figures. Those are not retrievable as history: the NSE endpoint serves the current day and ignores a date parameter, and both archive filename patterns 404 for past dates. What is retrievable, as a dated daily archive with its own publication date, is the **participant-wise open-interest** file — institutional **positioning** in index futures, stock futures and options, not cash flows. It is point-in-time and honest, and it answers a different question. Every table below is about positioning.

Coverage: **1355 sessions**, 2019-01-01 to 2024-06-28; **525 trades** in A, 467 of them with a reading at the signal Friday (the rest are before the 126-session minimum for a z-score).

## Mean R per closed trade by positioning z-bucket, at the signal Friday

**fii_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 122 | 101 | 0.36 | [-0.36, +1.47] | 52 | 139.20 | 48.50 | 41.60 |
| -1..0 | 128 | 101 | 0.55 | [-0.19, +1.62] | 52 | 165.00 | 50.50 | 37.60 |
| 0..+1 | 158 | 131 | 1.13 | [+0.39, +1.93] | 66 | 283.20 | 35.90 | 46.60 |
| z>+1 | 59 | 50 | 0.71 | [-0.06, +1.44] | 23 | 64.00 | 48.00 | 50.00 |

**fii_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 82 | 63 | 0.54 | [-0.43, +2.19] | 35 | 123.50 | 50.80 | 39.70 |
| -1..0 | 140 | 116 | 0.58 | [-0.08, +1.36] | 61 | 158.40 | 45.70 | 44.00 |
| 0..+1 | 158 | 130 | 1.09 | [+0.35, +1.88] | 63 | 282.60 | 43.10 | 43.10 |
| z>+1 | 80 | 67 | 0.63 | [-0.09, +1.57] | 30 | 97.00 | 37.30 | 49.30 |

**dii_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 111 | 96 | 0.80 | [+0.06, +1.62] | 50 | 107.00 | 46.90 | 40.60 |
| -1..0 | 128 | 104 | 0.25 | [-0.30, +0.82] | 55 | 130.90 | 50.00 | 37.50 |
| 0..+1 | 129 | 101 | 0.69 | [-0.06, +1.56] | 49 | 199.40 | 46.50 | 43.60 |
| z>+1 | 99 | 82 | 1.26 | [+0.17, +2.86] | 39 | 214.00 | 32.90 | 53.70 |

**dii_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 69 | 55 | 0.74 | [-0.13, +1.84] | 28 | 91.10 | 41.80 | 36.40 |
| -1..0 | 147 | 125 | 0.98 | [+0.34, +1.63] | 61 | 239.90 | 40.00 | 48.80 |
| 0..+1 | 146 | 114 | 0.28 | [-0.32, +1.06] | 60 | 180.20 | 47.40 | 38.60 |
| z>+1 | 98 | 82 | 1.09 | [-0.04, +2.70] | 40 | 150.30 | 47.60 | 48.80 |

**fii_stk_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 89 | 76 | 0.54 | [-0.24, +1.55] | 43 | 111.90 | 55.30 | 38.20 |
| -1..0 | 128 | 100 | 0.20 | [-0.21, +0.64] | 54 | 185.00 | 45.00 | 43.00 |
| 0..+1 | 97 | 79 | 0.79 | [-0.20, +2.20] | 37 | 122.20 | 46.80 | 40.50 |
| z>+1 | 153 | 128 | 1.18 | [+0.38, +2.05] | 59 | 232.20 | 36.70 | 48.40 |

**fii_stk_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 84 | 75 | 0.60 | [-0.08, +1.29] | 38 | 83.30 | 53.30 | 41.30 |
| -1..0 | 123 | 93 | 0.85 | [+0.03, +1.85] | 50 | 204.60 | 43.00 | 41.90 |
| 0..+1 | 144 | 111 | 0.70 | [+0.01, +1.63] | 56 | 249.10 | 41.40 | 48.60 |
| z>+1 | 109 | 97 | 0.86 | [+0.04, +1.93] | 45 | 124.50 | 41.20 | 42.30 |

**combined_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 132 | 107 | 0.19 | [-0.50, +1.22] | 57 | 137.70 | 49.50 | 36.40 |
| -1..0 | 134 | 113 | 0.82 | [+0.10, +1.69] | 57 | 156.40 | 46.00 | 43.40 |
| 0..+1 | 136 | 119 | 0.99 | [+0.23, +1.94] | 56 | 202.40 | 42.90 | 46.20 |
| z>+1 | 65 | 44 | 1.03 | [+0.15, +2.17] | 23 | 154.80 | 34.10 | 52.30 |

**combined_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | 95% CI (clustered on entry week) | weeks | total R | stop-out % | win % |
|---|---|---|---|---|---|---|---|---|
| z<-1 | 84 | 64 | 0.05 | [-0.37, +0.49] | 36 | 97.90 | 46.90 | 40.60 |
| -1..0 | 148 | 123 | 1.02 | [+0.17, +2.03] | 63 | 222.60 | 47.20 | 44.70 |
| 0..+1 | 137 | 111 | 0.68 | [+0.03, +1.33] | 54 | 203.90 | 42.30 | 40.50 |
| z>+1 | 91 | 78 | 1.05 | [+0.07, +2.28] | 36 | 137.10 | 39.70 | 50.00 |

## The headline feature crossed with the regime state

`fii_idx_net` (FII index-futures long minus short) against the three regime dimensions from the 2026-11 loss diagnosis. The weak-but-calm state is `above` / `<15` / `>60%`.

**nifty_vs_40w** (cells with fewer than 5 trades are dropped)

| nifty_vs_40w | z bucket | trades | mean R | 95% CI (clustered) | weeks | total R | stop-out % |
|---|---|---|---|---|---|---|---|
| above | z<-1 | 65 | -0.47 | [-0.90, -0.00] | 29 | 36.70 | 59.20 |
| above | -1..0 | 109 | 0.17 | [-0.40, +0.93] | 43 | 123.00 | 56.10 |
| above | 0..+1 | 123 | 0.56 | [-0.20, +1.48] | 53 | 181.60 | 41.20 |
| above | z>+1 | 53 | 0.39 | [-0.26, +1.06] | 21 | 45.80 | 54.50 |
| below | z<-1 | 57 | 1.14 | [-0.13, +3.44] | 23 | 102.50 | 38.50 |
| below | -1..0 | 19 | 2.21 | [-0.26, +6.13] | 9 | 41.90 | 26.30 |
| below | 0..+1 | 35 | 2.75 | [+1.44, +3.88] | 13 | 101.50 | 20.60 |
| below | z>+1 | 6 | 3.04 | [+2.16, +3.91] | 2 | 18.20 | 0.00 |

**vix_bucket** (cells with fewer than 5 trades are dropped)

| vix_bucket | z bucket | trades | mean R | 95% CI (clustered) | weeks | total R | stop-out % |
|---|---|---|---|---|---|---|---|
| 15-20 | z<-1 | 46 | 0.57 | [-0.72, +3.11] | 23 | 42.00 | 54.50 |
| 15-20 | -1..0 | 61 | 0.21 | [-0.51, +1.16] | 27 | 34.70 | 50.00 |
| 15-20 | 0..+1 | 26 | 0.73 | [-0.41, +2.56] | 14 | 29.10 | 44.00 |
| 15-20 | z>+1 | 12 | -0.49 | [-1.11, +0.45] | 6 | -5.80 | 66.70 |
| <15 | z<-1 | 42 | 0.23 | [-0.42, +0.93] | 17 | 63.30 | 48.30 |
| <15 | -1..0 | 53 | -0.24 | [-0.80, +0.25] | 18 | 78.00 | 60.60 |
| <15 | 0..+1 | 71 | -0.40 | [-0.86, +0.14] | 27 | 95.80 | 43.80 |
| <15 | z>+1 | 30 | 0.01 | [-0.70, +0.63] | 11 | 28.90 | 57.10 |
| >20 | z<-1 | 34 | 0.15 | [-0.82, +1.36] | 12 | 33.90 | 39.30 |
| >20 | -1..0 | 14 | 3.73 | [+0.07, +7.98] | 7 | 52.20 | 28.60 |
| >20 | 0..+1 | 61 | 2.56 | [+1.34, +3.77] | 25 | 158.30 | 25.90 |
| >20 | z>+1 | 17 | 2.41 | [+1.35, +3.37] | 6 | 40.90 | 23.50 |

**breadth_bucket** (cells with fewer than 5 trades are dropped)

| breadth_bucket | z bucket | trades | mean R | 95% CI (clustered) | weeks | total R | stop-out % |
|---|---|---|---|---|---|---|---|
| 40-60% | z<-1 | 30 | -0.32 | [-1.05, +0.45] | 15 | 6.80 | 59.30 |
| 40-60% | -1..0 | 17 | -1.32 | [-1.73, -0.98] | 7 | 34.50 | 80.00 |
| 40-60% | 0..+1 | 32 | 1.38 | [+0.16, +3.03] | 15 | 61.70 | 33.30 |
| 40-60% | z>+1 | 5 | 1.53 | [+0.57, +2.16] | 2 | 7.60 | 20.00 |
| <40% | z<-1 | 31 | 0.56 | [-0.40, +1.87] | 12 | 52.90 | 40.70 |
| <40% | -1..0 | 12 | 3.48 | [-0.39, +8.95] | 5 | 41.70 | 33.30 |
| <40% | 0..+1 | 28 | 3.04 | [+1.40, +4.58] | 10 | 90.20 | 22.20 |
| >60% | z<-1 | 43 | -0.58 | [-1.12, -0.01] | 17 | 32.90 | 58.60 |
| >60% | -1..0 | 71 | 0.16 | [-0.38, +0.77] | 28 | 69.60 | 51.00 |
| >60% | 0..+1 | 80 | 0.82 | [-0.19, +2.01] | 33 | 152.80 | 39.30 |
| >60% | z>+1 | 51 | 0.38 | [-0.31, +1.15] | 20 | 44.70 | 54.80 |

## By year, so one episode is visible

| year | z bucket | trades | mean R | 95% CI (clustered) | total R |
|---|---|---|---|---|---|
| 2019 | z<-1 | 18 | 2.59 | [-0.24, +9.46] | 46.60 |
| 2019 | -1..0 | 28 | 0.68 | [-0.53, +2.38] | 19.00 |
| 2019 | 0..+1 | 12 | -1.32 | [-2.02, -0.49] | -15.90 |
| 2020 | z<-1 | 11 | -1.95 | [-2.26, -1.60] | -21.40 |
| 2020 | -1..0 | 8 | 5.30 | [-0.52, +10.93] | 42.40 |
| 2020 | 0..+1 | 52 | 2.46 | [+1.19, +3.77] | 127.70 |
| 2020 | z>+1 | 24 | 1.64 | [+0.51, +2.69] | 39.50 |
| 2021 | z<-1 | 7 | 0.00 | [-1.53, +1.15] | 0.00 |
| 2021 | -1..0 | 24 | 0.80 | [-0.12, +1.98] | 19.20 |
| 2021 | 0..+1 | 27 | 0.24 | [-0.50, +1.08] | 6.50 |
| 2022 | z<-1 | 45 | 0.09 | [-0.44, +0.85] | 46.80 |
| 2022 | -1..0 | 16 | -0.81 | [-1.48, -0.19] | -13.00 |
| 2022 | 0..+1 | 24 | 1.21 | [-0.28, +3.46] | 45.60 |
| 2022 | z>+1 | 11 | -0.72 | [-1.52, -0.21] | -7.90 |
| 2023 | z<-1 | 30 | 0.48 | [-0.27, +1.34] | 55.00 |
| 2023 | -1..0 | 28 | -0.15 | [-0.80, +0.35] | 80.60 |
| 2023 | 0..+1 | 33 | 0.40 | [-0.30, +1.09] | 112.80 |
| 2023 | z>+1 | 19 | 0.42 | [-0.38, +1.30] | 29.00 |
| 2024 | z<-1 | 11 | -1.07 | [-1.07, -1.06] | 12.10 |
| 2024 | -1..0 | 24 | -0.94 | [-1.08, -0.79] | 16.70 |
| 2024 | 0..+1 | 10 | -1.10 | [-1.16, -1.00] | 6.40 |

## Is this the same information we already have?

Spearman correlation, weekly at the signal Friday, 232 weeks.

| feature | vs VIX | vs midcap breadth | vs Nifty 13w return | vs above 40w SMA |
|---|---|---|---|---|
| fii_idx_net | -0.07 | 0.34 | 0.51 | 0.28 |
| fii_idx_net_chg20 | -0.02 | -0.05 | 0.02 | -0.04 |
| dii_idx_net | -0.06 | -0.54 | -0.67 | -0.38 |
| dii_idx_net_chg20 | 0.13 | -0.09 | -0.33 | -0.11 |
| fii_stk_net | 0.17 | -0.39 | -0.37 | -0.43 |
| fii_stk_net_chg20 | -0.03 | 0.00 | -0.26 | -0.12 |
| combined_idx_net | -0.14 | 0.07 | 0.20 | 0.10 |
| combined_idx_net_chg20 | -0.00 | -0.06 | -0.06 | -0.06 |


## Added 2026-11-17 — clustered intervals, and what they change

The first version of this report gave bucket means with **no interval at all**, which the artifact audit flagged:
trades entered in the same week share a market, a regime state and one flow reading, so they are not independent
observations. Every mean R above now carries a **95% interval from a cluster bootstrap that resamples whole entry
weeks** (`nq.lab.stats.cluster_bootstrap_mean`, 2,000 draws, seed 20261117; tests in
`tests/test_cluster_bootstrap_mean.py`). The `weeks` column is the honest sample size.

Two things this changes:

1. **The real sample is weeks, not trades.** The headline `fii_idx_net` buckets hold 122 / 128 / 158 / 59 trades —
   but only **52 / 52 / 66 / 23 entry weeks**. The top bucket rests on 23 weeks.
2. **Half the buckets cannot be told from zero, and the "best" bucket's advantage cannot be told from the others.**
   Of 32 bucket cells across the eight features, **15 have an interval excluding zero**. For `fii_idx_net`, the
   apparently strong `0..+1` cell is +1.13 [+0.39, +1.93] while the cell below it is +0.55 [−0.19, +1.62] — the
   intervals overlap across most of their range, so the ordering between buckets is not established by this sample.

**The null verdict is unchanged and better supported.** Nothing here orders the buckets, the earlier observation
that the shape is non-monotone now has an interval behind it, and nothing is adopted.
