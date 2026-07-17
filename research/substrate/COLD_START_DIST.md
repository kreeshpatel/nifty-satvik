# Cold-start distribution — the FORWARD portfolio experience from an arbitrary start (measurement, no trial)

*Run 2026-07-16. Reproduce: `python scripts/rolling_coldstart_P.py`. Live config untouched.*

## The owner's question

> *"if i have already taken the initial stocks then what about the stocks that come my way from that day.
> how to test that."*

The 2017-start backtest (Rs 10L -> Rs 97.8L, 27% CAGR for P) is ONE history that caught 2020's +106% year.
It does not tell you what happens if you start TODAY. The method that does: a **rolling cold start** — fresh
Rs 10L on 30 different quarter-starts (2017Q1..2024Q2), each from **0 positions**, funding in CRS order and
skipping later signals for cash (the exact contention the owner asks about), forward 1yr and 2yr.

## Result — outcome depends HEAVILY on when you start

| config | horizon | p5 | p25 | **median** | p75 | p95 | P(loss) | worst..best start |
|---|---|---|---|---|---|---|---|---|
| **LIVE** | 1yr | -12.7% | +0.4% | **+17.3%** | +31.0% | +58.8% | **27%** | -20% .. +81% |
| **LIVE** | 2yr | -5.9% | +16.5% | **+35.6%** | +59.9% | +100.7% | 7% | -25% .. +107% |
| **P** | 1yr | -10.2% | +1.8% | **+9.0%** | +38.0% | +50.9% | **23%** | -12% .. +73% |
| **P** | 2yr | -15.1% | +8.6% | **+22.5%** | +73.9% | +131.0% | 13% | -31% .. +138% |

- **The spread is enormous:** 100-170 percentage points between the worst and best start date. A single
  backtest path hides this completely.
- **~1 in 4 chance of a DOWN first year** (LIVE 27%, P 23% P(loss) at 1yr), purely on start-date luck.
- **The headline CAGR is start-lucky.** The 2017 run's 20% (LIVE) / 27% (P) caught the 2020 monster; the
  realistic cold-start median annualises to ~16%/yr (LIVE 2yr) and ~11%/yr (P 2yr) — materially lower.
- **Cold-start max drawdown:** LIVE median -17% (1yr) / -24% (2yr); P -17% / -26%, worst starts to -43%.
  Consistent with COLD_START.md's ~-11% first-6-months concentration finding, extended to full horizons.

## The result that reframes P vs LIVE

**P's cold-start MEDIAN is LOWER and more dispersed than LIVE, despite P's higher full-backtest CAGR:**

| | full-run CAGR (2017) | cold-start 1yr median | cold-start 2yr median | 2yr downside (p5) |
|---|---|---|---|---|
| LIVE | 20.2% | **+17.3%** | **+35.6%** | -5.9% |
| P | 27.2% | +9.0% | +22.5% | **-15.1%** |

P looks better on the single 2017 path because its edge is **lumpy and tail-dependent** — it needs to catch
a monster year, which a random cold start often misses. LIVE delivers a **higher and more reliable** result
from an arbitrary start, with a shallower downside. **For "what happens when I actually start", LIVE
dominates P** — the opposite of what the headline 27% CAGR suggests. This is a third independent argument
for the shipped LIVE book over P (after: P fails the 2022-26 gate, and P's -39.5% DD violates the owner's
drawdown priority).

## How to read this for a live start

- Expect a **wide** first year: median ~+17% (LIVE) but a real ~25% chance of finishing down, and a
  plausible -12% to -20% in a bad-timed start. Size psychological expectations by the p25, not the median.
- The **2-year** picture is much steadier (P(loss) 7% for LIVE) — the book needs ~2-3 months to ramp
  (COLD_START.md) and a full cycle to express its edge. Judge it over years, not the first quarter.
- Capital contention is real and modelled here: the freshly-funded book skips later signals for cash until
  positions half-book at 2R and free capital. That is why the first months are concentrated and the ramp
  takes time — not a bug, the documented cold-start profile.

## Caveat

Still IN-SAMPLE (2017-2026). P fails the 2022-26 gate; both books' edges concentrate in the 2017-21 bull.
The cold-start distribution is the honest read of *path/start-date dependence*, but it is NOT a forward
forecast — the forward wall remains the only out-of-sample certifier.
