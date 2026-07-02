# 0013 — The technical-analysis zoo at 63d (0079): oscillators dead, chart patterns lose to the slope, low-vol is the only lever (and it's a different strategy)

- **Status:** **KILL / family CLOSED at 63d** — now on real long-horizon evidence, not a v1 inference. One reframe: low-vol → the multi-sleeve fork.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0079-technical-signal-battery.md`](../../diagnostics/research/preregistry/0079-technical-signal-battery.md).
- **Type:** Stage A IC screen = MEASUREMENT (no trial); Stage B = 4 sole-ranker TRIALS (cumulative_n_trials 91 → 95).
- **Anchor:** pinned `baseline_v1`. Scripts: `scripts/screen_technical_ic.py`, `scripts/run_technical_battery.py`; raw `research/exports/technical_ic_0079.csv`, `technical_battery_0079.json`.

## Why this ran
The registry's technical kills were **v1** (chart-structure 0004 = 84f V1_FEATURES, INCONCLUSIVE) or a
**reasoned** LH reject (O-005). §11's own re-open condition for reversal is "IC evidence on the 63d label
specifically" — so this is the sanctioned test, not a relitigation.

## Stage A — IC screen (18 signals, cross-sectional rank-IC vs forward-63d return; base |IC|=0.062)
| Family | signals | mean IC | verdict |
|---|---|---|---|
| **Oscillators / reversal / indicators** | RSI, MACD-hist, Stochastic, Williams %R, CCI, Bollinger %b, MFI, OBV, ROC-21 | **≈ 0** (\|IC\| < 0.01, IC-IR < 0.1, ~50% days+) | **DEAD at 63d** |
| Trend / breakout | prox_52wh **+0.068 (beats base)**, dist_sma200 +0.052, roc_126 +0.047, roc_63 +0.030, donchian63 +0.022 | real, but same family as the base | → Stage B |
| Low-vol | rvol_63 **−0.044** (low vol → higher fwd return) | real, opposite family | → Stage B |

**The entire oscillator/reversal/momentum-indicator zoo has zero cross-sectional edge at 63d** — the
rigorous confirmation that RSI/MACD/Stochastic/etc. (what most "chart-pattern" swing traders watch) do
not predict the 63-day cross-section here. Not backtested (IC≈0 cannot rank → no trial spent).

## Stage B — sole-ranker backtests (base: Sharpe 0.667 / Sortino 0.836 / CAGR 15.5 / DD −46.3 / 22-26 Sh 0.570)
| signal | Sharpe | Sortino | CAGR | DD | ΔSharpe [CI] | DSR | 22-26 Sh | verdict |
|---|---|---|---|---|---|---|---|---|
| **prox_52wh** | 0.483 | 0.626 | 7.5 | −37.9 | −0.184 [−0.79,+0.34] | 0.07 | 0.400 | KILL |
| dist_sma200 | 0.221 | 0.276 | 2.3 | −54.5 | −0.446 [−0.94,−0.06] | 0.02 | −0.127 | KILL |
| roc_126 | 0.354 | 0.463 | 6.1 | −57.8 | −0.313 [−0.82,+0.10] | 0.04 | 0.111 | KILL |
| **rvol_63 (low-vol)** | **1.059** | **1.396** | 14.5 | **−32.5** | +0.392 [−0.28,+1.06] | 0.35 | **1.338** | KILL (uncertifiable) |

## Root-cause readout (REQUIRED)
- **Oscillators dead (IC≈0):** mean-reversion/oscillator signals key off short-term extremes that carry no
  information about the *multi-month* drift a 63d book harvests — exactly O-005's reasoned argument, now
  confirmed with 63d IC. No cross-sectional signal, so nothing to rank.
- **Chart/trend patterns lose despite real IC — the key lesson:** prox_52wh has *higher* IC than the slope
  yet a *far worse* portfolio (Sharpe 0.48 vs 0.67). **IC ≠ portfolio Sharpe.** Raw 52wh/ROC/SMA-distance
  rankings pick whipsaw-prone names; the 200-day *slope smooths the trend*, delivering better trade quality
  (fewer reversals, better excursions) even at marginally lower IC. This is *why* the incumbent wins — and
  it generalises the C4 horse-race (12-1/6-1/Donchian) to the chart-pattern family: the smoothed trend beats
  every raw technical formulation as a ranker.
- **Low-vol is the one strong signal — but it's not a chart pattern, it's a different STRATEGY.** As a sole
  ranker the low-vol factor looks excellent in-sample (Sharpe 1.06, DD −32.5, 2022-26 Sharpe 1.34) — the
  documented Indian low-vol anomaly — but ΔSharpe CI straddles 0 and DSR 0.35: **uncertifiable at ~34
  windows**, same wall as everything. KILL by the bar. This is O-006's factor (killed as a signal *blend*)
  showing real standalone strength — which is precisely the case for it as a **separate defensive sleeve**,
  not a ranker swap.

## Verdict
**The technical / chart-pattern family is CLOSED at 63d, on evidence:** oscillators have no IC; trend/
breakout patterns (incl. the 52-week-high) have IC but lose to the slope as rankers. No promotable
technical signal exists. The user's catch was right — this was never rigorously LH-tested; now it is.

## Next setup
- **Low-vol → the multi-sleeve fork.** rvol_63's standalone strength is the strongest in-repo evidence that
  a **defensive low-vol sleeve** (combined with momentum at the portfolio level, ERC) is the real
  diversification lever — exactly the `forward/prereg.md` §9 12-month fork. Not a ranker; a second book.
- **Do not re-test** oscillators/chart patterns at 63d unless a genuinely new label/universe emerges — the
  IC screen is the definitive answer for this horizon.
