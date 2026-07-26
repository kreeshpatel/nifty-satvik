# Finding 0102 — Always-on deep-OTM put ladder: KILL (single-event lottery + premium-leverage artifact)

**Verdict:** **KILL.** Pre-reg [0102](../../diagnostics/research/preregistry/0102-continuous-putladder-swing.md);
harness `scripts/run_0102_putladder_swing.py`; data `data/options_oi_pit.parquet` + `data/_fo_oi_raw.parquet`.
n_trials 130→131 (counted before run).

## Result (corrected universe 2017-2026, NET, continuous-slice)
Engine invariant OK (book leg reproduces 0094 byte-for-byte). Headline looks seductive — and is a mirage:

| | Sharpe | CAGR | MaxDD | Calmar | 2022-26 slice |
|---|---|---|---|---|---|
| book | +1.132 | +24.7% | −42.4% | 0.58 | +1.19 |
| + put ladder | **+0.581** | +29.2% | −25.0% | 1.17 | +1.06 |
| Δ | **−0.551** | +4.50pp | +17.34pp | +0.59 | −0.136 |

Pre-committed bar **2/4 FAIL** (ΔSharpe −0.551, 2022-26 slice −0.136). ΔSharpe CI [−0.823, +0.125].

## Root cause — the DD/CAGR "win" is one non-reproducible, artifact-inflated event
- **111 monthly cycles, exactly 1 paid** (COVID). **Ex-2020 net = −₹295k: every other year is pure drag.**
- The single 2020 cycle: bought a 10%-OTM put (K 10450, spot 11631) on 2020-02-27 for **0.45 index points**.
  Budget ₹1,771 ÷ 0.45 = **3,936 units** → COVID intrinsic 903 pts → **₹3.56M payoff = 167% of book NAV
  from one ₹1,771 put** (a ~2000× single-trade return).
- **That is a data-realism artifact, not an edge.** `units = budget / premium` explodes when the premium is
  a tiny **illiquid far-strike EOD print** (20/111 puts priced < 5 pts; this one 0.45). You cannot buy ~52
  lots at a 0.45 quote; the fill/impact is fiction. The headline DD/CAGR improvement is this phantom
  leverage, concentrated in one crash.
- Sharpe collapsed (−0.551) because the ladder injects enormous idiosyncratic variance (one giant jump then
  steady bleed) — the opposite of a smooth risk reducer.

All three pre-registered failure modes fired: drag > payoff ex-COVID (#1); the index hedge doesn't match
the book's idiosyncratic DD in the non-COVID years (#2, per 0101); monetization triggered once in 9 years (#3).

## Why a "realistic" version is not a rescue (do NOT relitigate)
A liquidity-realistic ladder (lot-based sizing, min-premium floor, liquid strikes only) buys **fewer** units
→ **smaller** COVID payoff → strictly worse net, on top of the same drag. The artifact HELPED this result;
removing it makes it worse. Combined with 0101 (index signals don't lead the book's idiosyncratic DD) and
AQR's negative-carry prior, the continuous index put hedge has no viable form here.

## Program consequence — the options tail-hedge arc on the swing book is CLOSED
Three converging KILLs settle it: timed put-spread on a coincident IV signal (0100), all timed triggers
pre-refuted by the lead-lag screen (0101), and now the always-on convex ladder (0102, a COVID lottery).
The swing book's −42% drawdown is **idiosyncratic/concentrated** (4-5 names) and **index options cannot
hedge it** — a structural mismatch, not a tuning problem. Do not re-propose an index-options DD overlay on
this book. The only un-refuted DD lever remains **sleeve-level allocation** (O-018 ERC / a smaller fraction
of total capital on the forward wall), never an intra-book or index-hedge overlay.

## Reusable lesson banked
Any future options backtest must **floor the premium / size by lots / restrict to liquid strikes** — dividing
a rupee budget by a sub-1-point illiquid EOD close manufactures phantom convexity. Add this to the options
harness before any further options work. (The PIT OI data layer + knowledge digest remain valid assets.)
