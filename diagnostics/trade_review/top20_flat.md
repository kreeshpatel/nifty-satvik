# 20 FLATTEST positions (exited at ~0%) — study 0001

**0001 has no time-stop.** These exited because the name fell out of the top-45 rank buffer, not on a clock. They are the book's churn: full round-trip cost paid for no move.

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
| 1 | **SUNTECK** | 2019-05-02 | 2019-09-03 | 84 | **-0.0** | -3 | 3 | NMS 2.30, rank **#14/150** (91th pct). 12m vol-adj mom +0.35 · 6m +1.46 |
| 2 | **ADANIGREEN** | 2024-04-01 | 2024-07-01 | 60 | **-0.0** | -25 | 2 | NMS 2.00, rank **#26/150** (83th pct). 12m vol-adj mom +2.93 · 6m +1.92 |
| 3 | **RECLTD** | 2019-06-03 | 2019-11-01 | 101 | **-0.1** | -20 | 5 | NMS 2.17, rank **#15/150** (91th pct). 12m vol-adj mom +1.05 · 6m +0.69 |
| 4 | **CEATLTD** | 2023-07-03 | 2023-10-03 | 63 | **+0.1** | +114 | 2 | NMS 1.92, rank **#29/150** (81th pct). 12m vol-adj mom +2.58 · 6m +0.49 |
| 5 | **OMAXE** | 2018-04-02 | 2018-05-02 | 21 | **+0.1** | +29 | 1 | NMS 1.66, rank **#22/150** (86th pct). 12m vol-adj mom +1.95 · 6m +0.88 |
| 6 | **GNFC** | 2018-02-01 | 2018-05-02 | 59 | **+0.1** | +38 | 2 | NMS 1.73, rank **#20/150** (87th pct). 12m vol-adj mom +2.28 · 6m +1.52 |
| 7 | **DBL** | 2021-04-01 | 2021-07-01 | 61 | **-0.1** | -79 | 2 | NMS 2.24, rank **#19/150** (88th pct). 12m vol-adj mom +4.30 · 6m +2.05 |
| 8 | **PNB** | 2025-11-03 | 2026-01-01 | 41 | **+0.1** | +222 | 1 | NMS 1.77, rank **#28/150** (82th pct). 12m vol-adj mom +0.75 · 6m +0.59 |
| 9 | **MANKIND** | 2025-02-01 | 2025-04-01 | 39 | **+0.1** | +206 | 1 | NMS 2.42, rank **#12/150** (93th pct). 12m vol-adj mom +1.24 · 6m +1.36 |
| 10 | **PRAJIND** | 2018-11-01 | 2019-09-03 | 205 | **+0.1** | +63 | 8 | NMS 1.59, rank **#30/150** (81th pct). 12m vol-adj mom +0.52 · 6m -0.08 |
| 11 | **LODHA** | 2024-05-02 | 2024-09-02 | 83 | **-0.1** | -290 | 3 | NMS 1.93, rank **#29/150** (81th pct). 12m vol-adj mom +3.59 · 6m +1.02 |
| 12 | **COCHINSHIP** | 2022-11-01 | 2023-01-02 | 43 | **-0.1** | -155 | 3 | NMS 2.29, rank **#20/150** (87th pct). 12m vol-adj mom +0.86 · 6m +0.85 |
| 13 | **TATACONSUM** | 2024-02-01 | 2024-05-02 | 59 | **+0.1** | +213 | 2 | NMS 1.83, rank **#26/150** (83th pct). 12m vol-adj mom +2.62 · 6m +1.31 |
| 14 | **IOC** | 2021-11-01 | 2022-02-01 | 63 | **-0.1** | -133 | 2 | NMS 1.72, rank **#22/150** (86th pct). 12m vol-adj mom +3.17 · 6m +1.72 |
| 15 | **AEGISLOG** | 2025-04-01 | 2025-06-02 | 40 | **+0.2** | +307 | 2 | NMS 2.47, rank **#17/150** (89th pct). 12m vol-adj mom +1.48 · 6m -0.00 |
| 16 | **COCHINSHIP** | 2023-02-01 | 2023-05-02 | 58 | **+0.2** | +176 | 2 | NMS 2.80, rank **#7/150** (96th pct). 12m vol-adj mom +1.69 · 6m +1.73 |
| 17 | **SIGNATURE** | 2024-11-01 | 2025-01-01 | 40 | **-0.2** | -448 | 1 | NMS 2.45, rank **#9/150** (95th pct). 12m vol-adj mom +4.93 · 6m +0.72 |
| 18 | **ALKEM** | 2024-01-01 | 2024-03-01 | 42 | **-0.2** | -337 | 1 | NMS 2.05, rank **#20/150** (87th pct). 12m vol-adj mom +2.36 · 6m +1.57 |
| 19 | **NMDC** | 2026-02-02 | 2026-03-02 | 20 | **+0.4** | +648 | 1 | NMS 1.92, rank **#29/150** (81th pct). 12m vol-adj mom +1.02 · 6m +0.58 |
| 20 | **GRANULES** | 2018-12-03 | 2019-01-01 | 20 | **+0.4** | +98 | 1 | NMS 1.68, rank **#23/150** (85th pct). 12m vol-adj mom -0.49 · 6m +0.50 |
