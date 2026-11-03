# What the model lacks, after four months live (2026-11-02)

**Class:** diagnosis (process tier MEASURE/EXPLORE). No trial, no screen. Standing counts: screens 23 · sealed
opens 3 · n_trials 2. Written from three seats at once — researcher (what the evidence can and cannot say),
trader (how the book behaves in this tape), and portfolio manager (where the money is actually lost) — and
built on the measurements of 2026-10-13..11-02, not on recollection. Each problem ends with the cheapest test
that would confirm or kill it, so they can be worked one at a time.

## The live record, 2026-07-06 → 2026-10-30

| measure | live | the backtest's own expectation (train 2019–24H1, live config) |
|---|---|---|
| capital book | **−9.0%**, MaxDD −13.9%, Sharpe −2.2 | CAGR 20.5%, MaxDD −40.1%, Sharpe 1.03 |
| Nifty, same window | −5.0% (and −15% from its January high) | — |
| tracker, closed | **32 closed: 1 win, 31 losses**, mean −1.26R, median −1.18R | win rate ~48%, mean +1.29R |
| tracker, open | 19 open, 10 in profit, mark-to-market −0.27R | — |
| losses beyond −1.5R | 9 of 32 | 90% of stop exits fill beyond the stop |
| kill gate | **triggered** (net Sharpe < 0), surfaced not applied | — |
| operations | 3 of the last 4 Saturday scans failed a guard; 2 weeks lost (10-10, 10-31) | — |

The book has gone from ahead of the Nifty (September) to ~4pp behind it. One closed winner in 32 is far
outside anything the backtest produced, so "unlucky" is not a sufficient explanation on its own — but
neither is "broken": the sample is small, censored, and drawn from one regime.

## The problems, ranked by how much return each is costing

### 1. The book has no notion of the market it is in (regime exposure) — the largest live drag
*Trader:* this is a trend-pullback buyer. In an uptrend, a touch of the 44-week line is a discount; in a
correction, the same touch is the first leg of a breakdown, and the line turns into resistance. The live
period is a correction (Nifty −15% from January), and the book stays fully deployed into it: every Saturday
it buys the five best-ranked touches regardless of tape. 31 of 32 closed trades lost.
*Researcher:* the programme's regime gates were all killed — but on other books, before the PIT membership
gate and the current exit (O-001, 0056, 0086, 0090, 0103: weak priors). Two new facts change the question:
in drawdowns the book's beta goes to ~1 and its holdings bunch (0142 corrected), and the clairvoyant hedge
ceiling is huge while a lagged trigger captures none of it (#156). So the open problem is not *which* stocks
but *how much capital is at risk* in a falling tape — exposure, not selection.
*Cheapest test:* replay the live config through the train window's own corrections (2020 Q1, 2022 H1) as
continuous slices and compare with the live record. If the live drawdown sits inside those episodes, the
problem is regime exposure; if it is far worse, something else is broken.

### 2. Losses are larger than the design says (gap-through weekly stops)
*PM:* the book is designed to lose 1R. It loses about 1.3–1.6R: the stop is checked on the weekly close and
filled at the next open, so 90% of stop exits fill beyond the stop (train mean 0.9R beyond; live 9 of 32 worse
than −1.5R). That alone moves the break-even win rate several points.
*Researcher:* exit geometry was closed (0105/0106/0109, Law V), but on the frozen 0094 book and the old exit
(weak). The live config never had a daily or intraday protective stop tested.
*Cheapest test:* ensemble-score the existing `hard_stop` and `disaster_floor_pct` levers under the live
config (they are gated already).

### 3. Selection has no measurable skill, and wastes seats
*Researcher:* within a week, the CRS rank does not order outcomes (rank IC −0.008; 0150 corrected), and the
live top-5 wastes ~27% of its slots on names the book cannot buy (D6 lifts train Sharpe 1.025 → 1.275).
Touch depth and frog-in-the-pan did not rescue it. Whatever edge exists comes from the touch itself, the
market, and the exit's convexity — not from picking.
*Cheapest test:* already queued — D6 as a pre-registered trial for the 2027-01-01 review.

### 4. The live configuration is over-constrained
*PM:* four cap-like layers (extension cap, Grade-A gate, 20% notional, 10% max-risk) overlap; together with
the scaled exit they cost ~0.5 Sharpe in-sample (one-off costs sum to +0.94, together +0.48). The 2% risk rule
never binds — every position is the 20% notional cap, i.e. the book is equal-weight, and risk per trade is
whatever the stop happens to be.
*Cheapest test:* running now — the ensemble re-score of the ablation leads (scaled exit alone; all five off;
D6), so path noise is separated from effect.

### 5. Five seats that move together when it matters
*PM:* concentration is the edge in calm markets (more seats diluted Sharpe historically) and the risk in
corrections: average pairwise correlation rises from ~0.19 to ~0.32 in drawdown weeks (cluster study), the
same as random picks. Five correlated names is one bet in a sell-off.
*Cheapest test:* only structural answers have helped historically (a second sleeve, 0149's barbell). Measure
the live blend book (swing × low-vol) against the swing book over the live period.

### 6. We cannot yet tell bad luck from a broken model (measurement)
*Researcher:* the live sample is 51 trades from one regime; winners take 8–12+ weeks and are still open,
losers close in weeks, so closed-trade stats are biased toward losses (censoring). In-sample numbers come
from a trend-heavy window, single replays carry ±0.2 Sharpe of path noise, and research and live universes
pick different top-5s in 33–41% of weeks.
*Cheapest test:* a censoring-aware forward readout (mark open trades, report both), plus problem 1's
regime-matched comparison. A decisive but expensive test exists: the sealed 2024H2–2026H1 slice contains a
real correction; one sealed read of the *live config* would show how the book behaves in exactly this kind
of tape. That costs a sealed open and is an owner decision.

### 7. The plumbing keeps eating weeks and rewriting the record
*Engineer:* in four weeks, guards halted or failed three scans (two weeks lost), history was rewritten twice
(HEG erased; HINDZINC/BANDHANBNK displaced), a degenerate stop produced −389R in the tracker, the card's
no-chase line is not enforced by the engine, and the same company appears under two symbols in the top-5.
None of these lose money directly, but each corrupts the record we judge the model on. Root cause: a free,
unofficial vendor (Yahoo) feeding a rebuild-from-inception design.
*Cheapest test / fix:* #161 (guards tolerate dividend re-scaling), the post-scan fixes already listed
(stop-width floor, history-guard bars, per-name staleness, bad-tick filter), and longer-term the vintaged,
append-only data store from the 2026-10-20 ideas memo.

## Proposed order to work through

1. **Problem 1 — regime-matched comparison** (one lab run; decides whether the live loss is regime or defect).
2. **Problem 4 + 3 — ensemble re-score** (running) → D6 and any surviving simplification pre-registered for
   the 2027-01-01 review.
3. **Problem 2 — protective-stop levers on noise bands.**
4. **Problem 1, if confirmed — exposure control**: breadth- or drawdown-based capital-at-risk throttle,
   measured as a bound first (Law VII: it buys drawdown with return; owner risk preference).
5. **Problem 5 — book shape** (blend forward record; second sleeve).
6. **Problem 7** continuously; **Problem 6** as the honest frame around every number above.

Nothing here changes the live book; every change to it remains a CONFIRM-tier decision at a review.
