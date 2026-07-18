# Losing-trade gap hunt — the problems to look for in EACH loser (0094 book)

Goal: go through every losing trade in the frozen 0094 book and tag the **one gap** that caused it, so the
most common gaps define what to fix. Fresh start from 0094 (Sharpe 1.132 / 255 trades, 66 stop + N time
losers). Each loser is tagged with its DOMINANT gap from the checklist below.

## The candidate gaps (what can go wrong in a trade)

1. **Late / extended entry** — the signal fires on the setup week, but we buy the *next* week's open. If
   the stock rebounded hard, we fill far above the 44-SMA (extended), not on the pullback. `ext_vs_SMA%`.
2. **Wide stop** — stop = setup-week low. On an extended entry the stop is 15–25% below entry → a big loss
   in %-terms even at a "1R" stop. `risk% = (entry − stop)/entry`.
3. **Gap-through stop** — the stop is a weekly-close decision executed at next-Monday's open; a gap-down
   Monday fills *below* the stop → loses more than 1R. `exit_px < stop`.
4. **Sizing** — fixed 2%-risk sizing means position size = ~200/risk%. A tight stop → oversized position
   (concentration); a wide stop → tiny position (no contribution). Flag both tails.
5. **Fast reversal / whipsaw** — entered, reversed within ~2 weeks and stopped. `held ≤ 2 wk & stop`.
6. **Time-cap bleed** — held the full 13 weeks and exited flat/negative (dead capital). `reason = time & R ≤ 0`.
7. **Exit gave back a gain** — hit +2R (booked half) then the runner reversed to a net loss. `half_done & R < 0`.
8. **Crash cohort** — stopped inside a market-wide crash week (many names down together), not stock-specific.
9. **Stop placement** — is the setup-candle low the right stop? (design question, flagged for the exit rework)

## Owner-named problems to keep front of mind (the rebuild levers)
- **Sizing** — the fixed 2% rule and its concentration tails (gap 4).
- **Late entry** — buying the next-week open instead of the pullback (gap 1).
- **Proper exit strategy** — the 2R half + trail + 13-week cap: is it the right exit? (gaps 6, 7).
- **Stop-loss = setup-candle low** — is this the right stop, or too wide on extended entries? (gaps 2, 3, 9).

## Method
`scripts/loser_gap_scan.py` tags every 0094 loser with its dominant gap (priority: gap-through → wide-stop
→ late-entry → fast-reversal → time-bleed → giveback → crash). Output: `loser_gaps.csv` + a gap-frequency
summary. Run on /loop to keep deepening — each pass adds detail and refines the taxonomy.
