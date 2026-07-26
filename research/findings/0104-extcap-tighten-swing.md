# Finding 0104 — Tightening ext_cap 0.20→0.15 KILLs the book (cash redeploys into worse trades)

**Verdict:** **KILL** — keep live `ext_cap = 0.20`. Pre-reg
[0104](../../diagnostics/research/preregistry/0104-extcap-tighten-swing.md); harness
`scripts/run_0104_extcap_swing.py`. n_trials 131→132 (counted before run). Motivated by the FACT
2024-12-04 chart forensic (owner) + the matched-control extension gradient.

## Result (live config: A-only + max_risk 0.10 + max_notional 0.20 + config-P exit, corrected universe)

| | trades | win | expR | CAGR | Sharpe | MaxDD | 2022-26 |
|---|---|---|---|---|---|---|---|
| baseline ext_cap 0.20 | 130 | 58% | +1.74 | +27.2% | +1.227 | −39.5% | +0.91 |
| candidate ext_cap 0.15 | **161** | **48%** | **+0.99** | **+18.9%** | **+0.954** | −39.3% | **+0.49** |
| Δ | +31 | −10pp | −0.75 | **−8.3pp** | **−0.273** | +0.15pp | **−0.42** |

Pre-committed bar **3/4 FAIL** (only ΔMaxDD passes, and only by +0.15pp — no DD benefit). ΔSharpe CI
[−0.610, +0.112], n_indep≈37.

## Root cause — the exact mechanism we've now hit three times
Tightening the cap **skips the +15-20% extended fills → frees cash → the cash-constrained book redeploys
it into MORE, weaker signals** (130→**161** trades). Win rate collapses 58→48%, expR +1.74→+0.99, CAGR
−8.3pp. The freed cash doesn't sit idle or find better near-SMA entries (those are rare and can't be
manufactured) — it funds marginal trades that the +15-20% fills had been crowding out. **The extended
fills FACT lived in, though lower-quality per-trade, are better than what the book buys without them.**
And DD didn't even improve (−39.5→−39.3). This is pre-registered failure mode #1, and the **same
cash-redeployment inversion as 0095** (vol-target de-gross) and the same "IC ≠ portfolio Sharpe / ext IS
the engine" lesson as O-015/O-019/0079/O-022.

## The teaching point (why we test instead of eyeball)
The owner's chart forensic was sharp — FACT *was* an extended, worst-bucket fill, and the timing queue
*did* worsen it. But the portfolio verdict is the **opposite** of the per-trade intuition: cutting the
"bad-looking" extended fills makes the whole book materially worse. Combined with the **body-fraction
null** (winners median body 0.68 vs losers 0.66 — the JSL "green body" rule doesn't separate outcomes),
both loser-chart hypotheses this session are portfolio-negative or null. Loser-review *generates*
hypotheses; the matched-control + full re-run is what *kills* the ones that don't generalize — which is
most of them (the O-022 arc: every "make it safer" entry filter removes winners faster than losers).

## What actually killed FACT / the worst trades (unchanged from the forensic)
Not the entry filters. The real levers remain: (a) the **close-only weekly stop** that turns −1R into
−2..−5R on gaps (JSL −5.36R), and (b) **crash-clustering** of the concentrated book (a sizing/barbell
problem — `forward/action_plan.md`), which no entry rule touches. Do NOT re-propose ext_cap tightening or
a candle-body filter on this book.

## Next
The one un-refuted forensic lead is the **fill-priority queue delaying entries to worse prices** (FACT
Dec 2 → Dec 4, +2.8% / +16.6%→+20% ext) — a mechanic, not an entry filter. Quantify how often the CRS
cash-priority queue pushes fills to materially worse prices across the book before proposing any change.
