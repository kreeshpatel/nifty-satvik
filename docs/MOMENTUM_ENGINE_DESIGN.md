# Cross-Sectional Momentum Engine — Design Charter

**Status:** DESIGN (pre-registration follows in `research/0001-xsec-momentum/prereg.md`)
**Date:** 2026-08-07
**Source:** the midcap research compendium (Jegadeesh-Titman; George-Hwang; Barroso-Santa-Clara;
Daniel-Moskowitz; Medhat-Schmeling; Agarwalla-Jacob-Varma IIMA four-factor; BacktestIndia 18.5yr NSE)

---

## 0. What this is, and why it is a new build

This is **not** a variant of anything currently running. The two engines in the repo are:

| existing | shape |
|---|---|
| `nq/engine/portfolio.py::simulate` | rank-gate top-15, **ATR stop + fixed target + trail**, event-driven exits |
| `nq/engine/signal_book.py` | discrete entry signals, **per-signal stop / R-multiple target** |

The compendium's architecture is a **third shape** neither can express:

> equal-weight top-N, **rebalanced on a fixed cadence**, with **no stops and no targets** — positions
> leave the book by falling out of the ranking buffer, not by hitting a price level.

That difference is load-bearing, and the source is explicit about why:

> *"in pure systematic momentum, discretionary stops often hurt because the rebalance already exits
> losers; stops add value chiefly for crash control and for circuit-risk names."*

So the engine, the signal, the sizing and the exit discipline are all new. Nothing here re-runs a
prior configuration.

## 1. Non-negotiables carried forward

Four **defect fixes** carry over. These are not verdicts about strategies; they are bugs that would
silently corrupt fresh numbers:

1. **Period-aligned pivots / period features** — map each date to its own period and read that
   period's shifted value. Never `resample().shift(1).reindex(ffill)`, which double-shifts.
2. **ISO-week bars** via `nq.data.weekly.build_weekly_panel` — never `resample("W-FRI")`.
3. **Continuous-slice sub-periods** — slice one full equity curve; never re-run from a sub-window
   start with fresh capital.
4. **Two-pass entry pricing** — size at the tier slippage rate, then re-price with the
   0.5%-of-ADV market-impact term once notional is known.

Plus the standing engine invariants: signal on close **T**, execute **T+1 open**; PIT membership;
truncation-invariant features; golden masters stay byte-identical.

## 2. Stage 1 — Universe (build before any signal work)

**Primary:** a PIT **size-banded midcap** universe derived from Nifty-500 membership. The repo has
Nifty-500 PIT membership (813 names, real entry/exit/re-entry) but **no Midcap-150 constituent
history**, so the band is reconstructed:

    rank the eligible PIT N500 members each rebalance by trailing 63-day median turnover
    LARGE = ranks 1-100 · MID = 101-250 · SMALL = 251+

`MID` is the primary universe; the full N500 is the robustness universe. Bands are assigned
**per rebalance date from trailing data only** — a name migrates as it would have in life.

**Screens (all PIT):**

| screen | rule | source |
|---|---|---|
| liquidity | trailing 63d median turnover ≥ ₹5cr | repo convention |
| listing history | ≥ 252 sessions | compendium §4 (Nifty momentum indices require ≥1yr) |
| price floor | close ≥ ₹10 | avoid penny names |
| solvency | `nq.data.eligibility.solvent_universe_mask` (D/E < 1.5, PIT) | existing |
| data integrity | no trade may span an unadjusted-split event | `nq.data.integrity` |
| **circuit proxy** | exclude names whose daily \|return\| hit ±19.5% on ≥20% of the prior 126 sessions | compendium §4 — the NSE momentum-index tradability rule, approximated without a circuit feed |

**Gap declared, not hidden:** we have no ASM/GSM surveillance history and no circuit-band feed. The
circuit proxy above is an approximation from returns. This is a known coverage limit and gets stated
in every readout rather than assumed away.

## 3. Stage 2 — Baseline signal

**`mom_12_1`** — cross-sectional momentum, the compendium's core engine:

    mom_12_1(t) = close(t - 21) / close(t - 252) - 1

Twelve-month formation, **skipping the most recent month** (short-term reversal contaminates it —
Jegadeesh-Titman). Ranked cross-sectionally per rebalance date among eligible names.

**Book:**

| parameter | value | rationale |
|---|---|---|
| selection | top **30** by rank | compendium: 20-50 for a midcap book |
| weight | equal | *"equal-weight with a 5% cap is the recommended default"* |
| single-name cap | 5% | NSE momentum index convention |
| rebalance | **monthly**, last session | keeps turnover and tax drag bounded |
| exit | fall out of the **top-60 buffer** at a rebalance | hysteresis; halves turnover vs a hard top-30 |
| stops / targets | **none** | see §0 |
| execution | signal close T → **T+1 open**, two-pass slippage | |
| costs | full Indian stack (below) | |

**Cost/tax stack**, per leg, PIT rates: STT 0.1% **both legs** (delivery) · exchange ~0.00297% ·
SEBI 0.0001% · GST 18% on (brokerage + exchange) · stamp 0.015% buy-side · brokerage ₹20/order ·
DP on sell · **slippage by liquidity bucket** (existing tiered model + ADV impact). **STCG 20%**
accrued *inside* the compounding, not subtracted at the end — a monthly-rebalanced book realises
essentially all gains short-term.

**No performance expectation is written here.** The pre-registration states the hypothesis and the
gates; the number is whatever it is.

## 4. Stage 3 — Overlays (each isolated, each one arm)

Added **one at a time**, never as a bundle, so attribution is possible:

| # | overlay | spec |
|---|---|---|
| **O1** | **Regime filter** | hold new entries when the universe index closes below its 200-DMA / 10-month MA (Clenow). *Note: the compendium calls this the highest-value overlay; its cited mechanism (Daniel-Moskowitz) is a **short-leg** beta phenomenon, so its value on a long-only book is an open empirical question, not an assumption.* |
| **O2** | **Volatility targeting** | Barroso-Santa-Clara: scale gross exposure by trailing 6-month realised book volatility to a constant annual target. De-gross and re-gross, capped. |
| **O3** | **Anti-speculation gate** | the compendium's scaled-turnover filter needs market cap, which the repo lacks. **Proxy: trailing 63d median delivery %** (3.5M rows held). Low delivery = intraday churn = speculative. Exclude the bottom band. |
| **O4** | **52-week-high proximity** | `close / max(high, 252)` as an alternative ranker (George-Hwang; Raju 2023 India) — tested as a **left-tail** lever, which is its documented role. |
| **O5** | **Turnover-conditioned horizon** | Medhat-Schmeling: double-sort on prior-month return × turnover. Reversal is predicted among **low**-turnover names, momentum among **high**-turnover. |
| **O6** | **Sector cap** | max 30% of book in any one `config.SECTOR_MAP` sector. |

## 5. Stage 4 — Validation gate

Every arm reports, via `nq.runner.research.adjudicate` plus the additions below:

- paired **block bootstrap** ΔSharpe CI (63-day blocks, 5000 draws) and **DSR** at the live
  `n_trials` (counter reset to 0 on 2026-08-07 — increment **before** each run)
- **CPCV** with purge + embargo (`nq/validation/cpcv.py`, horizon=embargo=21 for a monthly book)
- **PBO** — Probability of Backtest Overfitting (**to build**, `nq/validation/pbo.py`)
- **Monte Carlo trade resampling** for the drawdown and terminal-wealth *distribution* rather than
  one path (**to build**, `nq/validation/montecarlo.py`)
- **cost sensitivity at ±50%** — the compendium's deployability test: *"if the edge disappears
  under 1.5× costs, it is not deployable"*
- **per-regime slicing** (continuous-slice, never re-run): 2018 midcap crash · 2020 COVID ·
  2022 drawdown · 2024-25 correction
- **parameter neighbourhood** — lookback {3,6,9,12}m, top-N {20,30,50}, rebalance {weekly,
  fortnightly, monthly}; the chosen cell must sit on a plateau
- **benchmarks reported alongside, always**: equal-weight universe buy-and-hold, Nifty-50, and a
  matched **random-selection** control at the same turnover

## 6. Stage 5 — Capacity and forward

ADV participation capped at 5%; liquidity-bucketed slippage; then the winner is logged to the
independent model-wall stream (`nq/paper/model_wall.py`) for ≥2 quarters before any capital
question is opened.

---

## Build order

| # | deliverable | status |
|---|---|---|
| 1 | `nq/universe/` — PIT service, size bands, screens | to build |
| 2 | `nq/signals/` — `mom_12_1`, `high_52w`, `reversal_z`, `quality` as pure functions | to build |
| 3 | `nq/engine/rebalance_book.py` — periodic rebalance, top-N equal weight, buffer exit, `simulate`'s return contract | **the centrepiece** |
| 4 | `nq/validation/pbo.py`, `montecarlo.py` | to build |
| 5 | `research/0001-xsec-momentum/prereg.md` + runner | to build |
| 6 | repo reorganisation (`pipelines/`, `archive/`) | to build |

`rebalance_book` returns `{equity_curve, trades, metrics}` — the same contract `simulate` and
`signal_book` return — so it inherits the whole adjudication layer with no further work.
