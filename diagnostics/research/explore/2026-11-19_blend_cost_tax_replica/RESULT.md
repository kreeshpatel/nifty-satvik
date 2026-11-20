# RESULT (independent replica, from SPEC.md only)

Tax days used: ['2019-03-29', '2020-03-31', '2021-03-31', '2022-03-31', '2023-03-31', '2024-03-28']; final session 2024-06-28; calendar days 1942

## A. Anchors

| run | final cash | CAGR % |
|---|---|---|
| after-tax | 5,101,171.32 | 19.26 |
| pre-tax | 6,222,132.32 | 23.80 |
| pre-tax no costs | 6,658,416.86 | 25.38 |

## B. STCG/LTCG split (after-tax run)

| source | bucket | class | count | gain Rs |
|---|---|---|---|---|
| liquid | 0-30 | SL | 430 | 71,645 |
| liquid | 31-90 | SL | 589 | 235,433 |
| passthrough | 0-30 | ST | 389 | 48,163 |
| passthrough | 31-90 | ST | 677 | 343,538 |
| passthrough | 91-180 | ST | 550 | 850,795 |
| passthrough | 181-330 | ST | 302 | 984,666 |
| passthrough | 331-364 | ST | 30 | 154,795 |
| passthrough | 365+ | LT | 65 | 621,046 |
| passthrough | 365+ | ST | 5 | 76,831 |
| terminal | 0-30 | ST | 13 | 3,023 |
| terminal | 31-90 | ST | 21 | 97,141 |
| wrapper | 0-30 | ST | 91 | -80,114 |
| wrapper | 31-90 | ST | 1537 | 166,154 |
| wrapper | 91-180 | ST | 756 | 95,966 |
| wrapper | 181-330 | ST | 208 | 436,680 |

By bucket (all sources):

| bucket | class | count | gain Rs |
|---|---|---|---|
| 0-30 | SL | 430 | 71,645 |
| 0-30 | ST | 493 | -28,928 |
| 31-90 | SL | 589 | 235,433 |
| 31-90 | ST | 2235 | 606,833 |
| 91-180 | ST | 1306 | 946,761 |
| 181-330 | ST | 510 | 1,421,345 |
| 331-364 | ST | 30 | 154,795 |
| 365+ | LT | 65 | 621,046 |
| 365+ | ST | 5 | 76,831 |

Tax per period:

| period | settle date | net ST | net LT | slab | ST tax | LT tax | slab tax | total |
|---|---|---|---|---|---|---|---|---|
| 0 | 2019-03-29 | 8,978 | 0 | 0 | 1,796 | 0 | 0 | 1,796 |
| 1 | 2020-03-31 | -57,598 | 55,541 | 15,739 | 0 | 0 | 4,722 | 4,722 |
| 2 | 2021-03-31 | 1,158,513 | 82,040 | 55,178 | 231,291 | 0 | 16,553 | 247,844 |
| 3 | 2022-03-31 | 220,672 | 286,100 | 67,108 | 44,134 | 20,137 | 20,132 | 84,404 |
| 4 | 2023-03-31 | -243,778 | 120,019 | 81,753 | 0 | 0 | 24,526 | 24,526 |
| 5 | 2024-03-28 | 1,794,585 | 77,347 | 41,977 | 334,165 | 0 | 12,593 | 346,758 |
| 6 | 2024-06-28 | 296,266 | 0 | 45,322 | 59,253 | 0 | 13,597 | 72,850 |

Total tax: 782,900.07

| class | count | gain Rs | tax Rs |
|---|---|---|---|
| ST | 4579 | 3,177,637 | 670,639 |
| LT | 65 | 621,046 | 20,137 |
| SL | 1019 | 307,078 | 92,123 |

331-364 ceiling: 30 exits relabelled (gain 154,795); recomputed baseline tax 782,900.07 (check vs run 782,900.07); relabelled tax 767,671.52; difference -15,228.56

## C. Rebalance cost by trade size (pre-tax run)

n = 3660, total cost = 231,579.84, total turnover = 212,908,971.14

size percentiles (% NAV, numpy linear): p10 0.0481, p50 0.4311, p90 4.1491, p99 17.8531

| size band | n | cost share % | turnover share % |
|---|---|---|---|
| <0.5% | 1937 | 8.51 | 5.63 |
| 0.5-1% | 505 | 8.12 | 5.94 |
| 1-2% | 482 | 13.02 | 11.04 |
| >2% | 736 | 70.36 | 77.39 |

| band | cost of trades below band Rs | n |
|---|---|---|
| 0.5% | 19,696.91 | 1937 |
| 1.0% | 38,492.79 | 2442 |
| 2.0% | 68,634.73 | 2924 |

By instrument: LIQ: n=1036 cost=3,221, MOM: n=1312 cost=158,644, SW: n=1312 cost=69,714

## D. Diagnostic variants (after-tax CAGR)

| variant | after-tax CAGR % | delta pp | total tax Rs |
|---|---|---|---|
| baseline | 19.2561 | +0.0000 | 782,900 |
| 1 pass-through on session after exit | 19.2526 | -0.0034 | 783,130 |
| 2 tax on first session of April | 19.2681 | +0.0120 | 784,268 |
| 3 same-day post-settle gains to current period | 19.2904 | +0.0343 | 784,719 |
| 4 no cost on tax-day trades | 19.2645 | +0.0084 | 783,053 |
| 5 LIFO | 19.6754 | +0.4193 | 727,802 |
| 6 no basis step-up on pass-through | 15.7688 | -3.4873 | 1,303,807 |
| 7 LT threshold >=365 | 19.3156 | +0.0595 | 771,687 |
| 8a lot basis includes buy cost | 19.3869 | +0.1308 | 762,148 |
| 8b basis incl buy cost AND sale gain net of sell cost | 19.5140 | +0.2579 | 741,778 |
| 8c sale gain net of sell cost only | 19.3833 | +0.1272 | 762,627 |
| 8d no tax day on 2019-03-29 (window starts in March 2019) | 19.2721 | +0.0160 | 782,121 |
| 8e combo 8a + 7 (two changes) | 19.4461 | +0.1900 | 750,942 |

**D conclusion.** My after-tax CAGR is 19.26%, the same as the reference to 2 dp. None of the seven listed single
changes moves it by about +0.26pp. Variant 5 (LIFO) gives +0.42 and the rest move it by less than 0.06. Variant 8b,
which charges trading costs in the tax computation (lot basis = price x (1 + buy cost) and sale proceeds = price x
(1 - sell cost)), gives 19.51% (+0.258pp). That reproduces the earlier replica's 19.52%. The component is **costs**,
and specifically whether brokerage and transfer costs count against capital gains. It is one modelling choice with
two legs: 8a (buy leg only) gives +0.13 and 8c (sell leg only) gives +0.13. The spec's formula "units x (price - lot
basis)" with "cost per unit" can be read either way. This is an inference from matching the earlier replica's
number; I did not see its code.

## Ambiguities and how I resolved them
1. Lot "cost per unit": I took the purchase price, excluding the buy cost, and sale gain = gross price - basis.
   The other reading is variant 8b (+0.26pp). This is the largest open ambiguity.
2. Tax day 2019-03-29: the window starts on 2019-03-05, and that date is the last session on or before 31 March
   2019. Read literally, it is a tax day, so I settled it (variant 8d skips it: +0.016pp).
3. Cash residual: units = target / price, and costs come out of cash, so cash ends slightly negative after a buy.
   I did not gross targets up for costs.
4. Pass-through when u = 0: no gain event and no count. The basis step-up still applies to (zero) lots.
5. Pass-through class and bucket: the trade's own (exit - entry) days, not the time the sleeve units were held.
6. Buckets use holding days; class uses > 365. A 365-day exit therefore falls in bucket "365+" but is short-term
   (5 pass-through exits).
7. Slab losses: max(SL, 0), with no carry-forward and no set-off against ST or LT.
8. The 1,25,000 LT exemption and the 20% / 12.5% rates apply to every period, as written. The spec does not
   switch rates before 23 July 2024.
9. Settling on a tax day: pass-through gains that day belong to the current period. Re-target sales that day
   belong to the next period.
10. Trade threshold: I trade any amount with |diff| > 1e-9 rupees. There is no tolerance band.
11. Part C: size uses the NAV after that day's tax is paid (pre-tax run, so tax is always 0 anyway). Bands are
    [0, 0.5%), [0.5%, 1%), [1%, 2%] and > 2%. Percentiles use numpy linear interpolation. The first session (i = 0)
    is excluded entirely. The terminal liquidation is excluded. Re-target trades on the final session are included.
12. Momentum or swing exits dated before the first session map to session 0, where u = 0, so they have no effect.
