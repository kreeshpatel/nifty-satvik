# Blind replication brief — the SWING base (the actual rejection bar)

**Prepared 2026-08-06.** Class: documentation. **Zero trials, zero screens. Counts unchanged:
screens 15 · sealed opens 1 · n_trials 138.** No number in this document was newly computed for it;
every figure is read from the committed engine's own output.

---

## 0. What this is, and the standard it is held to

You are asked to rebuild one backtest from scratch, from this document alone, and reconcile against
a stated claim. **You do not get our source code.** Everything needed to implement is written below
as plain specification. (An appendix maps each section to `file:line` in our tree; it is there so
*our* side can audit the brief, and you can ignore it entirely.)

**The target is near-exact reconciliation, not shape.** Matching direction, or landing "within
10%", is a failure of the exercise. Round one landed within 11% and could not close the trade-count
gap; that gap was traced to four conventions that had never been written down. This document exists
to remove that excuse.

> **Any residual gap is a math error in one of the two implementations. It must be hunted, not
> averaged, not explained by "different but reasonable choices".** Every convention that could
> legitimately differ is pinned below. If you find yourself inventing a rule to close a gap, the
> rule you invented is the bug — in yours or in ours — and the point of the exercise is to find out
> which. A reconciliation that ends in "close enough" tells us nothing we did not already know.

If a rule below is ambiguous, **stop and say so** rather than choosing. An ambiguity you had to
resolve is itself the finding.

---

## 1. The claim to reproduce

Run the engine with **every lever at its default** (the frozen configuration; §11 lists what must be
OFF). One run, no variants.

| Quantity | Claimed value |
|---|---|
| **Sharpe (net, annualised)** | **1.1319** |
| **Trades (positions resolved)** | **255** |
| Closed-trade ledger rows | 249 |
| Exit-reason mix | `time` 164 · `stop` 66 · `trail` 19 · `eos` 6 |
| Win rate | 0.592157 |
| Mean R per trade | 0.481241 |
| CAGR | 0.246944 |
| Max drawdown | −0.423743 |
| Final equity | ₹8,114,623.22 (from ₹1,000,000) |
| Equity-curve points | 2,348 |

**Exact date range.** The curve runs **2017-01-02 → 2026-06-29** inclusive — 2,348 daily points, the
union of all universe members' session dates on or after the start bound `2017-01-01`. The
**first trade entry is 2017-01-30**; the last bar is 2026-06-29.

`yrs` for CAGR = `(2026-06-29 − 2017-01-02).days / 365.25` = `3465 / 365.25` = **9.4867**.

**`trades` counts positions RESOLVED, not closed trades.** 249 positions closed through an exit
rule; 6 were still open on the last bar and are force-resolved at that bar's close with reason
`eos`. Both figures are given above; reconcile **both**, and if only one matches you have located
the gap.

**Secondary reconciliation targets.** The exit-reason mix is the single most useful diagnostic. A
trade-count gap concentrated in `time` is a weekly-clock or week-grouping bug; concentrated in
`stop` is a stop-geometry or weekly-close bug; concentrated in `eos` is a date-range bug; a gap
spread evenly across all four is an entry/fill or universe bug.

---

## 2. Inputs — get exactly these bytes

All are public. **Verify every sha256 before you start.** A silent input substitution is the most
expensive way to fail this exercise.

| File | Where | sha256 | bytes |
|---|---|---|---|
| `ohlcv.pkl` | GitHub release **`dataset-pin-20260701`**, repo `kreeshpatel/nifty-satvik` | `f8625a8ff6abae06baf4d5c3c10eef2c9bbe98df785248a2b360d7d2a3c52142` | 64,297,056 |
| `ohlcv_backfill.pkl` | GitHub release **`dataset-pin-20260729`** | `9ebbe448fa52314db998edab0afcc5dee4da807b298ac3f1fe71f4ab70d5d366` | 7,410,822 |
| `nifty500_membership.csv` | repo path `data/nifty500_membership.csv` | `5a06411ae44590cb78a9264a7b3e7378e3d5ab0de0c26c95fc3476d022b95663` | 27,392 |
| `benchmark_nifty50.csv` | repo path `research/exports/benchmark_nifty50.csv` | `53aef29255b5b2f61b9d8993550ffa0197ef2f1144b6e3b790d34f3fdd9e0c5d` | — |
| alias map | inlined in §3.3 below — you do not need the file | `a5edfc74dffbfdcbcb5decde3cd9863299a5a1f52a51b33b7aa9210e94405d20` | 2,788 |

**Schemas.**

- **`ohlcv.pkl` / `ohlcv_backfill.pkl`** — a Python pickle of `dict[str, pandas.DataFrame]`. Key is
  the NSE ticker (no `.NS` suffix). Each frame has a `DatetimeIndex` (naming: `Date`) and columns
  exactly `Open, High, Low, Close, Volume`, ascending by date, one row per session the vendor
  reported. Prices are vendor-**adjusted** floats; volume is float.
- **`nifty500_membership.csv`** — header `ticker,from_date,to_date`; 880 rows over 813 tickers;
  dates `YYYY-MM-DD`; periods are **inclusive** at both ends; a ticker may appear on several rows
  (several membership spells). Parse to `{TICKER_UPPER: [(from, to), …]}`. A row whose dates fail to
  parse, or where `to < from`, is dropped.
- **`benchmark_nifty50.csv`** — header `date,nifty50_close`; 2,830 rows spanning 2015-01-02 →
  2026-07-03. This is the CRS denominator.

**A warning about the price data, stated because it is load-bearing and not a defect you should
"fix".** The pinned series contains 13 known adjustment discontinuities (a corporate action applied
to only part of a name's history). They are the vendor's, they are in the bytes you are told to use,
and **the claim above was produced with them present.** Do not clean, repair or filter them — that
would guarantee a mismatch. If you detect them, note them and move on; we already have them
catalogued.

---

## 3. Universe construction

### 3.1 Assemble the corrected universe

1. Load `ohlcv.pkl` → a dict of frames. (710 names.)
2. Load `ohlcv_backfill.pkl`. For each ticker in it, **add it only if the ticker is not already
   present**. The pinned series always wins; the backfill never overwrites.
3. Apply the alias map (§3.3): for each `old → new` pair, if `new` exists in the dict, set
   `dict[old] = dict[new]` — i.e. the old symbol is given the successor's series. This **overwrites**
   any series already stored under `old` (including one that came from the backfill in step 2).
   Where the alias carries a `valid_until` date, first truncate the copied series to rows with
   `index <= valid_until`.

**Result: 814 tickers.** If you do not get 814, stop here — nothing downstream can reconcile.

### 3.2 Filter

Drop any ticker whose frame has **fewer than 300 rows**. `len(df) < 300 → skip`.

**Result: 788 tickers.** These are the names the engine sees.

### 3.3 The alias map, inlined

17 pairs. Only `TATAMOTORS` carries a `valid_until`.

```
BAJAJCORP  -> BAJAJCON
ESSELPACK  -> EPL
GLS        -> ALIVUS
IBULHSGFIN -> SAMMAANCAP
IIFLWAM    -> 360ONE
INFRATEL   -> INDUSTOWER
LAXMIMACH  -> LMW
MAHINDCIE  -> CIEINDIA
MERCK      -> PGHL
NBVENTURES -> NAVA
ORIENTREF  -> RHIM
PHILIPCARB -> PCBL
PVR        -> PVRINOX
STRTECH    -> STLTECH
SUVENPHAR  -> COHANCE
TATAMOTORS -> TMPV        valid_until 2025-09-30
ZOMATO     -> ETERNAL
```

### 3.4 Index membership

Membership is a **filter on order activation only** (§7 step 1). It is *not* re-checked at fill time,
and *not* checked while a position is open. A name that leaves the index mid-trade is held to its
normal exit.

`in_index(ticker, d)` = true iff any membership period for that ticker satisfies
`from_date <= d <= to_date`, comparing **dates**, not timestamps. A ticker absent from the file is
**not** a member and can never be activated.

### 3.5 The history-start subtlety — this one moves the trade count

The pinned file starts 2017-01-02 for most names, **but 31 tickers carry history from 2016-01-01**
(they arrive via the backfill in step 3.1.2). Those 31 complete their 44-week warm-up during 2016 and
are therefore **tradeable from the start of 2017**, which is why the first entry is 2017-01-30 rather
than a year later.

If your first trade is in 2018, you have dropped the backfill or mis-ordered steps 1–3.

---

## 4. Weekly bars and the anchor — read this twice

**The weekly grouping is by ISO year-week over each ticker's own sessions. It is NOT a
`resample("W-FRI")`.** This is the convention most likely to break a replication, and the pipeline
genuinely contains both — a `W-FRI` resample is used for an unrelated daily-path series that the
signal never reads. **For everything in this brief, use the ISO grouping.**

For each ticker independently:

1. Take the frame's `DatetimeIndex` in ascending order.
2. Compute the ISO calendar `(iso_year, iso_week)` for every session.
3. Walk the sessions in order and start a **new group whenever the `(iso_year, iso_week)` key
   differs from the previous session's**. Groups are runs of consecutive sessions sharing a key.
4. Each group is one weekly bar, holding the **integer positions** of its member sessions.

From each group, with `dd` = its positions into the daily arrays:

| Weekly field | Definition |
|---|---|
| `wopen` | `Open[dd[0]]` — open of the group's **first** session |
| `whigh` | `max(High[dd])` |
| `wlow` | `min(Low[dd])` |
| `wclose` | `Close[dd[-1]]` — close of the group's **last** session |
| **`weekend`** | the daily position `dd[-1]` — the group's **last session** |

**`weekend` is the last session of the ISO week, which is frequently not a Friday.** A holiday-shortened
week ends on Thursday; the NSE Diwali *Muhurat* special session can put a week's end on a Saturday or
Sunday. Weekly exit decisions (§10) are taken on this bar, whatever weekday it is. Getting this wrong
shifts exit timing by a session and will not show up as a shape difference — it will show up as a
handful of trades landing in the wrong bucket.

Because grouping is per-ticker over that ticker's own sessions, **two tickers can have different
numbers of weekly bars over the same span.** That is correct; do not align them.

---

## 5. Derived weekly series

All indexed by weekly-bar number `k`, per ticker.

| Series | Definition |
|---|---|
| `wsma[k]` | rolling mean of `wclose` over **44** weekly bars. NaN for `k < 43`. |
| `slope[k]` | `wsma[k] / wsma[k-13] − 1`. NaN for `k < 13`. Lookback **13** weekly bars. |
| `rng[k]` | `whigh[k] − wlow[k]` |
| `qgreen[k]` | `(wclose[k] > wopen[k]) AND (rng[k] > 0) AND ((wclose[k] − wlow[k]) >= 0.5 × rng[k])` |
| `touch[k]` | `(wlow[k] <= wsma[k] × 1.07) AND (wclose[k] > wsma[k])` |

**The CRS series (the ranking metric).**

1. Load `benchmark_nifty50.csv` into a date-indexed series `n50`, sorted ascending.
2. Reindex `n50` onto **this ticker's daily index** with **forward-fill**. Call it `ia`.
3. `iw[k] = ia[weekend_position_of_week_k]` — the index level on the week's last session.
4. `rs[k] = wclose[k] / iw[k]` where `iw[k] > 0`, else NaN.
5. `rs_sma[k]` = rolling mean of `rs` over **40** weekly bars.
6. **`crs_dist[k] = rs[k] / rs_sma[k] − 1`** — this is the rank used for fill priority.

`rs_term[k] = rs[k] > rs_sma[k]` (NaN → false).

Also needed for exits: **`ema20`** — despite the name it is a **simple** rolling mean of the
**daily** `Close` over **20 sessions**. It is not an exponential average. Getting this wrong moves
only the 19 `trail` exits, which makes it an easy residual to misattribute.

`adv20[i] = rolling mean over 20 daily sessions of (Close[i] × Volume[i])` — rupee turnover, used
only by the cost model.

---

## 6. The signal

A weekly bar `k` fires a signal when **all five** hold:

```
slope[k]  >= 0.03
qgreen[k]
touch[k]
wclose[k] >  wsma[k]
rs_term[k]
```

Any NaN participating in a comparison makes that term false. There is no other condition in the
default configuration — no volume test, no base test, no fundamental screen, no regime filter.

---

## 7. The entry window and the fill convention

### 7.1 Building the window

For each weekly bar `k` that fired, **if `k+1` exists**, create one entry window:

- **`days`** = the daily positions of weekly bar **`k+1`** (the whole following ISO week).
- **`lo`** = `wlow[k]` — the **signal week's** low.
- **`hi`** = `whigh[k]` — the **signal week's** high.
- **`rank`** = `crs_dist[k]`.

The window is keyed by `days[0]`, its first day. A signal on the final weekly bar produces no
window and no trade.

### 7.2 Activation

On each date `d`, for each ticker, let `i` be that ticker's daily position for `d` (skip if the
ticker has no bar that day). Activate an order when **all** hold:

- the ticker has no open position and no already-active order;
- `i` is a window key (i.e. `i == days[0]` of some window);
- **`in_index(ticker, d)`** — the membership check, applied here and only here.

An activated order carries `days`, `lo`, `hi`, `rank`, and `adv20` at the activating bar.

### 7.3 The fill test

On each date `d`, for every ticker with an **active** order whose `days` contains today's position
`i`, and which has no open position, let `opn = Open[i]`. The order is a fill candidate iff

```
lo < opn < hi
```

**Both inequalities are strict.** An open exactly equal to the signal week's low or high does not
fill.

The fill price is **`opn` — that day's open, unmodified.** There is no limit, no buy-stop, no
slippage applied to the price (slippage lives in the cost model, §9).

### 7.4 Fill priority and the cash gate

Collect all candidates across all tickers for the day, then sort by **descending `rank`
(`crs_dist`), ties broken by ticker symbol ascending**, and attempt them in that order. For each:

1. `entry = opn`, `stop = lo` (the order's, i.e. the signal week's low).
2. Require `entry > stop`; otherwise skip.
3. Size and cost as §8–§9, giving `notional`.
4. **If `notional <= cash`**, fill: subtract `notional` from cash, open the position, and remove the
   order.
5. **If not**, the order is *not* removed. It stays active and is retried on the window's remaining
   days. (Increment a counter if you like; nothing reads it.)

**Consequence, and a likely source of a trade-count gap:** a rejected-for-cash order can fill later
in the same window at a different open. Ordering matters — a stronger-ranked name consuming cash
changes which weaker names fill, and on which day.

### 7.5 Window expiry

At the end of each date `d`, any active order for which `i == max(days)` — today is the window's
last day — is deleted. Windows do not roll over.

---

## 8. Sizing

Let `sizing_eq` = the book's **equity at the end of the previous day** (see §12 for how equity is
formed). On the very first day it is the opening capital.

```
EQ0        = 1,000,000          (rupees)
risk_frac  = 0.02               (2% of sizing equity per fill)

risk_per_share = entry − stop
shares         = sizing_eq × 0.02 / risk_per_share
```

**Shares are fractional. Do not round, floor, or convert to lots.**

**All of the following caps are OFF in the default run** and must not be applied:

| Lever | Default |
|---|---|
| notional cap per name | **off** (no cap) |
| max risk % (stop lifted toward entry) | **off** (stop stays at the signal-week low) |
| extension cap (skip fills far above the SMA) | **off** |
| max concurrent positions | **off** |
| ATR-based stop | **off** (stop is the candle low) |
| volatility targeting | **off** (`sizing_eq` is plain equity) |
| Grade-A / top-N-per-week filter | **off** (all signals are eligible) |

The engine asserts that realised risk is `2.00% ± 0.02%` of sizing equity on every fill. Assert the
same; it catches sizing bugs immediately.

---

## 9. The cost model

Costs are charged as a **fraction of the leg's gross notional**, on **both** entry and exit, and on
each partial exit separately.

```
cost_fraction(adv, notional) = 0.0013 + slippage_tier(adv) + impact(adv, notional)

slippage_tier(adv) = 0.0005   if adv >= 500,000,000      (LARGE_CAP)
                     0.0022   if adv >=  50,000,000      (MID_CAP)
                     0.0040   otherwise                  (SMALL_CAP)

impact(adv, notional) = 0.0010 if (adv > 0 and notional > 0.005 × adv) else 0
```

- `0.0013` is STT (0.0010) + brokerage (0.0003), charged per leg.
- `adv` is `adv20` **captured at the entry bar** and reused for every leg of that position,
  including exits years later. Do not recompute it at exit.
- A non-finite `adv` is treated as `0`, i.e. SMALL_CAP.

Applying them:

```
entry:  notional = shares × entry × (1 + cost_fraction(adv, shares × entry))     # cash leaves
exit :  proceeds = shares × exit  × (1 − cost_fraction(adv, shares × exit ))     # cash returns
```

Reported STT for a trade is `0.0010 × (gross entry + gross of every exit leg)` — an observational
field, a subset of the cost already charged, never added on top.

---

## 10. Exits — the default ladder

Exits are decided on **weekly-close bars** and executed at the **next session's open**. Decision and
fill are different days; this is not a rounding detail, it is the convention.

### 10.1 Pending fills come first

At the start of processing a position on date `d` (with a bar), if a pending action is set from a
previous weekly close, execute it **at today's open** and clear it:

- `("half", …)` — sell **half of the ORIGINAL share count** at today's open, credit proceeds net of
  cost, mark the position `half_done`. **The position stays open and the stop does not move.**
- `("full", reason)` — sell all remaining shares at today's open, close the position, record the
  trade.

### 10.2 The weekly-close decision

Only when `i` is this ticker's `weekend` position (§4):

1. `weeks_held += 1` (starts at 0 on entry; the entry week's own close counts if the entry day is
   before its week's end).
2. `wc = Close[i]`.
3. Evaluate **in this exact order, first match wins**:
   - **stop** — `wc <= stop` → pending `("full", "stop")`, or `("full", "stop_half")` if already
     `half_done`.
   - **half** — `not half_done and wc >= target` → pending `("half", "half")`.
   - **trail** — `half_done` → first update `trail = max(trail, ema20[i] × (1 − 0.04))`, then if
     `wc < trail` → pending `("full", "trail")`.
4. **Time cap** — after the above, if no pending action was set and `weeks_held >= 13` → pending
   `("full", "time")`.

`stop` is set at entry to the signal week's low and **never moves** in the default run — no
break-even shift, no ratchet, no chandelier. `trail` is initialised to the stop and only ever
ratchets upward, and only after the half has booked.

`target = entry + 2 × (entry − stop)`.

### 10.3 What must be OFF

The engine carries many gated levers. In the default run **all** of these are off, and enabling any
of them breaks the claim: intraweek/resting-limit target fills, hard intraday stops, gap-through
stop fills, disaster floors, scaled tranche exits (60/20/20 or 40/40/20), runner profit caps,
blow-off pattern exits, 20-week trailing exits, lower-close exits, trend-hold exits, soft stops,
early-MAE cuts, stop widening, per-origin exit routing, and the staleness force-close.

**Config P, named because you were told it exists:** the *live* book runs an overlay called config P
— `no_time_cap = True`, a 20-week trailing exit at 4%, and a blow-off exit armed at 2R — together
with a live discipline set (extension cap 0.20, max risk 0.10, notional cap 0.20) and a staleness
guard. **None of it is in this claim.** The run you are reproducing has the 13-week time cap ON and
every one of those overlays OFF. It is described here only so you can be certain you are not
supposed to implement it.

### 10.4 R, and the end-of-series resolution

```
r_rest = (exit_price − entry) / (entry − stop)
R      = r_rest                                   if the half never booked
R      = 0.5 × 2.0 + 0.5 × r_rest                 if it did
```

Note the booked half is credited at exactly **2.0 R**, not at its realised fill.

At the final bar, every still-open position is resolved at **that ticker's last available close**
(not the next open — there is none), with reason `eos`, and counted in `trades`. There were **6**.

---

## 11. Order of operations within a day

The daily loop runs over the **sorted union of all universe members' session dates**, from
`2017-01-01` onward. For each date `d`, in this order:

1. **Manage open positions** — for each open position with a bar today: execute any pending fill at
   today's open; then, if today is that ticker's weekly-close bar, run §10.2. A held ticker with **no
   bar today is skipped entirely** (no exit logic runs for it).
2. **Activate orders** (§7.2) and **collect fill candidates** (§7.3).
3. **Fill** in rank order, subject to cash (§7.4).
4. **Expire** windows ending today (§7.5).
5. **Mark to market and append the curve** (§12).

A position opened today is not managed until tomorrow.

---

## 12. Equity, the curve, and the metrics

### 12.1 Daily mark

```
mtm    = Σ over open positions of  shares × mark
equity = cash + mtm
```

where `mark` is that ticker's **Close today** if it has a bar, and **otherwise its ENTRY price**.

**The absent-bar mark is the entry price, and that is deliberate.** A suspended or delisting holding
is carried at cost rather than at its last traded price. This is a known engine bug, captured as
behaviour of record and present in the claim. Implement it as written.

Append `(d, equity)` to the curve on every date in the loop — including dates where nothing happened.
The curve therefore has **2,348 points**, one per union session date, not one per trade.

### 12.2 Metrics

Let `e` be the curve as a date-indexed series and `r = e.pct_change().dropna()`.

```
yrs    = (e.index[-1] − e.index[0]).days / 365.25
Sharpe = mean(r) / std(r) × sqrt(252)
CAGR   = (e[-1] / e[0]) ** (1 / yrs) − 1
MaxDD  = min(e / cummax(e) − 1)
```

Three conventions worth stating because they are silent killers:

- **`std(r)` is the SAMPLE standard deviation, `ddof = 1`** (pandas' default), not the population
  form. On 2,347 returns the difference is ~0.02% of Sharpe — small, but if you are hunting a
  fourth decimal it matters, and you should not discover it by accident.
- **Risk-free rate is ZERO.** This is a raw-return Sharpe, not an excess-return Sharpe.
- **`yrs` is calendar years from the curve's own endpoints**, not trading-bar years and not a count
  of calendar years spanned. Using bar-years instead inflates CAGR by roughly 4%.

`√252` is applied to a **daily** series. Do not mix frequencies.

---

## 13. The conventions most likely to cost you the trade count

Ranked by how much damage they do while looking correct. Round one's gap was traced to four
undocumented conventions; rather than guess which four you will hit, here is every one that can move
the count while leaving the equity curve's shape intact.

1. **ISO-week grouping, not `resample("W-FRI")`** (§4). Different weekly bars → different signals,
   different `weekend` days, different exit timing. The single highest-risk item.
2. **`weekend` is the week's last session, not Friday** (§4). Holiday weeks and Muhurat sessions move
   it. Affects when every weekly decision is taken.
3. **The 31 backfill names carrying 2016 history** (§3.5). Omit them and you lose all of 2017's
   trades and your first entry lands a year late.
4. **The cash gate does not cancel the order** (§7.4). A name rejected for cash retries on the
   window's remaining days. Cancelling instead loses trades; refilling greedily gains them.
5. **Strict inequalities in the fill test** (§7.3): `lo < open < hi`, not `<=`.
6. **Membership is checked at activation only** (§3.4, §7.2), never at fill and never during a hold.
7. **The 300-row minimum** (§3.2) — 788 names, not 814.
8. **`trades` = 255 includes 6 `eos`**; the closed ledger is 249 (§1).
9. **The entry window is the *following* ISO week, and `lo`/`hi` come from the *signal* week** (§7.1).
   Mixing these up produces a plausible engine with a completely different trade set.
10. **`ema20` is a simple 20-day mean despite its name** (§5).
11. **`adv20` is frozen at entry** for all cost legs (§9).
12. **The absent-bar NAV mark is the entry price** (§12.1).
13. **The alias map overwrites, and `TATAMOTORS` truncates at 2025-09-30** (§3.1, §3.3).

---

## 13b. A self-test you can run before the full backtest

One real trade from the claimed run, end to end. **Most of it is book-independent** — it depends only
on VGUARD's own bars and the rules above, not on cash, sizing or any other position. Reproduce this
single trade first. If it does not match, do not run the full backtest; you have a rule bug and the
full run will only hide it in an aggregate.

**Book-independent (check these first):**

| Field | Value |
|---|---|
| Signal week (ISO) | sessions 2019-07-22 … 2019-07-26 |
| Signal-week low → **stop** | **210.06** |
| Signal-week high → fill upper bound | 235.68 |
| 44-week SMA at the signal week | 205.8503 |
| `crs_dist` (rank) | 0.0864 |
| Entry window | the ISO week beginning 2019-07-29 |
| **Entry** — open of the first window day passing `lo < open < hi` | **2019-07-29 @ 227.01** |
| `risk_per_share` = entry − stop | 16.9528 |
| Target = entry + 2 × risk | 260.92 |
| Weekly closes counted | **13** |
| **Exit trigger** — the 13th weekly-close bar | **2019-10-27** |
| **Exit fill** — next session's open | **2019-10-29 @ 232.18** |
| Exit reason | `time` |
| **R** = (232.18 − 227.01) / 16.9528 | **0.305** |

**Note the exit trigger date: 2019-10-27 is a SUNDAY.** It is the last session of ISO week 2019-W43
because the NSE ran a Diwali *Muhurat* special session that day, and 2019-10-28 was a holiday, which
is why the fill lands on Tuesday 2019-10-29. If your implementation triggers on Friday 2019-10-25
and fills on Monday 2019-10-28, your weekly grouping is a `W-FRI` resample and §4 is where to look.
This one trade is the cheapest possible test of the highest-risk convention in this brief.

**Book-dependent (only checkable once your whole run matches):** the sizing equity on the fill day
was ₹1,644,799.97, giving 1,940.445954 shares at a 0.0035 entry cost fraction, ₹6,901.45 net P&L and
₹891.03 reported STT.

---

## 14. Reconciliation protocol

1. Verify all input hashes. Report them back.
1b. Reproduce the §13b single-trade self-test. Report every book-independent field. Do this
    before anything else — it isolates the week-grouping convention in minutes.
2. Report universe counts at each stage: after assembly (expect **814**), after the 300-row filter
   (expect **788**).
3. Report the curve's first and last dates and its length (expect **2017-01-02**, **2026-06-29**,
   **2,348**).
4. Report the first trade's entry date (expect **2017-01-30**).
5. Report **trades, closed-ledger rows, and the full exit-reason mix** before reporting Sharpe. The
   mix localises a gap faster than any aggregate.
6. Report Sharpe, CAGR, MaxDD, win rate, mean R, final equity.
7. **If anything differs, do not tune.** Report the difference, your value, and the smallest
   reproducible case you can isolate — ideally a single ticker and a single week where your engine
   and this specification disagree. A one-trade disagreement with a named cause is worth more than a
   matching headline.

**We will treat a residual gap as our bug until proven otherwise.** The purpose of a blind
replication is to find errors in the incumbent; a brief that only lets you confirm us would be
worthless. If this document is ambiguous, wrong, or incomplete, that is the most valuable thing you
can return.

---

## Appendix — provenance (for our audit; not needed to implement)

| Section | Source |
|---|---|
| §2 inputs | `data/ohlcv.pkl`, `data/ohlcv_backfill.pkl`, `data/nifty500_membership.csv`, `research/exports/benchmark_nifty50.csv` |
| §3.1 universe assembly | `scripts/run_bhanushali_path1.py:26-41` (`corrected_universe`) |
| §3.2 300-row filter | `scripts/run_bhanushali_sixstep.py:59-64` (`prep`) |
| §3.3 alias map | `data/delisted_alias_map.json` |
| §3.4 membership | `nq/data/membership.py:88-94` (`ticker_in_index_on`), `:66-88` (`load_membership`) |
| §4 ISO weekly grouping | `scripts/run_bhanushali_weekly_rank.py:67-79` |
| §4 `weekend` | `scripts/run_bhanushali_weekly_rank.py:307` |
| §5 weekly series, CRS | `scripts/run_bhanushali_weekly_rank.py:88-104`; constants `:40` |
| §5 `ema20`, `adv20` | `scripts/run_bhanushali_weekly_rank.py:66`; `scripts/run_bhanushali_sixstep.py:83` |
| §6 signal | `scripts/run_bhanushali_weekly_rank.py:191-192` (`wsig`) |
| §7.1 entry window | `scripts/run_bhanushali_weekly_rank.py:317-327` |
| §7.2 activation | `scripts/run_bhanushali_weekly_rank.py:748-760` (membership gate at `:755`) |
| §7.3 fill test | `scripts/run_bhanushali_weekly_rank.py:798-813` |
| §7.4 priority + cash gate | `scripts/run_bhanushali_weekly_rank.py:836-880` |
| §7.5 expiry | `scripts/run_bhanushali_weekly_rank.py:898-902` |
| §8 sizing | `scripts/run_bhanushali_weekly_rank.py:866-891`; `RISK` `scripts/run_bhanushali_sixstep.py:46` |
| §9 cost model | `scripts/run_bhanushali_sixstep.py:52-56`; `nq/engine/portfolio.py:53-75` (`_tier`, `_slip`) |
| §10.1 pending fills | `scripts/run_bhanushali_weekly_rank.py:452-497` |
| §10.2 weekly ladder | `scripts/run_bhanushali_weekly_rank.py:642-736` |
| §10.3 config P | `scripts/run_bhanushali_cron.py:66,86` (`P2_EXIT`, `LIVE_DISCIPLINE`) |
| §10.4 R and `eos` | `scripts/run_bhanushali_weekly_rank.py:484-490, 913-928` |
| §11 day loop | `scripts/run_bhanushali_weekly_rank.py:419-905` |
| §12.1 NAV mark | `scripts/run_bhanushali_weekly_rank.py:903-910` |
| §12.2 metrics | `scripts/run_bhanushali_weekly_rank.py:930-945` |
| §1 the claim | `scripts/build_substrate.py:163-170` (`guard`), reproduced 2026-08-06 |

**Reproduce our side with:** `corrected_universe()` → `prep_weekly_rank(ohlcv)` →
`backtest(P, load_membership(), start="2017-01-01")`, all other arguments defaulted.
