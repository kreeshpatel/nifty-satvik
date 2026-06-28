# 0061 — EXP-0: structure-overlay reality-check (does structure predict OUR outcomes?)

**Status:** PRE-REGISTERED (pass/kill fixed before running)
**Date:** 2026-06-23
**Arc:** per-stock-adaptive joint system (selection filter+rank + structural levels).
See the approved plan + `diagnostics/research/entry_exit_rr_research.md` (the simple-first finding).
**Harness:** `diagnostics/run_exp0_structure_overlay.py` + `_exp0_overlay_core.py` (7 unit tests).
CLOUD-ONLY (OHLCV/features absent locally), `REPRODUCIBLE_MODE=1`.

## Motivation
Before spending any engineering on a structural redesign, ask the cheapest possible question on the
trades we ALREADY take: **does chart structure relate to our realized outcomes at all?** If not, the
whole per-stock-adaptive thesis is dead for our system and we stop here for ~the cost of one backtest.
This is a *precondition probe*, not a promote decision — it only decides whether to BUILD Track B / A.

## Method
Run the production backtest (config.json, honest window). For each trade, overlay the structural
**support** (rolling-min of lows) and **resistance** (rolling-max of highs) at the entry date using
`chart_structure`'s exact lookahead-safe formula (`.shift(5).rolling(115)`), and the **structural R:R
= (resistance − entry)/(entry − support)**. Read the **exact logged `stop_price`** from the trade
ledger (it IS logged). Build the level series on a **tz-normalized** OHLCV index with a **split-scale
guard** (reject trades whose raw-OHLCV close diverges grossly from the cleaned entry price) and **skip
characterization** (a > 15% skip-fraction flags the verdict as possibly selection-biased).

## Hypotheses + PRE-COMMITTED pass/kill
- **SELECTION signal — GATES THE DECISION (Track B filter + rank):** structure predicts which picks
  worked. PASS iff **Spearman(R:R, return) ≥ 0.05** AND **top-minus-bottom R:R-bucket mean return > 0**
  AND **clean-vs-poor mean-return difference CI-low > 0** (clean = R:R ≥ median). The bootstrap CI-low>0
  is the binding condition; a lone Spearman of 0.05 cannot carry a pass.
- **STOP signal — CORROBORATING ONLY, never gates (informs whether to also build Track A):**
  recovery-conditioned. Among fixed-ATR (close-only) stop-outs, the fraction where a wider STRUCTURAL
  stop would have **held** (close never reached support during the hold) **AND** price **recovered**
  above entry within the time-stop window after the ATR exit. Corroborates Track A if ≥ 30%. This
  REPLACES the degenerate "stop above the 115-bar rolling-min support" metric, which is ~always-true for
  a momentum book (support sits months below an entry near the highs) and could fabricate a PASS — caught
  by the pre-run 3-verifier audit.
- **DECISION:** **PASS** (proceed — build Track B) iff the **SELECTION** signal fires; the stop arm only
  corroborates whether to also build Track A and **never gates**. **KILL** (stop) if the selection signal
  fails. Corroborating (not gating): the worst-PnL trades should have lower mean setup R:R.

## Caveats (acknowledged, do not over-read)
- **In-sample** (test window overlaps the model's 2010–2024 train) — EXP-0 is a *correlation* probe, not
  an OOS edge claim; the OOS verdict is EXP-1/2/3 (walk-forward + DSR + plateau).
- **Stop arm is corroborating-only** (recovery-conditioned) — the SELECTION arm alone gates the build,
  so a noisy stop arm cannot drive the decision. The exact logged `stop_price` is used (not reconstructed).
- Structural levels are at the **signal date T**; entry fills at **T+1 open** — a small basis mismatch.
- No DSR here (it's a precondition probe, not a promotion); the DoF-aware bars apply to EXP-1+.

## On PASS / on KILL
- **PASS:** proceed to pre-register + build EXP-1 (selection filter + rank) and EXP-2 (structural stop),
  flag-gated + golden-master-safe, then the EXP-3 arms walk-forward.
- **KILL:** the structural thesis does not relate to our trades — stop; the simple-first research already
  warned the level itself isn't alpha. Cheap, decisive, ~one backtest.
