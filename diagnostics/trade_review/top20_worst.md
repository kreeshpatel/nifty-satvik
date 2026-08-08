# 20 WORST positions — study 0001

Note these are AFTER averaging down — the loss on the original entry price was larger still.

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
| 1 | **WELCORP** | 2020-03-02 | 2020-05-04 | 39 | **-53.5** | -27,256 | 1 | NMS 1.95, rank **#27/150** (83th pct). 12m vol-adj mom +2.12 · 6m +1.26 |
| 2 | **AUBANK** | 2020-03-02 | 2020-05-04 | 39 | **-37.9** | -17,301 | 3 | NMS 2.39, rank **#15/150** (90th pct). 12m vol-adj mom +2.51 · 6m +1.66 |
| 3 | **KEC** | 2025-01-01 | 2025-03-03 | 43 | **-37.0** | -91,572 | 2 | NMS 1.72, rank **#24/150** (85th pct). 12m vol-adj mom +1.85 · 6m +0.48 |
| 4 | **INOXLEISUR** | 2020-03-02 | 2020-05-04 | 39 | **-36.5** | -17,833 | 3 | NMS 2.00, rank **#26/150** (83th pct). 12m vol-adj mom +1.58 · 6m +1.65 |
| 5 | **BOMDYEING** | 2018-08-01 | 2018-10-01 | 39 | **-35.0** | -13,364 | 1 | NMS 2.03, rank **#14/150** (91th pct). 12m vol-adj mom +2.57 · 6m -0.15 |
| 6 | **NATCOPHARM** | 2024-10-01 | 2025-03-03 | 105 | **-34.6** | -86,478 | 3 | NMS 2.33, rank **#10/150** (93th pct). 12m vol-adj mom +2.38 · 6m +1.85 |
| 7 | **AVANTIFEED** | 2020-01-01 | 2020-04-01 | 63 | **-33.5** | -17,944 | 5 | NMS 1.81, rank **#27/146** (82th pct). 12m vol-adj mom +0.73 · 6m +1.02 |
| 8 | **APARINDS** | 2025-01-01 | 2025-03-03 | 43 | **-32.2** | -78,242 | 3 | NMS 1.91, rank **#20/150** (87th pct). 12m vol-adj mom +2.24 · 6m +0.50 |
| 9 | **EDELWEISS** | 2018-07-02 | 2018-10-01 | 61 | **-31.7** | -12,366 | 1 | NMS 1.74, rank **#19/150** (88th pct). 12m vol-adj mom +1.86 · 6m +0.33 |
| 10 | **ADANIENSOL** | 2020-01-01 | 2020-04-01 | 63 | **-31.0** | -14,685 | 5 | NMS 2.01, rank **#21/146** (86th pct). 12m vol-adj mom +1.11 · 6m +1.02 |
| 11 | **OFSS** | 2024-12-02 | 2025-03-03 | 64 | **-30.9** | -62,314 | 2 | NMS 2.76, rank **#7/150** (96th pct). 12m vol-adj mom +3.71 · 6m +0.99 |
| 12 | **TAKE** | 2018-07-02 | 2018-10-01 | 61 | **-30.0** | -10,535 | 1 | NMS 2.17, rank **#7/150** (95th pct). 12m vol-adj mom +1.39 · 6m +1.10 |
| 13 | **VTL** | 2022-02-01 | 2022-07-01 | 103 | **-29.8** | -40,768 | 5 | NMS 1.50, rank **#20/150** (87th pct). 12m vol-adj mom +3.00 · 6m +0.61 |
| 14 | **FACT** | 2023-02-01 | 2023-04-03 | 41 | **-28.9** | -30,490 | 1 | NMS 4.83, rank **#1/150** (100th pct). 12m vol-adj mom +2.44 · 6m +3.94 |
| 15 | **TTML** | 2022-01-03 | 2022-03-02 | 40 | **-28.5** | -44,402 | 5 | NMS 7.17, rank **#2/150** (99th pct). 12m vol-adj mom +24.30 · 6m +2.82 |
| 16 | **PCBL** | 2024-10-01 | 2025-03-03 | 105 | **-27.7** | -72,526 | 4 | NMS 3.09, rank **#2/150** (99th pct). 12m vol-adj mom +4.23 · 6m +1.84 |
| 17 | **ZENTEC** | 2025-01-01 | 2025-04-01 | 62 | **-26.9** | -76,279 | 4 | NMS 3.13, rank **#4/150** (98th pct). 12m vol-adj mom +3.41 · 6m +1.33 |
| 18 | **IEX** | 2025-06-02 | 2025-08-01 | 44 | **-26.8** | -64,718 | 1 | NMS 2.01, rank **#29/150** (81th pct). 12m vol-adj mom +0.62 · 6m +0.42 |
| 19 | **IBVENTURES** | 2018-08-01 | 2019-03-01 | 143 | **-26.7** | -15,621 | 8 | NMS 3.44, rank **#1/150** (100th pct). 12m vol-adj mom +2.52 · 6m +1.50 |
| 20 | **PRESTIGE** | 2019-12-02 | 2020-04-01 | 84 | **-26.4** | -12,713 | 6 | NMS 1.73, rank **#26/147** (83th pct). 12m vol-adj mom +1.52 · 6m +0.26 |
