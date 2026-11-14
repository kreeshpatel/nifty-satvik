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
