# Bhanushali Weekly-Swing — Reproduction & Methodology Spec

*Everything needed to reproduce our exact numbers, or to understand precisely why a different
environment gets different ones. If another tool/chat reports very different results, work down the
**Divergence checklist** (§7) — in our experience the answer is almost always **the data**, not the
rules.*

Our headline result of record (the live paper book, `weekly-swing-0094-rank`), **NET after real
costs, corrected universe, 2017–2026, in-sample**:

| Sharpe | CAGR | MaxDD | Win rate | CI-low | DSR |
|--------|------|-------|----------|--------|-----|
| **1.132** | **+24.7%** | **−42.4%** | 59.2% | +0.474 | 0.894 |

Sub-period Sharpe (continuous slice): 2017-18 **+1.17** · 2019-21 **+1.05** · 2022-26 **+1.19**.
This is **byte-deterministic** from the pinned data + the committed engine — it reproduces identically
across machines. It is **not certified** (DSR 0.894 < our 0.95 bar) and is in-sample.

---

## 0. Why your other chat gets very different numbers (read this first)

The strategy numbers depend on **five** things. A different value for **any one** produces a very
different result. In order of how much they move the number:

1. **The data.** This is the #1 cause of divergence. See §2.
   - A fresh `yfinance` pull is **survivor-only** (delisted names — DHFL, RCOM, Yes Bank pre-crash,
     the merged PSU banks — are simply absent). Survivorship **inflates** trend results, and the bias
     **grows with holding period** (finding 0025: −0.04 Sharpe tight-stop vs −0.18 wide-stop).
   - `yfinance` history also **drifts run-to-run**: we observed CAGR **14.2% / 15.6% / 16.25%** from
     the *identical* command on different days. A number is only reproducible against a **fixed
     snapshot** (our `dataset-pin-20260701`, sha `f8625a8f…`).
   - We run on a **corrected** universe = pinned survivor cache **+** a delisted-price backfill **+**
     a validated alias map (814 names). A survivor-only pull is a *different universe*.
2. **The exact rules.** "Bhanushali strategy" is ambiguous. The **letter-faithful** taught system
   (RSI-35 + candle-low stop + 1:2/1:3) is **break-even gross and loses net** (finding 0022). Our
   1.132 is a *reconstruction* (`weekly-swing-0094-rank`) that keeps his principles but changes the
   mechanics our tests vindicated. If the other chat runs the *taught* rules, it *should* get a poor
   number — that's a real finding, not a bug. Full spec in §3.
3. **The universe & period.** We use point-in-time Nifty-500 large+mid, **2017–2026**. A different
   index, a different date range, or a today-membership (look-ahead) universe all move it.
4. **The cost model.** We charge brokerage + STT + ADV-tiered slippage per leg (§4). Gross (cost-off)
   vs net is a large gap on this book; a zero-cost or flat-cost backtest is not comparable.
5. **Determinism details.** Weekly-bar bucketing (ISO week), the CRS **index** (Nifty-50, not
   Nifty-500-TRI — they give 0.90 vs 0.68 Sharpe), and **fill order** (strongest-CRS-first, not hash
   order — worth +0.23 Sharpe) all matter. See §3.

---

## 1. What produces the number (the pipeline)

```
corrected OHLCV (pinned + backfill + aliases)          # scripts/run_bhanushali_path1.corrected_universe()
      │
      ▼
prep_weekly_rank()  → weekly bars + 44-wk SMA + slope + quality-green + 44-wk touch
      │                + CRS (RS vs Nifty-50, its 40-wk SMA) + per-signal CRS-distance rank
      ▼
backtest()          → in-range weekly entry, 2% risk sizing, strongest-CRS-first fills,
      │                4 exits (stop / +2R half / 20-day-SMA trail / 13-wk cap), tiered costs
      ▼
NET metrics (Sharpe / CAGR / MaxDD / slices / bootstrap CI / DSR)
```

Canonical code: [`scripts/run_bhanushali_weekly_rank.py`](../scripts/run_bhanushali_weekly_rank.py)
(engine) — `prep_weekly_rank()` builds the features, `backtest()` runs the book. Frozen params:
[`models/bhanushali_weekly/config.json`](../models/bhanushali_weekly/config.json).

---

## 2. The data (the single biggest source of divergence)

### 2.1 The pinned snapshot
- **File:** `data/ohlcv.pkl`, SHA-256 `f8625a8f…`, tag **`dataset-pin-20260701`**.
- **Get it:** `gh release download dataset-pin-20260701` (pulls the exact pickle). Verify:
  `python -c "from nq.data.ohlcv import file_sha256; print(file_sha256())"` → must start `f8625a8f`.
- Format: `{ticker -> DataFrame}` with title-cased `Open/High/Low/Close/Volume` on a `DatetimeIndex`,
  `auto_adjust=True`. **This pin is survivor-only** (103 of 813 PIT members missing).

### 2.2 The corrected universe (what we actually run on)
`corrected_universe()` assembles three committed pieces (never fetched live):
- `data/ohlcv.pkl` — the pinned survivor cache (never overwritten).
- `data/ohlcv_backfill.pkl` — recovered delisted-name price series (103/103 resolved, ~100% member-day
  coverage). Added only where the pin lacks a name.
- `data/delisted_alias_map.json` — old-symbol → successor series (dividend-adjusted, identity-
  validated), with optional `valid_until` cutoffs.

Result: **814 names**, no survivorship gap. **A `yfinance`/`stooq`/`tushare` pull cannot match this**
— it has neither the pin nor the delisted backfill.

### 2.3 The CRS denominator
Nifty-50 (`^NSEI`), pinned to 2015 in `research/exports/benchmark_nifty50.csv` (so the 40-week RS SMA
is warm before 2017). Using Nifty-500-TRI instead gives Sharpe **0.68**, not 0.90 (finding 0037) —
the index choice is not cosmetic.

---

## 3. The exact strategy spec (re-implementable from scratch)

All values are the frozen config + the engine constants — reproduce these **exactly**.

### 3.1 Universe & bookkeeping
- Universe: the 814-name corrected set; PIT index membership enforced per day
  (`ticker_in_index_on`). A name needs ≥ 300 daily bars to be eligible.
- Starting equity **₹1,000,000**; backtest start **2017-01-01**; one book, cash-constrained.

### 3.2 Weekly bar construction
Group each stock's daily bars by **ISO (year, week)**. Per week: `open` = first day's open,
`high` = max daily high, `low` = min daily low, `close` = last day's close. The "week-end" index is
the last daily bar of each ISO week. (Getting this bucketing wrong is a common divergence.)

### 3.3 Entry — five conditions, all on weekly bars, at the setup week's close
Let `wsma = 44-week rolling mean of weekly close`.

1. **Rising trend (slope floor):** `wsma[t] / wsma[t-13] - 1 ≥ 0.03` (44-wk SMA up ≥ 3% over 13 weeks).
2. **Above trend:** `weekly_close > wsma`.
3. **Touch/pullback:** `weekly_low ≤ wsma × (1 + 0.07)` **and** `weekly_close > wsma` (dipped within
   7% of the line but closed above it).
4. **Quality green:** `close > open` **and** `(close − low) ≥ 0.5 × (high − low)` (upper-half close).
5. **CRS:** `RS = weekly_close / Nifty-50_weekly_close`; `RS > SMA40(RS)` (leading the market).

Signal for week *t* = all five true. It becomes actionable the **following week**.
Per-signal **rank** = `crs_dist = RS / SMA40(RS) − 1` at the setup week.

### 3.4 Entry mechanics
The signal is valid the **whole next trading week**. On each day of that week, if the day's **open is
inside the setup week's range** `[weekly_low, weekly_high]`, **buy at that open**. If no day's open is
in range, the signal **expires unfilled**. Stop = the **setup week's low**.

### 3.5 Sizing
`shares = floor( equity × 0.02 / (entry − stop) )` — a fixed **2% of current equity at risk** per
fill. Fills are attempted in **descending `crs_dist`** (strongest first) and taken while
`notional ≤ available cash`. No leverage in the backtest.

### 3.6 Exits — decided at the weekly close, executed at the next Monday's open
Evaluated in this order each week for each open position:
1. **Stop:** `weekly_close ≤ stop` → exit full.
2. **First target (+2R):** if not yet halved and `weekly_close ≥ entry + 2×(entry − stop)` → **sell
   half**; mark `half_done`.
3. **Trailing stop (runner):** once halved, `trail = max(trail, SMA20_daily × (1 − 0.04))`; if
   `weekly_close < trail` → exit the remainder.
4. **Time cap:** if still open after **13 weeks** → exit.
`SMA20_daily` is the **20-day** simple moving average of the daily close (the only daily input).

### 3.7 Frozen constants (copy these)
```
weekly_sma        = 44 weeks        slope_floor_pct   = 0.03 (over 13 weeks)
trail_sma         = 20 days         slope_lookback    = 13 weeks
trail_pct         = 0.04            touch_band        = 0.07
crs_index         = Nifty-50 (^NSEI)  crs_length      = 40 weeks
risk_pct          = 0.02            cap_weeks         = 13
target_r          = 2              start_equity      = 1,000,000
fill order        = descending CRS distance (strongest first)
```

---

## 4. The cost model (per leg — buy and sell each pay)
- **Brokerage** `BROKERAGE_PCT = 0.0003` + **STT** `STT_PCT = 0.001` → `0.0013` fixed per leg.
- **Slippage by ADV tier** (`SLIPPAGE`): 20-day rupee ADV ≥ ₹50cr → **LARGE 0.0005**; ≥ ₹5cr →
  **MID 0.0022**; else / NaN → **SMALL 0.0040**. Plus a market-impact add-on when an order exceeds
  0.5% of the name's daily traded value (see `config.leg_slippage`).
- Position cap `MAX_ADV_PARTICIPATION = 0.05` (5% of the name's 20-day ADV).
- Total per-leg fraction = `0.0013 + tier_slippage(+impact)`. Run **cost-off** to see gross; the
  gross↔net gap is large on this book, so a flat-cost or zero-cost backtest will not match.

---

## 5. How to run it (reproduce our exact numbers)
```bash
# 1. get the pinned data (survivor cache) — the backfill + alias map are already committed
gh release download dataset-pin-20260701          # -> data/ohlcv.pkl (verify sha starts f8625a8f)

# 2. run the frozen 0094 engine on the corrected universe
python scripts/run_bhanushali_weekly_rank.py
#    prints: corrected GROSS / corrected NET rows, continuous-slice Sharpes,
#            RANK-IC, bootstrap CI, DSR@n_trials, verdict
```
Expected NET row ≈ `Sh +1.132 | CAGR +24.7% | DD -42.4% | win 59%`, slices `+1.17/+1.05/+1.19`.
The dashboard/paper book is generated by `scripts/run_weekly_paper_cron.py` (same engine, live data,
forward inception) — not the backtest of record.

---

## 6. What we tested (so you can compare like-for-like)
Full ledger: [`docs/BHANUSHALI_TEST_LOG.md`](BHANUSHALI_TEST_LOG.md). The most likely mismatches:

| If the other chat ran… | It should get… | Because |
|---|---|---|
| The **taught letter-faithful** rules (RSI-35, candle-low stop, 1:2/1:3) | break-even gross, net loss | finding 0022 — the mechanics have no edge |
| A **survivor-only yfinance** pull | a *higher, unstable* number | survivorship inflates; drifts run-to-run |
| **Nifty-500-TRI** as the CRS index | ~0.68 Sharpe | finding 0037 — N50 admits the mid-cap trends |
| **Hash/arbitrary fill order** | ~0.90 Sharpe | finding 0038 — strongest-first fills add +0.23 |
| **Zero / flat cost** | a much higher CAGR | the tiered cost gap is real |
| A **different period** (e.g. 2015–2020, or 2022+) | very different | edge concentrates ≥2019; 2023 carries a lot |

---

## 7. Divergence checklist (work down in order)
1. **Data pin:** is `file_sha256()` = `f8625a8f…`? If not, you're on different bars → stop here, this
   explains most gaps.
2. **Universe:** survivor-only vs corrected (814 names, backfill + aliases)? PIT membership or
   today-membership (look-ahead)?
3. **Period:** exactly 2017-01-01 → end-2026? Warm-up for the 44-week SMA + 40-week RS SMA present?
4. **CRS index:** Nifty-50 (`^NSEI`), warmed from 2015 — not Nifty-500-TRI?
5. **Rules:** the §3 reconstruction, not the taught letter-faithful system?
6. **Weekly bars:** ISO-week bucketing; signal at the week close; entry the *following* week at the
   in-range open (not a breakout above the high)?
7. **Sizing & fills:** 2% risk of current equity; strongest-CRS-first; cash-capped?
8. **Exits:** decided at the weekly close, filled Monday; the 20-**day** SMA ×0.96 ratchet only after
   the +2R half; 13-week cap?
9. **Costs:** brokerage 0.03% + STT 0.10% + ADV-tiered slippage per leg?

If 1–9 all match and the number still differs, it is a genuine bug worth investigating — capture both
trade ledgers and diff them trade-by-trade (that is exactly how finding 0022's over-statement and
0095's DD-sign bug were caught).

---

*In-sample research on paper. Not investment advice; backtested/past performance does not indicate
future results. The only certifier is the forward wall (`forward/prereg.md`).*
