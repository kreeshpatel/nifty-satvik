# Ingested digest — Options-OI signals for LEADING stress + tail-hedge construction

**Imported 2026-07-26** for the reopened defined-risk tail-hedge / vol-carry sleeve arc (overlay_registry
line 159; owner request after the 0100 coincident-IV hedge KILL). Evidence-weighted, adversarial. Judge
every signal below on **drawdown/stress, never as return-alpha** (methodology-synthesis: PCR/OI is
risk-context; PCR-as-alpha collides with our KILLs). **IC ≠ portfolio Sharpe** applies to all of these
(our 52-week-high / USD-beta / 0079 lessons).

## Bottom line
Most options/OI "signals" are **coincident or lagging** stress, not leading — which is exactly why the
0100 coincident IV-spike put-spread made drawdown worse (bought the richest volatility-risk-premium
protection *after* the move, into the recovery). The three worth testing as LEADING context:
1. **Put-SKEW steepening** (OTM-put richness vs ATM) — the **best academic claim to actually leading
   crashes** (Gao–Pan Option-Implied Crash Index; skewness-swap & IV-smirk studies). Buildable from our
   **bhavcopy wings** — we are NOT limited to the ATM-straddle proxy. Caveat: small, noisy R².
2. **IV term-structure slope** (front vs next-month ATM IV; backwardation = stress) — near-coincident, so
   its real value is a **"protection is already expensive, don't arm now" veto** and a monetization timer.
3. **VRP filter** (ATM IV − trailing realized vol) — not a trigger but a **veto**: high VRP = protection
   richest, do not buy. This is precisely the filter that would have blocked 0100.

**Construction verdict:** timed/event-armed ATM protection is the trap we hit. AQR: index-put tail hedges
have **negative long-run expected return, "more expensive when most needed."** CBOE **PPUT** (roll monthly
ATM puts) underperforms the unhedged index. A **put-spread truncates exactly the convex tail** you're
buying — the worst structure, and the worst thing to arm on a coincident spike (the 0100 case). The
defensible design is an **always-on, small, deep-OTM put ladder with disciplined monetization on spikes**
(Spitznagel/Universa ~0.5–1% of portfolio/yr; convex payoff, harvest richness rather than hold to expiry).
Adversarial flag: Universa's headline numbers are marketing-selected and path-dependent; the edge is as
much *monetization discipline* as strike choice. AQR's counter: a **positive-carry** de-risk (trend) beats
a **negative-carry** late option-buy — the general lesson even if we don't run trend.

## Leading-vs-lagging (condensed)
| Signal | Leads/Lags | Note |
|---|---|---|
| **Put-skew steepening** | **Leading (best-evidenced)** | Gao–Pan CIX; small noisy power; build from wings |
| IV term-structure backwardation | Near-coincident | inverts *during* selloffs; use as veto/monetize timer |
| VRP (IV − realized) | Filter, not trigger | high = protection richest → don't arm (blocks 0100) |
| India-VIX *rate-of-rise* | Marginally leading | better than the *level* (which is where 0100 went wrong) |
| India-VIX level | Coincident/lagging | predicts realized vol, not returns; it reacts |
| PCR extremes (index) | Lags/weak/contrarian | contaminated by delta-hedging flow; **dead as alpha (our prior)** |
| OI buildup (put write vs buy) | Coincident, folklore | can't separate writing vs buying from OI alone |
| Max-pain gap / pinning | ~No predictive power | expiry-week micro-effect only; **control/null** |

## Concrete testable signals (from our fields + wings)
| # | Signal | Formula | Stress sign | Confidence |
|---|---|---|---|---|
| S1 | IV term slope | `atm_iv_front − atm_iv_next` | >0 (backwardation) | Med (veto/timer) |
| S2 | **Put-skew** | `otm_put_iv(≈−5%) − atm_iv` (or put/call wing premium ratio) | rising/high | **Med-high lead** |
| S3 | VRP veto | `atm_iv − realized_vol_20d` | high = DON'T buy | Med (the 0100 filter) |
| S4 | IV rate-of-rise | `atm_iv_t − atm_iv_{t−k}` | >0 rising = fear building | Low-med |
| S5 | PCR tail fade | `z(pcr)`, act only \|z\|>2 | very high = fear peak (fade) | Low (dead-as-alpha) |
| S7 | Max-pain gap | `(spot − max_pain)/spot` | ~0 | Very low (control) |

## Sources
PCR (mixed/contrarian): MDPI Econometrics 2019; ResearchGate PCR-forecasting; ECTAP. IV term structure /
VIX backwardation: Macrosynergy; CMRA/Niculescu; RavenQuant. Skew/smirk as crash lead: **Gao–Pan CIX**
(saif.sjtu.edu.cn/junpan/CIX.pdf); JFQA skewness-swap; ScienceDirect IV-smirk & GFC. Max-pain (conditional):
Strike.money; ApexVol. India VIX: NSE Working Paper 9; ResearchGate India-VIX–Nifty. Tail-hedge
construction: Institutional Investor (Universa/PPUT/deep-OTM); AQR "Tail Risk Hedging: Put vs Trend";
Taylor & Francis 2025 trend+tail overlays. Internal vibe-trading skills: `hedging-strategy`,
`sentiment-analysis` (PCR bands = folklore, not evidenced).

**Folklore flags:** PCR fixed bands, PCR×VIX quadrants, put-write-vs-buy OI reads, max-pain distance =
practitioner lore, weakly/not evidenced. **Best lead:** put-skew (S2). **Most decision-relevant:** VRP
veto (S3) + term-slope (S1) — they encode *why* 0100 failed and *when* protection is worth buying at all.
