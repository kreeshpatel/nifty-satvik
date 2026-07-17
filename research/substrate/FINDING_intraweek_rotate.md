# Finding — intraweek 2R/3R rotation: higher Sharpe/CAGR IN-SAMPLE, but it caps the fat tail and fails the gate

*Pre-registered `research/preregistry_intraweek_rotate.md`, frozen before the run (R4). n_trials 124->126.
Guards: A-only baseline parity 1.004/171 PASS.*

## The owner's claim

> *"if our 2R or 3R hits intraweek then why not sell. that how we can rotate the capital also get into
> new opportunities"*

A CAPITAL-VELOCITY claim, not profit protection. Tested on the LIVE book (A-only + LIVE_DISCIPLINE):
- **A: tp_on_high** — book the 2R half at the intraweek high (resting limit) vs the weekly close.
- **B: scaled_exit 60%@2R / 40%@3R** — full intraweek target rotation (resting limits), sma-break runner.

## Result

| arm | tr | full Sh | CAGR | MaxDD | **2022-26** | win | max R | R>=3 | skip_cash |
|---|---|---|---|---|---|---|---|---|---|
| LIVE (P2 trend exit) | 184 | 1.055 | 20.2% | -31.2% | **1.04** | 51% | **16.7** | 23 | 3419 |
| A: + tp_on_high | 220 | 0.909 | 16.8% | -43.5% | 0.70 | 54% | - | - | 3308 |
| **B: scaled 60/40** | 250 | **1.161** | **22.1%** | -31.5% | **1.03** | 57% | **2.4** | **0** | 3256 |

- **A KILLED** (-0.146 Sharpe, DD -43.5%): books half-winners early but keeps full losers -> asymmetric.
- **B is the interesting one:** +0.106 full Sharpe, +1.9pp CAGR, flat DD, +6pp win rate, +66 trades.

## Why B does NOT ship, despite the aggregate lift

1. **Fails the pre-registered gate.** The R3 gate is the 2022-26 continuous slice: **1.04 -> 1.03, flat**
   (-0.01, not the +0.10 required). The entire full-sample lift is **2017-21 (1.07 -> 1.28)** — a
   trending bull run where 2R targets hit reliably. The gate period, the most forward-relevant, is flat.
2. **It removes the fat tail entirely.** Max winner **16.7R -> 2.4R**; trades >=3R **23 -> 0**. Every winner
   is capped at the blended 0.6*2R+0.4*3R = 2.4R. This is the exact truncation seven prior findings
   (FINDING_taught_mechanics, EXT_IS_THE_ENGINE, FINDING_owner_6040_poscap, small-candle, more-slots,
   lockin) identified as the edge. B's higher Sharpe is *smoothness* — many small consistent wins — not
   more edge; sum-R 113 -> 147 comes from 250 small wins, not from the tail.
3. **In-sample at trial 126** — DSR heavily deflated; a +0.10 in-sample delta certifies nothing.

## The rotation claim — PARTIALLY validated, but not via cash

`skipped_cash` barely moved (3419 -> 3256). On the A-only book cash starvation is mild (the 19k figure in
FINDING_cash_starvation was the all-grades book). So B does **not** work by un-starving cash. The +66
trades come from **faster capital turnover** (holds 12.4 -> 10.1wk) — the same capital doing more trades
over time. That IS a real rotation effect, and it did not hurt (win rate rose). The owner's intuition is
mechanically sound; it is just inseparable from capping the winner (you cannot rotate out of a trade
without booking it, and booking it at 2R/3R caps it).

## Why B != the earlier 60/40 KILL

FINDING_owner_6040_poscap killed 60/40 at 0.64 / DD -54.5% — but bundled with **R-cap-5%**, which forced
40% notional/name. Here with **R-cap-10%** + A-only the notional stays ~20% and the geometry is sane. So
that kill was confounded by the 5% cap; B is the clean read, and clean, it does not lose — it trades the
tail for smoothness.

## The genuine fork this exposes

This is the classic **lumpy-fat-tail vs smooth-many-small-wins** choice, and it is the ONLY lever all
session that improved the aggregate in-sample:

- **LIVE (shipped):** Sharpe 1.06, CAGR 20.2%, win 51%, one 16.7R monster carries years. Tail-dependent.
- **B (rotation):** Sharpe 1.16, CAGR 22.1%, win 57%, max 2.4R, smooth. Regime-dependent (needs 2R to hit).

The program has always favored the tail on the thesis that momentum's edge lives in the rare monster.
B says in-sample that on THIS book, capping at 2.4R and rotating is higher Sharpe AND CAGR. **Only
out-of-sample evidence resolves it** — precisely the low-vol-sleeve situation. The 2022-26-flat result is
the warning: B's edge showed up in the 2017-21 bull and vanished in the recent chop, which is where a
tail-capping target book is expected to struggle.

## Verdict

**Does NOT ship (R11): fails the pre-registered 2022-26 gate.** NOT a KILL either — it is a **forward-wall
candidate / owner fork**, the session's one genuine aggregate improvement, held back by (a) a flat gate
period, (b) total fat-tail removal against the program thesis, (c) in-sample trial 126. The owner decides
whether smoothness-over-tail is the book they want; if so, the honest route is the forward wall, not an
in-sample cfg flip.

## Next setup

If the owner wants to pursue B: route it to the forward wall as a second book alongside LIVE, and let
~2-3 quarters of out-of-sample decide lumpy-vs-smooth. Do NOT retune the 60/40 split in-sample (R4). If
not, LIVE stands and the exit question is closed.
