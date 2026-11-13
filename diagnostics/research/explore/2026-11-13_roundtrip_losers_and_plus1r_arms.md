# 2026-11-13 — Round-trip losers, and what to do at +1R

**Tier:** EXPLORE (`docs/PROCESS_TIERS.md`). No screen row, no `n_trials` change, nothing changes live.
Standing counts: screens 24 · sealed opens 3 · n_trials 2. History window 2019-01-01..2024-06-30, PIT membership,
prices cut at 2024-06-30 and asserted. Live is the 55-trade record from 2026-07-06, prices to 2026-11-11.

Reproduce:
- `python pipelines/diagnostics/explore_plus1r_arms.py` → `2026-11-13_plus1r_arms.json` (round-trip counts, single-path arms)
- `python pipelines/diagnostics/explore_ensemble_plus1r_arms.py 20 [week_high]` → `2026-11-13_ensemble_plus1r_arms[_week_high].json`
- `python pipelines/diagnostics/explore_live_replay_plus1r.py` → `2026-11-13_live_replay_plus1r.json`

## 1. Round-trip losers

A round-trip loser is a trade that reached +1R and still exited at the full stop.

| | basis for "+1R" | count | share of full stops | R on them | R given back from peak |
|---|---|---|---|---|---|
| history (196 full stops) | Friday close | 11 | 5.6% | −19.2 | 34.2 |
| history | intraweek high | 48 | 24.5% | −73.3 | 140.8 |
| live (27 full stops) | Friday close | 1 | 3.7% | −1.2 | 2.4 |
| live | intraweek high | 6 | 22.2% | −8.2 | 16.0 |

Almost every round-trip loser touched +1R intraweek but never closed a week there. On a Friday-close basis the
problem is small: 11 trades in 5.5 years.

## 2. Big winners that dipped back first

History has 101 trades closing at or above +2R, worth +497R (76% of the book's 650R).

| after first touching +1R, the trade later… | big winners | their R |
|---|---|---|
| traded back to +0.25R or lower intraday | 57 (56%) | 271 |
| closed a Friday at or below entry | 19 (19%) | 69 |
| closed a Friday at or below −0.5R | 5 (5%) | 16 |

Live, 6 trades are at or above +2R (4 still open, marked to market). 4 of them traded back to +0.25R or lower after +1R,
and 1 closed a Friday at or below entry.

A breakeven stop on the Friday close would save at most the 19.2R of the 11 close-basis round-trippers. It would also
stop out 19 big winners worth 69R before they ran. That arithmetic is why the stop-raising rules do not win.

## 3. The +1R rules on the current live exit

Uncapped = per-trade book. The 20-path paired check uses the same rule as every ensemble, fixed before the run:
robustly better if p5 of the paired delta vs live is above 0, robustly worse if p95 is below 0. Live band: Sharpe 1.25,
CAGR 26.1%, MaxDD −37.5% (medians). Live replay = all 55 live trades, open ones marked; the base replay reproduces the
closed record (−45.7R simulated against −46.6R recorded).

| rule | uncapped ΣR (live 650) | 20-path ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp median | ΔCAGR pp | live replay ΔR |
|---|---|---|---|---|---|---|
| breakeven at +1R | 632 | +0.15 [−0.04, +0.35] | 85% | +1.6 | +1.0 | +1.7 |
| stop to −0.5R at +1R | 646 | +0.00 [−0.33, +0.35] | 50% | +1.0 | −1.7 | +0.9 |
| sell 20% at +1R (20% at +2R, rest unchanged) | 630 | +0.09 [−0.15, +0.42] | 60% | +3.0 | +0.8 | +0.5 |
| **first 40% at +1R instead of +2R** | 609 | **+0.22 [+0.004, +0.34]** | 95% | +1.2 | +5.4 | +1.0 |
| trail 1R behind the peak after +1R | 388 | −0.36 [−0.53, −0.13] | 0% | +1.3 | −9.7 | −1.7 |
| trail 1.5R behind after +1.5R | 491 | +0.11 [−0.04, +0.33] | 90% | +0.9 | +1.9 | +0.2 |

### The stop-raising rules on the week's real high

The engine arms its ratchets from the highest **week-end session** high, so a week that touched +1R on a Wednesday and
closed lower never arms them. That is not how a trader moves a stop. A new cfg-gated lever,
`scaled_exit.ratchet_peak="week_high"`, arms them from the week's full high instead. It is off by default and the golden
masters are unchanged.

| rule, armed on the week's high | uncapped ΣR | 20-path ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp | live replay ΔR |
|---|---|---|---|---|---|
| breakeven at +1R | 607 | −0.01 [−0.28, +0.42] | 45% | +1.7 | +6.3 |
| stop to −0.5R at +1R | 644 | −0.18 [−0.38, +0.44] | 15% | +1.0 | +3.8 |
| trail 1R behind after +1R | 339 | −0.42 [−0.59, −0.30] | 0% | +5.6 (robust) | +5.3 |
| trail 1.5R behind after +1.5R | 440 | −0.17 [−0.31, +0.28] | 15% | +0.4 | +3.2 |

## Reading

- **Round-trip losers are real but mostly an intraweek-high phenomenon.** On the weekly close the book acts on,
  they are about 6% of full stops. The R they give back is smaller than the R the big winners earn after dipping
  through the same zone.
- **Raising the stop does not help once it is measured the way it would be traded.** Armed on the week's real high,
  breakeven at +1R falls from +0.15 to −0.01 Sharpe, and every stop-raising rule is inside noise or worse. The
  live-replay gains (+3 to +6R over 55 trades) are one falling-market regime. That is the trap 0148 warned about, and
  history does not back it.
- **Trailing 1R behind the peak is robustly worse on both peak definitions.** It cuts Sharpe on every path and
  per-trade R by about 40%. Trend runners need room.
- **Taking the first 40% at +1R instead of +2R is the one arm that clears the bar, by a hair** (p5 +0.004, 19 of 20
  paths). It raises CAGR (+5.4pp median) but costs 6% of per-trade R and barely moves the drawdown. It works by freeing
  capital sooner, the same channel as h5 and the half-size throttle. Its live-replay effect is small (+1.0R).
  The 2026-11-03 single-path run of "first 40% at +1.5R" (−4% per-trade, +2.3R live) did not look like a lead.
  Treat this as a candidate to pre-register next to h5, not as a finding.
- **Cheapest next tests:** the first-tranche level as a short sweep (+1.0 / +1.25 / +1.5R) on the 20 paths, to tell
  whether +1R is a plateau or a spike; and the first-tranche rule combined with h5, since they act through the same
  channel and may not add.

## Addendum: first-tranche level sweep (owner request, same day)

Same 20 paired paths and reading rule. The 40% first target is moved from +2R to each level, and everything else
stays live. Reproduce with `python pipelines/diagnostics/explore_ensemble_plus1r_arms.py 20 tp1_sweep` →
`2026-11-13_ensemble_plus1r_arms_tp1_sweep.json`; per-trade and capped single path with
`python pipelines/diagnostics/explore_plus1r_arms.py tp1_sweep` → `2026-11-13_tp1_sweep.json`.

| first 40% at | uncapped ΣR (live 650) | 20-path ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp median [p5, p95] | ΔCAGR pp median | live replay ΔR |
|---|---|---|---|---|---|---|
| +1.0R | 609 | +0.22 [+0.004, +0.34] | 95% | +1.2 [−6.2, +10.9] | +5.4 | +0.8 |
| +1.25R | 620 | +0.06 [−0.24, +0.36] | 55% | +1.1 [−15.9, +12.8] | +0.2 | −0.5 |
| +1.5R | 625 | +0.08 [−0.17, +0.23] | 60% | +1.5 [+0.2, +10.7] | +1.4 | −1.5 |

The live replay was re-run on prices to 2026-11-12; its base is −20.2R.

**Reading: +1R is a spike, not a plateau.** Moving the target a quarter-R either side drops the gain from +0.22 to
+0.06–0.08 and puts it inside path noise. A real effect of taking money off the table earlier should fade smoothly as
the level rises; this one falls off a cliff between +1.0R and +1.25R. Combined with the marginal p5 (+0.004), the +1R
arm is best read as a fit to this path set. It does not earn a pre-registration on this evidence. +1.5R's drawdown band
sits just above zero, which is one band out of many read here and is not a lead. h5 remains the only candidate that
holds in every ensemble run so far.
