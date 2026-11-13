# 2026-11-13 — 20-path check of the January candidates (train window)

**Tier:** EXPLORE. No screen row, no `n_trials` change, nothing changes live. Standing counts: screens 24 · sealed
opens 3 · n_trials 2. Same 20 paired paths as every ensemble (cost ±10bp, start in the first 20 trading days of 2019),
reported 2019-03-01..2024-06-30 as continuous slices, PIT membership, prices cut at 2024-06-30. Rule fixed before the
run: robustly better if p5 of the paired delta vs live is above 0, robustly worse if p95 is below 0.
Reproduce: `python pipelines/diagnostics/explore_ensemble_jan_candidates.py 20` → `2026-11-13_ensemble_jan_candidates.json`.

Live band (medians): Sharpe 1.25, CAGR 26.1%, MaxDD −37.5%.

| arm | ΔSharpe median [p5, p95] | paths better | ΔMaxDD pp median [p5, p95] (+ = shallower) | ΔCAGR pp | reading |
|---|---|---|---|---|---|
| h5 (four caps off), reference | +0.27 [+0.12, +0.71] | 20/20 | −1.9 [−5.6, +14.9] | +8.3 | Sharpe robustly better (third time) |
| **h5-30** (h5, per-name cap 30%) | **+0.34 [−0.10, +0.59]** | 18/20 | +4.5 [−3.0, +15.1] | +11.3 | higher median, shallower drawdown, **not robust** |
| skip if results within 4 weeks | −0.04 [−0.24, +0.32] | 9/20 | **+3.1 [+0.2, +13.2]** | −1.8 | drawdown robustly shallower; Sharpe inside noise |
| half size when Nifty < 40w SMA | +0.22 [−0.13, +0.37] | 16/20 | +3.9 [−2.4, +11.3] | +4.8 | inside noise on both |
| add half a unit at +1R (engine) | +0.00 [−0.03, +0.09] | 17/20 | +0.0 [−0.0, +4.1] | +0.1 | no effect |

Concentration, unperturbed run (largest position at entry, % of equity): live 22.0%, h5 49.2%, h5-30 30.5%, the
others ≤ 22%.

## Reading

- **h5-30 is the best median in any ensemble so far, but less robust than uncapped h5.** Capping a name at 30% raises
  the median Sharpe gain (+0.34 vs +0.27) and turns h5's slightly deeper drawdown into a shallower one (+4.5pp). It also
  widens the spread: 2 of 20 paths are worse than live, so its 5th percentile is −0.10 and it misses the bar uncapped
  h5 clears. That is now the subject of pre-registration 0151 (owner's arm choice), with this result disclosed.
- **The results filter is a drawdown dial, not an edge.** Skipping signals with results due inside 4 weeks gives a
  shallower drawdown on 19 of 20 paths, at no Sharpe gain. Its single-path 1.28 Sharpe was path luck.
- **Half size in weak markets** keeps more of the S1 drawdown benefit than the zero-size S1 at a smaller cost (S1 was
  −0.30 Sharpe, robustly worse). It lands inside noise on both measures.
- **Adding half a unit at +1R does nothing under the live caps.** With the 20% per-name cap, most positions are already
  near their limit at +1R, so the add is mostly blocked. The per-trade overlay's +201R (adds unrestricted) does not
  survive the capital book. It would only matter together with a looser per-name cap, which is h5-30's territory, and
  that combination was not run.

## Engine

`scaled_exit.add_at_r` / `add_frac` is a new cfg-gated research lever in `scripts/run_bhanushali_weekly_rank.py`. One add
of `add_frac` × the original rupee risk fills at the next open after a Friday close at or above +`add_at_r` R, before any
tranche is booked. The add stays inside the per-name notional cap and the cash on hand, and joins `sh0`, so later
tranches sell it in proportion. Off by default; both golden masters are byte-identical; `tests/test_add_on_strength.py`
covers absent-key identity, at most one add per trade, and the notional cap.
