# Bhanushali Arc — Complete Test Log

*Every path we tested on Siddharth Bhanushali's method, with the honest verdict and the numbers.
Compiled from `research/findings/0020`–`0038`, `0095`–`0096` and the rows in
[`research/overlay_registry.md`](../research/overlay_registry.md). All metrics are **NET after tiered
real costs** unless marked GROSS; sub-2019 folds and old v1 7–14d results are not comparable and are
excluded. Nothing here is certified — the bar is DSR > 0.95 and the only certifier is the forward
wall.*

Two numbering systems appear: the **finding** number (`0020`–`0038`) and, once trials became
DSR-counted, the **pre-registration / trial** number (`0083`–`0096`). The map is given per row.

---

## Master table (chronological by finding)

| Finding | Pre-reg | Path tested | Net Sharpe | Net CAGR | MaxDD | Verdict |
|---|---|---|---|---|---|---|
| **0020** | — | 6-step setup tested "all together" (RSI-35 + pullback, taught exits) | ~0 (trivial) | — | — | **KILL** — real but trivial entry edge, eaten by costs |
| **0021** | 0083 | Volume-confirmed momentum-pullback (distilled hybrid: visible trend + pullback + HVC + wide ATR + let-run) | **+1.09** | — | — | **UNDERPOWERED** — CI [+0.40,+1.78] excludes 0, but DSR@101 0.60 |
| **0022** | — | The COMPLETE taught system, letter-faithful (Engine A RSI-35 + Engine B pullback) | +0.09 GROSS | −13% (min-cost) | — | **KILL** — no gross edge; cost-killed on ~5,100%/yr turnover |
| **0023** | — | His REAL method (method-faithful: trailing/let-winners-run + volume + watchlist + 2% sizing) | +0.15…+0.34 (gross +0.39) | +5.9% GROSS | — | **Real but modest** — edge lives in let-winners-run + volume; below base |
| **0024** | — | Run as a PRACTITIONER (weekly top-50 watchlist, no-overtrade throttle, regime pause) | +0.19 | **net +1.4%/yr** | **−19%** | **Risk fixed, return too low** — 260→21 trades/yr; RSI leg loses (−0.49) |
| **0025** | — | Path-1: 4×ATR initial stop (vs candle-low), corrected universe | **+0.397** | +2.8% | **−12.1%** | **Misses the +0.40 bar by 0.003** — recorded, not relitigated |
| **0026** | 0084 | Owner six-step variant (weekly-bucket→daily pullback→green buy-stop; scaled partials + MA-breach trail) | **+0.477** | +8.6% | −37.2% | **UNDERPOWERED** — DSR@102 0.085 |
| **0027** | 0085 | Runner-trail (post-2R rides EMA20×0.96 ratchet, 63d cap) | **+0.59** | — | — | **UNDERPOWERED** — best exit geometry of the funnel |
| **0028** | 0086 | Comparative-RS entry gate on the six-step book | ΔSharpe **−0.14** | — | — | **UNDERPOWERED/WEAK** — fixes 2025 but breaks the book |
| **0029** | — | 0085 end-to-end validation (leakage / robustness / execution audit) | — | — | — | **Diagnostic** — leakage CLEAN; param+cost FRAGILE; exec optimistic ~15%; chop is the bleed |
| **0030** | 0087 | Trend-death exit (EMA44 stall / deep −6.5%) on all positions + T+1 recycle | **−0.073** | −4.3% | −53.9% | **KILL** — worse on every axis; did not free capital |
| **0031** | 0088 | Weekly-confirmation breakout entry on the 0085 book | +0.215 | **+2.3%** | −41.3% | **KILL** — CAGR more than halved (opposite of the goal) |
| **0032** | 0089 | Fully-weekly six-step (in-range open entry + weekly-close exits) | **+0.63** | +11.8% | **−54.3%** | **UNDERPOWERED** — family-best raw Sharpe, worst DD |
| **0033** | 0090 | Market-regime entry filter (block entries below N500-TRI 44-wk EMA) | +0.447 | +7.0% | −55.6% | **KILL** — cut CAGR 4.8pp, DD got *worse* |
| **0034** | 0091 | All-SMA fully-weekly (44-wk SMA + 20-day SMA trail; no EMA anywhere) | **+0.869** | **+18.2%** | −41.5% | **UNDERPOWERED** — arc-best then; robust plateau; first CI-low>0; DSR 0.466 |
| **0035** | 0092 | Tighten 0091 to "clean" pullback charts (slope floor + tight band + qgreen) | +0.142 | **+0.5%** | **−61.0%** | **KILL** — the definitive "backtest > your eyes" result |
| **0036** | 0093 | Slope + quality-green + CRS filter (RS vs N500-TRI) on the loose band | **+0.677** | +11.9% | **−36.8%** | **UNDERPOWERED** — first entry-side change that didn't KILL; more robust |
| **0037** | 0093-N50 | Same, CRS vs the intended **Nifty-50** (2015 data) | **+0.900** | **+18.7%** | −42.5% | **UNDERPOWERED** — strongest/most robust; DSR 0.745 (arc high) |
| **0038** | 0094 | **CRS-strength fill ranking** (fund strongest CRS-distance first) | **+1.132** | **+24.7%** | −42.4% | **SHIPPED to the live paper book** — DSR 0.894, ordering-probe verified |
| **0095** | 0095 | Vol-target de-gross sizing ported to the 0094 book | 1.13→**0.73** | 24.7→13.8% | −40.3% | **KILL** — de-gross inverts on a cash-constrained book |
| **0096** | 0096 | Sector-relative CRS denominator (RS vs own-sector index) | 1.13→**0.46** | 24.7→7.6% | −45.0% | **KILL** — residualising strips the trend edge |

*(0025's number is the corrected-universe 4×ATR cell; 0021's +1.09 is the standalone hybrid; 0095/0096
show the 0094 baseline → overlay.)*

---

## Read by research thread (what the arc actually learned)

### Thread A — the raw entries: momentum wins, mean-reversion loses
- **RSI-oversold is triple-killed** (0020, 0022, 0024): buying RSI < 35 weakness catches falling
  knives — negative forward excess and a losing standalone Sharpe every time it was isolated.
  Bollinger-lower-band (0020) same. **Do not relitigate.**
- **Momentum-continuation + volume wins:** the **HVC / high-volume breakout was the single best signal
  measured (+0.56pp/20d)** — his "volume is the voice of god" is empirically his most useful tool.
  Hidden divergence (+0.39pp) also positive. The **strong-uptrend pullback** (his "magical placement")
  is the core edge.
- **His "visible uptrend" emphasis is right:** a weak "MA ticked up" filter → ~0 edge; a strong
  sustained 44-SMA filter **doubled** the pullback edge (−0.11 → +0.48pp).

### Thread B — the three faithful tests (letter → method → practitioner)
- **Letter-faithful (0022):** the taught system as-written is **break-even gross**, cost-killed on
  turnover. The mechanics have no edge.
- **Method-faithful (0023):** add trailing/let-winners-run + volume + curated watchlist + 2% sizing →
  a **genuine positive gross edge** (the trail rides 18–28R rockets). **Volume is load-bearing**
  (remove it → −0.90 Sharpe). Net modest, below base.
- **Practitioner (0024):** add the portfolio process → **overtrading vanishes (260→21 tr/yr), DD
  −92%→−19%**, but realized risk ~1%/trade caps return at **net +1.4%/yr**. The process rescues the
  *risk* profile, not the *return*.

### Thread C — exit geometry is where the funnel's edge lives
0022 taught exits (KILL, −1.6) → **0025 4×ATR (+0.397)** → **0026 scaled partials + MA-breach
(+0.477)** → **0027 runner-trail (+0.59)**. The candle-low stop bleeds on noise; wide stops that let
winners run are the lever. Confirmed by our own let-winners-run results (0047/0071).

### Thread D — every entry gate / regime filter fails (5 straight)
O-001, A5, **0028 (RS gate, −0.14)**, **0033/0090 (market-regime, −4.8pp CAGR, DD worse)**, 0086 —
all KILL/UNDERPOWERED. Mechanism: **blocking new entries can't rescue already-deployed capital**, so
the drawdown (an exit/exposure problem) is untouched while recovery entries are lost. **Settled — do
not re-propose an entry-side regime gate on this family.** (A regime pause survives ONLY inside the
practitioner B-sleeve spec, sleeve-internal.)

### Thread E — capital efficiency destroys this book
**0030/0087 recycle (−0.073, DD −53.9%)** and 0087's twin: faster cycling / T+1-only entry collapse
expectancy (~100% of profit lives in the few long-held winners — 0029). **The locked capital IS the
strategy.** Capital-efficiency concerns route to portfolio-level allocation, never intra-sleeve churn.

### Thread F — tightening the entry removes edge, not noise (3 straight)
**0035/0092 (+0.5% CAGR, −61% DD), 0088, 0086** — stricter/"cleaner" entries all lose. The extended,
"ugly" names the eye rejects are where the trend money is; a "visibly rising" MA is a *late* signal.
**The definitive "backtest > your eyes" lesson (0035).**

### Thread G — the CRS-denominator axis is fully mapped
Broad cap-weighted **N500-TRI (0036, +0.677)** < large-cap **Nifty-50 (0037, +0.900)** ; residualised
**sector-relative (0096, +0.46)** is worst. **Market-relative RS vs the large-cap Nifty-50 is
correct** — the book profits from stocks *beating the large-cap tape*, not from breadth or
idiosyncratic strength.

### Thread H — the winning assembly, and its ceiling
The fully-weekly all-SMA book (0034/0091) + Nifty-50 CRS (0037) + CRS-rank fills (0038/0094) is the
**live paper book**: **Sharpe 1.132 / CAGR 24.7% / DD −42.4% / DSR 0.894** — the closest the whole
program has come to the 0.95 bar, but still under it. The two 2026-07-09 sizing/denominator overlays
(0095 vol-target, 0096 sector-CRS) both KILL, confirming the edge is **concentrated and factor-driven
and resists intra-book re-engineering.** The only lever left is portfolio-level allocation, decided on
the forward wall.

---

## Bottom line
- **What's real:** trade a clearly-rising trend, buy strength pulling back (the swing-low/44-SMA
  retest), confirm with **volume/HVC**, use a **wide stop and let winners run**, size at 2%. These are
  his *principles*, and they match our own validated findings.
- **What isn't:** RSI-oversold / Bollinger mean-reversion entries, tight candle-low stops, entry-side
  regime gates, faster capital cycling, and "cleaner"/tighter entries — all measured, all rejected.
- **Status:** the best assembly (live 0094 book) is **UNDERPOWERED in-sample (DSR 0.894 < 0.95)**. It
  is a **forward-watch paper book**; the **2026-10-01 review** and the forward wall are the only
  certifiers. See [`forward/prereg.md`](../forward/prereg.md) and the dashboard **Forward Review** tile.

*Not investment advice; backtested/past performance does not indicate future results.*
