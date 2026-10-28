# 2026-10-23 — Live-switch ablation: which of the five live-only switches carries the live-vs-bridge gap

**Tier:** EXPLORE / MEASURE (`docs/PROCESS_TIERS.md`, tiers 0-1). No pre-registration, no screen row, no
`n_trials` change. Descriptive: it adopts nothing and recommends no change to the live config. Any change to
the live config is a CONFIRM-tier decision for the 2027-01-01 review (`forward/prereg_swing.md` §4 and §12).

**Standing counts (read from the ledgers by the script):** screens **23** · sealed opens **3** · n_trials **2**.
Unchanged by this note.

**Reproduce:** `python pipelines/diagnostics/explore_live_switch_ablation.py` (about 6 minutes, 13 engine runs)
writes `2026-10-23_live_switch_ablation.json` beside this note. Code at `4934d66`, data vintage 2024-06-28.

**Train only.** Every price series is cut at 2024-06-30 by `nq.lab.runs.cut_universe` before the engine sees it,
and the cut is asserted (last bar seen 2024-06-28). Window 2019-01-01..2024-06-28, ₹10L, PIT membership. Nothing
in 2024-07-01..2026-06-30 is read; the sealed judge log is not touched. All runs go through `nq.lab.runs.replay`
(the bridge's own plumbing) except run (i); the lab multiplicity meter was pointed at a scratch file so the
repo's `lab_runs.jsonl` is untouched.

**Manifest labels.** (a) **LIVE BOOK** (replay exception `ca_hold_drop`, the standing one). Every other run is
**NOT LIVE BOOK**, differing on exactly the switches reverted (the manifest names the exit switch `scaled_exit`).
(g) differs on all five and reproduces the bridge. (i) is NOT LIVE BOOK (`a_grade=filter_before_rank`;
`replay` has no such key, so it is a direct `R94.backtest` call, parity-checked: the same call with the default
A-set reproduces the control NAV exactly).

**R-sanity rule (degenerate stops).** Per-trade mean R is reported both raw and with degenerate-stop trades
excluded (initial risk `(entry - stop0)/entry` below 0.5% of entry; the rule declared in `e3eae32`, mirrored
inline because `nq/lab/stats.r_sanity_flags` is not on main yet; |R| above 20 is a review flag, never an
exclusion). **All 13 capped books contain zero degenerate-stop trades**, so raw and excluded means are identical,
as the degenerate-stop note anticipated for capped books (the VMART -389.75R sits in the uncapped ledger only).
NAV-based metrics (Sharpe, CAGR, MaxDD) are untouched by the rule.

## Results (full window; Sharpe/Sortino daily, ddof 1, rf 0; CAGR calendar; sub-periods are continuous slices of the one full run)

Deflated Sharpe = raw minus the expected-max Sharpe of **13** configs (this study's count), via
`nq.lab.runs.deflated_sharpe` (per-63-day-window basis); the probability form is in parentheses.

| run | Sharpe | deflated (P) | Sortino | CAGR | MaxDD | Calmar | trades | avg seats | Sharpe 2019-21 | Sharpe 2022-24H1 | worst year | mean R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **a. live (control)** | **1.025** | 0.28 (0.72) | 1.31 | 20.5% | −40.1% | 0.51 | 77 | 7.06 | 1.03 | 1.03 | 2022 −3.9% | +1.29 |
| b1. no ext_cap | 1.247 | 0.50 (0.85) | 1.64 | 26.0% | −38.0% | 0.68 | 78 | 8.16 | 1.39 | 1.05 | 2022 −9.1% | +1.59 |
| b2. grade gate off | 1.266 | 0.52 (0.86) | 1.63 | 25.7% | −40.1% | 0.64 | 84 | 8.24 | 1.04 | 1.56 | 2019 +3.8% | +1.27 |
| b3. notional cap default | 1.242 | 0.50 (0.85) | 1.63 | 28.5% | −39.5% | 0.72 | 65 | 6.59 | 1.42 | 1.00 | 2022 +2.0% | +1.58 |
| b4. risk cap default | 1.221 | 0.48 (0.84) | 1.51 | 24.6% | −36.4% | 0.68 | 87 | 8.71 | 1.29 | 1.13 | 2022 +3.8% | +1.28 |
| b5. engine-default exit | 1.086 | 0.34 (0.76) | 1.43 | 21.7% | −36.3% | 0.60 | 142 | 4.50 | 0.89 | 1.33 | 2024H1 +3.9% | +0.45 |
| **g. all five reverted (bridge)** | **1.503** | 0.76 (0.93) | 1.86 | 35.9% | −42.3% | 0.85 | 157 | 5.98 | 1.06 | 2.12 | 2020 +11.5% | +0.60 |
| h1. only ext_cap live | 1.382 | 0.64 (0.90) | 1.88 | 30.0% | −31.0% | 0.97 | 128 | 4.79 | 1.11 | 1.73 | 2021 +4.1% | +0.61 |
| h2. only grade gate live | 1.474 | 0.73 (0.93) | 1.87 | 35.5% | −42.3% | 0.84 | 149 | 5.65 | 1.22 | 1.82 | 2024H1 +20.1% | +0.62 |
| h3. only notional cap live | 1.190 | 0.45 (0.82) | 1.54 | 26.4% | −35.4% | 0.75 | 169 | 6.29 | 0.75 | 1.76 | 2020 +7.7% | +0.50 |
| h4. only risk cap live | 1.064 | 0.32 (0.75) | 1.40 | 25.1% | −45.3% | 0.55 | 126 | 4.21 | 0.85 | 1.37 | 2020 −4.5% | +0.56 |
| h5. only config-P exit live | **1.679** | 0.94 (0.96) | 2.15 | 42.0% | −34.5% | 1.22 | 87 | 10.28 | 1.68 | 1.67 | 2024H1 +21.1% | +1.49 |
| i. live + D6 filter-before-rank | 1.275 | 0.53 (0.86) | 1.65 | 27.3% | −40.1% | 0.68 | 85 | 7.98 | 1.01 | 1.64 | 2022 −1.3% | +1.48 |

(2024H1 is a half-year; "avg seats" is the mean number of distinct names held per session over the window,
counting empty days as zero. Sub-period MaxDDs, year-by-year returns, per-run configs and hashes are in the JSON.)

(g) reproduces the bridge: 1.503 / 35.9% / −42.3% (the earlier note rounds the MaxDD to −42.4%) / 157 trades.

## Attribution

All deltas below are single-replay point estimates; read each with the ~0.2 Sharpe path-noise caveat.

| switch | Δ Sharpe, revert one from live | Δ MaxDD (pp) | Δ Sharpe, keep only this one live (vs all-reverted) | Δ MaxDD (pp) |
|---|---|---|---|---|
| ext_cap | +0.22 | +2.1 | −0.12 | +11.4 |
| grade gate | +0.24 | 0.0 | −0.03 | 0.0 |
| max_notional_pct | +0.22 | +0.6 | −0.31 | +7.0 |
| max_risk_pct | +0.20 | +3.7 | −0.44 | −3.0 |
| config-P exit | +0.06 | +3.8 | **+0.18** | +7.8 |
| sum of the five | +0.94 | +10.2 | −0.73 | +23.2 |
| all five together (gap) | **+0.48** | −2.2 | | |

(Positive MaxDD delta = shallower drawdown. D6 filter-before-rank on the live book: ΔSharpe +0.25, ΔCAGR +6.8pp,
MaxDD unchanged at −40.1%.)

1. **No single switch carries the gap.** Reverting any one of ext_cap, the grade gate, the notional cap or the
   risk cap lifts Sharpe by a similar +0.20 to +0.24; the exit is the odd one out at +0.06. Each of those is
   inside the ~0.2 path noise on its own. Only the combined reversal (+0.48) is comfortably larger.
2. **The effects are not additive; they are sub-additive by about half.** The five one-offs sum to +0.94
   Sharpe but all five together give +0.48 (interaction −0.46; CAGR +24.1pp summed vs +15.4pp together). The
   four "cap-like" switches are largely redundant with one another: each blunts the same large winners, and
   removing the first recovers most of the loss.
3. **The live exit is not a drag in isolation; the live exit combined with the live caps is.** Keeping only
   the config-P exit and reverting the four caps gives the best book in the study (1.679 / 42.0% / −34.5%,
   Calmar 1.22, 87 trades), above the bridge by +0.18 Sharpe. Keeping only the risk cap live is the worst
   (1.064, MaxDD −45.3%, Δ −0.44 vs the bridge). That is, most of the live shortfall appears when the
   scaled exit and the caps are stacked. This is one path per config and the +0.18 is within path noise, so
   it is a lead, not a finding.
4. **MaxDD: no switch is shown to buy drawdown protection at this resolution.** Reverting any one switch from
   the live book never deepens MaxDD (it is flat or shallower by 0.0 to 3.8pp), and the live book's own
   2022-24H1 drawdown (−25.2%) is deeper than the bridge's (−17.8%). Reverting all five deepens the full-window
   MaxDD by only 2.2pp (−40.1% to −42.3%), while CAGR rises 15.4pp. In the leave-one-in view, ext_cap (+11.4pp),
   the config-P exit (+7.8pp) and the notional cap (+7.0pp) each give a shallower drawdown than the all-reverted
   book (−31.0%, −34.5%, −35.4% vs −42.3%), so a defensive effect shows up for those three when taken alone, but not
   once they are stacked, and it comes bundled with a CAGR cost for ext_cap (−5.9pp) and the notional cap (−9.5pp).
   The grade gate is MaxDD-neutral in both directions, consistent with the registry's reading of A-only as a
   defensive variant that is not a return edge. The −40.1% / −42.3% troughs are the same 2020 episode in every
   book.
5. **D6 filter-before-rank** (seat waste on alias duplicates and non-members) lifts the live book by +0.25
   Sharpe and +6.8pp CAGR (85 vs 77 trades, 2022-24H1 Sharpe 1.64 vs 1.03) at unchanged MaxDD. It is the one
   change here that adds return without touching a risk switch, and the same size as any single revert. Still one
   path.

## Guardrails (read before quoting anything above)

- **In-sample, trend-heavy window.** 2019-01..2024-06 is one regime sample with one 2020 drawdown. The bridge's
  2022-24H1 Sharpe of 2.12 is what the earlier note flagged as unmatched by the record's sealed-inclusive 2022-26 slice.
- **Resolution.** ΔSharpe half-width is about 0.59 (n_eff about 37), plus about 0.2 single-replay path noise
  (`2026-10-20_batch.md`: +50bp cost raised CAGR by 4.6pp). Every one-off delta here (0.06-0.24) is below that
  resolution; so is the +0.18 exit-alone-in lead. The all-five gap (+0.48) is below the half-width too.
- **Deflation.** Deflating by this study's 13 configs removes about 0.74 Sharpe (the live 1.025 becomes 0.28);
  that is the lab's documented proxy, not a trial on the program ledger.
- **Law VII.** Robustness bought with return is a risk preference, not a defect. The caps and the A-only gate
  cost return here; whether that is a price worth paying is the owner's call, not a finding of this note.
- **Not a recommendation.** The bridge and every leave-one-in book is NOT LIVE BOOK. Any change to the live
  config is a CONFIRM-tier decision (full method, pre-registration, `n_trials` incremented, sealed read) for the
  2027-01-01 review (`forward/prereg_swing.md` §4 and §12). `forward/*.md` is not edited here.
- **Cheapest test that would change the answer** (not run): repeat (h5) and (g) under a cost/slippage perturbation
  set and a shifted start date to get a path-noise band per config, then see whether the exit-alone-in lead survives.
