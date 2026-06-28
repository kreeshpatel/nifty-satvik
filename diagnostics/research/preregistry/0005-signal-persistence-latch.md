# 0005 — Signal persistence (latch-and-track once confidence crosses)

- **ID:** 0005
- **Registered:** 2026-06-02
- **Holdout:** unseen-universe (Holdout #2, immediate backtest of the strategy logic)
  → forward-wall (Holdout #1, decisive). This is a STRATEGY-LOGIC change (gating /
  entry timing) — **no retrain**, so it can be backtested on the frozen model over
  the unseen universe AND measured forward on live signals.
- **n_trials (cumulative):** ~51 (continues the count from 0004; tally precisely
  before the DSR read).
- **Status:** PENDING

## Motivation (a stock is not above the gate every day)

The live gate is a **daily snapshot**: a stock is a BUY only if its ensemble
confidence ≥ 0.92 on the scan day. But confidence is noisy and a real mover does not
hold ≥0.92 continuously. HFCL (2026-06-02 audit) peaked at conf **0.929 on a single
day** (2026-03-13, ₹72), then fell back into the 0.75–0.89 watchlist band for weeks
while the stock ran to ₹88+. The daily-snapshot gate saw one fleeting BUY and then
nothing — so unless you scanned that exact day, the signal vanished. This is the
"unstable signals" failure CLAUDE.md warns about, in the wild.

The idea: once a stock **crosses (or nearly crosses) the gate**, do not let the
candidacy evaporate the next day — **latch it** for a bounded window and enter on a
qualifying day, with guardrails so we do NOT simply buy a stock that popped once and
is now rolling over.

## Hypothesis

A latch-and-track entry rule captures sustained movers the daily-snapshot gate
misses, improving total captured return / per-trade expectancy on the unseen
universe **net of** the extra losers introduced by latching onto failed breakouts —
i.e. the latch's winners outweigh its false-breakout bleed. Predicted direction:
non-negative delta in per-trade expectancy AND a positive delta in capture (more of
the large movers entered).

Candidate latch rule (exact thresholds frozen in the runner before the run):
- **Arm:** on day D, if ensemble conf ≥ `ARM_CONF` (test 0.90, i.e. within ε of the
  0.92 gate) AND predicted return ≥ min_ret, mark the stock *armed* with anchor =
  day-D close, for up to `K` trading days (test K = 5–10).
- **Enter while armed** on the first day that ALL hold: (a) close ≥ anchor (still
  working, not rolling over), (b) close above a short trend filter (e.g. EMA9), and
  (c) conf has not collapsed below the watchlist floor 0.75.
- **Disarm** if: K days elapse with no entry, OR close < day-D *low* (failed
  breakout — the critical bleed guard), OR conf < 0.60 (thesis gone).
- One entry per arm; standard exit logic (target/stop/expiry) thereafter.

The guardrails (anchor + failed-breakout disarm) are the whole point: a naive latch
that just "buys within K days of a pop" would load up on reversals. The pre-reg
tests whether the *guarded* latch is net-positive — it is allowed to FAIL.

## Holdout & procedure

1. Backtest BOTH rules — current daily-snapshot gate vs latch-and-track — on the
   SAME frozen ensemble, SAME unseen universe (145 tickers), SAME period, SAME costs,
   via a strategy-logic flag in the OOS runner (no retrain).
2. Forward-wall: run the latch rule in shadow alongside live and compare realized
   post-wall expectancy (the decisive, slow read).

## Primary metric

**Delta in mean after-cost per-trade return (%)** = `expectancy(latch) −
expectancy(daily-snapshot)` on the unseen universe, 95% bootstrap CI on the paired
difference, honest costs. (Per-trade, not total, is primary so the latch can't "win"
merely by taking many more marginal trades — the trade-count change is reported as a
guardrail metric.)

## Secondary / diagnostic

Capture: among realized +20%/30d unseen-universe moves, share entered by each rule;
trade-count delta (a latch that 3× the trades is suspect); WR delta; **bleed
accounting** — expectancy of latch-only entries (the trades the snapshot gate would
NOT have taken) in isolation, to see directly whether the latched-but-not-gated
trades are net-positive or net-negative; max-drawdown delta.

## Decision rule (fixed in advance)

- **SUPPORT (weak):** latch per-trade expectancy CI lower bound ≥ daily-snapshot
  point estimate (non-degradation) AND capture strictly higher AND the latch-only
  subset has positive mean return AND DSR > 0.95. → escalate to forward-wall shadow.
- **KILL:** latch per-trade expectancy CI upper bound < daily-snapshot point (the
  false-breakout bleed dominates), OR the latch-only subset is net-negative. → the
  daily snapshot's strictness is protective; do not latch.
- **INCONCLUSIVE:** overlapping CIs → no evidence; keep the daily gate.

## Notes / risks pre-committed

- This interacts with 0004: chart-structure features would give the latch a far
  better "is this a real breakout" guardrail than the price/EMA proxy above. They are
  registered separately so each can be killed independently, but a natural sequence
  is 0004 → 0005.
- Watchlist already persists candidates (`signals_watchlist.json`); the latch is a
  promotion rule FROM that bucket, so the plumbing largely exists.
- Honest framing: latching is a classic way to convert a precision-tuned system into
  a worse one (chasing). The pre-committed bleed-accounting metric exists precisely
  so a pretty capture number can't hide a negative latch-only expectancy.

## Result (2026-06-02) — KILL (decisive; the bleed metric caught it)

Latch vs daily-snapshot gate on the SAME live ensemble, SAME 145 unseen tickers,
2021-2025, identical costs/exits (both driven through `engine._simulate`):

| | trades | per-trade after-cost | WR |
|---|---|---|---|
| Snapshot (live 0.92 gate) | 412 | +4.197% [3.05, 5.35] | 68.5% |
| Latch (arm≥0.90, K=10) | 502 | +1.354% [0.29, 2.43] | 52.0% |
| **Latch-only (bleed)** | 485 | **+1.247% [0.18, 2.32]** | **51.3%** |

**Delta −2.84%/trade. KILL on both pre-registered triggers:** the latch CI upper
bound (2.43) < snapshot point (4.20), AND while the latch-only mean is technically
>0, it is a **51% win-rate, +1.25% near-coin-flip** — the bleed the pre-reg's
isolation metric exists to expose. The latch added 90 net trades (412→502), almost
all of them (485) sub-gate entries, and those entries are near-worthless.

**Interpretation — the gate's strictness is PROTECTIVE, and the model's low
confidence is INFORMATION, not noise.** The days a stock sits below 0.92 are
genuinely lower-EV; buying it then (the latch) converts a 68%-WR precision system
into a 52%-WR one. This is fully consistent with the original gate move: the
0.88-0.92 band was measured negative-EV (`diagnostics/tier_validation.md`), and the
latch is essentially "enter in/below that band on armed names." The one HFCL that
ran is survivorship — for every HFCL there are many armed-then-reversed names, and
they show up here as the 485 coin-flip trades.

**Meta-finding (0004 + 0005 together):** both "obvious" fixes for the HFCL miss —
add structure features (0004) and latch the signal (0005) — were KILLed on the
holdout. Both amount to "trade more / trade lower-confidence," and the model's
caution is empirically well-calibrated. The HFCL-type miss is the PRICE of
precision, not a fixable defect; relaxing it costs more than it saves. The
disciplined conclusion is to STOP trying to make this model trade more, and treat
"capture more movers" as a separate-strategy question (a distinct breakout system
with its own risk budget), with now-very-skeptical priors. The validated lever
remains the existing edge (0001/0003): let it run and accumulate the forward wall.

_(pre-registration above this Result section is immutable)_
