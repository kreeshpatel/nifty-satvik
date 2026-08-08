# 20 BEST positions — study 0001

Cross-sectional momentum, PIT Nifty-500 MID band (turnover rank 101-250), top-30 by NMS, monthly rebalance with a rank-45 buffer, 2017-01 to 2026-06, corrected universe.

> **How to read these.** A POSITION is one (ticker, first-buy-date), not a "trade": the engine
> books 2,951 sell rows but only **926 positions** — 69% of the rows are `rebalance_trim`, partial
> sells that push a winner back to equal weight and book a gain *by construction*.
>
> **`entry` is a WEIGHTED-AVERAGE cost basis, not the day-one price.** `rebalance_book.py:330-335`
> tops up an existing position each month to restore equal weight, so the basis drifts with every
> add. On a falling name it drifts BELOW the first day's open — the book averages down into losers.
> 37.4% of positions show this. It is mandated by equal-weight rebalancing, not a defect, but it
> means you could not have transacted at the `entry` shown on the date shown.
>
> **Why it was bought** is the state at the DECISION bar (the session before the fill): the NSE
> Normalized Momentum Score and its rank among that day's rankable MID-band names. Note that entry
> rank does **not** predict outcome inside the book (Spearman +0.045, p=0.17) — the edge is in being
> selected at all, not in where you rank once selected.


| # | ticker | first buy | final exit | days | ret % | P&L ₹ | sells | why it was bought |
|---|---|---|---|---|---|---|---|---|
| 1 | **ATGL** | 2020-10-01 | 2021-05-03 | 143 | **+152.6** | +85,860 | 14 | NMS 1.74, rank **#24/150** (85th pct). 12m vol-adj mom +0.64 · 6m +2.03 |
| 2 | **PERSISTENT** | 2020-10-01 | 2022-01-03 | 311 | **+146.9** | +83,855 | 9 | NMS 2.12, rank **#12/150** (93th pct). 12m vol-adj mom +1.80 · 6m +1.88 |
| 3 | **LAURUSLABS** | 2020-06-01 | 2020-10-01 | 88 | **+123.5** | +33,149 | 10 | NMS 3.00, rank **#7/150** (95th pct). 12m vol-adj mom +1.02 · 6m +1.40 |
| 4 | **KALYANKJIL** | 2023-08-01 | 2024-10-01 | 286 | **+102.1** | +207,396 | 16 | NMS 1.78, rank **#26/150** (83th pct). 12m vol-adj mom +2.46 · 6m +0.46 |
| 5 | **DIXON** | 2020-01-01 | 2021-04-01 | 312 | **+102.0** | +53,832 | 16 | NMS 2.52, rank **#11/146** (92th pct). 12m vol-adj mom +1.73 · 6m +1.28 |
| 6 | **DEEPAKNTR** | 2020-11-02 | 2021-05-03 | 122 | **+91.5** | +44,314 | 8 | NMS 2.11, rank **#17/150** (89th pct). 12m vol-adj mom +2.52 · 6m +1.08 |
| 7 | **BDL** | 2025-03-03 | 2025-06-02 | 59 | **+82.5** | +114,054 | 6 | NMS 1.79, rank **#30/150** (81th pct). 12m vol-adj mom +0.92 · 6m -0.05 |
| 8 | **GRANULES** | 2020-01-01 | 2020-10-01 | 188 | **+80.1** | +33,374 | 15 | NMS 1.94, rank **#24/146** (84th pct). 12m vol-adj mom +1.21 · 6m +0.85 |
| 9 | **RVNL** | 2023-03-01 | 2023-06-01 | 60 | **+75.2** | +65,262 | 7 | NMS 4.93, rank **#1/150** (100th pct). 12m vol-adj mom +3.13 · 6m +2.72 |
| 10 | **JSWENERGY** | 2021-06-01 | 2022-03-02 | 188 | **+74.0** | +79,854 | 15 | NMS 1.91, rank **#28/150** (82th pct). 12m vol-adj mom +3.65 · 6m +1.58 |
| 11 | **LUPIN** | 2023-09-01 | 2024-09-02 | 243 | **+69.8** | +107,290 | 5 | NMS 2.30, rank **#15/150** (91th pct). 12m vol-adj mom +1.86 · 6m +1.91 |
| 12 | **TATASTLBSL** | 2021-02-01 | 2021-07-01 | 102 | **+69.4** | +48,720 | 10 | NMS 1.87, rank **#28/150** (82th pct). 12m vol-adj mom +0.58 · 6m +1.58 |
| 13 | **DEEPAKNTR** | 2020-01-01 | 2020-10-01 | 188 | **+67.0** | +25,137 | 11 | NMS 1.80, rank **#28/146** (81th pct). 12m vol-adj mom +1.35 · 6m +0.57 |
| 14 | **NCC** | 2023-02-01 | 2024-02-01 | 245 | **+66.9** | +96,456 | 11 | NMS 1.93, rank **#25/150** (84th pct). 12m vol-adj mom +0.65 · 6m +1.30 |
| 15 | **ADANIENSOL** | 2021-02-01 | 2021-09-01 | 144 | **+65.4** | +81,040 | 19 | NMS 1.86, rank **#29/150** (81th pct). 12m vol-adj mom +0.59 · 6m +1.55 |
| 16 | **HUDCO** | 2023-10-03 | 2024-03-01 | 102 | **+63.7** | +107,885 | 9 | NMS 2.22, rank **#17/150** (89th pct). 12m vol-adj mom +2.56 · 6m +1.87 |
| 17 | **JBMA** | 2023-04-03 | 2023-10-03 | 123 | **+62.3** | +68,164 | 7 | NMS 2.19, rank **#23/150** (85th pct). 12m vol-adj mom +0.62 · 6m +1.24 |
| 18 | **MRPL** | 2023-10-03 | 2024-08-01 | 202 | **+61.7** | +117,150 | 7 | NMS 2.00, rank **#24/150** (85th pct). 12m vol-adj mom +1.32 · 6m +2.30 |
| 19 | **KEI** | 2022-07-01 | 2024-03-01 | 412 | **+61.6** | +99,104 | 13 | NMS 2.10, rank **#19/150** (88th pct). 12m vol-adj mom +1.72 · 6m +0.25 |
| 20 | **KPITTECH** | 2021-09-01 | 2022-02-01 | 104 | **+61.3** | +59,108 | 8 | NMS 2.27, rank **#15/150** (91th pct). 12m vol-adj mom +4.17 · 6m +1.98 |
