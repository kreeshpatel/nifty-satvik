# Finding 0103 — The momentum↔low-vol regime SWITCH is not learnable OOS; the STATIC blend dominates (MEASUREMENT, 0 trials)

**Type:** MEASUREMENT / feasibility go-no-go — no PROMOTE/KILL on the honest base, **no trial spent**
(n_trials stays 131). Harness `scripts/diag_regime_sleeve_learnability.py`; sleeves reproduced exactly as
pre-reg 0081 (r_mom = frozen base, r_lv = low-vol sole-ranker O-016), cached to
`research/exports/sleeve_daily_returns.csv`. Judged OOS only (owner rule).

## Question
Owner wants an adaptive ML "switch/dial" that tilts between the momentum and low-vol sleeves as the market
changes. Go/no-go BEFORE building any model: does observable PIT regime state predict which sleeve wins
next quarter well enough that a **walk-forward switch beats the fixed inverse-vol ERC** (0081) out-of-sample?

## Result — a clear NO for the switch, a clear YES for the static blend
**(A) No regime feature predicts the sleeve winner.** Spearman IC of each regime feature vs forward-63d
(mom−lv) relative return is **noise-level**: mkt_vol −0.09, mkt_trend +0.08, rel_mom63 −0.08, IV +0.04,
term −0.03, skew −0.00, vol-ratio +0.05. Signs are *directionally sensible* (high vol → low-vol wins; trend
→ momentum wins) but far too weak to time.

**(B) Every walk-forward switch LOSES to the fixed blend OOS** (2019-09→2026-06, post-2y burn-in):

| book | OOS Sharpe |
|---|---|
| low-vol alone | **+1.24** |
| **fixed ERC (0081)** | **+1.18** |
| fixed 50/50 | +1.10 |
| SWITCH vol-regime | +1.00 (loses) |
| SWITCH best-IC-feature | +0.80 (loses) |
| momentum alone | +0.86 |
| SWITCH trailing-Sharpe | +0.69 (loses) |

## Conclusion
The tilt is **not learnably better than static risk-parity.** Regime features carry ~0 forward IC for the
sleeve winner, and all three transparent switch rules underperform the fixed ERC OOS. **This settles the ML
question by the program's own logic:** if simple, low-parameter regime rules can't beat a static blend on
~37 independent windows / ~5 regime episodes, a higher-parameter ML model on the *same* sample cannot —
it would only overfit (0102 at strategy scale; the five regime-gate KILLs O-001/A5/0056/0086/0090 are the
same lesson). A softer/continuous tilt is no rescue: with ~0 signal it converges to the fixed blend.

**But the owner's underlying instinct is confirmed and valuable:** combining momentum + low-vol IS better
all-weather — the fixed ERC (+1.18) and low-vol weight beat momentum-alone (+0.86) robustly, no timing
needed. The honest reframe: **you defeat non-stationarity you can't forecast by DIVERSIFICATION, not by
prediction.** The static complementary blend is the win; the regime *timing* on top is the part the data
does not support.

## Decision
- **Do NOT build the regime-switching ML model.** It is an overfit machine on this sample; the measurement
  pre-refutes it (as the OI screen pre-refuted the hedge triggers).
- **DO route the fixed momentum×low-vol ERC blend (0081) to the forward wall** — it is the real, already-
  registered multi-sleeve edge the switch was reaching for. Certification is forward-wall/OOS, not in-sample.
- ML is not dead program-wide: the sanctioned learning avenue remains the **per-trade conviction model**
  (within-selection quality, judged forward — `skills/conviction-features`), which does not require
  forecasting the regime.

## Assets banked
Cached sleeve return series (`sleeve_daily_returns.csv`), the regime-feature substrate, and the walk-forward
learnability harness (re-runnable for any future sleeve pair or feature set).
