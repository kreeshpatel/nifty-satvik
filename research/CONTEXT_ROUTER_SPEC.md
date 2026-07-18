# Context-Router — architecture spec (the "ifs and buts" system)

*Drafted 2026-07-16. Status: **SPEC — awaiting owner approval**. Increments no trial. Nothing here
changes the live config; every certification route is the forward wall.*

## 1. Why this, and why now

The research loop established three things that jointly kill the "find a better filter" approach and
point at routing instead:

- **Entry quality is not separable at entry** — confirmed three ways (prior forensic; ML holdout
  AUC **0.536**; a 300-chart *blind* vision grade-gap of ~0: winners 2.72 vs losers 2.75). The median
  loser looks exactly like the median winner. You cannot fix the book by screening the touch entry.
- **The exit is a two-sided balance, not a leak** — the 200-chart exit search found giveback ≈
  cut-runner among genuine flaws; the loose exit that bleeds 88% of an average peak is the same one
  that lets the fat-tail runners run (per-trade ≠ portfolio, again).
- **But different states genuinely want different machinery** — box (consolidation-above-SMA) was
  *handicapped* by the touch-tuned exit and jumps to **Sharpe 1.04 / CAGR 21.0% / 22-26 slice 1.08**
  once given a let-it-run exit. Touch wants the opposite (book-half + cut the blow-off; let-run drops
  it to 0.77 and −45% DD).

So the leverage is **not** a better filter and **not** a better universal exit. It is **routing each
name to the branch whose entry *and* exit fit its current state** — the owner's "ifs and buts":

> *continuous uptrend that never touches the SMA → check the consolidation (volume, base).
> bought too far above the SMA → check the support below. near the SMA → the touch.*

Today the zoo detectors fire **in parallel and additively** — any detector that matches emits a
signal, regardless of whether that logic suits the name's state, and every branch inherits the
touch's exit. The router replaces that with **one state per name per week, one branch, one matched
exit.**

## 2. The honest ceiling (read before approving)

- This will **not** produce a large Sharpe jump. Entry quality is barely separable and the zoo
  families are **0.90-correlated** to the touch book; sleeves already failed to lift the capped book.
- Realistic value: **(a) coverage** — trade the GAIL/VBL-type names the single touch rule structurally
  misses; **(b) correct exit per branch** — the one validated, real gain so far; **(c) a clean
  substrate** for the conviction-ML/agent layer (step 3).
- **In-sample certification is exhausted** (n_trials=115; DSR ≈ 0.00 on every candidate tested). The
  router's verdict comes from the **forward wall**, not a 116th backtest. Any in-sample number it
  produces is a sanity check, not a promotion.

## 3. Architecture

### Layer 0 — State features (PIT-safe, weekly, trailing-only)
Per (ticker, week), from the cached weekly panel (`nq/data/weekly.py`): 44w SMA + slope; extension
(`close/sma−1`); base metrics (trailing range tightness, base duration); `dist_52wh`; volume regime
(dry-up vs expansion, `vol_ratio`); weekly ATR%; swing structure (HH/HL via pivots); **overhead
supply** (nearest pivot-high above); **support proximity** (nearest pivot-low below). Reuses the
detectors' primitives in `nq/research/setups.py`.

### Layer 1 — STATE CLASSIFIER (the "ifs and buts") — exactly one state per name-week

| state | condition (sketch) | route to |
|---|---|---|
| `S0_NO_TREND` | 44w SMA not rising, or close < SMA | **skip** |
| `S1_PULLBACK` | low within touch band of the rising SMA | TOUCH branch |
| `S2_CONSOLIDATION` | tight base held **above** the rising SMA ≥N weeks (never pulls back) | BOX branch |
| `S3_EXTENDED` | far above SMA, no base | SUPPORT-CHECK branch (enter only on a proven-support test, else skip) |
| `S4_SUPPORT_RETEST` | pulling into a proven prior swing low / pivot in an uptrend | S/R-RETEST branch |
| `S5_BASE_COMPLETING` | cup-with-handle / double-bottom base finishing | CUP / DBL branch |

Priority order resolves overlaps (a name is never in two states). `S0`/unroutable → no trade.

### Layer 2 — BRANCH LOGIC (each branch: own entry, own stop, **own exit** — validated)

| branch | entry | stop | exit | evidence |
|---|---|---|---|---|
| TOUCH | green wk, close>SMA, RS ok | signal-wk low | **P2** (half@2R + 20d trail + blow-off@2.5R) | 22-26 slice **1.29** (best) |
| BOX | green close > box high | box low | **LET-RUN** (no blow-off) | Sharpe **1.04** / CAGR **21%** / 22-26 **1.08** |
| CUP / DBL | green close > rim / mid-peak | handle / 2nd-bottom low | P2 | 22-26 1.02 / 0.94 |
| S/R-RETEST, SUPPORT-CHECK | green close off a tested level | below the level | P2 (default; to be characterised) | thin (sr_pivot N=57) |

### Layer 3 — CONVICTION SCORE (the ML)
Within routed candidates, score quality [0,1] from the weak-but-real OOS features
(`dist_52wh`, `vol_ratio`, low `atr_pct`, `rank_crs`) **+ state**. Trained 2019-22, judged on the
2023-26 holdout and forward only. **Expect weak** (AUC ≈ 0.54; Q5-vs-Q1 ≈ 6pp win-rate).

### Layer 4 — SIZING
Allocate the ₹10L across routed candidates by state + conviction. **Guard:** a mean-preserving
conviction *tilt* was already KILLED (0073) — conviction may gate/rank, not merely tilt weights.

### Layer 5 — LEARNING LOOP
Log every routed decision + outcome; retrain the conviction model on a schedule; judge on a **rolling
forward** holdout. Guards: slow/regularised updates, **no live retune between quarterly reviews**, and
the pre-committed thresholds cannot be relaxed retroactively.

## 4. Where the AI agent actually goes (the key architectural constraint)

**An LLM cannot live inside the backtest loop.** 788 tickers × ~496 weeks ≈ 390k decisions — that is
computationally and financially impossible, and non-deterministic, which breaks reproduce-before-trust
and the golden-master invariant. So:

- **The backtest of record is the RULES classifier** — deterministic, PIT-safe, byte-reproducible.
- **The AI agent's two real jobs:**
  1. **Calibration** — on samples, the vision agent labels a name's state from the chart; we measure
     agreement with the rules classifier and fix the rules where they disagree. (This is exactly what
     the chart-validation pass already did for the detectors — it changed two verdicts.)
  2. **Live oversight** — on the ~5-15 actionable signals/week the agent reviews ambiguous cases and
     flags state-misroutes. Feasible at that volume; logged, never silently overriding.
- The agent **teaches the rules**; the rules **do the trading**. Anything else is untestable.

## 5. Validation plan (what would make me believe it)

1. **Determinism**: router backtest byte-reproducible; golden master (`tests/test_stage2_golden.py`)
   unchanged with the router OFF.
2. **Coverage**: router trades ≥ the GAIL/VBL-class names the touch misses (count them explicitly).
3. **Sanity, not promotion**: router vs live touch book on the **continuous-slice 2022-26** gate
   (baseline to beat: Sharpe **1.29**, DD −34.8%, CAGR 21.2%). If it loses, that is a finding.
4. **Agent-vs-rules state agreement** ≥ some pre-declared bar on a labelled sample (calibration).
5. **Certification = forward wall only.** Pre-register; the shadow logs from day 1 (no October wait to
   *start*); a pre-committed trigger (e.g. 30 closed trades) sets the review.

## 6. Risks / what would kill this

- **Routing is just the zoo with extra steps** — if one-state-per-name produces ~the same trades as the
  additive zoo, there is no gain (Stage 4 says the additive zoo doesn't lift the capped book).
- **Correlation** — every branch is a long-only trend bet; 0.90 correlation caps diversification.
- **State-boundary overfit** — each threshold (touch band, base tightness, extension cut) is a knob;
  knobs are how you fit noise. Thresholds must be inherited from the *already-validated* detectors, not
  re-tuned. **No new sweeps.**
- **DSR** — nothing here can clear 0.95 in-sample. If we need an in-sample pass to justify it, stop.

## 7. Build sequence (each step gated)

1. Layer 0-1: state classifier from existing primitives + a coverage report (which names/states).
2. Layer 2: wire branches to their **validated** entry+exit (touch→P2, box→let-run).
3. Router backtest vs baseline on the 2022-26 slice (sanity).
4. Agent-vs-rules calibration on a sample (~100 charts, tiered/batched).
5. Layer 3-4 conviction + sizing (only if 1-4 hold).
6. Pre-register → forward-wall shadow from day 1.

## 8. Non-goals

- No live config change in-sample. No new threshold sweeps. No LLM in the backtest loop. No retuning
  toward a pass — UNDERPOWERED/KILL stays a first-class outcome.
