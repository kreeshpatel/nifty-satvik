# 2026-11-17 — Institutional positioning (FII / DII) against the book's trades

**Tier:** EXPLORE, descriptive. Dataset A only — entries 2019-01-01..2024-06-30, prices cut at 2024-06-30 and the cut asserted. No trial, no screen row, **no sealed read**, nothing live changed. Standing counts unchanged. It adopts nothing: any rule out of it needs its own pre-registration and its own trial.

## The instrument is not the one the backlog spec assumed

The spec asked for NSE's daily FII/DII **cash** net buy/sell figures. Those are not retrievable as history: the NSE endpoint serves the current day and ignores a date parameter, and both archive filename patterns 404 for past dates. What is retrievable, as a dated daily archive with its own publication date, is the **participant-wise open-interest** file — institutional **positioning** in index futures, stock futures and options, not cash flows. It is point-in-time and honest, and it answers a different question. Every table below is about positioning.

Coverage: **1355 sessions**, 2019-01-01 to 2024-06-28; **525 trades** in A, 467 of them with a reading at the signal Friday (the rest are before the 126-session minimum for a z-score).

## Mean R per closed trade by positioning z-bucket, at the signal Friday

**fii_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 122 | 101 | 0.36 | 139.20 | 30.30 | 48.50 | 41.60 |
| -1..0 | 128 | 101 | 0.55 | 165.00 | 32.80 | 50.50 | 37.60 |
| 0..+1 | 158 | 131 | 1.13 | 283.20 | 40.50 | 35.90 | 46.60 |
| z>+1 | 59 | 50 | 0.71 | 64.00 | 32.20 | 48.00 | 50.00 |

**fii_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 82 | 63 | 0.54 | 123.50 | 30.50 | 50.80 | 39.70 |
| -1..0 | 140 | 116 | 0.58 | 158.40 | 36.40 | 45.70 | 44.00 |
| 0..+1 | 158 | 130 | 1.09 | 282.60 | 37.30 | 43.10 | 43.10 |
| z>+1 | 80 | 67 | 0.63 | 97.00 | 33.80 | 37.30 | 49.30 |

**dii_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 111 | 96 | 0.80 | 107.00 | 33.30 | 46.90 | 40.60 |
| -1..0 | 128 | 104 | 0.25 | 130.90 | 30.50 | 50.00 | 37.50 |
| 0..+1 | 129 | 101 | 0.69 | 199.40 | 38.80 | 46.50 | 43.60 |
| z>+1 | 99 | 82 | 1.26 | 214.00 | 36.40 | 32.90 | 53.70 |

**dii_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 69 | 55 | 0.74 | 91.10 | 37.70 | 41.80 | 36.40 |
| -1..0 | 147 | 125 | 0.98 | 239.90 | 41.50 | 40.00 | 48.80 |
| 0..+1 | 146 | 114 | 0.28 | 180.20 | 29.50 | 47.40 | 38.60 |
| z>+1 | 98 | 82 | 1.09 | 150.30 | 32.70 | 47.60 | 48.80 |

**fii_stk_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 89 | 76 | 0.54 | 111.90 | 32.60 | 55.30 | 38.20 |
| -1..0 | 128 | 100 | 0.20 | 185.00 | 39.80 | 45.00 | 43.00 |
| 0..+1 | 97 | 79 | 0.79 | 122.20 | 33.00 | 46.80 | 40.50 |
| z>+1 | 153 | 128 | 1.18 | 232.20 | 32.70 | 36.70 | 48.40 |

**fii_stk_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 84 | 75 | 0.60 | 83.30 | 35.70 | 53.30 | 41.30 |
| -1..0 | 123 | 93 | 0.85 | 204.60 | 35.80 | 43.00 | 41.90 |
| 0..+1 | 144 | 111 | 0.70 | 249.10 | 40.30 | 41.40 | 48.60 |
| z>+1 | 109 | 97 | 0.86 | 124.50 | 27.50 | 41.20 | 42.30 |

**combined_idx_net** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 132 | 107 | 0.19 | 137.70 | 28.80 | 49.50 | 36.40 |
| -1..0 | 134 | 113 | 0.82 | 156.40 | 35.10 | 46.00 | 43.40 |
| 0..+1 | 136 | 119 | 0.99 | 202.40 | 33.80 | 42.90 | 46.20 |
| z>+1 | 65 | 44 | 1.03 | 154.80 | 47.70 | 34.10 | 52.30 |

**combined_idx_net_chg20** — z over the trailing 252 sessions

| z bucket | trades | closed | mean R | total R | runner % | stop-out % | win % |
|---|---|---|---|---|---|---|---|
| z<-1 | 84 | 64 | 0.05 | 97.90 | 34.50 | 46.90 | 40.60 |
| -1..0 | 148 | 123 | 1.02 | 222.60 | 35.10 | 47.20 | 44.70 |
| 0..+1 | 137 | 111 | 0.68 | 203.90 | 35.00 | 42.30 | 40.50 |
| z>+1 | 91 | 78 | 1.05 | 137.10 | 36.30 | 39.70 | 50.00 |

## The headline feature crossed with the regime state

`fii_idx_net` (FII index-futures long minus short) against the three regime dimensions from the 2026-11 loss diagnosis. The weak-but-calm state is `above` / `<15` / `>60%`.

**nifty_vs_40w** (cells with fewer than 5 trades are dropped)

| nifty_vs_40w | z bucket | trades | mean R | total R | stop-out % |
|---|---|---|---|---|---|
| above | z<-1 | 65 | -0.47 | 36.70 | 59.20 |
| above | -1..0 | 109 | 0.17 | 123.00 | 56.10 |
| above | 0..+1 | 123 | 0.56 | 181.60 | 41.20 |
| above | z>+1 | 53 | 0.39 | 45.80 | 54.50 |
| below | z<-1 | 57 | 1.14 | 102.50 | 38.50 |
| below | -1..0 | 19 | 2.21 | 41.90 | 26.30 |
| below | 0..+1 | 35 | 2.75 | 101.50 | 20.60 |
| below | z>+1 | 6 | 3.04 | 18.20 | 0.00 |

**vix_bucket** (cells with fewer than 5 trades are dropped)

| vix_bucket | z bucket | trades | mean R | total R | stop-out % |
|---|---|---|---|---|---|
| 15-20 | z<-1 | 46 | 0.57 | 42.00 | 54.50 |
| 15-20 | -1..0 | 61 | 0.21 | 34.70 | 50.00 |
| 15-20 | 0..+1 | 26 | 0.73 | 29.10 | 44.00 |
| 15-20 | z>+1 | 12 | -0.49 | -5.80 | 66.70 |
| <15 | z<-1 | 42 | 0.23 | 63.30 | 48.30 |
| <15 | -1..0 | 53 | -0.24 | 78.00 | 60.60 |
| <15 | 0..+1 | 71 | -0.40 | 95.80 | 43.80 |
| <15 | z>+1 | 30 | 0.01 | 28.90 | 57.10 |
| >20 | z<-1 | 34 | 0.15 | 33.90 | 39.30 |
| >20 | -1..0 | 14 | 3.73 | 52.20 | 28.60 |
| >20 | 0..+1 | 61 | 2.56 | 158.30 | 25.90 |
| >20 | z>+1 | 17 | 2.41 | 40.90 | 23.50 |

**breadth_bucket** (cells with fewer than 5 trades are dropped)

| breadth_bucket | z bucket | trades | mean R | total R | stop-out % |
|---|---|---|---|---|---|
| 40-60% | z<-1 | 30 | -0.32 | 6.80 | 59.30 |
| 40-60% | -1..0 | 17 | -1.32 | 34.50 | 80.00 |
| 40-60% | 0..+1 | 32 | 1.38 | 61.70 | 33.30 |
| 40-60% | z>+1 | 5 | 1.53 | 7.60 | 20.00 |
| <40% | z<-1 | 31 | 0.56 | 52.90 | 40.70 |
| <40% | -1..0 | 12 | 3.48 | 41.70 | 33.30 |
| <40% | 0..+1 | 28 | 3.04 | 90.20 | 22.20 |
| >60% | z<-1 | 43 | -0.58 | 32.90 | 58.60 |
| >60% | -1..0 | 71 | 0.16 | 69.60 | 51.00 |
| >60% | 0..+1 | 80 | 0.82 | 152.80 | 39.30 |
| >60% | z>+1 | 51 | 0.38 | 44.70 | 54.80 |

## By year, so one episode is visible

| year | z bucket | trades | mean R | total R |
|---|---|---|---|---|
| 2019 | z<-1 | 18 | 2.59 | 46.60 |
| 2019 | -1..0 | 28 | 0.68 | 19.00 |
| 2019 | 0..+1 | 12 | -1.32 | -15.90 |
| 2020 | z<-1 | 11 | -1.95 | -21.40 |
| 2020 | -1..0 | 8 | 5.30 | 42.40 |
| 2020 | 0..+1 | 52 | 2.46 | 127.70 |
| 2020 | z>+1 | 24 | 1.64 | 39.50 |
| 2021 | z<-1 | 7 | 0.00 | 0.00 |
| 2021 | -1..0 | 24 | 0.80 | 19.20 |
| 2021 | 0..+1 | 27 | 0.24 | 6.50 |
| 2022 | z<-1 | 45 | 0.09 | 46.80 |
| 2022 | -1..0 | 16 | -0.81 | -13.00 |
| 2022 | 0..+1 | 24 | 1.21 | 45.60 |
| 2022 | z>+1 | 11 | -0.72 | -7.90 |
| 2023 | z<-1 | 30 | 0.48 | 55.00 |
| 2023 | -1..0 | 28 | -0.15 | 80.60 |
| 2023 | 0..+1 | 33 | 0.40 | 112.80 |
| 2023 | z>+1 | 19 | 0.42 | 29.00 |
| 2024 | z<-1 | 11 | -1.07 | 12.10 |
| 2024 | -1..0 | 24 | -0.94 | 16.70 |
| 2024 | 0..+1 | 10 | -1.10 | 6.40 |

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


## What this says

**Nothing here separates a good entry week from a bad one.** Four readings, three things to look at:

1. **No monotone relation in any of the eight features.** The best-looking one, `fii_idx_net`, runs 0.36 → 0.55 →
   **1.13** → 0.71 mean R across the four z-buckets: the top bucket is worse than the one below it, which is the shape
   of noise, not of a gauge. `dii_idx_net` runs 0.80 → 0.25 → 0.69 → 1.26, which is not even ordered.
2. **The positioning *levels* are mostly the trend we already measure.** `fii_idx_net` correlates +0.51 with the
   Nifty's 13-week return and +0.34 with midcap breadth; `dii_idx_net` runs the other way at −0.67 and −0.54 (domestic
   desks are structurally short index futures as a hedge, and they hedge more after a rally). So the level is a
   re-encoding of trend state, and the book already conditions on trend. The *changes* (`*_chg20`) are genuinely
   near-orthogonal to everything we hold — |ρ| ≤ 0.33, mostly ≈ 0.0 — and they carry **no** separation either
   (0.54 / 0.58 / 1.10 / 0.63). An orthogonal variable that sees nothing is the cleanest possible null.
3. **The signs flip by year.** 2019's best bucket (z < −1, +2.59R) is 2020's worst (−1.95R); 2022 and 2024 are
   negative almost everywhere. Any bucket ranking out of the pooled table is one or two episodes.

**On the weak-but-calm state specifically**, which is why this was worth a look: inside VIX < 15 the mean R is
**negative in two of the four positioning buckets** and never above +0.23, and inside breadth > 60% the ordering
breaks at the top bucket (0.82 then 0.38). Positioning does not rescue the state the live losses came from. What the
cross-tab does show again, loudly, is the thing already on the record: the book earns its R with the Nifty **below**
its 40-week line (mean R 1.14 to 3.04 across buckets) and struggles above it (−0.47 to +0.56), and with VIX **above**
20 rather than below 15. That is the loss diagnosis, not a new finding.

**Verdict: descriptive null.** No rule is proposed and nothing is adopted. Consistent with 0134 (nine trailing
market-state variables, none cleared all three bars) with the same caveat: a null here means "not demonstrable on
this sample", not "absent". The one thing worth keeping is the data itself — the archive now spans 1,336 sessions of
participant positioning, which costs nothing to extend and would be re-read only if a *mechanism* argued for it, not
a fresh bucket search.

**The cheapest test that would change this answer**, if one is ever wanted: not another bucket, but the one place
positioning is supposed to matter — the distribution of *stop-outs within the first two weeks* conditioned on a sharp
FII index-futures unwind in the same week. That is a mechanism (positioning unwind → gap risk) rather than a sweep,
and it reuses this same archive at no multiplicity cost.
