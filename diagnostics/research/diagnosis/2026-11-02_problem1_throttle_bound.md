# Problem 1 — an exposure throttle on new seats: BOUND (2026-11-02)

**Class:** SCREEN / BOUND tier (`docs/PROCESS_TIERS.md`). It ranks what would be worth confirming; it is
**not a trial** and it never changes live. Screen-ledger row **24** was appended and committed BEFORE any
computation. Standing counts after that row: **screens 24 · sealed opens 3 · n_trials 2** (`n_trials`
unchanged). Train window only: prices cut at 2024-06-30 (asserted by `nq.lab.runs`), the sealed
2024-07-01..2026-06-30 slice is not read, `results/judge_log.jsonl` is not touched.

## Question

`2026-11-02_problem1_regime_match.md` (branch `diag/problem1-regime-match`) found the live loss to be REGIME,
narrowly, and left Problem 1 as an exposure problem: the book is fully deployed into corrections (2022 H1:
book -10.5% vs Nifty -3.8%, MaxDD -14.4%). Would limiting NEW seats on a point-in-time market-state signal
have bought drawdown cheaply, and how far is that from the best possible timing?

## Prior evidence (cited, not relitigated)

- Entry or regime gates on OTHER books (O-001, 0056, 0086, 0090, 0103): weak priors (other books, pre-PIT,
  old exit). Quoted as `not re-tested under the current harness`.
- 0095 vol-targeting KILL on the 0094 book: mechanism = freed cash redeployed into weaker names. The throttle
  here does the opposite on purpose (freed cash stays in cash), so the mechanism is not the same, but the
  cash-drag side of Law III is what this study has to price.
- The drawdown-switched hedge (`diagnostics/research/explore/2026-10-20_hedge_and_breakout_sleeve.md`, PR
  #156 branch `worktree-agent-afea2bdc957b2c234`): causal triggers LAG (hedge-on days were rebound days) while
  the clairvoyant ceiling was large. So timing is the whole prize, and the throttle has to react faster than a
  drawdown trigger. That is the reason for the clairvoyant row below.

## The throttle (frozen before any number)

Exposure, not selection. On each weekly decision (the signal-week close, i.e. the last session on or before the
Sunday before the entry week's Monday; only data up to that session is used) a scale is set for the NEW
fills of the following ISO week. Existing positions are untouched (no forced selling, exits unchanged). Freed
cash stays in cash. Implemented with the cfg-gated engine lever `entry_size_scale_by_week` (commit
`prod-fix(engine)`, default None byte-identical, tests in `tests/test_engine_fill_levers.py`). A scale of 0
skips the fill; 0.5 halves the share count of the fill (the 20% notional cap and the risk sizing are applied
first, then the scale). The scale is a size fraction of the normal new position, so "0 seats" and "half
size" are the two levels used; no 1-4 seat granularity is tested (frozen).

Candidate signals, all reported, none picked:

| id | rule | scale when ON |
|---|---|---|
| S1 | Nifty-50 weekly close below its 40-week SMA (weekly closes ending at the decision session) | 0 (no new entries) |
| S2 | Nifty-50 20-session return < 0 AND close below its 50-session SMA | 0.5 |
| S3 | own-funnel breadth = share of PIT Nifty-500 members (with >= 44 weekly closes) whose weekly close is above their own 44-week SMA, below its trailing 26-week median (26 weeks ending at and including the decision week; needs 26 weeks of history) | 0.5 |
| S4 | the book's own trailing-4-week result < 0: mean of {R of trades closed in the 28 days before the entry week} and {mark-to-market R of every position open at the decision close, (mark - entry) / initial risk}, empty set = not throttled | 0 (no new entries) |

S4 is path-dependent (it reads the throttled book's own results), so it is evaluated inside the one run through a
state-reading object handed to the same lever, not from the unthrottled run.

Reference rows (not signals): **CONTROL** (no throttle = the live config, must reproduce the standing anchor
exactly) and the **CLAIRVOYANT ceiling**: throttle exactly the weeks whose NEXT 13-week Nifty return (decision
close to the weekly close 13 weeks later) is below zero. CV0 = scale 0 in those weeks (the ceiling for S1/S4),
CVh = scale 0.5 (the ceiling for S2/S3). Weeks whose 13-week window runs past the 2024-06-30 cut are not
throttled. This is a hindsight bound, never a rule.

## Measures

One continuous live-config run per row (PIT membership via `nq.lab.runs`, start 2019-01-01, reporting from
2019-01-01). Per row: Sharpe raw and deflated (`nq.lab.runs.deflated_sharpe`, trials = the 4 signals +
CONTROL + CV0 + CVh = 7), CAGR, MaxDD, Calmar, worst calendar year, share of decision weeks throttled and
share of Grade-A entry windows hit, sub-periods 2019-21 and 2022-24H1 as CONTINUOUS SLICES of that one run
(never a fresh-capital re-run), the book's return in each of the regime-match study's 4-month correction
windows (8% Nifty drawdown episodes, 116 calendar days from each episode start) against the CONTROL, and the
Law-III bookend: mean/sum R of the CONTROL trades entered in the weeks each rule would have throttled, and the
average cash share of the book.

## Reading, committed BEFORE any number was computed

Fixed here; not revisited after the run.

- **EARNS A TRIAL PROPOSAL** (a proposal to pre-register a confirmation, never a live change): the throttle
  improves Calmar AND reduces MaxDD by >= 5 percentage points AND does not lower Sharpe by more than 0.10,
  each against CONTROL, in BOTH sub-periods (2019-21 and 2022-24H1, each a continuous slice of the one run).
- **RISK DIAL** (Law VII: drawdown bought with return = an owner preference, not an edge): MaxDD falls by
  >= 5pp in both sub-periods but the Calmar or Sharpe condition fails in at least one.
- **NO HELP**: anything else.
- The clairvoyant rows are bounds and are not graded. A causal signal is read against them as a fraction of the
  ceiling captured.
- Single-run caveat (the `nq/lab/ensemble` path-perturbation tool is not on main): each row is one path, with
  about 0.2 Sharpe of path noise, so a pass is a ranking for what to confirm, a fail is not a kill. A 0.10
  Sharpe tolerance sits inside that noise by construction; the verdict rule is as written and the noise is
  stated beside it.

---

# Result (everything above this line was written before the run)

*(filled in below after the run)*

Reproduce: `python pipelines/diagnostics/diag_problem1_throttle_bound.py` →
`diagnostics/research/diagnosis/2026-11-02_problem1_throttle_bound.json`. CONTROL reproduces the Strategy Lab
live-book anchor exactly (Sharpe 1.0248, MaxDD −40.1%, 77 trades); last bar seen 2024-06-28. Standing counts
(read from the ledgers by the script): screens 24 · sealed opens 3 · n_trials 2.

## Readout (one continuous run per row; sub-periods are slices of it)

| row | Sharpe | CAGR | MaxDD | Calmar | 2019-21 Sharpe / MaxDD | 2022-24H1 Sharpe / MaxDD | weeks throttled | trades | reading |
|---|---|---|---|---|---|---|---|---|---|
| CONTROL | 1.025 | 20.5% | −40.1% | 0.51 | 1.03 / −40.1% | 1.01 / −25.2% | — | 77 | — |
| S1 Nifty < 40w SMA → 0 | 0.916 | 21.4% | **−26.6%** | 0.80 | 0.75 / −26.6% | 1.35 / −16.0% | 21% | 70 | **RISK DIAL** |
| S2 Nifty weak → ½ | 1.313 | 26.0% | −38.3% | 0.68 | 1.18 / −38.3% | 1.48 / −18.9% | 26% | 118 | NO HELP |
| S3 breadth < median → ½ | 1.306 | 24.5% | −40.6% | 0.60 | 0.99 / −40.6% | 1.72 / −15.4% | 44% | 123 | NO HELP |
| S4 own 4w R < 0 → 0 | 1.095 | 20.3% | −39.1% | 0.52 | 1.03 / −39.1% | 1.19 / −19.4% | 2% | 79 | NO HELP |
| CV0 clairvoyant → 0 | 1.643 | 34.3% | −25.3% | 1.35 | 1.59 / −25.3% | 1.69 / −16.9% | 27% | 64 | (ceiling) |
| CVh clairvoyant → ½ | 1.142 | 22.6% | −42.4% | 0.53 | 0.67 / −42.4% | 1.78 / −18.1% | 27% | 111 | (ceiling) |

**Readings, as pre-committed:** no causal signal earns a trial proposal. **S1 is a RISK DIAL**: MaxDD falls 13.5pp
(2019-21) and 9.2pp (2022-24H1), Calmar rises in both, but 2019-21 Sharpe falls 0.28 (limit 0.10). S2, S3 and S4
are **NO HELP**: none cuts the 2019-21 drawdown by 5pp (the 2020 crash was too fast for any of them).

## What the numbers say beyond the grade

1. **The causal signals throttle the book's best weeks.** The Law-III bookend: CONTROL trades entered in the
   weeks S1 would have skipped averaged **+2.16R (65% wins)**, against +0.21R in the weeks it left open. S2:
   +1.21R vs +0.64R; S3: +1.11R vs +0.64R; S4: +7.46R (6 trades, all wins). The clairvoyant weeks are the
   opposite: −1.07R (17% wins) skipped vs +1.96R kept. A pullback buyer's best entries are bought in a weak
   tape, *after* the index has turned down, which is exactly when lagging market-state signals fire. Timing is
   the whole prize (CV0 Calmar 1.35 vs 0.51), and these signals capture it backwards. S1 captures 35% of the
   ceiling's Calmar gain only because it stays in cash through the 2020 crash; its precision against the
   clairvoyant weeks is 8%.
2. **The half-size rows change the book's shape, not just its timing.** S2, S3 and CVh take 111–123 trades
   against 77: half-size fills leave notional headroom, so more names fit under the 20% cap. Their Sharpe gains
   are confounded with "more, smaller seats", which program-laws already records as a separate lever (seat count
   and sizing grid). Even the half-size *clairvoyant* row fails in 2019-21 (Sharpe −0.36). These gains are not
   evidence of a timing edge.
3. **2022-24H1 flatters every throttle** (every row's 2022-24H1 Sharpe rises); 2019-21, with the fastest crash
   and the strongest rebound, is where they all pay. Picking a signal on 2022-24H1 would fit the regime after
   seeing it (the same trap as 0148's ratchet).

## What this closes, and what it does not

- **Closes (current harness, live book, train window):** a lagging market-state throttle on new seats as an
  edge. Cite as `BOUND (2026-11-02, live book)`. S1 is available as an owner **risk dial**: about −0.1 Sharpe
  for about 14pp less drawdown in-sample (Law VII), not an improvement.
- **Does not close:** a signal that fires *before* the correction rather than after it (a leading signal),
  which is what the clairvoyant gap asks for; and the seat-count effect in point 2, which belongs to the sizing
  grid, not to timing.
- Single path per row (≈0.2 Sharpe path noise): rankings only. Nothing changes live.
