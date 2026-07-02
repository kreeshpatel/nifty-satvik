# 0019 — Fundamentals-depth IC probe: revenue-growth is a real orthogonal signal, but it's ONE feature (not a learner's worth) and sits at the uncertifiable-tilt magnitude

- **Status:** **MEASUREMENT** (cross-sectional IC probe, no trade decision → no n_trials cost, per research-log). The go/no-go gate before building the learning-bot conviction model (Parts 4-6 of `docs/learning_bot/`).
- **Date:** 2026-07-03. Script `scripts/screen_depth_ic.py`. Data: `data/fundamentals_pit_depth.pkl` (653 names — 496 current fetched + 211 delisted from cache — built PIT-clean by `scripts/scrape_screener.py --mode all`, the Part-1.2 depth parser). 652,109 eligible feature-rows.

## Question
Do the PIT-clean fundamentals-depth features (Part 2) carry 63-day cross-sectional signal the price doesn't —
enough to justify a multi-feature learner? (The disciplined "train on new data" gate, mirroring the macro
probe 0016/0017.)

## Result — one feature is real, six are noise
| depth feature | mean IC | IC-IR | read |
|---|---|---|---|
| **rev_yoy** (revenue YoY growth) | **−0.0360** | **−0.390** | **REAL** (|IC| ≈ 0.58× base sma200_slope 0.062) |
| op_margin_delta | −0.0147 | −0.194 | weak |
| np_yoy / eps_yoy | −0.009 / −0.007 | ~−0.12 | ~0 |
| op_to_assets (Novy-Marx proxy) | −0.0014 | −0.009 | dead |
| op_margin / asset_turnover | +0.006 / −0.006 | ~±0.05 | dead |

**Robustness of rev_yoy (the artifact check — guilty until cleared):**
| slice | IC | IR | reading |
|---|---|---|---|
| ≥2019 (trusted folds) | **−0.0400** | −0.445 | **stronger** in the trusted period |
| 2022-2026 (live regime) | **−0.0359** | −0.429 | holds live |
| pre-2019 (survivor-biased) | −0.0137 | −0.134 | *weaker* pre-2019 |
| current names only | **−0.0280** | −0.273 | holds on tradeable names |
| delisted names only | −0.0885 | −0.487 | strongest among failed names |

## Verdict — the signal is REAL, but it is not a learner and its tradeable size is uncertifiable-tilt class
1. **Not an artifact.** rev_yoy is *stronger* in ≥2019 / 2022-26 and *weaker* pre-2019 — the opposite of a
   survivorship/restatement artifact (which would concentrate in the suspect pre-2018 slice). It survives on
   current-only names. So it clears the restatement/survivorship suspicion the truncation gate could not.
2. **Mechanism is credible.** Negative sign = **high revenue growth predicts underperformance** — the
   revenue-quality / growth-trap red flag (aggressive or unsustainable top-line growth reverts; strongest
   among delisted names, −0.089, i.e. companies that pumped revenue then failed).
3. **But there is no learner here.** 6 of 7 depth features are ~0 IC. A gradient/logistic learner on 1 real +
   6 noise features **overfits** (exactly the 0046/0025 failure). The "multi-way learning bot" the arc set out
   to build is **not supported by the data** — fundamentals-depth yields a *single* orthogonal feature.
4. **Tradeable magnitude ≈ the already-killed tilt level.** The current-names IC (−0.0280) is essentially the
   USD-sensitivity IC (−0.0295) that **KILLED as a rank tilt** in 0082 (IC ≠ portfolio Sharpe). Skeptical
   prior: a rev_yoy tilt/veto most likely lands UNDERPOWERED/KILL for the same reason.

## Root-cause readout (REQUIRED)
The arc's honest result: **orthogonal signals exist, but they are all ~half the base IC and none has monetized
as a portfolio overlay** — 52-week-high (0079, IC but loses as ranker), USD-sensitivity (0017 real → 0082 KILL
as tilt), and now revenue-growth (real, ≈USD magnitude). The pattern is consistent with the in-sample program
being *information-bound*, not *method-bound*: adding a real but small orthogonal feature does not clear the
~34-window certification wall, and stacking noise features around it (a "learner") only adds overfit. The
data does not support a rich fundamentals learner; it supports at most one more single-feature overlay bet.

## Next setup (owner decision)
- **Do NOT build the multi-feature learner** (Parts 4-6 as originally scoped) — only rev_yoy is real; the rest
  is noise the model would fit. This retires the "learning bot" as a multi-feature ML build.
- **rev_yoy earns at most ONE pre-registered single-feature trial** — a *quality veto* fits its negative sign
  (drop the highest-revenue-growth names from the momentum top-15, à la the 0078 residual veto / 0080 low-vol
  filter), or a rank tilt (à la 0082). **Honest prior: UNDERPOWERED/KILL** at −0.028, same wall as USD. If
  run, pre-register + increment n_trials first; crude-style artifact already excluded.
- **Or route rev_yoy to the forward wall** as a watched quality feature (portfolio-level, owner decision),
  never a frozen-cfg tilt on the spent in-sample budget.
- The offline learning-bot spine (Parts 1-2: PIT-clean depth data + features) is **banked and reusable** — it
  is the honest infrastructure; the probe just showed the payload is one feature, not a fleet.
