# 2027-01-01 quarterly review — candidates and their evidence

Started 2026-11-13 at the owner's request, so the parked items are written down where the review will find them.
Each row cites the evidence file, never a remembered number. Standing counts are read from the ledgers at review time.

| # | candidate | what it changes | evidence (train window unless stated) | status |
|---|---|---|---|---|
| 1 | **h5-30** (pre-reg 0151) | extension cap, Grade-A gate and stop-width cap off; per-name cap 30% | train 20 paths +0.34 [−0.10, +0.59]; **sealed read S4: KILL** (finding 0151: 14/20 paths, P4 and P5 fail; median +0.21). Uncapped h5 has no sealed evidence and may not be opened on this slice | **CLOSED: KILL (2026-11 harness, live book)**. The bigger point for the review: the live book itself had median Sharpe −0.41 on the sealed slice |
| 2 | **Half size when the Nifty is below its 40-week SMA** | new entries at half size in that state | 20 paths: +0.22 [−0.13, +0.37], 16/20 better; MaxDD +3.9pp [−2.4, +11.3]; both inside noise (`explore/2026-11-13_ensemble_jan_candidates.md`). The zero-size version (S1) is robustly worse on Sharpe | **PARKED by the owner 2026-11-13** for this review |
| 3 | **Skip signals with results due within 4 weeks** | entry filter (PIT board-meeting calendar) | 20 paths: Sharpe −0.04 (inside noise), MaxDD **+3.1pp, robustly shallower** (19/20). A drawdown dial, not an edge. Prior: 0121 earnings deferral, banked, decision-margin-negative | **PARKED by the owner 2026-11-13** for this review |
| 4 | Breakeven stop at +1R | stop to entry once a trade reaches +1R | 20 paths +0.15 [−0.04, +0.35]; armed on the week's real high −0.01 (`explore/2026-11-13_roundtrip_losers_and_plus1r_arms.md`). Forward shadow column logged since 2026-11-09 (`results/shadow_exit_forward.json`) | read the forward shadow; no in-sample case |
| 5 | Weak-market mean-reversion sleeve | a separate WATCHED paper book | not backtested; frozen spec and draft amendment (`forward/drafts/2026-11-13_amendment_mr_sleeve_DRAFT.md`) | awaiting the owner's signature to start paper logging |
| 6 | D6 filter-before-rank (seat-waste fix) | Grade-A ranking after the membership filter | 20 paths +0.04 [−0.06, +0.26], inside noise (`explore/2026-11-03_ensemble_breakeven_d6.json`) | queued earlier; weak case |

Closed for this review (measured, did not help): tighter, daily, trailing and partial-at-+1R exits (2026-11-12, 2026-11-13);
the first-tranche level (+1R was a spike); adding a unit at +1R (no effect under the live caps); midcap breadth and
own-40-week filters (dropped by the owner).

## Added 2026-11-14 (ADR-0020 owner decisions)

- **Live swing capital.** No change and no additions before its 26-week mark (early January 2027). Decide its capital here. It is at PILOT; PILOT is nominally ₹2,00,000 of the ₹20,00,000 system capital.
- **First lifecycle verdict date for the swing.** Its record reaches 26 weeks in early January 2027; before that its status is provisional.
- **Index-fund purchases.** Core capital goes into a Nifty Midcap150 Momentum 50 index fund in three equal monthly parts while momentum is in PAPER; confirm the amount and that the parts were bought.

## Added 2026-11-17 (owner)

- **Sizing: the 20% notional cap binds on ~55% of positions, so the 2% risk rule rarely decides size; review whether
  per-trade rupee risk should be made consistent.** Measured on the train window while decomposing the widen-to-8%
  rule (`explore/2026-11-17_widen_stop_decomposition.md`, §"sizing_fact" in the JSON): median weight at entry
  **0.200**, with **55%** of positions sitting exactly at the per-name notional cap. With 2% risk, the 10% stop cap
  and the 20% notional cap, risk sizing always asks for at least 20% of equity, so the notional cap is the binding
  constraint on most fills and the stop distance does not set the position size. Two consequences for the review:
  rupee risk per trade varies with the stop (a 5% stop risks half what a 10% stop risks, for the same rupees
  committed), and **no stop-width lever can change position size** — which is why 0152's funding premise was wrong.
  Nothing is proposed here; the question for the review is whether per-trade rupee risk should be equalised, and at
  what cost in concentration.

### Measured 2026-11-17, closed, no action asked

- **Widen tight stops to 8%** — pre-registration 0152 **WITHDRAWN unrun**. The stop level alone is inside path noise
  (+0.20 [−0.20, +0.32], 15/20 paths, drawdown 3.6pp deeper); the full rule's +0.37 is an interaction of two levers,
  neither robust alone (`explore/2026-11-17_widen_stop_decomposition.md`).
- **FII/DII institutional positioning** — descriptive null; no monotone relation in any of eight features, levels are
  largely the trend state already in hand, and it does not separate the weak-but-calm state
  (`explore/2026-11-17_fii_dii_positioning.md`).
- **IC decay of the two rankers** — the first version of this measurement used cumulative returns and was
  **withdrawn** the same day. On the corrected **marginal** measure each ranker's per-week information is flat out
  to about 13 weeks and dies between 26 and 52; half-life 21.6 weeks [9.0, 71.7] for momentum and 32.4 weeks
  [11.4, 255.9] for the swing ranker, intervals overlapping, so neither is shown to decay faster
  (`explore/2026-11-17_ic_marginal_decay.md`; the withdrawn version is `explore/2026-11-17_ic_decay_halflife.md`).
