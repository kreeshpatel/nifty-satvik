# Finding — the book is CASH-STARVED, and the CRS queue spends that scarce cash on the extended version of the same setup

*Measurement only — no trial spent, live config untouched. 2026-07-16. From the owner's round-3 chart
review (`scripts/diag_owner_charts3.py`).*

## The owner's observation

> *"in maxhealth we could have entered at the bottom but we entered at the top, why?"*
> *"we should have entered mindacorp at the open of 13jan as setup was ready with 30 dec and 6 jan candles"*

**Both are correct, and the engine's own rule state proves it.**

## The early signals fired — nothing in the rules blocked them

| | window opens | fill price | ext vs SMA | **CRS rank** | member | ext_cap |
|---|---|---|---|---|---|---|
| **MAXHEALTH** | 2025-03-17 | **994.05** | **+2.0%** | **0.071** | ✓ | allows |
| MAXHEALTH | 2025-03-24 | 1173.30 | +19.4% | **0.206** | ✓ | allows |
| **MINDACORP** | 2025-01-06 | **504.59** | **+4.1%** | **0.027** | ✓ | allows |
| **MINDACORP** | 2025-01-13 | **515.35** | **+5.8%** | **0.086** | ✓ | allows |
| MINDACORP | 2025-01-20 | 582.89 | +18.5% | **0.208** | ✓ | allows |

The signal fired, the window opened, a daily open landed in-band, membership held, the extension cap
allowed it. **The book took none of the cheap ones and filled the expensive one.**

## The mechanism — cash scarcity × CRS ordering

`skipped_cash` = **19,151** (spec book) / **19,728** (base). The engine abandons ~19-20k fill attempts
for lack of cash. It takes ~181 of ~8,518 signal windows (**~2%**). **Cash — not the signal — is what
decides the book.**

Cash is handed out **strongest-CRS-first**. And look at the CRS column above: *the same stock, the same
setup*, carries a **3-8× higher CRS rank once it is extended**. So the cheap early window sits at the
back of the queue and loses the cash to other names; the stock only wins the queue when it is expensive.

**This is NOT the documented "RS-lag late entry"** (`trade-forensic-lessons`, lever 1), which says the
`rs > SMA40(rs)` gate certifies one candle too late. That hypothesis is **wrong for these cases**: the RS
term was **TRUE on every early week** (2024-12-30, 2025-01-06, 2025-01-13 all fired). The signal was on
time. **The fill queue starved it.** New mechanism, distinct diagnosis.

It is also the operational face of `CRS_DISSECTED` §5 ("extension IS relative strength"): here we watch a
single name's CRS rank climb 0.027 → 0.086 → 0.208 as it extends, and the queue serve it only at 0.208.

## What the cheap entry was worth — run with cash unbound

| | entry | price | ext | **R** |
|---|---|---|---|---|
| MAXHEALTH (actual) | 2025-03-24 | 1173.30 | +19.4% | **−1.38** |
| MAXHEALTH (early window, uncapped) | 2025-03-17 | **994.05** | +2.0% | **+3.00** (trail) |
| MINDACORP (actual) | 2025-01-20 | 582.89 | +18.5% | **−1.12** |
| MINDACORP (early windows, uncapped) | 2025-02-24 / 03-10 | 512.54 / 513.58 | — | **−1.59 / −1.09** |

**MAXHEALTH is a −1.38R → +3.00R swing on the same setup one week apart.** MINDACORP goes the *other*
way. **n=2, opposite signs: the mechanism is established, the profit from fixing it is NOT.** Do not
conclude "enter early = better" from this.

## Why the obvious fix is already dead

Changing the queue to prefer near-SMA fills was tested: **`near_sma` fill-priority → −0.80 Sharpe**
(`trade-forensic-lessons`). It displaces the CRS-strongest names, which *are* the runners. **The
CRS-strongest-first fill order is load-bearing.** Do not re-propose reordering the queue.

## The unspent lever — MORE SLOTS, not a different queue

The queue is only decisive *because cash is scarce*. Nobody has tested **lowering `risk_per_trade` so more
names fit**:

| config | R% | notional/name = risk%÷R% | names |
|---|---|---|---|
| base | 14.2 | 14% | ~7 |
| spec (R cap 10%) | 9.2 | **22%** | **~4-5** |
| **untested: spec at risk 1.3%** | 9.2 | **14%** | **~7** |
| **untested: spec at risk 0.9%** | 9.2 | **10%** | **~10** |

This is now **triply motivated**: it fixes the spec book's concentration (the one real cost of the R cap),
it reduces cash starvation, and it is the deconfounding arm `FINDING_small_candle` declined to run. It is
**not** a queue reorder (killed) — it is more seats at the table.

**Caveat, stated up front:** more slots also means more of the *mediocre* signals, and the Monte-Carlo
work showed CRS sits at the 99-100th percentile of selection skill — diluting toward the pool mean may
simply pull the book toward the random null (0.74). The counter is that shorter holds already recycle
capital faster (spec skips *fewer* than base despite bigger positions). Genuinely uncertain → worth one
pre-registered trial.

## A correction to my own prior

I predicted the R cap would worsen cash starvation via concentration. **It did not** — 19,151 (spec) vs
19,728 (base). Shorter holds recycle capital faster, which offsets the bigger positions. Recorded.

## Verdict

**No trial spent.** Mechanism established and newly diagnosed; no config change proposed on n=2. Live
config FROZEN.

## Next setup

The slots experiment above, pre-registered, with `risk_per_trade` frozen before the run and the DSR bar
acknowledged at trial 117.
