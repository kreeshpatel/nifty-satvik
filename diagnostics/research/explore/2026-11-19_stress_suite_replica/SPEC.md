# Blind-replica spec — S1 (signal latency) and N1 (label shuffle), swing book and 0001 momentum

You must NOT read `pipelines/diagnostics/explore_stress_suite.py`, `.cache/stress_suite/`, or
`diagnostics/research/explore/2026-11-19_stress_suite.json`. Implement from this spec and the public harness APIs only.
Do NOT edit any engine file (`scripts/run_bhanushali_weekly_rank.py`, `nq/**`). If an engine behaviour must change, load a
source-modified COPY of the module in your own process (e.g. read source, string-replace, exec into a fresh module
registered under the same name in sys.modules BEFORE nq.lab imports it; nq.lab.runs._engine() imports
`run_bhanushali_weekly_rank` by name). Use the repo venv: `source .venv/bin/activate`. Data is already in `data/`.
Write your code and outputs under /tmp/claude-0/-home-user-nifty-satvik/73b5e4da-158a-56aa-b62e-60d0093c5120/scratchpad/replica/.

## Common

Swing book: the live book. Build context with `nq.lab.ensemble.prepare_context()`. For each perturbation draw `d` from
`nq.lab.ensemble.draw_perturbations(n, nq.lab.ensemble.DEFAULT_SEED)`:
`cfg = {**nq.lab.runs.normalize_config({}), "start": d.start}`; `kw = nq.lab.runs.engine_kwargs(cfg)`; run
`R94.backtest(ctx.P, ctx.mem, ledger=[], a_grade=ctx.a_grade("default"), **kw, demerger_events=ctx.events)` inside
`with nq.lab.ensemble.cost_jitter(d.cost_delta):`. NAV = `out["curve"]` (date-normalised, last duplicate kept).
Swing Sharpe = mean/std(daily pct change of NAV sliced to 2019-03-01..2024-06-28, continuous slice) × √252.
Sanity anchor: path 0 of the 20-path draw, unmodified, gives Sharpe 1.348913.

0001 momentum: the panel is built exactly as `pipelines/diagnostics/explore_blend_drawdown_sizing.py::navs()` builds `b`
(rank = NMS where eligible & size_band == BAND & nms notna, else NaN), run by
`nq.engine.rebalance_book.simulate_rebalance_book(b, cfg=RebalanceConfig(**BOOK, cost_mult=1 + d.cost_delta/0.0035),
start=d.start, end=M.END, initial_capital=1e6)`, with draws `draw_perturbations(n, DEFAULT_SEED, start_base=<first date of
the unperturbed 0001 NAV>)`. Sharpe = mean/std of daily NAV returns × √252 over the whole run up to 2026-06-30.
Anchor: unperturbed run = CAGR 21.73% / Sharpe 1.130.

## S1 — signal latency (20 paths, each book)

Swing: (a) every entry happens one session later: the entry window (the list of session indices in which an activated
order may fill, checked as `lo < open < hi` at that session's open) is shifted by +1 session index, so both the in-range test
and the fill use the next session's open; window expiry moves with it. (b) every signal-driven exit decided at a weekly
close (stop, pattern tranche, SMA break, time cap — anything queued as the engine's `pending` exit) fills one session later
than it normally would (normally: next session's open; under S1: the open of the session after that). Resting limit
tranches (+2R take-profit filled intraday at the target) are unchanged.

0001: at each month-end rebalance date D the engine normally reads ranks at D's close and fills at the next session's open.
Under S1 the ranks of D are read at the session after D (D+1) and fills happen at the open of D+2. (Equivalently: shift
each ticker's rank one session forward, and move each rebalance date to the next session in the panel's date list.)

Report per book: the 20 path Sharpes and their median.

## N1 — label shuffle negative control (seeds 0..99; seed k uses draw k of draw_perturbations(100, DEFAULT_SEED))

0001: on every date, randomly permute the rank values among the rows that have a non-NaN rank (RNG seeded by k).

Swing: for each ISO week of entry, every real signal (each ticker t and entry window in `ctx.P[t]["entry_win"]`, whose value
is (entry_session_indices, lo, hi, crs_rank, sma, origin)) is re-assigned to a uniformly random DIFFERENT ticker u that is
a PIT index member (`ctx.mem`, `nq.data.membership.ticker_in_index_on`) with a bar on the entry date, without
replacement within the week. The new ticker gets: entry sessions = u's sessions on the same dates; lo = u's minimum LOW over
the ISO week before the entry week; hi = u's maximum HIGH over that week; sma = u's `wsma_at` value at the last session of
that week (fallback lo if NaN); crs_rank and origin carried from the original signal. Real signals are removed. Recompute
Grade A with `R94.grade_a_entries(P_new)` and run the engine on `P_new`.

Metrics per seed: raw Sharpe; and the appraisal ratio = alpha/sd(residual) × √252 from OLS of the book's daily returns on
the equal-weight daily close-to-close return of its sampling universe (swing: PIT members with a bar; 0001: rows with
eligible & size_band == BAND).

Report per book: mean, SE (sd/√n), p95 and median of both metrics across the 100 seeds; whether |mean| ≤ 2·SE and p95 < 0.3.
Write results as JSON in your replica folder.
