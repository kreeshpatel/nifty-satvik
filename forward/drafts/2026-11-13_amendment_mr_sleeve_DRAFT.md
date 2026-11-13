# DRAFT — amendment to `forward/prereg_swing.md`, for the owner to review, edit and sign

**Status: DRAFT. Not in force.** It becomes the amendment only when the owner pastes it, dated and signed, at the end of
`forward/prereg_swing.md`, in the same commit that wires the logger. Nothing below has been backtested, and no
parameter was fitted. Source proposal: `diagnostics/research/explore/2026-11-13_weak_market_mr_sleeve_proposal.md`.

---

## Amendment 2026-11-__ — register the `mr-weak` WATCHED book (a §2 recorded logged book)

**What:** a weak-market mean-reversion sleeve, registered as a **WATCHED / observational** book. It carries **no paper
or real capital**; A-only stays the capital vehicle. The §2 cap on capital books is intact. Like the blend-hybrid book
(2026-07-26), this is an additional *logged* book, recorded here per the "no third without a recorded swap" rule.

**Why:** every one of the 55 live swing trades (2026-07-06 → 2026-11-13) was signalled while the Nifty's weekly close
was below its 40-week SMA, and the swing book lost money there. Removing swing entries in that state cuts drawdown but
costs Sharpe on every one of 20 paths (2026-11-12 ensemble), because rebounds start there too. A small book that is
active only in that state, and earns from short rebounds in relative-strength leaders, could diversify the swing book
across time. Prior evidence against (`KILL 0020/0022/0024`, v1 epoch, 7–14-day base book, not re-tested under the
current harness) sets priority, not closure. This rule adds a regime gate, a strength filter, a time exit and a wide
disaster stop, none of which those studies had.

**Fixed spec (frozen at signing; not retunable during the logging period):**

| part | rule |
|---|---|
| active | only when the Nifty's last weekly close is below its 40-week SMA; no new entries otherwise, while open trades run to their exit |
| universe | PIT Nifty-500 members on the signal day |
| strong | 26-week return minus the Nifty's 26-week return in the top 20% of the universe, **and** the stock's weekly close above its own 40-week SMA |
| oversold, logged as a family of three readings | **R1** close at least 8% below its 10-session high · **R2** RSI(2) below 10 · **R3** close below the lower Bollinger band (20, 2) |
| entry | the next session's open after the signal close |
| time exit | the close of the 10th session after entry |
| disaster stop | 15% below entry, standing daily; fill at the stop, or at the open on a gap through it |
| size | equal notional, 5% of sleeve capital per position, at most 8 open per reading; ₹2,00,000 notional per reading |
| costs | the swing book's cost model |
| re-entry | not within 10 sessions of the same stock's last exit (per reading) |

Each reading R1, R2 and R3 is logged as its own book, and the three are judged **as a family** (finding 0133:
specification uncertainty is a multiplicity axis). The decision reads the family median, never the best reading.

**Logger (the wiring this amendment authorises):** `scripts/run_mr_sleeve_paper.py`, run daily in the weekly-monitor job
after fresh OHLCV. It writes `results/mr_sleeve_paper.json`: per reading, the signals, fills, exits, open positions and
a daily NAV, plus a `regime_active` flag per day. Forward-only from the signing date: no reconstructed history enters the
forward record (§3 integrity). The live A-only book, its cards and the product are unchanged; the sleeve is not shown
to users.

**Decision rule (pre-committed; thresholds tighten, never relax):**
- **When:** the first quarterly review after **both** (a) at least 40 closed trades in the family-median reading and
  (b) at least 12 months of logging. Before that: log and leave it alone.
- **Promote to a paper-capital proposal** (a further amendment, not automatic) only if the family-median reading has
  **all** of:
  1. mean net return per trade above the Nifty's return over the same holding windows;
  2. a positive net total over the logging period;
  3. weekly-return correlation with the A-only book below 0.3 over the weeks either was active;
  4. a sleeve MaxDD shallower than −15% of sleeve capital.
- **Retire** if the family median fails 1 or 2 at the decision point.
- **Insufficient evidence** (below either count): carry it one more quarter; it earns nothing by default.

**Mechanical halt (no discretion):** if the family-median reading's sleeve NAV falls more than 15% below its peak at any
point, logging continues but the book is marked HALTED and cannot be promoted. That is the drawdown this sleeve was
supposed to avoid.

**What this amendment may never do:** change the A-only book, its grading, caps, exit or sizing; give the sleeve any
capital; or be tuned against its own forward record. A change to any number in the spec voids the logging period and
restarts its clock.

---

**Owner checklist before signing**
- [ ] The spec values above (8%, RSI(2) < 10, Bollinger 20/2, 10 sessions, 15%, 5% × 8, ₹2L) are acceptable as frozen.
- [ ] The decision rule and halt are acceptable.
- [ ] Optional, before signing: a one-run activation bound on the train window (2019..2024-06, frozen rule, family
      median) to check that it clears the ±10R/yr noise floor at all. It is not a tuning step, and it changes nothing
      above.
