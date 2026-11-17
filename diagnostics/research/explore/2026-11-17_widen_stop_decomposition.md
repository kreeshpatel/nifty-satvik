# 2026-11-17 — What earns the widen-to-8% gain, and why 0152 is withdrawn

**Tier:** EXPLORE. Train window only (prices cut at 2024-06-30, cut asserted). No trial, no screen row, **no sealed
read**, nothing live changed. Standing counts: screens 24 · sealed opens 4 · n_trials 3 (unchanged).
Reproduce: `python pipelines/diagnostics/explore_widen_stop_decomposition.py 20` →
`2026-11-17_widen_stop_decomposition.json`. 20 paired paths, the standard draws, reported 2019-03-01..2024-06-30.

## The decomposition the owner asked for, corrected before it was run

The request was to split the gain into **(a) the stop effect at fixed position sizes** and **(b) an extra-seat funding
effect**. Measuring first: **position size is already fixed, and there is no funding-through-sizing channel at all.**

With 2% risk per trade, the 10% stop cap and the 20% per-name notional cap, risk sizing always asks for at least 20%
of equity, so **the notional cap binds on essentially every live position**: median weight at entry **0.200**, 55%
exactly at the cap. A wider stop therefore does not shrink the position by one share. My earlier description of this
rule — "a wider stop means a smaller position, so more seats get funded" — **was wrong**, and it is wrong in
`0152` §3 as written.

What a wider stop actually changes is two things:

1. **The stop level.** The exit sits further away, so fewer trades stop out — but each stop-out loses *more* rupees,
   because the position is the same size.
2. **The target distance.** Every level in the scaled exit is defined in R, and R is measured from entry to stop. A
   wider stop pushes the +2R tranche, the +2.5R pattern arm and the ratchets further away, and shrinks every reported R.

So the honest decomposition is **stop level** against **target distance**, which together are the whole rule. Two new
cfg-gated research modes isolate them (`stop_only`, `risk_basis_only`; off by default, goldens byte-identical).

## Result (20 paired paths, against live)

| arm | what it isolates | ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp (+ = shallower) | Δ mean R | Δ big winners | reading |
|---|---|---|---|---|---|---|---|
| **widen** (the 0152 candidate) | both channels | **+0.37 [+0.12, +0.70]** | **20/20** | +3.1 | +0.23 | +4 | robustly better |
| **stop_only** | the stop level alone | +0.20 [−0.20, +0.32] | 15/20 | **−3.6 (deeper)** | **+0.69** | 0 | **inside path noise** |
| **risk_basis_only** | the target distance alone | +0.01 [−0.17, +0.24] | 10/20 | +1.8 | −0.23 | +1 | inside path noise |

Medians: live Sharpe 1.25 / CAGR 26.1% / MaxDD −37.5%; widen 1.61 / 36.6% / −32.8%; stop_only 1.41 / 32.8% / −41.1%;
risk_basis_only 1.21 / 24.3% / −35.4%. The floor binds on **37.7%** of live trades (median live stop 9.3%).

**Seats, measured rather than assumed** (unperturbed run): mean names held live 7.08 → widen 7.32, stop_only 7.90,
risk_basis_only 7.95. Positions opened: live 77 → **widen 67**, stop_only 77, risk_basis_only 75. The full rule opens
**fewer** positions and holds slightly more at a time, because trades last longer. There is no extra-seat story.

## What this says

- **Neither channel is robust on its own.** The stop level carries about half the median gain (+0.20 of +0.37) but its
  5th percentile is below zero and it wins on only 15 of 20 paths. The target distance contributes essentially no
  Sharpe (+0.01).
- **The two channels work against each other on drawdown.** Moving the stop alone makes drawdown **3.6 points deeper**
  — the expected result of keeping the position size and losing more per stop-out. The target channel gives back
  +1.8 points. Only the combination is shallower (+3.1).
- **The full rule's +0.37 is an interaction**, not a sum: +0.20 and +0.01 do not add to +0.37. A result that exists
  only in the interaction of two levers, neither of which stands alone, is the fragile kind.
- **Per trade, the stop level is the good part** (+0.69 mean R, the best of the three) and the target distance is the
  bad part (−0.23, by construction, since a wider R denominator shrinks every R).

## Verdict on pre-registration 0152

The owner's rule, set before this ran: *"If (a) is inside noise, record 0152 as withdrawn with that reason."*

**(a) is inside path noise** (+0.20 [−0.20, +0.32], 15 of 20 paths). **0152 is WITHDRAWN**, unrun. No sealed read was
spent, the counter did not move, and no other floor level is opened on the back of this.

What would re-open it is not a different floor level — that is the same search with a new number. It would be a reason
to believe the interaction is structural rather than a product of this window, and that reason does not exist today.

## Engine

`scaled_exit`-adjacent lever `min_stop_mode` gains `"stop_only"` and `"risk_basis_only"` alongside `"skip"` and
`"widen"`, all cfg-gated and off by default. Both golden masters are byte-identical and
`tests/test_min_stop_distance.py` covers the new modes, including that the fixture cannot prove a stop-only change on
its own and says so rather than asserting something false.
